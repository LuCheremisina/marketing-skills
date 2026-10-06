#!/usr/bin/env python3
"""Validate real Agent Skills YAML and public runtime resources; never execute them."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
from common import ROOT, SkillError, entries, frontmatter, json_write, runtime_files, safe_relative, tree_sha256

NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
VERSION = re.compile(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\Z")
PLUGIN_VERSION = re.compile(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\Z")
ALLOWED = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
AUTHOR = "Любовь Черемисина"
AUTHOR_LINKS = ("https://cheremisina.ru", "https://cheremisina.online", "https://github.com/LuCheremisina/marketing-skills")
PRIVACY = (
    ("personal filesystem path", re.compile(r"(?:/(?:Users|home)/[A-Za-z0-9._-]+/|GoogleDrive-[A-Za-z0-9@._-]+/)")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("credential token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{32,}|xox[baprs]-[A-Za-z0-9-]{20,})\b")),
    ("literal credential assignment", re.compile(r"(?im)\b(?:api_key|access_token|client_secret|password)\s*[:=]\s*[\"']([A-Za-z0-9+/=_-]{20,})[\"']")),
)

def resource_targets(text, entrypoint=False):
    """Explicit links plus bundled path literals; generated files and examples are not dependencies."""
    targets = [(target.strip().split(' "')[0].strip("<>"), False) for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)]
    # SKILL.md defines root-relative input resources. Inline references in other files can be
    # historical output examples, so those use explicit Markdown links for dependency checks.
    if entrypoint:
        for target in re.findall(r"\b(?:python[0-9.]*|bash|sh|node|ruby)\s+((?:scripts|evals)/[A-Za-z0-9_./-]+)", text):
            targets.append((target, True))
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        for line in text.splitlines():
            if re.search(r"не создавать|do not create|its `references/", line, re.I):
                continue
            for literal in re.findall(r"`([^`\n]+)`", line):
                target = literal.strip().split()[0] if literal.strip() else ""
                if re.match(r"^(?:references|scripts|evals|assets)/", target) and not any(char in target for char in "*{}<>$"):
                    targets.append((target.rstrip(",.;"), True))
    return targets

def plugin_issues(root):
    """Check portable listing limits and the native overlays before making archives."""
    issues = []
    def add(path, message):
        issues.append({"level": "error", "path": path.relative_to(root).as_posix(), "message": message})
    catalog_path = root / "catalog/skills.json"
    try:
        release = json.loads(catalog_path.read_text()).get("release_candidate") if catalog_path.exists() else None
    except (ValueError, OSError, AttributeError):
        release = None  # The catalogue parser below reports its own errors.
    for base, identity in ((root, "marketing-skills"), (root / "vendor", "marketing-skills-vendor")):
        path = base / "plugin.json"
        if not path.exists():
            continue
        try:
            portable = json.loads(path.read_text())
            if not isinstance(portable, dict):
                raise ValueError("plugin manifest must be an object")
        except (ValueError, OSError) as exc:
            add(path, str(exc))
            continue
        if portable.get("name") != identity:
            add(path, "portable plugin identity differs from package identity")
        version = portable.get("version")
        if not isinstance(version, str) or not PLUGIN_VERSION.fullmatch(version):
            add(path, "plugin version must be strict SemVer")
        if release is not None and version != release:
            add(path, "plugin version differs from catalog release_candidate")
        for key in ("skills", "mcpServers", "apps", "interface"):
            if key in portable:
                add(path, f"portable manifest must not contain top-level {key}")
        try:
            interface = portable.get("extensions", {}).get("com.openai", {}).get("interface")
            if interface is not None:
                if not isinstance(interface, dict):
                    raise ValueError("OpenAI interface must be an object")
                short = interface.get("shortDescription")
                if not isinstance(short, str) or not short.strip() or len(short) > 30:
                    add(path, "OpenAI shortDescription must be nonempty text at most 30 characters")
                prompts = interface.get("defaultPrompt")
                if prompts is not None and not (isinstance(prompts, str) or isinstance(prompts, list) and 1 <= len(prompts) <= 3 and all(isinstance(item, str) for item in prompts)):
                    add(path, "OpenAI defaultPrompt must be text or one to three strings")
        except (ValueError, AttributeError) as exc:
            add(path, str(exc))
        for directory in (".claude-plugin", ".codex-plugin"):
            overlay_path = base / directory / "plugin.json"
            if not overlay_path.exists():
                continue
            try:
                overlay = json.loads(overlay_path.read_text())
                if not isinstance(overlay, dict):
                    raise ValueError("native plugin manifest must be an object")
                for key in ("name", "version"):
                    if overlay.get(key) != portable.get(key):
                        add(overlay_path, f"native {key} differs from portable manifest")
                for key in ("description", "author", "homepage", "repository", "license", "keywords"):
                    if key in overlay and overlay[key] != portable.get(key):
                        add(overlay_path, f"native presentation field {key} differs from portable manifest")
            except (ValueError, OSError) as exc:
                add(overlay_path, str(exc))
    return issues

def validate(root: Path):
    issues = plugin_issues(root)
    def add(level, path, message):
        issues.append({"level": level, "path": str(path), "message": message})
    try:
        rows = entries(root)
    except (SkillError, ValueError, KeyError) as exc:
        return {"ok": False, "skills_checked": 0, "issues": [{"level": "error", "path": "catalog/skills.json", "message": str(exc)}]}
    seen = set()
    checked = 0
    for row in rows:
        ident = row.get("id", "")
        # External-only catalog links have no package and are not promised to be installable.
        if not row.get("path") or row.get("redistribution") == "external-only":
            continue
        try:
            relative = safe_relative(row["path"])
            folder = root.joinpath(*relative.parts)
            folder.resolve().relative_to(root.resolve())
            if folder.is_symlink():
                raise SkillError("skill directory cannot be a symlink")
            if not (folder / "SKILL.md").is_file():
                raise SkillError("missing SKILL.md")
            metadata, body, raw = frontmatter(folder / "SKILL.md")
        except (SkillError, OSError, ValueError) as exc:
            add("error", row.get("path", ident), str(exc))
            continue
        checked += 1
        if ident in seen:
            add("error", relative, f"duplicate skill ID: {ident}")
        seen.add(ident)
        name = metadata.get("name")
        if not isinstance(name, str) or not NAME.fullmatch(name) or len(name) > 64:
            add("error", relative, "name must be lower-case kebab-case, at most 64 characters")
        elif name != folder.name or name != ident:
            add("error", relative, "name must equal folder name and catalog ID")
        if isinstance(name, str) and "cheremisina" in name.lower():
            add("error", relative, "personal brand in skill ID; public attribution remains allowed")
        description = metadata.get("description")
        if not isinstance(description, str) or not description.strip() or len(description) > 1024:
            add("error", relative, "description must be nonempty text, at most 1024 characters")
        elif len(description.strip()) < 30:
            add("warning", relative, "short description: review capability and trigger clarity")
        unknown = sorted(str(key) for key in metadata if key not in ALLOWED)
        if unknown:
            add("error", relative, f"unsupported frontmatter fields: {', '.join(unknown)}; custom values belong in metadata")
        custom = metadata.get("metadata", {})
        if not isinstance(custom, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in custom.items()):
            add("error", relative, "metadata must contain only string keys and string values")
            custom = {}
        own = str(relative).startswith("skills/")
        version = custom.get("version", "")
        if own and not VERSION.fullmatch(version):
            add("error", relative, "authored metadata.version must be quoted SemVer")
        if row.get("version") and version and str(row["version"]) != version:
            add("error", relative, "catalog version differs from metadata.version")
        compatibility = metadata.get("compatibility", "")
        if compatibility and (not isinstance(compatibility, str) or len(compatibility) > 500):
            add("error", relative, "compatibility must be text at most 500 characters")
        allowed_tools = metadata.get("allowed-tools")
        if allowed_tools is not None and not isinstance(allowed_tools, str):
            add("error", relative, "experimental allowed-tools must be text; support varies by platform")
        if own:
            if metadata.get("license") != "MIT":
                add("error", relative, "authored skills must declare MIT")
            if AUTHOR not in raw or not all(url in raw for url in AUTHOR_LINKS):
                add("error", relative, "authored skill is missing methodologist or one of the three public links")
            if not re.search(r"методолог|methodolog", raw, re.I):
                add("error", relative, "label the author as methodologist")
        if len(raw.splitlines()) > 500:
            add("warning", relative, "SKILL.md exceeds recommended 500 lines; review progressive disclosure")
        try:
            files = runtime_files(folder)
        except SkillError as exc:
            add("error", relative, str(exc))
            continue
        packaged_paths = {resource.resolve() for resource in files}
        # Inspect all public text resources, not just entrypoints. Binary resources are packaged unchanged.
        for file in files:
            relfile = file.relative_to(root).as_posix()
            try:
                text = file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for label, pattern in PRIVACY:
                if pattern.search(text):
                    add("error", relfile, label)
            if file.parent.name == "references" and len(text.splitlines()) > 100 and not re.search(r"(?:table of contents|contents|оглавление|содержание|^- \[.+\]\(#)", text, re.I | re.M):
                add("warning", relfile, "long reference has no evident contents/navigation")
            if file.suffix == ".md":
                for target, root_relative in resource_targets(text, file == folder / "SKILL.md"):
                    if not target or target.startswith(("#", "https://", "http://", "mailto:")) or "${" in target:
                        continue
                    pathpart = unquote(urlsplit(target).path)
                    local = (folder if root_relative else file.parent) / pathpart
                    try:
                        local.resolve().relative_to(folder.resolve())
                    except ValueError:
                        add("error", relfile, f"resource link escapes skill: {target}")
                        continue
                    if not local.exists():
                        add("error", relfile, f"missing local resource: {target}")
                    elif local.is_file() and local.resolve() not in packaged_paths:
                        add("error", relfile, f"referenced resource excluded from package: {target}")
        expected = row.get("content_sha256")
        if expected and expected != tree_sha256(folder):
            add("error", relative, "content_sha256 does not match packaged resources")
    if not checked:
        add("error", ".", "no installable skills found")
    return {"ok": not any(i["level"] == "error" for i in issues), "skills_checked": checked, "issues": issues}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    report = validate(args.root.resolve())
    if args.json:
        json_write(args.json, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1

if __name__ == "__main__":
    sys.exit(main())
