#!/usr/bin/env python3
"""Evaluate read-only diagnosis calibration against explicit analyst feedback."""

from __future__ import annotations

import argparse
import html
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from db import CacheDB
from setup import resolve_project


def _complete_data_status(status: object) -> bool:
    if not isinstance(status, dict):
        return False
    if "complete" in status:
        return bool(status["complete"])
    coverage = status.get("coverage")
    return bool(isinstance(coverage, dict) and coverage.get("complete"))


def _has_evidence(record: dict[str, Any]) -> bool:
    return bool(record.get("trigger") and record.get("funnel") and (
        record.get("confirmed_causes") or record.get("likely_drivers") or record.get("hypotheses")
    ))


def _hours_between(created_at: object, feedback_at: object) -> float | None:
    if not isinstance(created_at, str) or not isinstance(feedback_at, str):
        return None
    try:
        return round((datetime.fromisoformat(feedback_at) - datetime.fromisoformat(created_at)).total_seconds() / 3600, 4)
    except ValueError:
        return None


def evaluate_shadow(records: list[dict[str, Any]], minimum_cases: int = 10) -> dict[str, Any]:
    completed = [item for item in records if item.get("verdict") in {"confirmed", "partial", "refuted"}]
    missing = []
    claim_records = []
    high_priority = []
    verdict_hours = []
    for item in completed:
        record = item.get("record", {})
        problems = []
        if not _complete_data_status(record.get("data_status")):
            problems.append("data_status_incomplete")
        if not _has_evidence(record):
            problems.append("evidence_trail_missing")
        if problems:
            missing.append({"run_id": item["run_id"], "problems": problems})
        if record.get("confirmed_causes"):
            claim_records.append(item)
        if record.get("trigger", {}).get("priority") == "high":
            high_priority.append(item)
        duration = _hours_between(item.get("created_at"), item.get("feedback_created_at"))
        if duration is not None:
            verdict_hours.append(duration)

    confirmed = sum(item["verdict"] == "confirmed" for item in completed)
    refuted_claims = sum(item["verdict"] == "refuted" for item in claim_records)
    confirmed_high = sum(item["verdict"] == "confirmed" for item in high_priority)
    passed = len(completed) >= minimum_cases and not missing
    return {
        "kind": "shadow_mode_gate",
        "read_only": True,
        "minimum_cases": minimum_cases,
        "eligible_cases": len(completed),
        "gate": "passed" if passed else "blocked",
        "missing_requirements": missing,
        "metrics": {
            "confirmed_cause_rate": round(confirmed / len(completed), 4) if completed else None,
            "false_certainty_rate": round(refuted_claims / len(claim_records), 4) if claim_records else None,
            "high_priority_precision": round(confirmed_high / len(high_priority), 4) if high_priority else None,
            "high_priority_sample_size": len(high_priority),
            "median_hours_to_human_verdict": round(statistics.median(verdict_hours), 4) if verdict_hours else None,
        },
        "definitions": {
            "confirmed_cause_rate": "Share of feedback verdicts marked confirmed.",
            "false_certainty_rate": "Share of explicit confirmed-cause claims later refuted by an analyst.",
            "high_priority_precision": "Share of high-priority diagnoses later confirmed; null until such cases exist.",
            "median_hours_to_human_verdict": "Elapsed time from stored diagnosis to saved analyst verdict, not model training data.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the ten-case shadow-mode gate without modifying campaigns")
    parser.add_argument("--project")
    parser.add_argument("--minimum-cases", type=int, default=10)
    parser.add_argument("--format", choices=("json", "html"), default="json")
    args = parser.parse_args()
    if args.minimum_cases < 1:
        parser.error("--minimum-cases must be positive")
    project = resolve_project(args.project)
    with CacheDB(project) as db:
        report = evaluate_shadow(db.feedback_records(), args.minimum_cases)
    if args.format == "html":
        destination = Path("/tmp") / "direct_shadow_gate.html"
        destination.write_text("<!doctype html><meta charset=\"utf-8\"><pre>" + html.escape(json.dumps(report, ensure_ascii=False, indent=2)) + "</pre>", encoding="utf-8")
        print(destination)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
