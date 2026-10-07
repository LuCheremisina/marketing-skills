#!/usr/bin/env python3
"""Read-only analysis over daily Direct and Metrika fact caches."""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from db import CacheDB
from setup import load_config, resolve_project


DIMENSIONS: dict[str, tuple[str, str, str]] = {
    "campaign": ("reconciliation", "campaign", "CampaignName"),
    "device": ("direct", "device", "DeviceType"),
    "region": ("direct", "region", "LocationOfPresenceName"),
    "keyword": ("direct", "keyword", "Criterion"),
    "placement": ("direct", "placement", "Placement"),
    "ad": ("direct", "ad", "AdId"),
    "day": ("reconciliation", "campaign", "Date"),
    "adnetwork": ("direct", "adnetwork", "AdNetworkType"),
}

DIRECT_METRICS = ("Impressions", "Clicks", "Cost", "DirectCTR", "DirectCPC")
BUSINESS_METRICS = ("MetrikaRevenue", "MetrikaTransactions", "CrossSourceROAS", "CrossSourceDRR", "MetrikaCPA", "MetrikaCR", "AOV")
RATIO_METRICS = {"DirectCTR", "DirectCPC", "CrossSourceROAS", "CrossSourceDRR", "MetrikaCPA", "MetrikaCR", "AOV"}
LABELS = {
    "Impressions": "Показы Direct", "Clicks": "Клики Direct", "Cost": "Расход Direct",
    "DirectCTR": "CTR Direct %", "DirectCPC": "CPC Direct",
    "MetrikaRevenue": "Выручка Метрики", "MetrikaTransactions": "Транзакции Метрики",
    "CrossSourceROAS": "ROAS Direct÷Метка %", "CrossSourceDRR": "ДРР Direct÷Метка %",
    "MetrikaCPA": "CPA Direct÷Метка", "MetrikaCR": "CR Click→Метка %", "AOV": "Средний чек Метрики",
}


def number(value: Any) -> float:
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


def _derived(group: dict[str, Any]) -> dict[str, Any]:
    impressions = group["Impressions"]
    clicks = group["Clicks"]
    cost = group["Cost"]
    business_rows = group["business_rows"]
    matched_cost = group["matched_cost"]
    revenue = group["MetrikaRevenue"]
    transactions = group["MetrikaTransactions"]
    output = {
        "Impressions": int(impressions),
        "Clicks": int(clicks),
        "Cost": round(cost, 2),
        "DirectCTR": round(clicks / impressions * 100, 4) if impressions else None,
        "DirectCPC": round(cost / clicks, 2) if clicks else None,
        "MetrikaRevenue": round(revenue, 2) if business_rows else None,
        "MetrikaTransactions": round(transactions, 4) if business_rows else None,
        "matched_direct_cost": round(matched_cost, 2) if business_rows else None,
        "attribution_coverage": round(business_rows / group["rows"], 4) if group["rows"] else 0,
    }
    if business_rows and matched_cost > 0:
        output["CrossSourceROAS"] = round(revenue / matched_cost * 100, 2)
        output["CrossSourceDRR"] = round(matched_cost / revenue * 100, 2) if revenue else None
        output["MetrikaCPA"] = round(matched_cost / transactions, 2) if transactions else None
        output["MetrikaCR"] = round(transactions / group["matched_clicks"] * 100, 4) if group["matched_clicks"] else None
        output["AOV"] = round(revenue / transactions, 2) if transactions else None
    else:
        output.update({metric: None for metric in ("CrossSourceROAS", "CrossSourceDRR", "MetrikaCPA", "MetrikaCR", "AOV")})
    return output


def aggregate(rows: list[dict[str, Any]], dimension: str, field: str | None = None) -> list[dict[str, Any]]:
    """Aggregate only compatible source facts; business KPIs remain separately labelled."""
    field = field or DIMENSIONS[dimension][2]
    groups: dict[str, dict[str, Any]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        key = str(row.get(field) or "—")
        group = groups[key]
        group["rows"] += 1
        for metric in ("Impressions", "Clicks", "Cost"):
            group[metric] += number(row.get(metric))
        if row.get("MetrikaRevenue") is not None and row.get("attribution_level") in {"exact", "estimated"}:
            group["business_rows"] += 1
            group["matched_cost"] += number(row.get("Cost"))
            group["matched_clicks"] += number(row.get("Clicks"))
            group["MetrikaRevenue"] += number(row.get("MetrikaRevenue"))
            group["MetrikaTransactions"] += number(row.get("MetrikaTransactions"))
    result = []
    for key, group in groups.items():
        item = {dimension: key, **_derived(group)}
        result.append(item)
    return sorted(result, key=lambda item: item["Cost"], reverse=True)


def shift_period(date_from: date, date_to: date, mode: str) -> tuple[date, date]:
    length = (date_to - date_from).days + 1
    if mode == "prev_period":
        return date_from - timedelta(days=length), date_to - timedelta(days=length)
    if mode == "prev_year":
        def previous_year(value: date) -> date:
            try:
                return value.replace(year=value.year - 1)
            except ValueError:  # 29 February
                return value.replace(year=value.year - 1, day=28)
        return previous_year(date_from), previous_year(date_to)
    raise ValueError(f"Unknown comparison mode: {mode}")


def add_period_delta(current: list[dict[str, Any]], previous: list[dict[str, Any]], dimension: str) -> list[dict[str, Any]]:
    previous_index = {str(item[dimension]): item for item in previous}
    for item in current:
        prior = previous_index.get(str(item[dimension]), {})
        for metric in (*DIRECT_METRICS, *BUSINESS_METRICS):
            value, prior_value = item.get(metric), prior.get(metric)
            if value is not None and prior_value not in (None, 0):
                item[f"{metric}_delta_pct"] = round((value - prior_value) / abs(prior_value) * 100, 2)
            else:
                item[f"{metric}_delta_pct"] = None
    return current


def total_row(rows: list[dict[str, Any]], dimension: str = "total") -> dict[str, Any]:
    """Calculate totals from source records, preserving matched-cost coverage."""
    raw = []
    for item in rows:
        record = dict(item)
        record["_"] = "TOTAL"
        raw.append(record)
    return aggregate(raw, dimension, "_")[0] if raw else {dimension: "TOTAL"}


def load_dimension_rows(db: CacheDB, dimension: str, date_from: str, date_to: str) -> list[dict[str, Any]]:
    source, scope, _ = DIMENSIONS[dimension]
    return db.load_facts(source, scope, date_from, date_to)


def data_status(db: CacheDB, dimension: str, date_from: date, date_to: date, config: dict[str, Any]) -> dict[str, Any]:
    source, scope, _ = DIMENSIONS[dimension]
    requirements = [(source, scope)]
    if source == "reconciliation":
        requirements.extend([("direct", "campaign"), ("metrika", "sessions"), ("metrika", "ecommerce")])
    return {
        "contract": {
            "timezone": config.get("REPORT_TIMEZONE", "Europe/Moscow"),
            "attribution_mode": config.get("ATTRIBUTION_MODE", "parallel"),
            "utm_source": config.get("UTM_SOURCE", "yandex"),
            "utm_medium": config.get("UTM_MEDIUM", "cpc"),
            "utm_campaign_mapping": config.get("UTM_CAMPAIGN_MAPPING", "campaign_id"),
            "currency": config.get("CURRENCY", "RUB"),
            "read_only": True,
        },
        "coverage": db.coverage(requirements, date_from, date_to),
        "metric_availability": {
            "direct": list(DIRECT_METRICS),
            "metrika_cross_source": list(BUSINESS_METRICS) if source == "reconciliation" else [],
        },
    }


def configured_alerts(rows: list[dict[str, Any]], config: dict[str, Any], dimension: str) -> list[dict[str, Any]]:
    """Apply only project-defined guardrails; there are no global ROAS/CPA rules."""
    guardrails = config.get("GUARDRAILS", {})
    alerts: list[dict[str, Any]] = []
    if not isinstance(guardrails, dict):
        return alerts
    for row in rows:
        for metric, rule in guardrails.items():
            if not isinstance(rule, dict) or metric not in row or row[metric] is None:
                continue
            value = number(row[metric])
            breached = ("min" in rule and value < number(rule["min"])) or ("max" in rule and value > number(rule["max"]))
            if breached:
                alerts.append({
                    "entity": row.get(dimension), "metric": metric, "value": row[metric],
                    "rule": rule, "kind": "project_guardrail", "read_only": True,
                })
    return alerts


def fmt(value: Any, metric: str) -> str:
    if value is None:
        return "—"
    if metric in {"DirectCTR", "CrossSourceROAS", "CrossSourceDRR", "MetrikaCR"}:
        return f"{number(value):.2f}%"
    if metric in {"Cost", "DirectCPC", "MetrikaRevenue", "MetrikaCPA", "AOV", "matched_direct_cost"}:
        return f"{number(value):,.2f}"
    return str(value)


def render_html(report: dict[str, Any]) -> str:
    dimension = report["dimension"]
    metrics = list(DIRECT_METRICS) + list(BUSINESS_METRICS)
    body = []
    for row in report["rows"]:
        cells = [f"<td>{html.escape(str(row.get(dimension, '')))}</td>"]
        cells.extend(f"<td>{html.escape(fmt(row.get(metric), metric))}</td>" for metric in metrics)
        body.append("<tr>" + "".join(cells) + "</tr>")
    header = "".join(f"<th>{html.escape(LABELS.get(metric, metric))}</th>" for metric in metrics)
    status = html.escape(json.dumps(report["data_status"], ensure_ascii=False, indent=2))
    return f"""<!doctype html><html lang=\"ru\"><meta charset=\"utf-8\"><title>Direct analytics</title>
<style>body{{font-family:Arial;padding:20px}}table{{border-collapse:collapse}}th,td{{border:1px solid #ddd;padding:6px;text-align:right}}th:first-child,td:first-child{{text-align:left}}pre{{white-space:pre-wrap;background:#f5f5f5;padding:12px}}</style>
<h1>{html.escape(dimension)}</h1><table><thead><tr><th>{html.escape(dimension)}</th>{header}</tr></thead><tbody>{''.join(body)}</tbody></table><h2>Data status</h2><pre>{status}</pre></html>"""


def parse_period(period: str, today: date) -> tuple[date, date]:
    days = int(period.removesuffix("d"))
    return today - timedelta(days=days), today - timedelta(days=1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only многомерная аналитика Директ + Метрика")
    parser.add_argument("--project")
    parser.add_argument("--period", default="7d")
    parser.add_argument("--date_from")
    parser.add_argument("--date_to")
    parser.add_argument("--dim", choices=tuple(DIMENSIONS), default="campaign")
    parser.add_argument("--compare", choices=("prev_period", "prev_year"))
    parser.add_argument("--anomaly", action="store_true", help="Только project-defined guardrails")
    parser.add_argument("--top", type=int, default=0)
    parser.add_argument("--format", choices=("table", "json", "html"), default="table")
    parser.add_argument("--cache-info", action="store_true")
    args = parser.parse_args()
    project = resolve_project(args.project)
    config = load_config(project)
    if args.date_from and args.date_to:
        date_from, date_to = date.fromisoformat(args.date_from), date.fromisoformat(args.date_to)
    else:
        date_from, date_to = parse_period(args.period, date.today())

    with CacheDB(project) as db:
        if args.cache_info:
            print(json.dumps(db.cache_info(), ensure_ascii=False, indent=2))
            return
        rows = load_dimension_rows(db, args.dim, date_from.isoformat(), date_to.isoformat())
        status = data_status(db, args.dim, date_from, date_to, config)
        if not rows:
            source, scope, _ = DIMENSIONS[args.dim]
            print(f"❌ Нет фактов {source}:{scope}. Соберите их: python scripts/collect.py --scope {scope} --date_from {date_from} --date_to {date_to}")
            sys.exit(1)
        aggregated = aggregate(rows, args.dim)
        previous = []
        if args.compare:
            previous_from, previous_to = shift_period(date_from, date_to, args.compare)
            previous = aggregate(load_dimension_rows(db, args.dim, previous_from.isoformat(), previous_to.isoformat()), args.dim)
            aggregated = add_period_delta(aggregated, previous, args.dim)

    output_rows = aggregated[:args.top] if args.top else aggregated
    report = {
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat(), "compare": args.compare},
        "dimension": args.dim, "rows": output_rows, "total": total_row(rows), "data_status": status,
        "alerts": configured_alerts(aggregated, config, args.dim) if args.anomaly else [], "read_only": True,
    }
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.format == "html":
        destination = Path("/tmp") / f"direct_analytics_{args.dim}.html"
        destination.write_text(render_html(report), encoding="utf-8")
        print(destination)
    else:
        print(f"📊 {args.dim} | {date_from} → {date_to} | coverage: {status['coverage']['complete']}")
        for row in output_rows:
            values = " | ".join(f"{LABELS[metric]}: {fmt(row.get(metric), metric)}" for metric in (*DIRECT_METRICS, *BUSINESS_METRICS))
            print(f"{row[args.dim]} | {values}")
        if report["alerts"]:
            print("\n⚠️ Project guardrails:")
            for alert in report["alerts"]:
                print(json.dumps(alert, ensure_ascii=False))


if __name__ == "__main__":
    main()
