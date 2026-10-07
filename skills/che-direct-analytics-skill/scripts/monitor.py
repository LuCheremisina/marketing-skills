#!/usr/bin/env python3
"""Local proactive monitor; emits JSON/HTML and never sends or changes anything."""

from __future__ import annotations

import argparse
import html
import json
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from analyze import BUSINESS_METRICS, DIRECT_METRICS, aggregate, data_status, load_dimension_rows, number
from db import CacheDB
from setup import load_config, resolve_project


AVAILABLE_METRICS = set(DIRECT_METRICS) | set(BUSINESS_METRICS)


def robust_baseline(values: list[float]) -> dict[str, float | None]:
    if len(values) < 4:
        return {"median": None, "mad": None}
    median = statistics.median(values)
    mad = statistics.median([abs(value - median) for value in values])
    return {"median": median, "mad": mad}


def modified_z_score(value: float, median: float | None, mad: float | None) -> float | None:
    if median is None or mad in (None, 0):
        return None
    return round(0.6745 * (value - median) / mad, 4)


def daily_totals(db: CacheDB, start: date, end: date) -> dict[str, dict[str, Any]]:
    rows = load_dimension_rows(db, "day", start.isoformat(), end.isoformat())
    return {row["day"]: row for row in aggregate(rows, "day")}


def baseline_dates(target: date) -> list[str]:
    return [(target - timedelta(days=7 * step)).isoformat() for step in range(1, 5)]


def build_monitor_record(db: CacheDB, project: str, config: dict[str, Any], target: date) -> dict[str, Any]:
    dates = baseline_dates(target)
    totals = daily_totals(db, min(date.fromisoformat(day) for day in dates), target)
    target_row = totals.get(target.isoformat())
    status = data_status(db, "day", target, target, config)
    baseline_quality_complete = all(
        data_status(db, "day", date.fromisoformat(day), date.fromisoformat(day), config)["coverage"]["complete"]
        for day in dates
    )
    metrics = [metric for metric in config.get("MONITOR_METRICS", []) if metric in AVAILABLE_METRICS]
    guardrails = config.get("GUARDRAILS", {}) if isinstance(config.get("GUARDRAILS", {}), dict) else {}
    results = []
    for metric in metrics:
        baseline_values = [number(totals[day].get(metric)) for day in dates if day in totals and totals[day].get(metric) is not None]
        current = target_row.get(metric) if target_row else None
        baseline = robust_baseline(baseline_values)
        z_score = modified_z_score(number(current), baseline["median"], baseline["mad"]) if current is not None else None
        delta = number(current) - number(baseline["median"]) if current is not None and baseline["median"] is not None else None
        rule = guardrails.get(metric, {}) if isinstance(guardrails.get(metric, {}), dict) else {}
        min_impact = rule.get("min_abs_delta")
        material = min_impact is not None and delta is not None and abs(delta) >= number(min_impact)
        anomaly = z_score is not None and abs(z_score) >= 3.5
        quality_ok = bool(status["coverage"]["complete"] and baseline_quality_complete)
        severity = "high" if anomaly and material and quality_ok else ("suppressed" if anomaly else "none")
        results.append({
            "metric": metric, "current": current, "baseline_dates": dates, "baseline_values": baseline_values,
            "median": baseline["median"], "mad": baseline["mad"], "modified_z_score": z_score,
            "absolute_delta": delta, "min_abs_delta": min_impact, "material": material,
            "severity": severity, "reason": "high requires MAD anomaly, project materiality and complete current and baseline data coverage",
        })
    return {
        "kind": "monitor_record", "project": project, "target_date": target.isoformat(), "read_only": True,
        "data_status": {"target": status, "baseline_complete": baseline_quality_complete},
        "baseline_status": "ready" if target_row and baseline_quality_complete and results and all(len(item["baseline_values"]) >= 4 for item in results) else "baseline_insufficient",
        "metrics": results, "delivery": "cli_json_or_html_only",
    }


def render_html(record: dict[str, Any]) -> str:
    return "<!doctype html><meta charset=\"utf-8\"><title>Direct monitor</title><style>body{font-family:Arial;padding:20px}pre{white-space:pre-wrap;background:#f5f5f5;padding:12px}</style><h1>Read-only monitor</h1><pre>" + html.escape(json.dumps(record, ensure_ascii=False, indent=2)) + "</pre>"


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only Direct + Metrika proactive monitor")
    parser.add_argument("--project")
    parser.add_argument("--date", help="Completed date YYYY-MM-DD; default yesterday")
    parser.add_argument("--format", choices=("json", "html"), default="json")
    args = parser.parse_args()
    project = resolve_project(args.project)
    target = date.fromisoformat(args.date) if args.date else date.today() - timedelta(days=1)
    with CacheDB(project) as db:
        record = build_monitor_record(db, project, load_config(project), target)
    if args.format == "html":
        destination = Path("/tmp") / f"direct_monitor_{target.isoformat()}.html"
        destination.write_text(render_html(record), encoding="utf-8")
        print(destination)
    else:
        print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
