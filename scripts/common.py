"""Shared deterministic primitives. No skill scripts are executed by these tools."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules", "tests", ".DS_Store"}

class SkillError(ValueError):
    pass

class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys instead of silently accepting the last value."""

def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, (str, int, float, bool, type(None))):
            raise SkillError("unsupported YAML mapping key")
        if key in result:
            raise SkillError(f"duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result

UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)

def frontmatter(path: Path):
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise SkillError("SKILL.md must start with YAML frontmatter")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise SkillError("unterminated YAML frontmatter")
    try:
        data = yaml.load("".join(lines[1:end]), Loader=UniqueLoader)
    except (yaml.YAMLError, SkillError) as exc:
        raise SkillError(f"invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise SkillError("frontmatter must be a mapping")
    return data, "".join(lines[end + 1:]), raw

def sha256(data: bytes):
    return hashlib.sha256(data).hexdigest()

def safe_relative(value: str):
    p = PurePosixPath(value)
    if not value or "\\" in value or p.is_absolute() or ".." in p.parts or ":" in p.parts[0]:
        raise SkillError(f"unsafe relative path: {value!r}")
    return p

def runtime_files(folder: Path):
    """All packaged resources, never symlinks, caches, private test directories or hidden profiles; runtime evals are included."""
    files = []
    for path in sorted(folder.rglob("*"), key=lambda item: item.relative_to(folder).as_posix()):
        rel = path.relative_to(folder)
        if any(part in EXCLUDED or part.startswith(".") for part in rel.parts):
            continue
        if path.is_symlink():
            raise SkillError(f"symlink cannot be packaged: {rel}")
        if path.is_file():
            files.append(path)
    return files

def tree_sha256(folder: Path):
    digest = hashlib.sha256()
    for path in runtime_files(folder):
        digest.update(path.relative_to(folder).as_posix().encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()

def discover(root: Path):
    found = []
    for prefix, origin in (("skills", "authored"), ("vendor/skills", "third_party")):
        base = root / prefix
        if not base.exists():
            continue
        for path in sorted(base.glob("*/SKILL.md")):
            found.append({"id": path.parent.name, "path": path.parent.relative_to(root).as_posix(), "origin": origin})
    return found

def entries(root: Path):
    path = root / "catalog/skills.json"
    if not path.exists():
        return discover(root)
    data = json.loads(path.read_text())
    rows = data if isinstance(data, list) else data.get("skills", data.get("entries", []))
    if not isinstance(rows, list):
        raise SkillError("catalog must contain a list of skills")
    known = {row["path"] for row in rows}
    # Never accidentally omit an authored resource just because the catalog is still being built.
    return rows + [row for row in discover(root) if row["path"] not in known]

def json_write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
