#!/usr/bin/env python3
"""Collect daily, source-separated facts from Yandex Direct and Metrika.

The collector is intentionally read-only. It never changes campaigns and it
does not distribute unattributed Metrika revenue across Direct entities.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

sys.path.insert(0, str(Path(__file__).parent))
from db import CacheDB
from setup import load_config, resolve_project


DIRECT_API = "https://api.direct.yandex.com/json/v5"
METRIKA_API = "https://api-metrika.yandex.net/stat/v1/data"

CORE_SCOPES = ("campaign", "device", "region", "placement", "adnetwork")
ALL_SCOPES = (*CORE_SCOPES, "keyword", "ad")

# Each scope is a separate fact grain. Never add dimensions from another scope
# to these reports; combining them manufactures a cross-product of entities.
DIRECT_SCOPE_SPECS: dict[str, tuple[str, list[str]]] = {
    "campaign": (
        "CAMPAIGN_PERFORMANCE_REPORT",
        ["Date", "CampaignId", "CampaignName", "Impressions", "Clicks", "Cost", "Ctr", "AvgCpc"],
    ),
    "device": (
        "CAMPAIGN_PERFORMANCE_REPORT",
        ["Date", "CampaignId", "CampaignName", "DeviceType", "Impressions", "Clicks", "Cost", "Ctr", "AvgCpc"],
    ),
    "region": (
        "CAMPAIGN_PERFORMANCE_REPORT",
        ["Date", "CampaignId", "CampaignName", "LocationOfPresenceId", "LocationOfPresenceName", "Impressions", "Clicks", "Cost", "Ctr", "AvgCpc"],
    ),
    "placement": (
        "CAMPAIGN_PERFORMANCE_REPORT",
        ["Date", "CampaignId", "CampaignName", "Placement", "Impressions", "Clicks", "Cost", "Ctr", "AvgCpc"],
    ),
    "adnetwork": (
        "CAMPAIGN_PERFORMANCE_REPORT",
        ["Date", "CampaignId", "CampaignName", "AdNetworkType", "Impressions", "Clicks", "Cost", "Ctr", "AvgCpc"],
    ),
    "keyword": (
        "SEARCH_QUERY_PERFORMANCE_REPORT",
        ["Date", "CampaignId", "CriterionId", "Criterion", "Impressions", "Clicks", "Cost", "Ctr", "AvgCpc"],
    ),
    "ad": (
        "AD_PERFORMANCE_REPORT",
        ["Date", "CampaignId", "CampaignName", "AdId", "Impressions", "Clicks", "Cost", "Ctr", "AvgCpc"],
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def direct_headers(token: str, login: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Client-Login": login,
        "Accept-Language": "ru",
        "Content-Type": "application/json",
    }


def direct_request(endpoint: str, body: dict[str, Any], token: str, login: str) -> dict[str, Any]:
    response = requests.post(f"{DIRECT_API}/{endpoint}", json=body, headers=direct_headers(token, login), timeout=90)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(f"Директ API ошибка: {payload['error']}")
    return payload


def fetch_campaigns(token: str, login: str) -> list[dict[str, Any]]:
    campaigns: list[dict[str, Any]] = []
    offset = 0
    while True:
        payload = direct_request(
            "campaigns",
            {
                "method": "get",
                "params": {
                    "SelectionCriteria": {},
                    "FieldNames": ["Id", "Name", "Status", "State", "Type"],
                    "Page": {"Limit": 10000, "Offset": offset},
                },
            },
            token,
            login,
        )
        result = payload.get("result", {})
        campaigns.extend(result.get("Campaigns", []))
        limited_by = result.get("LimitedBy")
        if limited_by is None:
            return campaigns
        offset = int(limited_by)


def _parse_tsv(text: str) -> list[dict[str, str]]:
    lines = text.strip().splitlines()
    if len(lines) < 2:
        return []
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"))) for line in lines[1:] if line]


def fetch_direct_scope(
    scope: str, token: str, login: str, date_from: str, date_to: str
) -> list[dict[str, str]]:
    if scope not in DIRECT_SCOPE_SPECS:
        raise ValueError(f"Неизвестный scope Директа: {scope}")
    report_type, fields = DIRECT_SCOPE_SPECS[scope]
    body = {
        "params": {
            "SelectionCriteria": {"DateFrom": date_from, "DateTo": date_to},
            "FieldNames": fields,
            "ReportType": report_type,
            "DateRangeType": "CUSTOM_DATE",
            "Format": "TSV",
            "IncludeVAT": "NO",
            "IncludeDiscount": "NO",
        }
    }
    headers = direct_headers(token, login)
    headers.update({
        "returnMoneyInMicros": "false",
        "skipReportHeader": "true",
        "skipColumnHeader": "false",
        "skipReportSummary": "true",
    })
    response: requests.Response | None = None
    for _ in range(10):
        response = requests.post(f"{DIRECT_API}/reports", json=body, headers=headers, timeout=180)
        if response.status_code == 200:
            return _parse_tsv(response.text)
        if response.status_code in (201, 202):
            time.sleep(int(response.headers.get("retryIn", 10)))
            continue
        response.raise_for_status()
    raise TimeoutError(f"Reports API не подготовил отчёт '{scope}' за 10 попыток ({response.status_code if response else 'no response'})")


def metrika_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"OAuth {token}"}


def _metrika_rows(token: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch every Metrika page without silently truncating a dimension."""
    result: list[dict[str, Any]] = []
    offset = 1
    limit = int(params.get("limit", 100000))
    while True:
        page_params = {**params, "offset": offset, "limit": limit}
        response = requests.get(METRIKA_API, params=page_params, headers=metrika_headers(token), timeout=90)
        response.raise_for_status()
        payload = response.json()
        rows = _flatten_metrika(payload)
        result.extend(rows)
        total_rows = int(payload.get("total_rows", len(rows)))
        if not rows or len(result) >= total_rows:
            return result
        offset += len(rows)


def _metrika_filter(config: dict[str, Any]) -> str:
    source = str(config.get("UTM_SOURCE", "yandex")).replace("'", "\\'")
    medium = str(config.get("UTM_MEDIUM", "cpc")).replace("'", "\\'")
    return f"ym:s:UTMSource=='{source}' AND ym:s:UTMMedium=='{medium}'"


def metrika_sessions(
    token: str, counter: str, date_from: str, date_to: str, config: dict[str, Any]
) -> list[dict[str, Any]]:
    metrics = ["ym:s:visits", "ym:s:users", "ym:s:bounceRate", "ym:s:pageDepth", "ym:s:avgVisitDurationSeconds"]
    for goal_id in str(config.get("METRIKA_GOAL_IDS", "")).split(","):
        goal_id = goal_id.strip()
        if goal_id:
            metrics.append(f"ym:s:goal{goal_id}reaches")
    return _metrika_rows(token, {
        "id": counter,
        "date1": date_from,
        "date2": date_to,
        "dimensions": "ym:s:date,ym:s:UTMSource,ym:s:UTMMedium,ym:s:UTMCampaign,ym:s:UTMContent,ym:s:UTMTerm",
        "metrics": ",".join(metrics),
        "filters": _metrika_filter(config),
        "limit": 100000,
    })


def metrika_ecommerce(
    token: str, counter: str, date_from: str, date_to: str, config: dict[str, Any]
) -> list[dict[str, Any]]:
    return _metrika_rows(token, {
        "id": counter,
        "date1": date_from,
        "date2": date_to,
        "dimensions": "ym:s:date,ym:s:UTMSource,ym:s:UTMMedium,ym:s:UTMCampaign,ym:s:UTMContent",
        "metrics": "ym:s:ecommercePurchases,ym:s:ecommerceRevenue,ym:s:ecommerceConvertionRate",
        "filters": _metrika_filter(config),
        "limit": 100000,
    })


def _flatten_metrika(payload: dict[str, Any]) -> list[dict[str, Any]]:
    names = [dimension["name"] for dimension in payload.get("query", {}).get("dimensions", [])]
    metric_names = payload.get("query", {}).get("metrics", [])
    rows: list[dict[str, Any]] = []
    for item in payload.get("data", []):
        row: dict[str, Any] = {}
        for index, dimension in enumerate(item.get("dimensions", [])):
            row[names[index] if index < len(names) else f"dimension_{index}"] = dimension.get("name", "")
        for index, value in enumerate(item.get("metrics", [])):
            row[metric_names[index] if index < len(metric_names) else f"metric_{index}"] = value
        rows.append(row)
    return rows


def _date_ranges(days: list[str]) -> list[tuple[str, str]]:
    if not days:
        return []
    ordered = sorted(days)
    ranges: list[tuple[str, str]] = []
    start = previous = date.fromisoformat(ordered[0])
    for raw in ordered[1:]:
        current = date.fromisoformat(raw)
        if current != previous + timedelta(days=1):
            ranges.append((start.isoformat(), previous.isoformat()))
            start = current
        previous = current
    ranges.append((start.isoformat(), previous.isoformat()))
    return ranges


def _partition_by_date(rows: Iterable[dict[str, Any]], days: list[str], date_field: str) -> dict[str, list[dict[str, Any]]]:
    groups = {day: [] for day in days}
    for row in rows:
        raw_date = str(row.get(date_field, ""))
        stat_date = raw_date[:10]
        if stat_date in groups:
            item = dict(row)
            item["Date"] = stat_date
            groups[stat_date].append(item)
    return groups


def _contract(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "timezone": config.get("REPORT_TIMEZONE", "Europe/Moscow"),
        "attribution_mode": config.get("ATTRIBUTION_MODE", "parallel"),
        "utm_source": config.get("UTM_SOURCE", "yandex"),
        "utm_medium": config.get("UTM_MEDIUM", "cpc"),
        "utm_campaign_mapping": config.get("UTM_CAMPAIGN_MAPPING", "campaign_id"),
        "currency": config.get("CURRENCY", "RUB"),
        "read_only": True,
    }


def _status(source: str, scope: str, contract: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "source": source,
        "scope": scope,
        "complete": True,
        "fetched_at": utc_now(),
        "contract": contract,
        **extra,
    }


def _enrich_campaign_rows(rows: list[dict[str, Any]], campaigns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index = {str(campaign.get("Id")): campaign for campaign in campaigns}
    result = []
    for row in rows:
        item = dict(row)
        campaign = index.get(str(item.get("CampaignId", "")), {})
        item["CampaignStatus"] = campaign.get("Status")
        item["CampaignState"] = campaign.get("State")
        item["CampaignType"] = campaign.get("Type")
        result.append(item)
    return result


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def reconcile_campaign_day(
    direct_rows: list[dict[str, Any]],
    ecom_rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Pair only explicit campaign mappings; leave all other revenue untouched."""
    mapping = str(config.get("UTM_CAMPAIGN_MAPPING", "campaign_id"))
    allow_name_match = bool(config.get("ALLOW_LEGACY_CAMPAIGN_NAME_MATCH", False))
    direct_by_key: dict[str, dict[str, Any]] = {}
    for row in direct_rows:
        key = str(row.get("CampaignName") if mapping == "campaign_name" else row.get("CampaignId", ""))
        if key:
            direct_by_key[key] = row

    ecom_by_key: dict[str, dict[str, float]] = {}
    unattributed_revenue = 0.0
    unattributed_transactions = 0.0
    matched_keys: set[str] = set()
    estimated_keys: set[str] = set()
    for row in ecom_rows:
        key = str(row.get("ym:s:UTMCampaign", ""))
        revenue = _float(row.get("ym:s:ecommerceRevenue"))
        transactions = _float(row.get("ym:s:ecommercePurchases"))
        resolved_key = key if key in direct_by_key else ""
        if not resolved_key and allow_name_match:
            lowered = key.lower()
            for candidate, direct_row in direct_by_key.items():
                if lowered and lowered == str(direct_row.get("CampaignName", "")).lower():
                    resolved_key = candidate
                    estimated_keys.add(candidate)
                    break
        if not resolved_key:
            unattributed_revenue += revenue
            unattributed_transactions += transactions
            continue
        bucket = ecom_by_key.setdefault(resolved_key, {"revenue": 0.0, "transactions": 0.0})
        bucket["revenue"] += revenue
        bucket["transactions"] += transactions
        matched_keys.add(resolved_key)

    result: list[dict[str, Any]] = []
    for key, direct_row in direct_by_key.items():
        item = dict(direct_row)
        business = ecom_by_key.get(key)
        if business:
            level = "estimated" if key in estimated_keys else "exact"
            item.update({
                "MetrikaRevenue": round(business["revenue"], 2),
                "MetrikaTransactions": round(business["transactions"], 4),
                "attribution_level": level,
                "match_confidence": 0.7 if level == "estimated" else 1.0,
                "RevenueSource": "metrika_ecommerce",
            })
        else:
            item.update({
                "MetrikaRevenue": None,
                "MetrikaTransactions": None,
                "attribution_level": "unpaired_direct",
                "match_confidence": 0.0,
                "RevenueSource": None,
            })
        result.append(item)

    summary = {
        "reconciliation_status": "complete" if not unattributed_revenue else "incomplete",
        "direct_campaigns": len(direct_by_key),
        "exact_campaigns": sum(1 for row in result if row["attribution_level"] == "exact"),
        "estimated_campaigns": sum(1 for row in result if row["attribution_level"] == "estimated"),
        "unpaired_direct_campaigns": sum(1 for row in result if row["attribution_level"] == "unpaired_direct"),
        "unattributed_metrika_revenue": round(unattributed_revenue, 2),
        "unattributed_metrika_transactions": round(unattributed_transactions, 4),
        "direct_cost": round(sum(_float(row.get("Cost")) for row in direct_rows), 2),
        "matched_metrika_revenue": round(sum(item["MetrikaRevenue"] or 0 for item in result), 2),
        "metrika_ecommerce_revenue": round(sum(_float(row.get("ym:s:ecommerceRevenue")) for row in ecom_rows), 2),
        "allocation": "none",
    }
    return result, summary


def _expanded_scopes(requested: list[str] | None) -> tuple[str, ...]:
    values = requested or ["core"]
    expanded: list[str] = []
    for value in values:
        scopes = CORE_SCOPES if value == "core" else (value,)
        for scope in scopes:
            if scope not in expanded:
                expanded.append(scope)
    return tuple(expanded)


def _collect_direct_scope(
    db: CacheDB,
    scope: str,
    date_from: date,
    date_to: date,
    token: str,
    login: str,
    contract: dict[str, Any],
    campaigns: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    missing = db.missing_fact_dates("direct", scope, date_from, date_to)
    for start, end in _date_ranges(missing):
        days = CacheDB.completed_dates(date.fromisoformat(start), date.fromisoformat(end))
        try:
            rows = _enrich_campaign_rows(fetch_direct_scope(scope, token, login, start, end), campaigns)
            by_day = _partition_by_date(rows, days, "Date")
            for stat_date, records in by_day.items():
                db.save_fact("direct", scope, stat_date, records, _status("direct", scope, contract, api="Direct Reports API", rows=len(records)))
        except Exception as error:  # preserve an auditable failed attempt and retry it next run
            message = f"direct:{scope}:{start}..{end}: {error}"
            errors.append(message)
            for stat_date in days:
                db.save_fact("direct", scope, stat_date, [], _status("direct", scope, contract, complete=False, error=message))
    return errors


def _collect_metrika_scope(
    db: CacheDB,
    scope: str,
    date_from: date,
    date_to: date,
    token: str,
    counter: str,
    config: dict[str, Any],
    contract: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    fetcher = metrika_sessions if scope == "sessions" else metrika_ecommerce
    missing = db.missing_fact_dates("metrika", scope, date_from, date_to)
    for start, end in _date_ranges(missing):
        days = CacheDB.completed_dates(date.fromisoformat(start), date.fromisoformat(end))
        try:
            rows = fetcher(token, counter, start, end, config)
            by_day = _partition_by_date(rows, days, "ym:s:date")
            for stat_date, records in by_day.items():
                db.save_fact("metrika", scope, stat_date, records, _status("metrika", scope, contract, api="Metrika Stat API", rows=len(records)))
        except Exception as error:
            message = f"metrika:{scope}:{start}..{end}: {error}"
            errors.append(message)
            for stat_date in days:
                db.save_fact("metrika", scope, stat_date, [], _status("metrika", scope, contract, complete=False, error=message))
    return errors


def _reconcile_missing_days(db: CacheDB, date_from: date, date_to: date, config: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for stat_date in db.missing_fact_dates("reconciliation", "campaign", date_from, date_to):
        try:
            direct_status = db.fact_status("direct", "campaign", stat_date, stat_date).get(stat_date, {})
            ecom_status = db.fact_status("metrika", "ecommerce", stat_date, stat_date).get(stat_date, {})
            if not direct_status.get("complete") or not ecom_status.get("complete"):
                raise RuntimeError("reconciliation skipped because Direct or Metrika source is incomplete")
            direct = db.load_facts("direct", "campaign", stat_date, stat_date)
            ecom = db.load_facts("metrika", "ecommerce", stat_date, stat_date)
            records, summary = reconcile_campaign_day(direct, ecom, config)
            db.save_fact("reconciliation", "campaign", stat_date, records, _status("reconciliation", "campaign", contract, summary=summary, direct_rows=len(direct), ecom_rows=len(ecom)))
        except Exception as error:
            message = f"reconciliation:campaign:{stat_date}: {error}"
            errors.append(message)
            db.save_fact("reconciliation", "campaign", stat_date, [], _status("reconciliation", "campaign", contract, complete=False, error=message))
    return errors


def run_collect(
    project: str,
    date_from: date,
    date_to: date,
    refresh: bool = False,
    scopes: list[str] | None = None,
) -> dict[str, Any]:
    config = load_config(project)
    contract = _contract(config)
    selected_scopes = _expanded_scopes(scopes)
    print(f"📦 Проект: {project} | {date_from.isoformat()} → {date_to.isoformat()} | scopes: {', '.join(selected_scopes)}")
    errors: list[str] = []

    with CacheDB(project) as db:
        if refresh:
            db.invalidate_all(date_from.isoformat(), date_to.isoformat())
            print("♻️  Кэш за период инвалидирован")

        snapshot_date = date_to.isoformat()
        campaigns = db.load("direct_campaigns", snapshot_date, snapshot_date) if db.has_structure(snapshot_date) and not refresh else []
        if not campaigns:
            try:
                campaigns = fetch_campaigns(config["DIRECT_TOKEN"], config["DIRECT_LOGIN"])
                db.save("direct_campaigns", snapshot_date, campaigns)
            except Exception as error:
                errors.append(f"direct:campaigns:{error}")

        for scope in selected_scopes:
            errors.extend(_collect_direct_scope(db, scope, date_from, date_to, config["DIRECT_TOKEN"], config["DIRECT_LOGIN"], contract, campaigns))
        errors.extend(_collect_metrika_scope(db, "sessions", date_from, date_to, config["METRIKA_TOKEN"], config["METRIKA_COUNTER"], config, contract))
        errors.extend(_collect_metrika_scope(db, "ecommerce", date_from, date_to, config["METRIKA_TOKEN"], config["METRIKA_COUNTER"], config, contract))
        if "campaign" in selected_scopes:
            errors.extend(_reconcile_missing_days(db, date_from, date_to, config, contract))

        coverage = db.coverage(
            [("direct", scope) for scope in selected_scopes] + [("metrika", "sessions"), ("metrika", "ecommerce")] + ([("reconciliation", "campaign")] if "campaign" in selected_scopes else []),
            date_from,
            date_to,
        )
        result = {"project": project, "contract": contract, "coverage": coverage, "errors": errors, "cache": db.cache_info()}

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise RuntimeError("Сбор завершён с ошибками; неполные факты сохранены только со статусом complete=false")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only сбор Директ + Метрика с дневным data contract")
    parser.add_argument("--project", help="Имя проекта (иначе — дефолтный)")
    parser.add_argument("--date", help="Конкретная завершённая дата YYYY-MM-DD")
    parser.add_argument("--date_from", help="Начало периода YYYY-MM-DD")
    parser.add_argument("--date_to", help="Конец периода YYYY-MM-DD")
    parser.add_argument("--scope", choices=("core", *ALL_SCOPES), action="append", help="Повторяемый scope; по умолчанию core")
    parser.add_argument("--refresh", action="store_true", help="Перезапросить и пересобрать период")
    args = parser.parse_args()
    project = resolve_project(args.project)
    yesterday = date.today() - timedelta(days=1)
    if args.date:
        date_from = date_to = date.fromisoformat(args.date)
    elif args.date_from and args.date_to:
        date_from, date_to = date.fromisoformat(args.date_from), date.fromisoformat(args.date_to)
    else:
        date_from = date_to = yesterday
    run_collect(project, date_from, date_to, args.refresh, args.scope)


if __name__ == "__main__":
    main()
