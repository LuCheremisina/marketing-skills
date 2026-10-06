#!/usr/bin/env python3
"""Create immutable deterministic skill archives, plugin archive and checksum manifest."""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path
import posixpath
import re
import sys
from urllib.parse import quote, urlsplit, urlunsplit
import zipfile
from common import ROOT, SkillError, entries, frontmatter, json_write, runtime_files, sha256, tree_sha256
from validate import validate

def archive_bytes(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            # Non-executable resources; invoke scripts with the documented interpreter.
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return stream.getvalue()

def payload_hash(files):
    import hashlib
    digest = hashlib.sha256()
    for name, data in sorted(files.items()):
        digest.update(name.encode() + b"\0" + data + b"\0")
    return digest.hexdigest()

def portable_document(data, source_path):
    """Make global documentation usable from minimal plugins; preserve skill resources verbatim."""
    text = data.decode("utf-8")
    pattern = re.compile(r"(\[[^\]]*\]\()([^\n)]+)(\))")
    def replace(match):
        value = match.group(2).strip()
        if value.startswith("<") and ">" in value:
            target, rest = value[1:].split(">", 1)
        else:
            parts = value.split(None, 1)
            target, rest = parts[0], (" " + parts[1] if len(parts) > 1 else "")
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            return match.group(0)
        relative = posixpath.normpath(posixpath.join(posixpath.dirname(source_path), parsed.path))
        if relative.startswith("../") or relative == "..":
            raise SkillError("global documentation link escapes public repository")
        image = match.start() > 0 and text[match.start() - 1] == "!"
        base = "https://raw.githubusercontent.com/LuCheremisina/marketing-skills/main/" if image else "https://github.com/LuCheremisina/marketing-skills/blob/main/"
        remote = urlsplit(base + quote(relative, safe="/%"))
        rewritten = urlunsplit((remote.scheme, remote.netloc, remote.path, parsed.query, parsed.fragment))
        return match.group(1) + rewritten + rest + match.group(3)
    return pattern.sub(replace, text).encode("utf-8")

def build(root: Path, output: Path, version: str, previous_manifest: Path | None = None):
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version):
        raise SkillError("release version must be SemVer")
    report = validate(root)
    if not report["ok"]:
        raise SkillError("validation failed: " + json.dumps(report["issues"], ensure_ascii=False))
    catalog_path = root / "catalog/skills.json"
    if catalog_path.exists():
        candidate_version = json.loads(catalog_path.read_text()).get("release_candidate")
        if candidate_version is not None and candidate_version != version:
            raise SkillError("requested release version differs from catalog release_candidate")
    output = output.resolve()
    for skill_root in (root / "skills", root / "vendor/skills"):
        try:
            output.relative_to(skill_root.resolve())
        except ValueError:
            pass
        else:
            raise SkillError("release directory cannot be inside a skill")
    result = {"schema_version": 1, "release_version": version, "repository": "https://github.com/LuCheremisina/marketing-skills", "skills": [], "bundles": []}
    artifacts = {}
    plugin_files = {}
    vendor_files = {}
    all_files = {}
    # Root documentation and license files are public-only inputs; no evidence or local inventory is included.
    for name in ("LICENSE", "NOTICE.md", "AUTHOR.md", "AUTHORS.md", "THIRD_PARTY_NOTICES.md", "CITATION.cff", "README.md", "README.ru.md", "CHANGELOG.md", "CONTRIBUTING.md", ".gitignore"):
        path = root / name
        if path.is_file():
            all_files[name] = path.read_bytes()
            if name not in {"CONTRIBUTING.md", ".gitignore"}:
                plugin_files[name] = path.read_bytes()
                if name in {"README.md", "README.ru.md", "THIRD_PARTY_NOTICES.md"}:
                    plugin_files[name] = portable_document(path.read_bytes(), name)
    for dirname in (".claude-plugin", ".codex-plugin"):
        for path in sorted((root / dirname).rglob("*.json")):
            name = path.relative_to(root).as_posix()
            plugin_files[name] = path.read_bytes()
            all_files[name] = path.read_bytes()
    for dirname in ("docs", "catalog", "assets", "scripts", "examples", "evals", "tests", ".github"):
        directory = root / dirname
        if directory.exists():
            for path in runtime_files(directory):
                all_files[path.relative_to(root).as_posix()] = path.read_bytes()
    for name in ("requirements-dev.txt", "pyproject.toml"):
        if (root / name).is_file():
            all_files[name] = (root / name).read_bytes()
    for row in sorted(entries(root), key=lambda row: row["id"]):
        if not row.get("path") or row.get("redistribution") == "external-only":
            continue
        folder = root / row["path"]
        meta, _, _ = frontmatter(folder / "SKILL.md")
        ident = row["id"]
        item_version = meta.get("metadata", {}).get("version") or row.get("version") or ("upstream-" + row.get("upstream_commit", "unversioned")[:12])
        if not re.fullmatch(r"[A-Za-z0-9._+-]+", str(item_version)):
            raise SkillError(f"unsafe version in archive filename: {ident}")
        resources = {path.relative_to(folder).as_posix(): path.read_bytes() for path in runtime_files(folder)}
        own = row["path"].startswith("skills/")
        if own and not any(name.upper().startswith("LICENSE") for name in resources):
            if not (root / "LICENSE").is_file():
                raise SkillError("root MIT LICENSE required")
            resources["LICENSE"] = (root / "LICENSE").read_bytes()
        if not own and not any(name.upper().startswith(("LICENSE", "COPYING")) for name in resources):
            raise SkillError(f"third-party skill missing original license: {ident}")
        adaptation = row.get("adaptation_version")
        package_version = str(item_version) + ("+adaptation." + str(adaptation) if adaptation and not own else "")
        if not re.fullmatch(r"[A-Za-z0-9._+-]+", package_version):
            raise SkillError("unsafe package adaptation version")
        filename = f"{ident}-{package_version}.zip"
        payload = {f"{ident}/{name}": data for name, data in resources.items()}
        blob = archive_bytes(payload)
        artifacts[filename] = blob
        result["skills"].append({
            "id": ident, "version": str(item_version), "package_version": package_version, "adaptation_version": adaptation, "origin": row.get("origin", "authored" if own else "third_party"),
            "archive": filename, "sha256": sha256(blob), "content_sha256": payload_hash(resources),
            "source_content_sha256": tree_sha256(folder), "license": meta.get("license", row.get("license")),
            "upstream_repository": row.get("upstream_repository"), "upstream_commit": row.get("upstream_commit"), "source_url": row.get("source_url"),
            "files": {name: sha256(data) for name, data in sorted(resources.items())},
        })
        destination = plugin_files if own else vendor_files
        for name, data in resources.items():
            package_name = f"skills/{ident}/{name}"
            destination[package_name] = data
            all_files[f"{row['path']}/{name}"] = data
    plugin_manifest = root / "plugin.json"
    if plugin_manifest.is_file():
        # Verify JSON syntax; the manifest is authored against the current provider schema.
        json.loads(plugin_manifest.read_text())
        plugin_files["plugin.json"] = plugin_manifest.read_bytes()
        all_files["plugin.json"] = plugin_manifest.read_bytes()
        name = f"marketing-skills-plugin-{version}.zip"
        artifacts[name] = archive_bytes(plugin_files)
        result["bundles"].append({"kind": "authored-plugin", "archive": name, "sha256": sha256(artifacts[name])})
    if vendor_files:
        vendor_manifest_path = root / "vendor/plugin.json"
        if not vendor_manifest_path.is_file():
            raise SkillError("vendor/plugin.json required for the licensed vendor plugin")
        vendor_manifest = json.loads(vendor_manifest_path.read_text())
        if vendor_manifest.get("name") != "marketing-skills-vendor":
            raise SkillError("vendor plugin must have its distinct marketing-skills-vendor identity")
        vendor_files["plugin.json"] = vendor_manifest_path.read_bytes()
        all_files["vendor/plugin.json"] = vendor_manifest_path.read_bytes()
        native_fields = {key: value for key, value in vendor_manifest.items() if key in {"name", "version", "description", "author", "homepage", "repository", "license", "keywords"}}
        for dirname in (".claude-plugin", ".codex-plugin"):
            source = root / "vendor" / dirname / "plugin.json"
            if source.is_file():
                native = json.loads(source.read_text())
                if native.get("name") != vendor_manifest["name"] or native.get("version") != vendor_manifest.get("version"):
                    raise SkillError("vendor native manifest identity/version differs from vendor/plugin.json")
                content = source.read_bytes()
            else:
                native = dict(native_fields)
                if dirname == ".codex-plugin":
                    native["skills"] = "./skills/"
                content = (json.dumps(native, ensure_ascii=False, indent=2) + "\n").encode()
            vendor_files[dirname + "/plugin.json"] = content
            all_files["vendor/" + dirname + "/plugin.json"] = content
        notices = root / "THIRD_PARTY_NOTICES.md"
        if not notices.is_file():
            raise SkillError("THIRD_PARTY_NOTICES.md required in licensed vendor plugin")
        vendor_files["THIRD_PARTY_NOTICES.md"] = portable_document(notices.read_bytes(), "THIRD_PARTY_NOTICES.md")
        name = f"marketing-skills-vendor-{version}.zip"
        artifacts[name] = archive_bytes(vendor_files)
        result["bundles"].append({"kind": "licensed-vendor-plugin", "archive": name, "sha256": sha256(artifacts[name])})
    # Public catalogue only; manifests never embed installed paths or private provenance evidence.
    manifest_blob = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()
    all_files["manifest.json"] = manifest_blob
    name = f"marketing-skills-{version}.zip"
    artifacts[name] = archive_bytes(all_files)
    result["bundles"].append({"kind": "complete", "archive": name, "sha256": sha256(artifacts[name])})
    artifacts["manifest.json"] = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()
    artifacts["SHA256SUMS"] = "".join(f"{sha256(blob)}  {name}\n" for name, blob in sorted(artifacts.items())).encode()
    baseline_path = previous_manifest or (output / "manifest.json" if (output / "manifest.json").exists() else None)
    if baseline_path:
        previous = json.loads(baseline_path.read_text())
        if previous.get("release_version") == version:
            old_bundles = {(row["kind"], row["archive"]): row["sha256"] for row in previous.get("bundles", [])}
            new_bundles = {(row["kind"], row["archive"]): row["sha256"] for row in result["bundles"]}
            if old_bundles != new_bundles:
                raise SkillError("immutable library release changed bundle contents; bump the library release version")
        old = {row["id"]: row for row in previous.get("skills", [])}
        for row in result["skills"]:
            prior = old.get(row["id"])
            if prior and prior.get("package_version", prior["version"]) == row["package_version"] and prior["content_sha256"] != row["content_sha256"]:
                raise SkillError(f"immutable skill version changed contents: {row['id']}; bump the authored/adaptation version")
    output.mkdir(parents=True, exist_ok=True)
    # Freeze existing versions. An interrupted build can only be completed with byte-identical artifacts.
    for name, blob in artifacts.items():
        path = output / name
        if path.exists() and path.read_bytes() != blob:
            raise SkillError(f"immutable artifact already exists with different bytes: {name}")
    for name, blob in artifacts.items():
        (output / name).write_bytes(blob)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--previous-manifest", type=Path, help="Published baseline; prevents same-version changes across release directories")
    args = parser.parse_args()
    try:
        result = build(args.root.resolve(), args.output, args.version, args.previous_manifest)
    except (SkillError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps({"release_version": result["release_version"], "skills": len(result["skills"]), "bundles": result["bundles"]}, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
