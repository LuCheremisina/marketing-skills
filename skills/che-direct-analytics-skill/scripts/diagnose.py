#!/usr/bin/env python3
"""Evidence-first, read-only diagnostics for Direct + Metrika changes."""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from analyze import (
    BUSINESS_METRICS,
    DIRECT_METRICS,
    DIMENSIONS,
    add_period_delta,
    aggregate,
    data_status,
    load_dimension_rows,
    number,
    parse_period,
    shift_period,
)
from db import CacheDB
from setup import load_config, resolve_project


SUPPORTED_METRICS = set(DIRECT_METRICS) | set(BUSINESS_METRICS)


def _total(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tagged = []
    for row in rows:
        item = dict(row)
        item["_total"] = "TOTAL"
        tagged.append(item)
    return aggregate(tagged, "_total", "_total")[0] if tagged else {"_total": "TOTAL"}


def _safe_delta(current: Any, previous: Any) -> dict[str, float | None]:
    if current is None or previous is None:
        return {"absolute": None, "percent": None}
    absolute = number(current) - number(previous)
    return {
        "absolute": round(absolute, 4),
        "percent": round(absolute / abs(number(previous)) * 100, 2) if number(previous) else None,
    }


def _session_totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {"visits": 0.0, "users": 0.0, "goal_reaches": 0.0}
    for row in rows:
        totals["visits"] += number(row.get("ym:s:visits"))
        totals["users"] += number(row.get("ym:s:users"))
        totals["goal_reaches"] += sum(number(value) for key, value in row.items() if key.startswith("ym:s:goal") and key.endswith("reaches"))
    return {key: round(value, 4) for key, value in totals.items()}


def _funnel(current_campaign: list[dict[str, Any]], previous_campaign: list[dict[str, Any]], current_sessions: list[dict[str, Any]], previous_sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    current = _total(current_campaign)
    previous = _total(previous_campaign)
    current_session_total = _session_totals(current_sessions)
    previous_session_total = _session_totals(previous_sessions)
    stages = [
        ("serving", "Impressions", current.get("Impressions"), previous.get("Impressions")),
        ("click", "Clicks", current.get("Clicks"), previous.get("Clicks")),
        ("click_efficiency", "DirectCTR", current.get("DirectCTR"), previous.get("DirectCTR")),
        ("post_click", "MetrikaVisits", current_session_total["visits"], previous_session_total["visits"]),
        ("goal", "MetrikaGoalReaches", current_session_total["goal_reaches"], previous_session_total["goal_reaches"]),
        ("business", "MetrikaTransactions", current.get("MetrikaTransactions"), previous.get("MetrikaTransactions")),
        ("business", "MetrikaRevenue", current.get("MetrikaRevenue"), previous.get("MetrikaRevenue")),
        ("business_value", "AOV", current.get("AOV"), previous.get("AOV")),
    ]
    return [
        {"stage": stage, "metric": metric, "current": value, "previous": prior, "delta": _safe_delta(value, prior)}
        for stage, metric, value, prior in stages
    ]


def _confirmed_causes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    causes = []
    for row in rows:
        status = str(row.get("CampaignStatus") or "")
        if status and status != "ON":
            causes.append({
                "classification": "confirmed_cause",
                "campaign": row.get("CampaignName") or row.get("CampaignId"),
                "evidence": {"CampaignStatus": status, "CampaignState": row.get("CampaignState")},
                "statement": "Campaign status is not ON in the Direct campaign snapshot.",
            })
    return causes


def _drivers(current_rows: list[dict[str, Any]], previous_rows: list[dict[str, Any]], metric: str) -> list[dict[str, Any]]:
    current = aggregate(current_rows, "campaign")
    previous = aggregate(previous_rows, "campaign")
    add_period_delta(current, previous, "campaign")
    previous_index = {row["campaign"]: row for row in previous}
    account_delta = number(_total(current_rows).get(metric)) - number(_total(previous_rows).get(metric))
    result = []
    for row in current:
        prior = previous_index.get(row["campaign"], {})
        value, prior_value = row.get(metric), prior.get(metric)
        if value is None or prior_value is None:
            continue
        delta = number(value) - number(prior_value)
        if delta == 0:
            continue
        result.append({
            "classification": "likely_driver",
            "campaign": row["campaign"],
            "metric": metric,
            "current": value,
            "previous": prior_value,
            "delta": round(delta, 4),
            "contribution_share": round(delta / account_delta, 4) if account_delta else None,
            "evidence": "deterministic period comparison at the campaign grain",
            "not_a_causal_claim": True,
        })
    return sorted(result, key=lambda item: abs(item["delta"]), reverse=True)[:3]


def _hypotheses(funnel: list[dict[str, Any]], metric: str) -> list[dict[str, Any]]:
    negative = {item["metric"] for item in funnel if item["delta"]["absolute"] is not None and item["delta"]["absolute"] < 0}
    hypotheses = []
    if "Impressions" in negative:
        hypotheses.append({"classification": "hypothesis", "statement": "Serving or demand may have declined.", "next_read_only_test": "Inspect Direct campaign status, budget constraints and auction-demand diagnostics by campaign."})
    if "Clicks" in negative or "DirectCTR" in negative:
        hypotheses.append({"classification": "hypothesis", "statement": "Creative, query mix or position may have reduced click acquisition.", "next_read_only_test": "Collect keyword and ad scopes, then compare CTR and CPC against the same prior period."})
    if "MetrikaVisits" in negative or "MetrikaGoalReaches" in negative:
        hypotheses.append({"classification": "hypothesis", "statement": "Post-click measurement or landing-page behaviour may have changed.", "next_read_only_test": "Inspect Metrika session and goal facts by campaign; verify goal instrumentation separately."})
    if "MetrikaTransactions" in negative or "MetrikaRevenue" in negative or metric in {"MetrikaRevenue", "CrossSourceROAS"}:
        hypotheses.append({"classification": "hypothesis", "statement": "Checkout, product availability, conversion mix or attribution may explain the business-metric change.", "next_read_only_test": "Compare Metrika transactions and AOV, then review reconciliation coverage before changing spend."})
    return hypotheses or [{"classification": "hypothesis", "statement": "The available facts do not isolate a driver.", "next_read_only_test": "Collect the missing compatible scope or extend the date range before acting."}]


def build_diagnosis(
    db: CacheDB,
    project: str,
    config: dict[str, Any],
    metric: str,
    date_from: date,
    date_to: date,
    compare: str,
) -> dict[str, Any]:
    if metric not in SUPPORTED_METRICS:
        raise ValueError(f"Unsupported metric: {metric}")
    previous_from, previous_to = shift_period(date_from, date_to, compare)
    current_campaign = load_dimension_rows(db, "campaign", date_from.isoformat(), date_to.isoformat())
    previous_campaign = load_dimension_rows(db, "campaign", previous_from.isoformat(), previous_to.isoformat())
    current_sessions = db.load_facts("metrika", "sessions", date_from.isoformat(), date_to.isoformat())
    previous_sessions = db.load_facts("metrika", "sessions", previous_from.isoformat(), previous_to.isoformat())
    if not current_campaign or not previous_campaign:
        raise ValueError("Campaign reconciliation facts are required for both periods")
    current_total = _total(current_campaign)
    previous_total = _total(previous_campaign)
    trigger = {
        "metric": metric, "current": current_total.get(metric), "previous": previous_total.get(metric),
        "delta": _safe_delta(current_total.get(metric), previous_total.get(metric)),
    }
    current_status = data_status(db, "campaign", date_from, date_to, config)
    previous_status = data_status(db, "campaign", previous_from, previous_to, config)
    status = {
        "current": current_status,
        "previous": previous_status,
        "complete": bool(current_status["coverage"]["complete"] and previous_status["coverage"]["complete"]),
    }
    coverage_complete = status["complete"]
    record = {
        "project": project,
        "kind": "diagnosis_record",
        "read_only": True,
        "period": {"current": {"from": date_from.isoformat(), "to": date_to.isoformat()}, "previous": {"from": previous_from.isoformat(), "to": previous_to.isoformat()}, "compare": compare},
        "data_status": status,
        "trigger": trigger,
        "funnel": _funnel(current_campaign, previous_campaign, current_sessions, previous_sessions),
        "confirmed_causes": _confirmed_causes(current_campaign),
        "likely_drivers": _drivers(current_campaign, previous_campaign, metric) if coverage_complete else [],
        "hypotheses": [],
        "recommended_next_action": {
            "kind": "read_only_investigation",
            "statement": "Review the listed evidence and run the linked read-only test before changing a campaign.",
            "approval_required_for_any_campaign_change": True,
        },
    }
    record["hypotheses"] = _hypotheses(record["funnel"], metric)
    record["confidence"] = "moderate" if coverage_complete else "low"
    record["limitations"] = [
        "Direct and Metrika remain parallel sources; cross-source KPIs include only exact or configured estimated matches.",
        "Likely drivers are numerical contributions, not causal proof.",
    ]
    return record


def _html(record: dict[str, Any]) -> str:
    payload = html.escape(json.dumps(record, ensure_ascii=False, indent=2))
    return f"<!doctype html><meta charset=\"utf-8\"><title>Diagnosis</title><style>body{{font-family:Arial;padding:20px}}pre{{white-space:pre-wrap;background:#f5f5f5;padding:12px}}</style><h1>Read-only diagnosis</h1><pre>{payload}</pre>"


def _date_range(args: argparse.Namespace) -> tuple[date, date]:
    if args.date_from and args.date_to:
        return date.fromisoformat(args.date_from), date.fromisoformat(args.date_to)
    return parse_period(args.period, date.today())


def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence-first read-only diagnostics")
    subparsers = parser.add_subparsers(dest="command")
    diagnose_parser = subparsers.add_parser("run", help="Create diagnosis record")
    diagnose_parser.add_argument("--project")
    diagnose_parser.add_argument("--metric", required=True, choices=tuple(sorted(SUPPORTED_METRICS)))
    diagnose_parser.add_argument("--period", default="7d")
    diagnose_parser.add_argument("--date_from")
    diagnose_parser.add_argument("--date_to")
    diagnose_parser.add_argument("--compare", choices=("prev_period", "prev_year"), default="prev_period")
    diagnose_parser.add_argument("--format", choices=("json", "html"), default="json")
    feedback_parser = subparsers.add_parser("feedback", help="Attach human verdict")
    feedback_parser.add_argument("--project")
    feedback_parser.add_argument("--run-id", required=True)
    feedback_parser.add_argument("--verdict", choices=("confirmed", "partial", "refuted"), required=True)
    feedback_parser.add_argument("--actual-cause", required=True)
    feedback_parser.add_argument("--action-outcome")
    argv = sys.argv[1:]
    # Preserve the documented ergonomic form: diagnose.py --project ...
    if not argv or argv[0] not in {"run", "feedback"}:
        argv = ["run", *argv]
    args = parser.parse_args(argv)
    command = args.command
    project = resolve_project(args.project)
    with CacheDB(project) as db:
        if command == "feedback":
            db.save_feedback(args.run_id, args.verdict, args.actual_cause, args.action_outcome)
            print(json.dumps({"run_id": args.run_id, "verdict": args.verdict, "saved": True}, ensure_ascii=False))
            return
        date_from, date_to = _date_range(args)
        record = build_diagnosis(db, project, load_config(project), args.metric, date_from, date_to, args.compare)
        record["run_id"] = db.save_diagnosis(record)
    if args.format == "html":
        destination = Path("/tmp") / f"direct_diagnosis_{record['run_id']}.html"
        destination.write_text(_html(record), encoding="utf-8")
        print(destination)
    else:
        print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
