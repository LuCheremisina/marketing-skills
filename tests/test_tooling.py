"""Safety properties of packaging and installation; no production systems are contacted."""
from __future__ import annotations
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import SkillError, frontmatter, json_write, sha256, tree_sha256
from validate import validate
from build_release import archive_bytes, build, payload_hash
from install import apply_install, existing_hash, plan_install, rollback, verified_payload, target_lock
from monitor_upstream import merge_resource, monthly_due, monitor, select_commit
from audit_public import audit, text_findings

def skill_text(ident, version="1.0.0", description=None):
    description = description or "Analyzes synthetic marketing evidence when the user requests an evidence-based report."
    return f'''---
name: {ident}
description: >-
  {description}

  It labels unavailable inputs without inventing evidence.
license: MIT
metadata:
  version: "{version}"
---
# Synthetic analysis

Read [reference](references/input.md) when its input schema is needed.
Methodologist / Методолог: Любовь Черемисина.
https://cheremisina.ru
https://cheremisina.online
https://github.com/LuCheremisina/marketing-skills
'''

def fixture(root, ids=("example-analysis",), version="1.0.0"):
    root.mkdir(parents=True, exist_ok=True)
    (root / "LICENSE").write_text("MIT License\nCopyright Synthetic Test\n")
    (root / "plugin.json").write_text('{"name":"marketing-skills","skills":"./skills"}')
    for ident in ids:
        folder = root / "skills" / ident
        (folder / "references").mkdir(parents=True)
        (folder / "scripts").mkdir()
        (folder / "SKILL.md").write_text(skill_text(ident, version))
        (folder / "references/input.md").write_text("# Input\nSynthetic rows with date, source and value.\n")
        (folder / "scripts/read_input.py").write_text("from pathlib import Path\nprint(Path(__file__).resolve().name)\n")
    return root

class ToolingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="marketing-skills-test-")
        self.base = Path(self.temp.name)
        self.root = fixture(self.base / "repository")
        self.output = self.base / "release"
        self.target = self.base / "installed"
        self.backup = self.base / "backups"

    def tearDown(self):
        self.temp.cleanup()

    def release(self):
        return build(self.root, self.output, "1.0.0")

    def test_multiline_yaml_blank_line_is_preserved(self):
        data, _, _ = frontmatter(self.root / "skills/example-analysis/SKILL.md")
        self.assertIn("It labels unavailable", data["description"])
        self.assertTrue(validate(self.root)["ok"])

    def test_yaml_duplicate_and_nonstring_metadata_rejected(self):
        path = self.root / "skills/example-analysis/SKILL.md"
        text = path.read_text()
        path.write_text(text.replace("name: example-analysis", "name: example-analysis\nname: duplicate"))
        self.assertFalse(validate(self.root)["ok"])
        path.write_text(text.replace('version: "1.0.0"', "version: 1"))
        self.assertFalse(validate(self.root)["ok"])

    def test_missing_dependency_resource_and_symlink_rejected(self):
        reference = self.root / "skills/example-analysis/references/input.md"
        reference.unlink()
        self.assertFalse(validate(self.root)["ok"])
        reference.symlink_to(self.root / "LICENSE")
        self.assertFalse(validate(self.root)["ok"])

    def test_catalog_hash_guards_frozen_baseline(self):
        folder = self.root / "skills/example-analysis"
        row = {"id": "example-analysis", "path": "skills/example-analysis", "version": "1.0.0", "content_sha256": tree_sha256(folder)}
        json_write(self.root / "catalog/skills.json", {"skills": [row]})
        self.assertTrue(validate(self.root)["ok"])
        (folder / "references/input.md").write_text("Changed methodology input\n")
        self.assertFalse(validate(self.root)["ok"])

    def test_archives_deterministic_and_include_all_runtime_files_and_license(self):
        first = self.release()
        hashes = {p.name: sha256(p.read_bytes()) for p in self.output.iterdir()}
        second_output = self.base / "release-again"
        build(self.root, second_output, "1.0.0")
        self.assertEqual(hashes, {p.name: sha256(p.read_bytes()) for p in second_output.iterdir()})
        with zipfile.ZipFile(self.output / first["skills"][0]["archive"]) as archive:
            self.assertEqual(set(archive.namelist()), {"example-analysis/SKILL.md", "example-analysis/LICENSE", "example-analysis/references/input.md", "example-analysis/scripts/read_input.py"})
        # Caches and private test fixture directories must never enter packages.
        (self.root / "skills/example-analysis/__pycache__").mkdir()
        (self.root / "skills/example-analysis/__pycache__/ignored.pyc").write_bytes(b"cache")
        self.assertEqual(first["skills"], build(self.root, second_output, "1.0.0")["skills"])

    def test_immutable_artifact_cannot_be_overwritten(self):
        self.release()
        (self.root / "skills/example-analysis/references/input.md").write_text("New schema\n")
        with self.assertRaises(SkillError):
            self.release()

    def test_referenced_evaluation_resources_are_packaged(self):
        folder = self.root / "skills/example-analysis"
        (folder / "evals").mkdir()
        (folder / "evals/synthetic.csv").write_text("channel,value\nexample,3\n")
        with (folder / "SKILL.md").open("a") as file:
            file.write("Read [synthetic QA fixture](evals/synthetic.csv) for the acceptance example.\n")
        manifest = self.release()
        with zipfile.ZipFile(self.output / manifest["skills"][0]["archive"]) as archive:
            self.assertIn("example-analysis/evals/synthetic.csv", archive.namelist())

    def test_backtick_missing_runtime_resource_and_excluded_dependency_rejected(self):
        folder = self.root / "skills/example-analysis"
        path = folder / "SKILL.md"
        original = path.read_text()
        path.write_text(original + "Read `evals/judge_prompt.md` before acceptance.\n")
        self.assertFalse(validate(self.root)["ok"])
        (folder / "tests").mkdir()
        (folder / "tests/private.md").write_text("Synthetic but excluded input\n")
        path.write_text(original + "Read [private dependency](tests/private.md).\n")
        self.assertFalse(validate(self.root)["ok"])

    def test_nested_reference_parent_path_resolves_to_packaged_resource(self):
        folder = self.root / "skills/example-analysis"
        (folder / "references/input.md").write_text("Use [helper](../scripts/read_input.py).\n")
        self.assertTrue(validate(self.root)["ok"])

    def test_previous_release_baseline_rejects_same_version_different_content(self):
        self.release()
        (self.root / "skills/example-analysis/references/input.md").write_text("Changed contract\n")
        with self.assertRaises(SkillError):
            build(self.root, self.base / "new-release", "1.1.0", self.output / "manifest.json")
        path = self.root / "skills/example-analysis/SKILL.md"
        path.write_text(path.read_text().replace('version: "1.0.0"', 'version: "1.0.1"'))
        self.assertEqual(build(self.root, self.base / "new-release", "1.1.0", self.output / "manifest.json")["skills"][0]["version"], "1.0.1")

    def test_same_library_release_changed_docs_across_directory_requires_release_bump(self):
        original = self.release()
        (self.root / "README.md").write_text("New public documentation; skill methodology unchanged.\n")
        with self.assertRaisesRegex(SkillError, "bump the library release version"):
            build(self.root, self.base / "changed-same-release", "1.0.0", self.output / "manifest.json")
        self.assertFalse((self.base / "changed-same-release").exists())
        next_release = build(self.root, self.base / "new-release", "1.1.0", self.output / "manifest.json")
        self.assertEqual(next_release["skills"], original["skills"])
        self.assertEqual(next_release["release_version"], "1.1.0")

    def test_release_output_cannot_be_under_vendor_root(self):
        with self.assertRaises(SkillError):
            build(self.root, self.root / "vendor/skills/release", "1.0.0")

    def test_complete_bundle_contains_public_cases_not_private_evidence(self):
        for name in ("AUTHOR.md", "THIRD_PARTY_NOTICES.md", ".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "examples/synthetic.md", "evals/cases.json", "evidence/private.json"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{}' if path.suffix == '.json' else "Public synthetic example\n")
        self.release()
        with zipfile.ZipFile(self.output / "marketing-skills-1.0.0.zip") as archive:
            files = set(archive.namelist())
            self.assertIn("AUTHOR.md", files)
            self.assertIn("THIRD_PARTY_NOTICES.md", files)
            self.assertIn("evals/cases.json", files)
            self.assertIn("examples/synthetic.md", files)
            self.assertIn(".claude-plugin/plugin.json", files)
            self.assertNotIn("evidence/private.json", files)

    def test_complete_source_and_minimal_plugin_global_markdown_links_resolve(self):
        fixtures = {
            "README.md": "[RU](README.ru.md) [Install](docs/INSTALL.md#usage) [Catalogue](catalog/skills.json) [Contribute](CONTRIBUTING.md)\n![Cover](assets/social-preview.png)\n",
            "README.ru.md": "[English](README.md) [Guide](docs/INSTALL.md)\n",
            "THIRD_PARTY_NOTICES.md": "[Policies](docs/third-party-sources.md)\n",
            "CONTRIBUTING.md": "[Install](docs/INSTALL.md)\n",
            ".gitignore": "__pycache__/\n",
            "docs/INSTALL.md": "# Install\n[Contribute](../CONTRIBUTING.md)\n",
            "docs/third-party-sources.md": "Original publisher notices.\n",
            "catalog/skills.json": json.dumps({"skills": []}),
            "assets/social-preview.png": "Synthetic image placeholder\n",
            "tests/public_test.py": "# Public regression fixture\n",
            ".github/workflows/verify.yml": "name: Synthetic verification\n",
        }
        for name, text in fixtures.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        original_skill = (self.root / "skills/example-analysis/SKILL.md").read_bytes()
        self.release()
        for filename in ("marketing-skills-1.0.0.zip", "marketing-skills-plugin-1.0.0.zip"):
            with zipfile.ZipFile(self.output / filename) as archive:
                names = set(archive.namelist())
                for name in names:
                    if name.endswith(".md") and ("/" not in name or name.startswith("docs/")):
                        text = archive.read(name).decode()
                        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                            parsed = urlsplit(target)
                            if parsed.scheme or not parsed.path:
                                continue
                            local = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(parsed.path)))
                            self.assertIn(local, names, f"{filename}:{name} -> {target}")
                if filename == "marketing-skills-1.0.0.zip":
                    for name in ("CONTRIBUTING.md", ".gitignore", "tests/public_test.py", ".github/workflows/verify.yml"):
                        self.assertIn(name, names)
                else:
                    readme = archive.read("README.md").decode()
                    self.assertIn("https://raw.githubusercontent.com/LuCheremisina/marketing-skills/main/assets/social-preview.png", readme)
                    self.assertIn("https://github.com/LuCheremisina/marketing-skills/blob/main/docs/INSTALL.md#usage", readme)
                self.assertEqual(archive.read("skills/example-analysis/SKILL.md"), original_skill)

    def test_vendor_plugin_has_separate_manifest_original_licenses_and_no_authored_skills(self):
        (self.root / "vendor").mkdir()
        manifest = {"name": "marketing-skills-vendor", "version": "1.0.0", "description": "Original publisher workflows; portable packaging.", "author": {"name": "Original publishers"}, "license": "Apache-2.0 AND MIT"}
        json_write(self.root / "vendor/plugin.json", manifest)
        (self.root / "THIRD_PARTY_NOTICES.md").write_text("Original publisher A — Apache-2.0; original publisher B — MIT.\n[Policies](docs/third-party-sources.md)\n")
        expected = {}
        for ident, license_name in (("vendor-apache", "Apache-2.0"), ("vendor-mit", "MIT")):
            folder = self.root / "vendor/skills" / ident
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_text(f'---\nname: {ident}\ndescription: Analyze synthetic input when an evidence report is requested.\nlicense: {license_name}\n---\nPreserve original methodology.\n')
            text = "Original " + license_name + " license and attribution\n"
            (folder / "LICENSE").write_text(text)
            expected["skills/" + ident + "/LICENSE"] = text
        result = self.release()
        self.assertTrue(any(row["kind"] == "licensed-vendor-plugin" for row in result["bundles"]))
        with zipfile.ZipFile(self.output / "marketing-skills-vendor-1.0.0.zip") as archive:
            files = set(archive.namelist())
            self.assertEqual(json.loads(archive.read("plugin.json"))["name"], "marketing-skills-vendor")
            for dirname in (".claude-plugin", ".codex-plugin"):
                native = json.loads(archive.read(dirname + "/plugin.json"))
                self.assertEqual(native["name"], "marketing-skills-vendor")
                self.assertEqual(native["author"]["name"], "Original publishers")
            self.assertIn("THIRD_PARTY_NOTICES.md", files)
            self.assertIn("https://github.com/LuCheremisina/marketing-skills/blob/main/docs/third-party-sources.md", archive.read("THIRD_PARTY_NOTICES.md").decode())
            self.assertFalse(any(name.startswith("skills/example-analysis/") for name in files))
            for name, text in expected.items():
                self.assertEqual(archive.read(name).decode(), text)
        with zipfile.ZipFile(self.output / "marketing-skills-1.0.0.zip") as archive:
            self.assertIn("vendor/plugin.json", archive.namelist())
            self.assertIn("vendor/.claude-plugin/plugin.json", archive.namelist())

    def test_transaction_lock_shared_between_backup_locations_and_symlink_target_rejected(self):
        self.release()
        plan = plan_install(self.output / "manifest.json", self.target, ["example-analysis"])
        with target_lock(self.target, self.backup):
            with self.assertRaises(SkillError):
                apply_install(self.target, self.base / "different-backups", plan)
        elsewhere = self.base / "elsewhere"
        elsewhere.mkdir()
        self.target.symlink_to(elsewhere)
        with self.assertRaises(SkillError):
            apply_install(self.target, self.backup, plan)

    def test_stable_release_selector_does_not_select_unstable_default_branch(self):
        source = {"repository": "example/vendor", "policy": "latest non-prerelease release", "ref": "main"}
        calls = []
        def fake_json(repository, endpoint):
            calls.append(endpoint)
            return {"tag_name": "v4.0.533", "draft": False, "prerelease": False} if endpoint == "releases/latest" else {"sha": "stable-commit"}
        with patch("monitor_upstream.github_json", side_effect=fake_json):
            commit, release = select_commit(source)
        self.assertEqual(commit, "stable-commit")
        self.assertEqual(calls, ["releases/latest", "commits/v4.0.533"])
        self.assertEqual(release["tag"], "v4.0.533")

    def test_dry_run_never_writes_target(self):
        self.release()
        plan = plan_install(self.output / "manifest.json", self.target, ["example-analysis"])
        self.assertEqual(plan[0]["action"], "install")
        self.assertFalse(self.target.exists())
        self.assertFalse(self.backup.exists())

    def test_tampered_archive_and_resource_allowlist_rejected(self):
        manifest = self.release()
        row = manifest["skills"][0]
        archive = self.output / row["archive"]
        original = archive.read_bytes()
        archive.write_bytes(original + b"changed")
        with self.assertRaises(SkillError):
            verified_payload(self.output / "manifest.json", row)
        archive.write_bytes(original)
        row["files"].pop("LICENSE")
        with self.assertRaises(SkillError):
            verified_payload(self.output / "manifest.json", row)

    def test_traversal_and_symlink_archive_rejected_even_with_matching_zip_checksum(self):
        manifest = self.release()
        row = manifest["skills"][0]
        malicious = archive_bytes({"example-analysis/../../outside": b"bad"})
        path = self.output / row["archive"]
        path.write_bytes(malicious)
        row["sha256"] = sha256(malicious)
        with self.assertRaises(SkillError):
            verified_payload(self.output / "manifest.json", row)
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            info = zipfile.ZipInfo("example-analysis/SKILL.md")
            info.create_system = 3
            info.external_attr = 0o120777 << 16
            archive.writestr(info, "../../outside")
        malicious = stream.getvalue()
        path.write_bytes(malicious)
        row["sha256"] = sha256(malicious)
        with self.assertRaises(SkillError):
            verified_payload(self.output / "manifest.json", row)

    def test_backup_and_rollback_restore_exact_previous_contents(self):
        self.release()
        installed = self.target / "example-analysis"
        installed.mkdir(parents=True)
        (installed / "SKILL.md").write_text(skill_text("example-analysis", "0.9.0"))
        (installed / ".profile.json").write_text('{"synthetic":true}')
        original = existing_hash(installed)
        plan = plan_install(self.output / "manifest.json", self.target, ["example-analysis"], {"example-analysis": original})
        journal = apply_install(self.target, self.backup, plan)
        self.assertEqual(existing_hash(installed), plan[0]["next_sha256"])
        self.assertNotIn(self.target, journal.parents)
        self.assertEqual(rollback(journal)["action"], "rollback-preview")
        rollback(journal, apply=True)
        self.assertEqual(existing_hash(installed), original)
        self.assertTrue((installed / ".profile.json").exists())

    def test_component_vs_lexical_path_order_install_and_rollback(self):
        folder = self.root / "skills/example-analysis"
        for subdir in ("api", "api-shield"):
            reference = folder / "references" / subdir / "README.md"
            reference.parent.mkdir(parents=True)
            reference.write_text("Synthetic " + subdir + " reference\n")
        # A leading hyphen sorts before slash in ZIP/payload lexicographic order.
        resource_map = {file.relative_to(folder).as_posix(): file.read_bytes() for file in folder.rglob("*") if file.is_file()}
        self.assertEqual(tree_sha256(folder), payload_hash(resource_map))
        self.release()
        installed = self.target / "example-analysis"
        installed.mkdir(parents=True)
        (installed / "SKILL.md").write_text(skill_text("example-analysis", "0.9.0"))
        (installed / ".local-profile.json").write_text('{"synthetic":true}')
        original = existing_hash(installed)
        plan = plan_install(self.output / "manifest.json", self.target, ["example-analysis"], {"example-analysis": original})
        journal = apply_install(self.target, self.backup, plan)
        self.assertEqual(existing_hash(installed), plan[0]["next_sha256"])
        self.assertTrue((installed / "references/api/README.md").is_file())
        self.assertTrue((installed / "references/api-shield/README.md").is_file())
        rollback(journal, apply=True)
        self.assertEqual(existing_hash(installed), original)
        self.assertTrue((installed / ".local-profile.json").exists())

    def test_user_changes_conflict_and_rollback_refuses_post_install_edits(self):
        self.release()
        plan = plan_install(self.output / "manifest.json", self.target, ["example-analysis"])
        journal = apply_install(self.target, self.backup, plan)
        baseline = {"example-analysis": existing_hash(self.target / "example-analysis")}
        (self.target / "example-analysis/references/input.md").write_text("User changes\n")
        plan = plan_install(self.output / "manifest.json", self.target, ["example-analysis"], baseline)
        self.assertEqual(plan[0]["action"], "conflict")
        with self.assertRaises(SkillError):
            rollback(journal, apply=True)

    def test_version_downgrade_refused_even_with_matching_reviewed_baseline(self):
        self.release()
        folder = self.target / "example-analysis"
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text(skill_text("example-analysis", "2.0.0"))
        current = existing_hash(folder)
        plan = plan_install(self.output / "manifest.json", self.target, ["example-analysis"], {"example-analysis": current})
        self.assertEqual(plan[0]["action"], "conflict")
        self.assertEqual(plan[0]["reason"], "version downgrade refused")

    def test_same_authored_version_changed_installed_content_refused(self):
        self.release()
        installed = self.target / "example-analysis"
        installed.mkdir(parents=True)
        (installed / "SKILL.md").write_text(skill_text("example-analysis", "1.0.0") + "Local methodology edit\n")
        current = existing_hash(installed)
        plan = plan_install(self.output / "manifest.json", self.target, ["example-analysis"], {"example-analysis": current})
        self.assertEqual(plan[0]["action"], "conflict")
        self.assertEqual(plan[0]["reason"], "authored version unchanged but installed contents differ")

    def test_backup_cannot_be_inside_skill_root(self):
        self.release()
        plan = plan_install(self.output / "manifest.json", self.target, ["example-analysis"])
        with self.assertRaises(SkillError):
            apply_install(self.target, self.target / "backups", plan)
        self.assertFalse(self.target.exists())

    def test_partial_swap_failure_restores_every_skill(self):
        fixture(self.root, ids=("second-analysis",))
        self.release()
        self.target.mkdir()
        before = {}
        for ident in ("example-analysis", "second-analysis"):
            folder = self.target / ident
            folder.mkdir()
            (folder / "SKILL.md").write_text(skill_text(ident, "0.9.0"))
            before[ident] = existing_hash(folder)
        plan = plan_install(self.output / "manifest.json", self.target, list(before), before)
        original_replace = os.replace
        def fail_second(source, destination):
            if str(source).endswith("second-analysis.new"):
                raise OSError("synthetic failed swap")
            return original_replace(source, destination)
        with patch("install.os.replace", side_effect=fail_second):
            with self.assertRaises(OSError):
                apply_install(self.target, self.backup, plan)
        self.assertEqual(before, {ident: existing_hash(self.target / ident) for ident in before})
        self.assertEqual(json.loads(next(self.backup.glob("*/transaction.json")).read_text())["status"], "failed-restored")

    def test_arbitrary_working_directory(self):
        original = Path.cwd()
        try:
            os.chdir(self.base)
            self.assertTrue(validate(self.root)["ok"])
            self.release()
            self.assertEqual(plan_install(self.output / "manifest.json", self.target, ["example-analysis"])[0]["action"], "install")
        finally:
            os.chdir(original)

    def test_monthly_utc_boundary_regular_february_and_leap_year(self):
        for moment in ("2026-09-30T17:00:00+00:00", "2026-02-28T17:00:00+00:00", "2028-02-29T17:00:00+00:00"):
            self.assertTrue(monthly_due(datetime.fromisoformat(moment)))
        self.assertFalse(monthly_due(datetime.fromisoformat("2028-02-28T17:00:00+00:00")))
        self.assertFalse(monthly_due(datetime.fromisoformat("2026-09-30T16:59:00+00:00")))
        self.assertTrue(monthly_due(datetime.fromisoformat("2026-09-30T18:20:00+00:00")))

    def test_three_way_merge_preserves_local_adaptation_and_rejects_conflict(self):
        previous = b"first\nsecond\nthird\nfourth\nfifth\nsixth\n"
        local = previous.replace(b"first", b"local first")
        latest = previous.replace(b"sixth", b"upstream sixth")
        merged = merge_resource(local, previous, latest)
        self.assertIn(b"local first", merged)
        self.assertIn(b"upstream sixth", merged)
        with self.assertRaises(SkillError):
            merge_resource(b"local\n", b"original\n", b"upstream\n")

    def test_monitor_external_only_never_downloads_or_installs_packages(self):
        json_write(self.root / "catalog/vendor-sources.json", {"sources": [{"repository": "example/proprietary", "head_commit": "old", "default_branch": "main", "redistribution_allowed": False, "redistribution": "external-only", "skills": []}]})
        with patch("monitor_upstream.github_json", return_value={"sha": "new"}), patch("monitor_upstream.blob", side_effect=AssertionError("must not download")):
            report = monitor(self.root)
        self.assertTrue(report["changed"])
        self.assertEqual(report["sources"][0]["status"], "external-only-update-review")

    def test_monitor_updates_licensed_skill_and_preserves_attribution(self):
        folder = self.root / "vendor/skills/vendor-analysis"
        folder.mkdir(parents=True)
        old_skill = b'---\nname: vendor-analysis\ndescription: Analyze synthetic records when users request a report.\nlicense: MIT\nmetadata:\n  version: "1.0.0"\n---\nUse evidence.\n'
        new_skill = old_skill.replace(b'"1.0.0"', b'"1.1.0"').replace(b"Use evidence.", b"Use current evidence.")
        (folder / "SKILL.md").write_bytes(old_skill)
        (folder / "LICENSE").write_text("Original MIT attribution")
        (folder / "ADAPTATION.md").write_text("Original vendor author; portable wrapper only.")
        row = {"id": "vendor-analysis", "path": "vendor/skills/vendor-analysis", "upstream_path": "skills/vendor-analysis", "upstream_commit": "old", "content_sha256": tree_sha256(folder), "version": "1.0.0", "compatibility": {"codex": "verified"}}
        source = {"repository": "example/vendor", "head_commit": "old", "pinned_commit": "old", "ref": "main", "redistribution_allowed": True, "license_files": ["LICENSE"], "skills": [row]}
        json_write(self.root / "catalog/vendor-sources.json", {"sources": [source]})
        json_write(self.root / "catalog/skills.json", {"skills": [dict(row)]})
        def fake_blob(repository, commit, path):
            if path == "LICENSE":
                return b"Original MIT attribution"
            return old_skill if commit == "old" else new_skill
        def fake_tree(repository, commit):
            return {"skills/vendor-analysis/SKILL.md": {"sha": commit, "mode": "100644"}}
        with patch("monitor_upstream.github_json", return_value={"sha": "new"}), patch("monitor_upstream.tree", side_effect=fake_tree), patch("monitor_upstream.blob", side_effect=fake_blob):
            report = monitor(self.root)
        self.assertEqual((folder / "SKILL.md").read_bytes(), new_skill)
        self.assertIn("Original vendor author", (folder / "ADAPTATION.md").read_text())
        updated = json.loads((self.root / "catalog/skills.json").read_text())["skills"][0]
        self.assertEqual(updated["compatibility"]["codex"], "not_verified")
        self.assertEqual(updated["upstream_commit"], "new")
        provenance = json.loads((folder / "SOURCE.json").read_text())
        self.assertEqual(provenance["commit"], "new")
        self.assertEqual(provenance["upstream_version"], "1.1.0")
        self.assertEqual(provenance["license_files"][0]["sha256"], sha256(b"Original MIT attribution"))
        self.assertTrue(validate(self.root)["ok"])

    def vendor_monitor_fixture(self, same_version=False, row_commit="old"):
        folder = self.root / "vendor/skills/vendor-analysis"
        folder.mkdir(parents=True)
        old = b'---\nname: vendor-analysis\ndescription: Analyze synthetic records when users request a report.\nlicense: MIT\nmetadata:\n  version: "1.0.0"\n---\nUse evidence.\n'
        new = old.replace(b"Use evidence.", b"Use current evidence.")
        if not same_version:
            new = new.replace(b'"1.0.0"', b'"1.1.0"')
        (folder / "SKILL.md").write_bytes(old)
        (folder / "LICENSE").write_bytes(b"Original MIT attribution")
        row = {"id": "vendor-analysis", "path": "vendor/skills/vendor-analysis", "upstream_path": "skills/vendor-analysis", "upstream_commit": row_commit, "content_sha256": tree_sha256(folder), "version": "1.0.0"}
        source = {"repository": "example/vendor", "pinned_commit": "old", "ref": "main", "redistribution_allowed": True, "license_files": ["LICENSE"], "skills": [row]}
        json_write(self.root / "catalog/vendor-sources.json", {"sources": [source]})
        json_write(self.root / "catalog/skills.json", {"skills": [dict(row)]})
        def fake_blob(repository, commit, path):
            return b"Original MIT attribution" if path == "LICENSE" else (new if commit == "new" else old)
        def fake_tree(repository, commit):
            return {"skills/vendor-analysis/SKILL.md": {"sha": commit, "mode": "100644"}}
        return folder, old, fake_blob, fake_tree

    def test_monitor_same_version_changed_bytes_is_review_conflict_without_mutation(self):
        folder, old, fake_blob, fake_tree = self.vendor_monitor_fixture(same_version=True)
        with patch("monitor_upstream.github_json", return_value={"sha": "new"}), patch("monitor_upstream.tree", side_effect=fake_tree), patch("monitor_upstream.blob", side_effect=fake_blob):
            report = monitor(self.root)
        self.assertEqual((folder / "SKILL.md").read_bytes(), old)
        result = report["sources"][0]["skills"][0]
        self.assertEqual(result["status"], "conflict-needs-review")
        self.assertIn("immutable artifact", result["reason"])

    def test_monitor_partial_retry_fetches_each_rows_actual_old_tree(self):
        folder, old, fake_blob, fake_tree = self.vendor_monitor_fixture(row_commit="older")
        with patch("monitor_upstream.github_json", return_value={"sha": "new"}), patch("monitor_upstream.tree", side_effect=fake_tree) as fetched, patch("monitor_upstream.blob", side_effect=fake_blob):
            report = monitor(self.root)
        self.assertIn(("example/vendor", "older"), [call.args for call in fetched.call_args_list])
        self.assertEqual(report["sources"][0]["skills"][0]["status"], "candidate-update-needs-review")
        self.assertIn(b'"1.1.0"', (folder / "SKILL.md").read_bytes())

    def test_monitor_changed_license_does_not_update_any_package(self):
        folder, old, fake_blob, fake_tree = self.vendor_monitor_fixture()
        def changed_license(repository, commit, path):
            if path == "LICENSE" and commit == "new":
                return b"New restrictive license"
            return fake_blob(repository, commit, path)
        with patch("monitor_upstream.github_json", return_value={"sha": "new"}), patch("monitor_upstream.tree", side_effect=fake_tree), patch("monitor_upstream.blob", side_effect=changed_license):
            report = monitor(self.root)
        self.assertEqual(report["sources"][0]["status"], "check-failed")
        self.assertEqual((folder / "SKILL.md").read_bytes(), old)

    def test_public_tree_scans_docs_catalog_assets_and_redacts_seeded_findings(self):
        seeds = {
            "docs/private.md": "/" + "Users" + "/seeded-person/project\n",
            "catalog/contact.json": json.dumps({"mailbox": "seeded.owner" + "@private-mail.tld"}),
            "assets/token.txt": "gh" + "p_" + "A" * 40,
            "docs/account.md": "account_id: " + "975382461",
        }
        for name, content in seeds.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        result = audit(self.root)
        self.assertFalse(result["ok"])
        self.assertEqual({item["path"] for item in result["issues"]}, set(seeds))
        serialized = json.dumps(result)
        self.assertNotIn("A" * 40, serialized)
        self.assertNotIn("seeded.owner", serialized)

    def test_public_attribution_examples_prefix_documentation_and_regex_literals_allowed(self):
        text = skill_text("example-analysis") + "Original synthetic example: user@gmail.com\nDocumentation: ghp_…\n"
        self.assertEqual(text_findings(text), [])
        scanner = Path(__file__).resolve().parents[1] / "scripts/audit_public.py"
        self.assertEqual(text_findings(scanner.read_text()), [])
        self.assertTrue(audit(self.root)["ok"])

    def test_public_archive_contents_scanned_even_when_outside_repository(self):
        self.output.mkdir()
        value = "sk" + "-" + "B" * 40
        (self.output / "seed.zip").write_bytes(archive_bytes({"example-analysis/assets/input.txt": value.encode()}))
        result = audit(self.root, self.output)
        self.assertFalse(result["ok"])
        self.assertEqual(result["archives"], 1)
        self.assertIn("seed.zip!", result["issues"][0]["path"])
        self.assertNotIn(value, json.dumps(result))

    def test_original_vendor_license_author_attribution_allowed_but_private_path_forbidden(self):
        path = self.root / "vendor/skills/example-vendor/LICENSE"
        path.parent.mkdir(parents=True)
        path.write_text("Copyright Original Author <" + "publisher" + "@original-publisher.tld>\n")
        self.assertTrue(audit(self.root)["ok"])
        path.write_text(path.read_text() + "/" + "home" + "/seeded-person/private\n")
        self.assertFalse(audit(self.root)["ok"])

    def test_private_evidence_is_not_silently_ignored(self):
        path = self.root / "evidence/private.json"
        path.parent.mkdir()
        path.write_text('{}')
        self.assertFalse(audit(self.root)["ok"])

if __name__ == "__main__":
    unittest.main()
