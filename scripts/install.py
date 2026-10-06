#!/usr/bin/env python3
"""Reviewed allowlist installation. Default is read-only; backups live outside skill roots."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import uuid
import zipfile
import re
from common import SkillError, frontmatter, json_write, safe_relative, sha256, tree_sha256
from build_release import payload_hash

MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_EXPANDED_BYTES = 400 * 1024 * 1024

def verified_payload(manifest_path: Path, row):
    filename = safe_relative(row["archive"])
    if len(filename.parts) != 1:
        raise SkillError("archive must be a sibling of manifest")
    path = manifest_path.parent / str(filename)
    if path.is_symlink() or path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise SkillError("archive is a symlink or exceeds size limit")
    blob = path.read_bytes()
    if sha256(blob) != row["sha256"]:
        raise SkillError(f"archive checksum mismatch: {row['id']}")
    payload = {}
    expanded = 0
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            rel = safe_relative(info.filename)
            if rel.parts[0] != row["id"] or len(rel.parts) < 2:
                raise SkillError("archive must contain exactly one matching top-level skill folder")
            if info.is_dir():
                continue
            if stat.S_ISLNK(info.external_attr >> 16):
                raise SkillError("archive symlink rejected")
            expanded += info.file_size
            if expanded > MAX_EXPANDED_BYTES:
                raise SkillError("expanded archive exceeds size limit")
            name = "/".join(rel.parts[1:])
            if name in payload:
                raise SkillError("duplicate archive member")
            payload[name] = archive.read(info)
    expected = row.get("files")
    if not isinstance(expected, dict) or set(expected) != set(payload):
        raise SkillError("manifest file allowlist does not match archive")
    if "SKILL.md" not in payload:
        raise SkillError("archive missing SKILL.md")
    for name, data in payload.items():
        if sha256(data) != expected[name]:
            raise SkillError(f"resource checksum mismatch: {name}")
    if payload_hash(payload) != row["content_sha256"]:
        raise SkillError("skill content checksum mismatch")
    return payload

def existing_hash(path: Path):
    if path.is_symlink():
        raise SkillError("installed skill directory is a symlink")
    if path.exists() and not path.is_dir():
        raise SkillError("installed skill path is not a directory")
    # Full installed tree, including formerly excluded user files, is guarded against data loss.
    if not path.exists():
        return None
    import hashlib
    digest = hashlib.sha256()
    for file in sorted(path.rglob("*"), key=lambda item: item.relative_to(path).as_posix()):
        if file.is_symlink():
            raise SkillError("installed resource is a symlink; review separately")
        if file.is_file():
            digest.update(file.relative_to(path).as_posix().encode() + b"\0" + file.read_bytes() + b"\0")
    return digest.hexdigest()

def read_baseline(path):
    if not path:
        return {}
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise SkillError("baseline must be a mapping")
    return data.get("skills", data)

def plan_install(manifest_path, target, ids, baseline=None, reviewed=None):
    data = json.loads(manifest_path.read_text())
    if data.get("schema_version") != 1:
        raise SkillError("unsupported manifest schema")
    rows = data.get("skills", [])
    index = {row["id"]: row for row in rows}
    if len(index) != len(rows):
        raise SkillError("duplicate manifest skill IDs")
    if not ids or len(set(ids)) != len(ids):
        raise SkillError("an explicit nonempty unique skill allowlist is required")
    baseline = baseline or {}
    reviewed = reviewed or {}
    result = []
    for ident in ids:
        if ident not in index or len(safe_relative(ident).parts) != 1:
            raise SkillError(f"unknown or unsafe skill ID: {ident}")
        row = index[ident]
        payload = verified_payload(manifest_path, row)
        current = existing_hash(target / ident)
        previous = baseline.get(ident)
        if isinstance(previous, dict):
            previous = previous.get("content_sha256")
        if current == row["content_sha256"]:
            action = "unchanged"
        elif current is None:
            action = "install"
        elif current == previous or current == reviewed.get(ident):
            action = "update"
        else:
            action = "conflict"
        reason = None
        if current and action == "update" and (target / ident / "SKILL.md").is_file():
            current_meta = frontmatter(target / ident / "SKILL.md")[0]
            old_version = current_meta.get("metadata", {}).get("version", current_meta.get("version"))
            next_version = row.get("version")
            if row.get("origin") == "authored" and old_version == next_version:
                action = "conflict"
                reason = "authored version unchanged but installed contents differ"
            if isinstance(old_version, str) and isinstance(next_version, str) and re.fullmatch(r"\d+\.\d+\.\d+", old_version) and re.fullmatch(r"\d+\.\d+\.\d+", next_version):
                if tuple(map(int, next_version.split("."))) < tuple(map(int, old_version.split("."))):
                    action = "conflict"
                    reason = "version downgrade refused"
        result.append({"id": ident, "action": action, "reason": reason, "current_sha256": current, "next_sha256": row["content_sha256"], "row": row, "payload": payload})
    return result

def ensure_backup_location(target: Path, backup: Path):
    target, backup = target.resolve(), backup.resolve()
    if target == backup or target in backup.parents or backup in target.parents:
        raise SkillError("backup directory must not overlap the skill root")

def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    os.replace(temp, path)

@contextmanager
def target_lock(target: Path, backup: Path):
    if target.is_symlink() or backup.is_symlink():
        raise SkillError("target and backup directories cannot be symlinks")
    ensure_backup_location(target, backup)
    backup.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = target.parent / (".marketing-skills-lock-" + sha256(str(target.resolve()).encode())[:24])
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise SkillError("another transaction owns this target; review a stale lock before removal") from exc
    try:
        yield
    finally:
        lock.rmdir()

def apply_install(target: Path, backup: Path, plan):
    ensure_backup_location(target, backup)
    if target.is_symlink() or backup.is_symlink():
        raise SkillError("target and backup directories cannot be symlinks")
    if any(item["action"] == "conflict" for item in plan):
        raise SkillError("edited or untracked installed copies conflict; provide a reviewed current hash to replace")
    if all(item["action"] == "unchanged" for item in plan):
        return None
    with target_lock(target, backup):
        return _apply_install(target, backup, plan)

def _apply_install(target: Path, backup: Path, plan):
    ensure_backup_location(target, backup)
    if any(item["action"] == "conflict" for item in plan):
        raise SkillError("edited or untracked installed copies conflict; provide a reviewed current hash to replace")
    changes = [item for item in plan if item["action"] != "unchanged"]
    if not changes:
        return None
    transaction = backup / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    transaction.mkdir(parents=True)
    target.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".marketing-skills-stage-", dir=target.parent))
    journal_path = transaction / "transaction.json"
    journal = {"schema_version": 1, "target": str(target.resolve()), "status": "prepared", "skills": []}
    moved = []
    try:
        # Verify everything and prepare every backup before modifying any installed skill.
        for item in changes:
            ident = item["id"]
            destination = target / ident
            if existing_hash(destination) != item["current_sha256"]:
                raise SkillError(f"installed copy changed since review: {ident}")
            fresh = stage / (ident + ".new")
            fresh.mkdir()
            for name, data in item["payload"].items():
                path = fresh.joinpath(*safe_relative(name).parts)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            if existing_hash(fresh) != item["next_sha256"]:
                raise SkillError("staged resource checksum mismatch")
            previous = transaction / "backups" / ident
            if destination.exists():
                previous.parent.mkdir(exist_ok=True)
                shutil.copytree(destination, previous)
                if existing_hash(previous) != item["current_sha256"]:
                    raise SkillError("backup verification failed")
            journal["skills"].append({"id": ident, "previous_sha256": item["current_sha256"], "installed_sha256": item["next_sha256"], "backup": str(previous) if destination.exists() else None})
        atomic_json(journal_path, journal)
        for item in changes:
            ident = item["id"]
            destination, previous = target / ident, stage / (ident + ".old")
            # Recheck immediately before swap; no stale baseline may authorize data loss.
            if existing_hash(destination) != item["current_sha256"]:
                raise SkillError(f"installed copy changed during transaction: {ident}")
            if destination.exists():
                os.replace(destination, previous)
            moved.append((destination, previous))
            os.replace(stage / (ident + ".new"), destination)
        journal["status"] = "committed"
        atomic_json(journal_path, journal)
        state = {"schema_version": 1, "target": str(target.resolve()), "skills": {item["id"]: {"content_sha256": item["next_sha256"], "version": item["row"]["version"]} for item in plan}}
        atomic_json(transaction / "installed-state.json", state)
        return journal_path
    except BaseException:
        for destination, previous in reversed(moved):
            if destination.exists():
                shutil.rmtree(destination)
            if previous.exists():
                os.replace(previous, destination)
        journal["status"] = "failed-restored"
        atomic_json(journal_path, journal)
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)

def rollback(journal_path: Path, apply=False):
    if not apply:
        return _rollback(journal_path, False)
    journal = json.loads(journal_path.read_text())
    with target_lock(Path(journal["target"]), journal_path.parent.parent):
        return _rollback(journal_path, True)

def _rollback(journal_path: Path, apply=False):
    journal = json.loads(journal_path.read_text())
    if journal.get("schema_version") != 1 or journal.get("status") != "committed":
        raise SkillError("only a committed transaction can be rolled back")
    target = Path(journal["target"])
    if target.is_symlink():
        raise SkillError("target directory is a symlink")
    # Tampered journal must not redirect backups outside its transaction directory.
    for item in journal["skills"]:
        safe_relative(item["id"])
        if len(Path(item["id"]).parts) != 1:
            raise SkillError("unsafe journal ID")
        if existing_hash(target / item["id"]) != item["installed_sha256"]:
            raise SkillError(f"installed copy edited after transaction; rollback refused: {item['id']}")
        if item["backup"]:
            source = Path(item["backup"])
            if source.resolve() != (journal_path.parent / "backups" / item["id"]).resolve():
                raise SkillError("backup path does not match transaction")
            if existing_hash(source) != item["previous_sha256"]:
                raise SkillError("backup checksum mismatch")
    if not apply:
        return {"action": "rollback-preview", "skills": [i["id"] for i in journal["skills"]]}
    stage = Path(tempfile.mkdtemp(prefix=".marketing-skills-rollback-", dir=target.parent))
    moved = []
    try:
        for item in journal["skills"]:
            ident = item["id"]
            if item["backup"]:
                shutil.copytree(item["backup"], stage / (ident + ".restore"))
        for item in journal["skills"]:
            ident = item["id"]
            destination = target / ident
            if existing_hash(destination) != item["installed_sha256"]:
                raise SkillError(f"installed copy changed during rollback: {ident}")
            os.replace(destination, stage / (ident + ".current"))
            moved.append(item)
            if item["backup"]:
                os.replace(stage / (ident + ".restore"), destination)
        journal["status"] = "rolled-back"
        atomic_json(journal_path, journal)
        return {"action": "rolled-back", "skills": [i["id"] for i in journal["skills"]]}
    except BaseException:
        for item in reversed(moved):
            destination = target / item["id"]
            if destination.exists():
                shutil.rmtree(destination)
            os.replace(stage / (item["id"] + ".current"), destination)
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--manifest-sha256", help="Expected manifest hash from the reviewed immutable release")
    parser.add_argument("--target-dir", type=Path)
    parser.add_argument("--ids", help="Explicit comma-separated allowlist; no implicit all-skills installation")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--replace-edited", action="append", default=[], metavar="ID=REVIEWED_SHA256")
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--rollback", type=Path)
    parser.add_argument("--apply", action="store_true", help="Apply a reviewed plan; default only previews")
    args = parser.parse_args()
    try:
        if args.rollback:
            print(json.dumps(rollback(args.rollback.resolve(), args.apply), indent=2))
            return 0
        if not args.manifest or not args.target_dir or not args.ids:
            parser.error("--manifest, --target-dir and --ids are required")
        if args.manifest_sha256 and sha256(args.manifest.read_bytes()) != args.manifest_sha256:
            raise SkillError("manifest differs from reviewed release checksum")
        target = args.target_dir.expanduser().absolute()
        if target.is_symlink():
            raise SkillError("skill root cannot be a symlink")
        reviewed = {}
        for item in args.replace_edited:
            key, value = item.split("=", 1)
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise SkillError("reviewed replacement requires exact SHA256")
            reviewed[key] = value
        plan = plan_install(args.manifest.resolve(), target, args.ids.split(","), read_baseline(args.baseline), reviewed)
        public = [{k: v for k, v in item.items() if k not in {"row", "payload"}} for item in plan]
        print(json.dumps({"mode": "apply" if args.apply else "dry-run", "skills": public}, indent=2))
        if args.apply:
            if not args.backup_dir:
                parser.error("--backup-dir outside the skill root is required for --apply")
            journal = apply_install(target, args.backup_dir.expanduser().absolute(), plan)
            print(json.dumps({"transaction": str(journal) if journal else None}))
        return 2 if any(item["action"] == "conflict" for item in plan) else 0
    except (SkillError, OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
