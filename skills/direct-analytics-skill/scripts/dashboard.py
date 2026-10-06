#!/usr/bin/env python3
"""Validate a constrained ReportSpec and render a reproducible dashboard payload."""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from analyze import BUSINESS_METRICS, DIMENSIONS, DIRECT_METRICS, aggregate, data_status, load_dimension_rows, parse_period
from db import CacheDB
from setup import load_config, resolve_project


ALLOWED_METRICS = set(DIRECT_METRICS) | set(BUSINESS_METRICS)
ALLOWED_CHARTS = {"table", "line", "bar"}


def load_report_spec(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("ReportSpec must be a JSON object")
    return value


def validate_report_spec(spec: dict[str, Any]) -> dict[str, Any]:
    dimension = spec.get("dimension")
    metrics = spec.get("metrics")
    chart = spec.get("chart", "table")
    if dimension not in DIMENSIONS:
        raise ValueError(f"Unknown dimension: {dimension}")
    if not isinstance(metrics, list) or not metrics or any(metric not in ALLOWED_METRICS for metric in metrics):
        raise ValueError("metrics must be a non-empty list of registered metrics")
    if chart not in ALLOWED_CHARTS:
        raise ValueError(f"chart must be one of: {', '.join(sorted(ALLOWED_CHARTS))}")
    if not ((spec.get("date_from") and spec.get("date_to")) or spec.get("period")):
        raise ValueError("ReportSpec requires date_from + date_to or period")
    return {"dimension": dimension, "metrics": metrics, "chart": chart, "top": int(spec.get("top", 0))}


def build_dashboard(db: CacheDB, project: str, config: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    valid = validate_report_spec(spec)
    if spec.get("date_from") and spec.get("date_to"):
        date_from, date_to = date.fromisoformat(spec["date_from"]), date.fromisoformat(spec["date_to"])
    else:
        date_from, date_to = parse_period(str(spec["period"]), date.today())
    rows = aggregate(load_dimension_rows(db, valid["dimension"], date_from.isoformat(), date_to.isoformat()), valid["dimension"])
    if valid["top"]:
        rows = rows[:valid["top"]]
    return {
        "kind": "dashboard", "project": project, "read_only": True,
        "query_spec": {**valid, "date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
        "data_status": data_status(db, valid["dimension"], date_from, date_to, config),
        "rows": [{valid["dimension"]: row[valid["dimension"]], **{metric: row.get(metric) for metric in valid["metrics"]}} for row in rows],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Constrained, reproducible Direct analytics dashboard")
    parser.add_argument("--project")
    parser.add_argument("--spec", required=True, help="Path to a validated ReportSpec JSON")
    parser.add_argument("--format", choices=("json", "html"), default="json")
    args = parser.parse_args()
    project = resolve_project(args.project)
    with CacheDB(project) as db:
        report = build_dashboard(db, project, load_config(project), load_report_spec(args.spec))
    if args.format == "html":
        destination = Path("/tmp") / "direct_dashboard.html"
        destination.write_text("<!doctype html><meta charset=\"utf-8\"><pre>" + html.escape(json.dumps(report, ensure_ascii=False, indent=2)) + "</pre>", encoding="utf-8")
        print(destination)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
