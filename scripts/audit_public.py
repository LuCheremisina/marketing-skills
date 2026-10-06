#!/usr/bin/env python3
"""Scan the entire public tree and release archives for private data without printing matches.

This deterministic red-flag check complements human anonymization review; binary imagery
and arbitrary business facts cannot be proved anonymous by regular expressions.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import stat
import sys
import zipfile
from common import ROOT, safe_relative, SkillError, json_write

IGNORED = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules", ".DS_Store"}
PRIVATE_DIRS = {"evidence", "private", "backups", ".skill-governance-backups", ".ssh", ".aws", ".gnupg"}
SYNTHETIC_MAILBOXES = {
    "user@gmail.com", "anything@that-domain.com", "dmarc-reports@yourdomain.com",
    "noreply@app.com", "bad@nonexistent.com", "slow@recipient.com",
    "notifications@yourdomain.com", "agent@yourdomain.com", "developer@company.com",
    "team@company.com", "support@yourdomain.com", "your@email.com", "reply@yourdomain.com",
}
EMAIL = re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9.-])")
PATTERNS = (
    ("private filesystem path", re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+(?:/|\b)")),
    ("private Windows path", re.compile(r"[A-Za-z]:\\+Users\\+[A-Za-z0-9._-]+", re.I)),
    ("personal cloud storage path", re.compile(r"GoogleDrive-[A-Za-z0-9@._-]+/")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("credential token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{32,}|xox[baprs]-[A-Za-z0-9-]{20,})\b")),
    ("literal credential", re.compile(r"(?im)\b(?:api_key|access_token|client_secret|password)\s*[:=]\s*[\"']([A-Za-z0-9+/=_-]{20,})[\"']")),
)
IDENTIFIER = re.compile(r"(?im)[\"']?\b(?:account|client|customer|counter|campaign|project|user)[_-]?id[\"']?\s*[:=]\s*[\"']?([0-9a-f]{7,40})\b")

def private_component(part):
    return part in PRIVATE_DIRS or part == ".env" or (part.startswith(".env.") and part not in {".env.example", ".env.template"})

def text_findings(text, original_notice=False):
    findings = []
    def add(label, start):
        findings.append({"reason": label, "line": text.count("\n", 0, start) + 1})
    for label, pattern in PATTERNS:
        for match in pattern.finditer(text):
            add(label, match.start())
    for match in EMAIL.finditer(text):
        address = match.group().lower()
        domain = address.rsplit("@", 1)[1]
        if address in SYNTHETIC_MAILBOXES or domain in {"example.com", "example.org", "example.net"} or domain.endswith((".example", ".invalid")):
            continue
        line = text[text.rfind("\n", 0, match.start()) + 1:text.find("\n", match.end()) if "\n" in text[match.end():] else len(text)]
        if original_notice and re.search(r"\bcopyright\b|\boriginal author\b|\bauthors?\b|\bpublisher\b", line, re.I):
            continue
        add("non-example mailbox; verify explicit original-source attribution", match.start())
    for match in IDENTIFIER.finditer(text):
        value = match.group(1)
        if len(set(value)) == 1 or value in "0123456789012345678901234567890" or value in "123456789012345678901234567890":
            continue
        add("literal account/client identifier", match.start())
    return findings

def inspect_bytes(label, data, issues, counters):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        counters["binary_files"] += 1
        return
    counters["text_files"] += 1
    pathpart = label.split("!", 1)[-1]
    original_notice = pathpart.startswith("vendor/skills/") and Path(pathpart).name.upper().startswith(("LICENSE", "COPYING", "NOTICE", "UPSTREAM"))
    for finding in text_findings(text, original_notice):
        issues.append({"path": label, **finding})

def inspect_archive(path, issues, counters):
    total = 0
    seen = set()
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            label = path.name + "!" + member.filename
            try:
                rel = safe_relative(member.filename)
                if member.filename in seen:
                    raise SkillError("duplicate archive member")
                seen.add(member.filename)
                if stat.S_ISLNK(member.external_attr >> 16):
                    raise SkillError("archive symlink")
                if any(private_component(part) for part in rel.parts):
                    raise SkillError("private evidence/profile path in archive")
                if member.is_dir():
                    continue
                total += member.file_size
                if total > 400 * 1024 * 1024:
                    raise SkillError("archive expansion exceeds limit")
                inspect_bytes(label, archive.read(member), issues, counters)
            except SkillError as exc:
                issues.append({"path": label, "reason": str(exc)})
    counters["archives"] += 1

def audit(root, archives_dir=None):
    root = root.resolve()
    issues = []
    counters = {"text_files": 0, "binary_files": 0, "archives": 0}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in IGNORED for part in rel.parts):
            continue
        if path.is_symlink():
            issues.append({"path": rel.as_posix(), "reason": "public tree symlink"})
            continue
        if any(private_component(part) for part in rel.parts):
            if path.is_file():
                issues.append({"path": rel.as_posix(), "reason": "private evidence/profile file in public tree"})
            continue
        if path.is_file():
            if zipfile.is_zipfile(path):
                try:
                    inspect_archive(path, issues, counters)
                except (OSError, zipfile.BadZipFile) as exc:
                    issues.append({"path": rel.as_posix(), "reason": "archive cannot be inspected: " + str(exc)})
            else:
                inspect_bytes(rel.as_posix(), path.read_bytes(), issues, counters)
    if archives_dir:
        for path in sorted(archives_dir.iterdir()):
            if path.suffix.lower() not in {".zip", ".skill"}:
                continue
            if path.is_symlink():
                issues.append({"path": path.name, "reason": "release archive symlink"})
                continue
            try:
                inspect_archive(path, issues, counters)
            except (OSError, zipfile.BadZipFile) as exc:
                issues.append({"path": path.name, "reason": "archive cannot be inspected: " + str(exc)})
    return {"ok": not issues, **counters, "issues": issues, "scope": "automated text red flags; human review of business context and binary imagery still required"}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--archives-dir", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    report = audit(args.root, args.archives_dir)
    if args.json:
        json_write(args.json, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1

if __name__ == "__main__":
    sys.exit(main())
