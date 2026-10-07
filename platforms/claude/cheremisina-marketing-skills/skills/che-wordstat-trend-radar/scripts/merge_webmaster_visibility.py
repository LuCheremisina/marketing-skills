#!/usr/bin/env python3
"""Join a Wordstat report with explicitly mapped Yandex Webmaster query metrics."""

import argparse
import json
from collections import defaultdict
from pathlib import Path


def clamp(value, low, high):
    return max(low, min(high, value))


def validate_rows(rows):
    flags = []
    required = {"query", "cluster_id", "url", "impressions", "clicks", "position"}
    for row in rows:
        missing = required - set(row)
        if missing:
            flags.append("missing_fields:" + ",".join(sorted(missing)))
            continue
        if float(row["impressions"]) < 0 or float(row["clicks"]) < 0:
            flags.append("negative_metrics")
        if float(row["clicks"]) > float(row["impressions"]):
            flags.append("clicks_exceed_impressions")
    return sorted(set(flags))


def merge(report, webmaster_rows):
    flags = validate_rows(webmaster_rows)
    grouped = defaultdict(lambda: {"impressions": 0.0, "clicks": 0.0, "positions": [], "urls": set(), "queries": set()})
    for row in webmaster_rows:
        if not {"query", "cluster_id", "url", "impressions", "clicks", "position"} <= set(row):
            continue
        target = grouped[row["cluster_id"]]
        target["impressions"] += float(row["impressions"])
        target["clicks"] += float(row["clicks"])
        target["positions"].append(float(row["position"]))
        target["urls"].add(row["url"])
        target["queries"].add(row["query"])
    output = []
    for result in report.get("results", []):
        metrics = grouped.get(result.get("id"))
        signal, coverage = result.get("signal"), result.get("coverage", {}).get("status", "gap")
        if not metrics or metrics["impressions"] == 0:
            action = "market_rising_no_page" if signal in {"breakout", "emerging", "rapid_growth", "growing"} and coverage in {"gap", "partial"} else None
            output.append({"cluster_id": result.get("id"), "visibility_action": action, "webmaster": None})
            continue
        impressions, clicks = metrics["impressions"], metrics["clicks"]
        ctr = clicks / impressions if impressions else 0.0
        position = sum(metrics["positions"]) / len(metrics["positions"])
        action = None
        if signal in {"breakout", "emerging", "rapid_growth", "growing"} and position > 10:
            action = "optimize_visibility"
        elif position <= 10 and ctr < 0.03 and impressions >= 50:
            action = "improve_ctr"
        elif signal in {"declining", "structural_decline"} and impressions > 0:
            action = "review_offer"
        output.append({"cluster_id": result.get("id"), "visibility_action": action, "webmaster": {"impressions": round(impressions), "clicks": round(clicks), "ctr": round(ctr, 4), "position": round(position, 2), "urls": sorted(metrics["urls"]), "queries": sorted(metrics["queries"])}})
    return {"project": report.get("project", {}), "data_quality_flags": flags, "results": output}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trend_report")
    parser.add_argument("webmaster_export")
    parser.add_argument("--json", required=True)
    args = parser.parse_args()
    report = json.loads(Path(args.trend_report).read_text(encoding="utf-8"))
    source = json.loads(Path(args.webmaster_export).read_text(encoding="utf-8"))
    rows = source.get("rows", source) if isinstance(source, (dict, list)) else []
    Path(args.json).write_text(json.dumps(merge(report, rows), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
