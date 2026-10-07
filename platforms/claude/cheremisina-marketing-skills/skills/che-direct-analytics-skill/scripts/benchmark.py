#!/usr/bin/env python3
"""Internal cohort benchmarking only; no external peer data is inferred."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from analyze import BUSINESS_METRICS, DIRECT_METRICS, aggregate, data_status, load_dimension_rows, parse_period
from db import CacheDB
from setup import load_config, resolve_project


METRICS = ("DirectCTR", "DirectCPC", "CrossSourceROAS", "CrossSourceDRR", "MetrikaCPA", "MetrikaCR", "AOV")


def percentile(values: list[float], point: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * point
    lower, upper = int(position), min(int(position) + 1, len(values) - 1)
    return round(values[lower] + (values[upper] - values[lower]) * (position - lower), 4)


def cohort_for(row: dict[str, Any], rules: dict[str, Any]) -> str:
    name = str(row.get("CampaignName", ""))
    labels = [f"type:{row.get('CampaignType') or 'unknown'}"]
    for label, pattern in rules.items():
        if isinstance(pattern, str) and re.search(pattern, name, re.IGNORECASE):
            labels.append(label)
    return " | ".join(labels)


def build_benchmark(db: CacheDB, project: str, config: dict[str, Any], date_from: date, date_to: date) -> dict[str, Any]:
    records = load_dimension_rows(db, "campaign", date_from.isoformat(), date_to.isoformat())
    campaign_rows = aggregate(records, "campaign")
    raw_by_campaign = {str(row.get("CampaignName")): row for row in records}
    rules = config.get("COHORT_RULES", {}) if isinstance(config.get("COHORT_RULES", {}), dict) else {}
    cohorts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in campaign_rows:
        metadata = raw_by_campaign.get(str(row["campaign"]), {})
        cohorts[cohort_for(metadata, rules)].append(row)
    result = []
    for cohort, rows in sorted(cohorts.items()):
        summary: dict[str, Any] = {"cohort": cohort, "n": len(rows)}
        for metric in METRICS:
            values = [float(row[metric]) for row in rows if row.get(metric) is not None]
            summary[metric] = {"n": len(values), "p25": percentile(values, .25), "median": percentile(values, .5), "p75": percentile(values, .75)}
        result.append(summary)
    return {
        "kind": "internal_benchmark", "project": project, "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "read_only": True, "external_peer_data": False, "data_status": data_status(db, "campaign", date_from, date_to, config),
        "cohorts": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Internal Direct + Metrika cohort benchmark")
    parser.add_argument("--project")
    parser.add_argument("--period", default="30d")
    parser.add_argument("--date_from")
    parser.add_argument("--date_to")
    parser.add_argument("--format", choices=("json", "html"), default="json")
    args = parser.parse_args()
    project = resolve_project(args.project)
    date_from, date_to = (date.fromisoformat(args.date_from), date.fromisoformat(args.date_to)) if args.date_from and args.date_to else parse_period(args.period, date.today())
    with CacheDB(project) as db:
        record = build_benchmark(db, project, load_config(project), date_from, date_to)
    if args.format == "html":
        destination = Path("/tmp") / f"direct_benchmark_{date_from}_{date_to}.html"
        destination.write_text("<!doctype html><meta charset=\"utf-8\"><pre>" + html.escape(json.dumps(record, ensure_ascii=False, indent=2)) + "</pre>", encoding="utf-8")
        print(destination)
    else:
        print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
