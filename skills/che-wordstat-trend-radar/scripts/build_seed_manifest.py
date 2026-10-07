#!/usr/bin/env python3
"""Build a deterministic Wordstat seed manifest from a confirmed registry."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from validate_registry import validate_registry


PRIORITY = {"low": 1, "medium": 2, "high": 3}


def normalize_phrase(value):
    return re.sub(r"\s+", " ", value.strip().lower())


def registry_fingerprint(data):
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def seed_id(phrase):
    digest = hashlib.sha1(phrase.encode("utf-8")).hexdigest()[:12]
    return f"seed:{digest}"


def build_manifest(data):
    errors, _ = validate_registry(data, require_confirmed=True)
    if errors:
        raise ValueError("Registry is not ready: " + ", ".join(errors))
    bucket = {}

    def add(item, source_type, force_monitor=False):
        if item.get("status") != "active":
            return
        source_id = item["id"]
        priority = item.get("priority", "high" if source_type == "required_theme" else "medium")
        for raw in item.get("seed_phrases", []):
            phrase = normalize_phrase(raw)
            if not phrase:
                continue
            entry = bucket.setdefault(phrase, {
                "seed_id": seed_id(phrase),
                "phrase": phrase,
                "status": "active",
                "priority": priority,
                "source_refs": [],
                "source_types": [],
                "force_monitor": False,
            })
            if PRIORITY[priority] > PRIORITY[entry["priority"]]:
                entry["priority"] = priority
            entry["source_refs"].append(source_id)
            entry["source_types"].append(source_type)
            entry["force_monitor"] = entry["force_monitor"] or force_monitor

    for item in data["products_services"]:
        add(item, "product_service")
    for item in data["product_categories"]:
        add(item, "product_category")
    for item in data["customer_jobs"]:
        add(item, "customer_job")
    for item in data["themes"]["required"]:
        add(item, "required_theme", bool(item.get("force_monitor")))

    seeds = []
    for phrase in sorted(bucket):
        entry = bucket[phrase]
        entry["source_refs"] = sorted(set(entry["source_refs"]))
        entry["source_types"] = sorted(set(entry["source_types"]))
        seeds.append(entry)
    return {
        "schema_version": "2.0",
        "project_id": data["project"]["id"],
        "registry_fingerprint": registry_fingerprint(data),
        "seeds": seeds,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("registry")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    try:
        manifest = build_manifest(data)
    except ValueError as exc:
        parser.error(str(exc))
    Path(args.output).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"SEEDS {len(manifest['seeds'])} -> {args.output}")


if __name__ == "__main__":
    main()
