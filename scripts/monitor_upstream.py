#!/usr/bin/env python3
"""Check public upstreams and prepare licensed, baseline-preserving updates for review only."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile
import yaml
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from common import ROOT, SkillError, frontmatter, json_write, runtime_files, safe_relative, sha256, tree_sha256
from validate import validate

def monthly_due(now=None):
    local = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo("Asia/Novosibirsk"))
    # GitHub dispatch can be delayed; the cron fixes the intended hour, this guard fixes the date.
    return local.day == 1

def request_bytes(url):
    headers = {"User-Agent": "marketing-skills-upstream-review/1.0", "Accept": "application/vnd.github+json"}
    # Authentication is never sent to arbitrary URLs or raw content hosts.
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, headers=headers), timeout=45) as response:
        data = response.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024:
        raise SkillError("upstream response exceeds limit")
    return data

def github_json(repository, endpoint):
    if len(repository.split("/")) != 2 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.\/" for c in repository):
        raise SkillError("invalid public GitHub repository")
    return json.loads(request_bytes(f"https://api.github.com/repos/{repository}/{endpoint}"))

def tree(repository, commit):
    result = github_json(repository, f"git/trees/{commit}?recursive=1")
    if result.get("truncated"):
        raise SkillError("upstream tree truncated; review with dedicated checkout")
    return {row["path"]: row for row in result["tree"] if row["type"] == "blob"}

def blob(repository, commit, path):
    safe_relative(path)
    return request_bytes(f"https://raw.githubusercontent.com/{repository}/{commit}/{quote(path, safe='/')}")

def merge_resource(local, previous, latest):
    """Three-way merge keeps packaging adaptations. Conflicts always stop candidate updates."""
    if local == previous:
        return latest
    if previous == latest or local == latest:
        return local
    if any(b"\0" in data for data in (local, previous, latest)):
        raise SkillError("changed binary resource has local adaptations")
    try:
        for data in (local, previous, latest):
            data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SkillError("changed binary resource has local adaptations") from exc
    with tempfile.TemporaryDirectory(prefix="marketing-skills-merge-") as folder:
        paths = [Path(folder) / name for name in ("local", "base", "upstream")]
        for path, data in zip(paths, (local, previous, latest)):
            path.write_bytes(data)
        result = subprocess.run(["git", "merge-file", "-p", "--", *map(str, paths)], capture_output=True, timeout=15)
        if result.returncode != 0:
            raise SkillError("three-way merge conflict; preserve local adaptations and review manually")
        return result.stdout

def prepare_skill(root, row, repository, old_commit, new_commit, old_tree, new_tree):
    folder = root / row["path"]
    if tree_sha256(folder) != row.get("content_sha256"):
        raise SkillError("candidate differs from frozen vendor baseline")
    prefix = row["upstream_path"].rstrip("/") + "/"
    old = {name[len(prefix):]: info for name, info in old_tree.items() if name.startswith(prefix)}
    new = {name[len(prefix):]: info for name, info in new_tree.items() if name.startswith(prefix)}
    if "SKILL.md" not in new:
        raise SkillError("upstream skill removed or moved")
    # Local runtime map preserves license/attribution/adapter files that were never in upstream.
    local = {path.relative_to(folder).as_posix(): path.read_bytes() for path in runtime_files(folder)}
    proposed = dict(local)
    changed = False
    for name in sorted(set(old) | set(new)):
        safe_relative(name)
        if any(part.startswith(".") or part in {"tests", "__pycache__", "node_modules"} for part in Path(name).parts):
            continue
        for info in (old.get(name), new.get(name)):
            if info and info.get("mode") == "120000":
                raise SkillError("upstream symlink requires manual review")
        if old.get(name, {}).get("sha") == new.get(name, {}).get("sha"):
            continue
        changed = True
        prior = blob(repository, old_commit, prefix + name) if name in old else None
        latest = blob(repository, new_commit, prefix + name) if name in new else None
        current = local.get(name)
        if latest is None:
            if current != prior:
                raise SkillError(f"removed upstream resource has local edits: {name}")
            proposed.pop(name, None)
        elif prior is None:
            if current is not None and current != latest:
                raise SkillError(f"new upstream resource collides with adapter: {name}")
            proposed[name] = latest
        elif current is None:
            raise SkillError(f"upstream resource absent in adapted package: {name}")
        else:
            proposed[name] = merge_resource(current, prior, latest)
    if not changed:
        return None
    # Stage and validate the changed package without executing any upstream code.
    with tempfile.TemporaryDirectory(prefix="marketing-skills-vendor-") as temp:
        stage_root = Path(temp)
        stage = stage_root / "vendor/skills" / row["id"]
        for name, data in proposed.items():
            path = stage.joinpath(*safe_relative(name).parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        report = validate(stage_root)
        if not report["ok"]:
            raise SkillError("new upstream package fails portable/privacy validation; review adaptations")
        version = frontmatter(stage / "SKILL.md")[0].get("metadata", {}).get("version")
        if version == row.get("version") and version is not None:
            raise SkillError("content changed without an upstream version bump; immutable artifact conflict")
    return proposed

def update_catalog(root, updates):
    catalog = root / "catalog/skills.json"
    if not catalog.exists():
        return
    data = json.loads(catalog.read_text())
    rows = data if isinstance(data, list) else data.get("skills", data.get("entries", []))
    for row in rows:
        if row.get("path") in updates:
            row.update(updates[row["path"]])
    json_write(catalog, data)

def select_commit(source):
    repository = source["repository"]
    policy = source.get("selection_policy", source.get("policy", ""))
    if policy == "latest-stable-release" or "latest non-prerelease release" in policy:
        release = github_json(repository, "releases/latest")
        if release.get("draft") or release.get("prerelease") or not release.get("tag_name"):
            raise SkillError("no reviewed stable upstream release available")
        tag = release["tag_name"]
        commit = github_json(repository, f"commits/{quote(tag, safe='')}")["sha"]
        return commit, {"tag": tag, "url": release.get("html_url"), "published_at": release.get("published_at")}
    ref = source.get("ref", source.get("default_branch", "main"))
    return github_json(repository, f"commits/{quote(ref, safe='')}")["sha"], None

def checked_licenses(source, repository, previous, latest):
    checks = []
    for item in source.get("license_files", []):
        name = item["path"] if isinstance(item, dict) else item
        old, new = blob(repository, previous, name), blob(repository, latest, name)
        expected = item.get("sha256") if isinstance(item, dict) else None
        if old != new or (expected and sha256(old) != expected):
            raise SkillError("upstream license changed or baseline mismatch; redistribution requires review")
        checks.append({"path": name, "sha256": sha256(new)})
    if not checks:
        raise SkillError("no reviewed upstream license baseline")
    return checks

def provenance_package(package, row, repository, latest, licenses):
    source_url = f"https://github.com/{repository}/tree/{latest}/{row['upstream_path']}"
    updated = dict(package)
    current_metadata = yaml.safe_load(package["SKILL.md"].decode().split("---", 2)[1])
    upstream_version = current_metadata.get("metadata", {}).get("version", current_metadata.get("version"))
    provenance = {"schema_version": 1, "repository": repository, "commit": latest,
                  "source_url": source_url, "original_author": row.get("author", repository.split('/')[0]),
                  "license": row.get("license"), "license_files": licenses,
                  "upstream_version": upstream_version, "adaptation_version": row.get("adaptation_version"),
                  "runtime_acceptance": "not_verified"}
    updated["SOURCE.json"] = (json.dumps(provenance, ensure_ascii=False, indent=2) + "\n").encode()
    if "UPSTREAM.md" in updated:
        text = updated["UPSTREAM.md"].decode()
        text = text.replace(row.get("source_url", "__absent__"), source_url)
        if row.get("upstream_commit"):
            text = text.replace(row["upstream_commit"], latest)
        updated["UPSTREAM.md"] = text.encode()
    return updated

def monitor(root):
    path = root / "catalog/vendor-sources.json"
    data = json.loads(path.read_text())
    sources = data["sources"]
    observations = []
    updates = {}
    for source in sources:
        repository = source["repository"]
        ref = source.get("ref", source.get("default_branch", "main"))
        before = source.get("pinned_commit", source.get("head_commit"))
        observation = {"repository": repository, "previous_commit": before, "policy": source.get("redistribution", "external-only")}
        try:
            latest, latest_release = select_commit(source)
            if latest_release:
                observation["observed_release"] = latest_release
            observation["observed_commit"] = latest
            if latest == before:
                observation["status"] = "unchanged"
                observations.append(observation)
                continue
            if not source.get("redistribution_allowed", False):
                observation["status"] = "external-only-update-review"
                observations.append(observation)
                continue
            if not before:
                raise SkillError("missing pinned baseline commit")
            license_checks = checked_licenses(source, repository, before, latest)
            observation["licenses"] = license_checks
            trees = {before: tree(repository, before), latest: tree(repository, latest)}
            new_tree = trees[latest]
            results = []
            all_ok = True
            for row in source.get("skills", []):
                if not row.get("path"):
                    continue
                try:
                    row_before = row.get("upstream_commit", before)
                    if row_before == latest:
                        results.append({"id": row["id"], "status": "skill-unchanged"})
                        continue
                    row_licenses = checked_licenses(source, repository, row_before, latest) if row_before != before else license_checks
                    if row_before not in trees:
                        trees[row_before] = tree(repository, row_before)
                    package = prepare_skill(root, row, repository, row_before, latest, trees[row_before], new_tree)
                    if package is None:
                        results.append({"id": row["id"], "status": "skill-unchanged"})
                        continue
                    package = provenance_package(package, row, repository, latest, row_licenses)
                    folder = root / row["path"]
                    # All conflicts were resolved and validation passed before writing review-only candidate state.
                    old_files = runtime_files(folder)
                    for file in old_files:
                        if file.relative_to(folder).as_posix() not in package:
                            file.unlink()
                    for name, content in package.items():
                        destination = folder.joinpath(*safe_relative(name).parts)
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(content)
                    row["upstream_commit"] = latest
                    row["source_url"] = f"https://github.com/{repository}/tree/{latest}/{row['upstream_path']}"
                    row["content_sha256"] = tree_sha256(folder)
                    refreshed_meta = frontmatter(folder / "SKILL.md")[0]
                    row["version"] = refreshed_meta.get("metadata", {}).get("version")
                    row["description"] = refreshed_meta["description"]
                    row["license_files"] = row_licenses
                    prefix = row["upstream_path"].rstrip("/") + "/"
                    row["upstream_files"] = sorted(name[len(prefix):] for name in new_tree if name.startswith(prefix))
                    row["upstream_file_hashes"] = {name[len(prefix):]: {"git_blob_sha1": info["sha"]} for name, info in new_tree.items() if name.startswith(prefix)}
                    # A real upstream tree digest is re-established from fetched bytes when preparing the release.
                    row["upstream_tree_sha256"] = None
                    # Every upstream update invalidates earlier runtime compatibility acceptance.
                    row["compatibility"] = {key: "not_verified" for key in row.get("compatibility", {})}
                    updates[row["path"]] = {key: row[key] for key in ("upstream_commit", "source_url", "content_sha256", "version", "description", "compatibility", "upstream_files", "upstream_file_hashes", "upstream_tree_sha256", "license_files")}
                    results.append({"id": row["id"], "status": "candidate-update-needs-review"})
                except (SkillError, OSError, ValueError) as exc:
                    all_ok = False
                    results.append({"id": row["id"], "status": "conflict-needs-review", "reason": str(exc)})
            if all_ok:
                if latest_release:
                    source["latest_release"] = latest_release
                source["pinned_commit"] = latest
                source["head_commit"] = latest
            observation["status"] = "review-required"
            observation["skills"] = results
        except Exception as exc:
            observation["status"] = "check-failed"
            observation["reason"] = str(exc)
        observations.append(observation)
    # Preserve initial evidence when every source is unchanged; avoid monthly no-change PR churn.
    changed = any(item["status"] != "unchanged" for item in observations)
    if changed:
        json_write(path, data)
        update_catalog(root, updates)
        report = {"schema_version": 1, "requires_human_review": True, "sources": observations}
        json_write(root / "catalog/upstream-observations.json", report)
    return {"changed": changed, "sources": observations}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--scheduled", action="store_true", help="Run only at the real Novosibirsk monthly boundary")
    parser.add_argument("--check-schedule", action="store_true")
    args = parser.parse_args()
    if args.check_schedule:
        print("true" if monthly_due() else "false")
        return 0
    if args.scheduled and not monthly_due():
        print(json.dumps({"changed": False, "reason": "not Novosibirsk first-of-month midnight"}))
        return 0
    try:
        print(json.dumps(monitor(args.root.resolve()), ensure_ascii=False, indent=2))
        return 0
    except (SkillError, OSError, ValueError) as exc:
        print(str(exc), file=__import__("sys").stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
