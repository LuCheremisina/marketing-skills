#!/usr/bin/env python3
"""Validate the mandatory Wordstat project registry without external packages."""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


TOP_LEVEL = [
    "schema_version", "project", "products_services", "product_categories",
    "audiences", "customer_jobs", "existing_urls", "themes",
    "relevance_policy", "thresholds", "clustering_rules", "change_log",
]
STATUSES = {"draft", "active", "paused", "retired"}
PRIORITIES = {"high", "medium", "low"}
INTENTS = {
    "informational_definition", "informational_howto", "commercial_research",
    "transactional", "navigational", "support", "education", "job", "news",
}


def is_url(value):
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except (TypeError, ValueError):
        return False


def validate_registry(data, require_confirmed=False):
    errors, warnings = [], []
    for key in TOP_LEVEL:
        if key not in data:
            errors.append(f"MISSING_TOP_LEVEL:{key}")

    if errors:
        return errors, warnings
    if data.get("schema_version") != "2.0":
        errors.append("UNSUPPORTED_SCHEMA_VERSION:expected 2.0")

    project = data.get("project", {})
    for key in ("id", "name", "domain", "registry_status", "regions", "devices", "monitoring_frequency"):
        if not project.get(key):
            errors.append(f"MISSING_PROJECT_FIELD:{key}")
    if project.get("registry_status") not in {"draft", "confirmed"}:
        errors.append("INVALID_REGISTRY_STATUS:use draft or confirmed")
    if require_confirmed and project.get("registry_status") != "confirmed":
        errors.append("REGISTRY_NOT_CONFIRMED")
    regions = project.get("regions", [])
    if not isinstance(regions, list) or not regions:
        errors.append("EMPTY_REGIONS")
    else:
        for i, region in enumerate(regions):
            if not region.get("name") or not isinstance(region.get("region_id"), int):
                errors.append(f"INVALID_REGION:{i}")
    devices = project.get("devices", [])
    if not isinstance(devices, list) or not devices or any(x not in {"all", "desktop", "phone", "tablet"} for x in devices):
        errors.append("INVALID_DEVICES")

    collections = {
        "products_services": data.get("products_services"),
        "product_categories": data.get("product_categories"),
        "audiences": data.get("audiences"),
        "customer_jobs": data.get("customer_jobs"),
        "existing_urls": data.get("existing_urls"),
    }
    for name, items in collections.items():
        if not isinstance(items, list) or not items:
            errors.append(f"EMPTY_REQUIRED_COLLECTION:{name}")

    all_ids = {}
    for name in ("products_services", "product_categories", "audiences", "customer_jobs"):
        for i, item in enumerate(data.get(name, [])):
            item_id = item.get("id")
            if not item_id:
                errors.append(f"MISSING_ID:{name}[{i}]")
            elif item_id in all_ids:
                errors.append(f"DUPLICATE_ID:{item_id}")
            else:
                all_ids[item_id] = name
            if item.get("status") not in STATUSES:
                errors.append(f"INVALID_STATUS:{item_id or name}[{i}]")

    product_ids = {x.get("id") for x in data.get("products_services", [])}
    audience_ids = {x.get("id") for x in data.get("audiences", [])}
    job_ids = {x.get("id") for x in data.get("customer_jobs", [])}

    for item in data.get("products_services", []):
        if item.get("priority") not in PRIORITIES:
            errors.append(f"INVALID_PRIORITY:{item.get('id')}")
        if item.get("status") == "active" and not item.get("seed_phrases"):
            errors.append(f"EMPTY_ACTIVE_SEEDS:{item.get('id')}")
        for url in item.get("urls", []):
            if not is_url(url):
                errors.append(f"INVALID_URL:{item.get('id')}:{url}")

    for item in data.get("product_categories", []):
        if item.get("priority") not in PRIORITIES:
            errors.append(f"INVALID_PRIORITY:{item.get('id')}")
        if item.get("status") == "active" and not item.get("seed_phrases"):
            errors.append(f"EMPTY_ACTIVE_SEEDS:{item.get('id')}")
        for ref in item.get("product_ids", []):
            if ref not in product_ids:
                errors.append(f"UNKNOWN_PRODUCT_REF:{item.get('id')}:{ref}")

    for item in data.get("audiences", []):
        for ref in item.get("customer_job_ids", []):
            if ref not in job_ids:
                errors.append(f"UNKNOWN_JOB_REF:{item.get('id')}:{ref}")

    for item in data.get("customer_jobs", []):
        if item.get("priority") not in PRIORITIES:
            errors.append(f"INVALID_PRIORITY:{item.get('id')}")
        if item.get("status") == "active" and not item.get("seed_phrases"):
            errors.append(f"EMPTY_ACTIVE_SEEDS:{item.get('id')}")
        for ref in item.get("audience_ids", []):
            if ref not in audience_ids:
                errors.append(f"UNKNOWN_AUDIENCE_REF:{item.get('id')}:{ref}")
        for ref in item.get("product_ids", []):
            if ref not in product_ids:
                errors.append(f"UNKNOWN_PRODUCT_REF:{item.get('id')}:{ref}")

    for i, item in enumerate(data.get("existing_urls", [])):
        if not is_url(item.get("url")):
            errors.append(f"INVALID_EXISTING_URL:{i}")
        if item.get("intent") not in INTENTS:
            errors.append(f"INVALID_URL_INTENT:{item.get('url')}")
        for ref in item.get("product_ids", []):
            if ref not in product_ids:
                errors.append(f"UNKNOWN_PRODUCT_REF:{item.get('url')}:{ref}")

    themes = data.get("themes", {})
    required = themes.get("required")
    forbidden = themes.get("forbidden")
    if not isinstance(required, list):
        errors.append("INVALID_REQUIRED_THEMES")
        required = []
    if not isinstance(forbidden, list):
        errors.append("INVALID_FORBIDDEN_THEMES")
        forbidden = []
    if not required:
        warnings.append("NO_REQUIRED_THEMES")
    if not forbidden:
        warnings.append("NO_FORBIDDEN_THEMES")
    theme_ids = set()
    for item in required + forbidden:
        item_id = item.get("id")
        if not item_id:
            errors.append("MISSING_THEME_ID")
        elif item_id in theme_ids or item_id in all_ids:
            errors.append(f"DUPLICATE_ID:{item_id}")
        theme_ids.add(item_id)
    for item in required:
        if item.get("status") not in STATUSES:
            errors.append(f"INVALID_STATUS:{item.get('id')}")
        if item.get("status") == "active" and not item.get("seed_phrases"):
            errors.append(f"EMPTY_ACTIVE_SEEDS:{item.get('id')}")
    for item in forbidden:
        if not item.get("pattern") or item.get("match_type") not in {"exact", "contains", "regex"}:
            errors.append(f"INVALID_FORBIDDEN_RULE:{item.get('id')}")

    policy = data.get("relevance_policy", {})
    levels = policy.get("levels", {})
    for name in ("direct", "adjacent", "exploratory", "irrelevant"):
        value = levels.get(name)
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            errors.append(f"INVALID_RELEVANCE_LEVEL:{name}")
    minimum = policy.get("minimum_auto_include")
    if not isinstance(minimum, (int, float)) or not 0 <= minimum <= 1:
        errors.append("INVALID_MINIMUM_AUTO_INCLUDE")

    thresholds = data.get("thresholds", {})
    for key in ("min_volume_default", "top_requests_limit", "max_representative_queries", "max_unreviewed_candidates"):
        value = thresholds.get(key)
        if not isinstance(value, int) or value < 0:
            errors.append(f"INVALID_THRESHOLD:{key}")
    if isinstance(thresholds.get("top_requests_limit"), int) and thresholds["top_requests_limit"] > 2000:
        errors.append("TOP_REQUESTS_LIMIT_TOO_HIGH")
    if isinstance(thresholds.get("max_representative_queries"), int) and not 1 <= thresholds["max_representative_queries"] <= 10:
        errors.append("INVALID_MAX_REPRESENTATIVE_QUERIES")

    rules = data.get("clustering_rules", {})
    for key in ("merge_required_fields", "split_on", "intent_taxonomy", "stable_id_format", "canonical_selection_order"):
        if not rules.get(key):
            errors.append(f"MISSING_CLUSTERING_RULE:{key}")
    taxonomy = set(rules.get("intent_taxonomy", []))
    if taxonomy != INTENTS:
        errors.append("INTENT_TAXONOMY_MUST_MATCH_CLOSED_LIST")
    if not isinstance(data.get("change_log"), list):
        errors.append("INVALID_CHANGE_LOG")
    return errors, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("registry")
    parser.add_argument("--require-confirmed", action="store_true")
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID_JSON:{exc}", file=sys.stderr)
        return 1
    errors, warnings = validate_registry(data, args.require_confirmed)
    for warning in warnings:
        print(f"WARNING {warning}")
    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        print(f"INVALID errors={len(errors)} warnings={len(warnings)}", file=sys.stderr)
        return 1
    print(f"VALID errors=0 warnings={len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
