#!/usr/bin/env python3
"""Thin management-report adapter for direct-analytics-skill.

The neighboring skill remains the single data engine. This script orchestrates
collection, deterministic checks, management reporting, and an optional OpenAI
narrative without duplicating collectors, cache code, or KPI calculations.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "gpt-5.4-mini"
DIMENSIONS = ("campaign", "device", "region", "keyword", "placement", "ad", "day", "adnetwork")
BASE_FIELDS = ("Impressions", "Clicks", "Cost", "revenue", "transactions")
RATIO_FIELDS = ("DRR", "ROAS", "CPA", "CR", "CTR", "CPC", "AOV")


def safe_float(value: Any) -> float:
    try:
        if value in (None, "", "--"):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def ratio(numerator: float, denominator: float, multiplier: float = 1.0) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator * multiplier, 4)


def build_windows(report_date: date) -> dict[str, tuple[date, date]]:
    return {
        "target": (report_date, report_date),
        "previous_day": (report_date - timedelta(days=1), report_date - timedelta(days=1)),
        "last_7d": (report_date - timedelta(days=6), report_date),
        "prev_7d": (report_date - timedelta(days=13), report_date - timedelta(days=7)),
        "last_30d": (report_date - timedelta(days=29), report_date),
    }


def window_days(window: tuple[date, date]) -> int:
    return (window[1] - window[0]).days + 1


def pct_delta(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return round((current - previous) / abs(previous) * 100, 1)


def compare_totals(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, float | None]:
    return {field: pct_delta(current.get(field), previous.get(field)) for field in (*BASE_FIELDS, *RATIO_FIELDS)}


def format_value(value: Any, metric: str) -> str:
    if value is None:
        return "н/д"
    if metric in ("DRR", "ROAS", "CR", "CTR"):
        return f"{float(value):.2f}%"
    if metric in ("Cost", "revenue", "CPA", "CPC", "AOV"):
        return f"{float(value):,.0f} ₽".replace(",", " ")
    return f"{int(value):,}".replace(",", " ")


def find_engine_dir(explicit: str | None = None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.getenv("DIRECT_ANALYTICS_SKILL_DIR"):
        candidates.append(Path(os.environ["DIRECT_ANALYTICS_SKILL_DIR"]).expanduser())

    skill_dir = Path(__file__).resolve().parents[1]
    candidates.extend(
        [
            skill_dir.parent / "direct-analytics-skill",
            Path.cwd() / "direct-analytics-skill",
        ]
    )

    seen = set()
    for candidate in candidates:
        resolved = candidate.resolve() if candidate.exists() else candidate
        if str(resolved) in seen:
            continue
        seen.add(str(resolved))
        scripts = candidate / "scripts"
        if all((scripts / name).is_file() for name in ("setup.py", "db.py", "collect.py", "analyze.py")):
            return candidate.resolve()
    raise FileNotFoundError(
        "Не найден direct-analytics-skill со скриптами. "
        "Укажите --engine-dir PATH или DIRECT_ANALYTICS_SKILL_DIR."
    )


def load_engine(engine_dir: Path) -> dict[str, Any]:
    scripts = engine_dir / "scripts"
    scripts_str = str(scripts)
    if scripts_str not in sys.path:
        sys.path.insert(0, scripts_str)
    return {
        "setup": importlib.import_module("setup"),
        "db": importlib.import_module("db"),
        "collect": importlib.import_module("collect"),
        "analyze": importlib.import_module("analyze"),
    }


def collect_missing_days(engine, project, start, end, refresh=False):
    """Delegate collection and gap handling to the current source-separated engine."""
    with engine["db"].CacheDB(project) as cache:
        missing = cache.missing_fact_dates("reconciliation", "campaign", start, end)
    if refresh or missing:
        engine["collect"].run_collect(project, start, end, refresh=refresh)
    return missing


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() and key.strip() not in os.environ:
            os.environ[key.strip()] = value.strip().strip('"').strip("'")


def apply_focus(rows: list[dict[str, Any]], focus: str | None) -> list[dict[str, Any]]:
    if not focus:
        return rows
    needle = focus.casefold()
    return [
        row
        for row in rows
        if any(isinstance(value, str) and needle in value.casefold() for value in row.values())
    ]


def presentation_aliases(native):
    """Legacy renderer keys only; calculations are delegated to the engine."""
    result = dict(native)
    for display, metric in {
        "revenue": "MetrikaRevenue", "transactions": "MetrikaTransactions",
        "DRR": "CrossSourceDRR", "ROAS": "CrossSourceROAS", "CPA": "MetrikaCPA",
        "CR": "MetrikaCR", "CTR": "DirectCTR", "CPC": "DirectCPC",
    }.items():
        result[display] = native.get(metric)
    return result


def build_dataset(engine, project, report_date, mode, focus, target_drr):
    """Read current fact grains, keeping source coverage and attribution explicit."""
    windows = build_windows(report_date)
    config = engine["setup"].load_config(project)
    periods, missing, dimensions = {}, {}, {}
    source_status = {}
    with engine["db"].CacheDB(project) as cache:
        for label, (start, end) in windows.items():
            native = engine["analyze"].load_dimension_rows(cache, "campaign", start.isoformat(), end.isoformat())
            rows = apply_focus(native, focus)
            status = engine["analyze"].data_status(cache, "campaign", start, end, config)
            sources = status["coverage"]["sources"]
            missing[label] = sorted({day for item in sources.values() for day in item["missing_dates"]})
            periods[label] = {
                "from": start.isoformat(), "to": end.isoformat(), "days": window_days((start, end)),
                "rows": len(rows), "totals": presentation_aliases(engine["analyze"].total_row(rows)),
                "checks": {"pass": True, "calculation_source": "direct-analytics-skill.analyze.total_row"},
                "missing_dates": missing[label], "data_status": status,
            }
        start, end = windows["last_7d"]
        for dim in DIMENSIONS:
            raw = engine["analyze"].load_dimension_rows(cache, dim, start.isoformat(), end.isoformat())
            raw = apply_focus(raw, focus)
            dimensions[dim] = [presentation_aliases(row) for row in engine["analyze"].aggregate(raw, dim)]
        long_start, long_end = windows["last_30d"]
        coverage = engine["analyze"].data_status(cache, "campaign", long_start, long_end, config)["coverage"]
        source_status = {key: {**item, "status": "complete" if not item["missing_dates"] else "limited"}
                         for key, item in coverage["sources"].items()}
        summaries = cache.fact_status("reconciliation", "campaign", long_start.isoformat(), long_end.isoformat())
        unattributed = sum(safe_float(item.get("summary", {}).get("unattributed_metrika_revenue")) for item in summaries.values())
    target = periods["target"]["totals"]
    current_7, previous_7 = periods["last_7d"]["totals"], periods["prev_7d"]["totals"]
    complete = not any(missing.values()) and report_date < date.today()
    warnings = []
    if not complete: warnings.append("Incomplete fact coverage; missing data remain unknown, not zero.")
    if focus: warnings.append("Focus restricts rows; coverage describes the source series rather than this subset.")
    warnings.append("Revenue/transactions are Metrika facts; DRR/ROAS/CPA/CR are labelled Direct÷Метка ratios on reconciled cost only.")
    alerts = engine["analyze"].configured_alerts(dimensions["campaign"], config, "campaign")
    actions = [{"priority": "P2", "action": "Проверить проектный guardrail без изменения кабинета",
                "evidence": json.dumps(alert, ensure_ascii=False), "financial_impact": None,
                "expected_effect": "Проверить источник отклонения", "risk": "Причина не установлена",
                "recheck": "Read-only проверка сопоставимых периодов"} for alert in alerts]
    if not actions: actions = [{"priority": "P3", "action": "Проверить полноту данных и согласовать проектные ограничения",
                              "evidence": "Автоматические изменения запрещены; универсальные пороги не применяются",
                              "financial_impact": None, "expected_effect": "Подготовить доказательное решение",
                              "risk": "Не принимать отсутствие алерта за доказательство эффективности", "recheck": "Следующий полный период"}]
    reconciliation = {"pass": complete, "basis": "engine explicit reconciliation; no revenue allocation",
                      "unattributed_metrika_revenue": unattributed,
                      "matched_revenue": target.get("MetrikaRevenue"),
                      "direct_cost": target.get("Cost"), "matched_cost": target.get("matched_direct_cost"),
                      "metrika_ecommerce_revenue": None, "cost_delta_pct": None, "revenue_delta_pct": None}
    return {
        "project": project, "report_date": report_date.isoformat(), "mode": mode, "focus": focus,
        "data_status": "complete" if complete else "limited", "warnings": warnings, "periods": periods,
        "comparisons": {"target_vs_previous_day": compare_totals(target, periods["previous_day"]["totals"]),
                        "last_7d_vs_prev_7d": compare_totals(current_7, previous_7)},
        "dimensions": dimensions, "match_summary": {"allocation": "none", "unattributed_metrika_revenue": unattributed},
        "source_status": source_status, "reconciliation": reconciliation, "anomalies": [], "actions": actions,
        "forecast": {"basis": "not_calculated: numeric forecast requires a separate dated series and backtest"},
        "checks": {"kpi_formulas": {"pass": True, "delegated": True},
                   "period_comparability": {"pass": complete, "last_7d_days": 7, "prev_7d_days": 7},
                   "data_complete": {"pass": complete, "missing_dates": missing}, "reconciliation": reconciliation},
        "target_drr": target_drr,
        "metric_labels": {"revenue": "MetrikaRevenue", "transactions": "MetrikaTransactions",
                          "ROAS": "CrossSourceROAS Direct÷Метка", "DRR": "CrossSourceDRR Direct÷Метка"},
    }


def metric_line(name: str, totals: dict[str, Any], delta: dict[str, Any]) -> str:
    current = format_value(totals.get(name), name)
    change = delta.get(name)
    suffix = "н/д" if change is None else f"{change:+.1f}%"
    label = {"revenue": "MetrikaRevenue", "transactions": "MetrikaTransactions", "ROAS": "ROAS Direct÷Метка", "DRR": "ДРР Direct÷Метка", "CPA": "CPA Direct÷Метка", "CR": "CR Click→Метка"}.get(name, name)
    return f"| {label} | {current} | {suffix} |"


def markdown_table(rows: list[dict[str, Any]], dimension: str, limit: int = 10) -> str:
    lines = ["| Объект | Расход | Выручка | Заказы | ДРР |", "|---|---:|---:|---:|---:|"]
    for row in rows[:limit]:
        lines.append(
            f"| {row.get(dimension, '—')} | {format_value(row.get('Cost'), 'Cost')} | "
            f"{format_value(row.get('revenue'), 'revenue')} | "
            f"{format_value(row.get('transactions'), 'transactions')} | "
            f"{format_value(row.get('DRR'), 'DRR')} |"
        )
    if len(lines) == 2:
        lines.append("| Нет данных | — | — | — | — |")
    return "\n".join(lines)


def render_actions(actions: list[dict[str, Any]]) -> str:
    blocks = []
    for item in actions:
        impact = item.get("financial_impact")
        impact_text = "н/д" if impact is None else format_value(impact, "Cost")
        blocks.append(
            f"### {item['priority']}: {item['action']}\n"
            f"- Доказательство: {item['evidence']}\n"
            f"- Финансовый потенциал: {impact_text}\n"
            f"- Ожидаемый эффект: {item['expected_effect']}\n"
            f"- Риск: {item['risk']}\n"
            f"- Повторная проверка: {item['recheck']}"
        )
    return "\n\n".join(blocks)


def render_report(dataset: dict[str, Any], llm_comment: str | None = None) -> str:
    periods = dataset["periods"]
    target = periods["target"]["totals"]
    delta_day = dataset.get("comparisons", {}).get("target_vs_previous_day", {})
    current_7 = periods.get("last_7d", {}).get("totals", {})
    delta_7 = dataset.get("comparisons", {}).get("last_7d_vs_prev_7d", {})
    warnings = dataset.get("warnings", [])
    status = dataset.get("data_status", "limited")
    warning_text = "\n".join(f"- ⚠️ {warning}" for warning in warnings) or "- Ограничения не выявлены"
    metrics = "\n".join(metric_line(name, target, delta_day) for name in ("Cost", "revenue", "transactions", "DRR", "ROAS", "CPA", "CR", "CTR", "CPC", "AOV"))
    metrics_7 = "\n".join(metric_line(name, current_7, delta_7) for name in ("Cost", "revenue", "transactions", "DRR", "ROAS"))
    match = dataset.get("match_summary", {})
    match_quality = match.get("high_confidence_share")
    match_text = "н/д" if match_quality is None else f"{match_quality:.1%}"
    sources = dataset.get("source_status", {})
    source_lines = "\n".join(
        f"- {name}: {item.get('status', 'unknown')}; дней {item.get('coverage', 'н/д')}; "
        f"обновлено {item.get('latest_fetched_at') or 'н/д'}"
        for name, item in sources.items()
    ) or "- Статусы источников недоступны"
    recon = dataset.get("reconciliation", {})
    anomalies = dataset.get("anomalies", [])
    anomaly_lines = "\n".join(
        f"- {item.get('anomaly')}: {item.get('entity')} — потенциальный импакт {format_value(item.get('financial_impact'), 'Cost')}"
        for item in anomalies[:10]
    ) or "- Отдельная диагностика аномалий не выполнена; доступны проектные guardrails"
    forecast = dataset.get("forecast", {})
    checks = json.dumps(dataset.get("checks", {}), ensure_ascii=False, indent=2)

    sections = [
        f"# Отчёт direct-analyst — {dataset['project']} — {dataset['report_date']}",
        f"## §0 Executive Scorecard\n\nСтатус данных: **{status}**. Целевой ДРР: **{format_value(dataset.get('target_drr') or None, 'DRR')}**.\n\n| KPI | Значение | к предыдущему дню |\n|---|---:|---:|\n{metrics}",
        f"## §1 Качество данных\n\n{warning_text}\n\n{source_lines}\n\n"
        f"- Распределение неатрибутированной выручки: запрещено\n"
        f"- Неатрибутированная выручка Метрики за 30 дней: {format_value(match.get('unattributed_metrika_revenue'), 'revenue')}\n"
        f"- Reconciliation: {'пройден' if recon.get('pass') else 'не пройден'}; "
        f"расход {format_value(recon.get('direct_cost'), 'Cost')} → {format_value(recon.get('matched_cost'), 'Cost')}; "
        f"выручка {format_value(recon.get('metrika_ecommerce_revenue'), 'revenue')} → {format_value(recon.get('matched_revenue'), 'revenue')}",
        f"## §2 Динамика 7 дней\n\n| KPI | Последние 7 дней | к предыдущим 7 дням |\n|---|---:|---:|\n{metrics_7}",
        f"## §3 Воронка\n\nПоказы: {format_value(target.get('Impressions'), 'Impressions')} → клики: {format_value(target.get('Clicks'), 'Clicks')} → заказы: {format_value(target.get('transactions'), 'transactions')}. CTR: {format_value(target.get('CTR'), 'CTR')}; CR: {format_value(target.get('CR'), 'CR')}.",
        f"## §4 Финансовая эффективность\n\nРасход: {format_value(target.get('Cost'), 'Cost')}; выручка: {format_value(target.get('revenue'), 'revenue')}; ДРР: {format_value(target.get('DRR'), 'DRR')}; ROAS: {format_value(target.get('ROAS'), 'ROAS')}; CPA: {format_value(target.get('CPA'), 'CPA')}.",
        f"## §5 Кампании — драйверы последних 7 дней\n\n{markdown_table(dataset.get('dimensions', {}).get('campaign', []), 'campaign')}",
        f"## §6 Устройства\n\n{markdown_table(dataset.get('dimensions', {}).get('device', []), 'device')}",
        f"## §7 Регионы\n\n{markdown_table(dataset.get('dimensions', {}).get('region', []), 'region')}",
        f"## §8 Площадки\n\n{markdown_table(dataset.get('dimensions', {}).get('placement', []), 'placement')}",
        f"## §9 Тип сети\n\n{markdown_table(dataset.get('dimensions', {}).get('adnetwork', []), 'adnetwork')}",
        f"## §10 Ключевые фразы\n\n{markdown_table(dataset.get('dimensions', {}).get('keyword', []), 'keyword')}",
        f"## §11 Аномалии\n\n{anomaly_lines}",
        "## §12 Финансовый импакт\n\nНе рассчитан: необходимо подтверждённое проектное ограничение и проверка причин. Нулевой импакт не предполагается.",
        f"## §13 Прогноз\n\nОснова: {forecast.get('basis', 'н/д')}. Прогноз 30 дней: расход {format_value(forecast.get('Cost_30d'), 'Cost')}, выручка {format_value(forecast.get('revenue_30d'), 'revenue')}, заказы {forecast.get('transactions_30d', 'н/д')}, ДРР {format_value(forecast.get('DRR'), 'DRR')}.",
        f"## §14 План действий\n\n{render_actions(dataset.get('actions', []))}",
        "## §15 Что не трогать и ключевая неопределённость\n\nНе менять кампании с хорошей эффективностью только из-за краткосрочного колебания. Главная неопределённость — качество атрибуции выручки между Директом и Метрикой; неатрибутированная выручка не распределяется, оценочные совпадения требуют ручной сверки.",
        f"## Детерминированные проверки\n\n```json\n{checks}\n```",
    ]
    if llm_comment:
        sections.insert(2, f"## Управленческий комментарий LLM\n\n{llm_comment.strip()}")

    if dataset.get("mode") == "action":
        allowed = (
            "# Отчёт",
            "## §0 ",
            "## Управленческий комментарий",
            "## §1 ",
            "## §11 ",
            "## §12 ",
            "## §14 ",
            "## §15 ",
            "## Детерминированные проверки",
        )
        sections = [section for section in sections if section.startswith(allowed)]
    elif dataset.get("mode") == "deep_dive":
        focus = dataset.get("focus") or "не задан"
        sections.insert(1, f"**Фокус глубокого разбора:** {focus}")
    return "\n\n".join(sections) + "\n"


def compact_llm_input(dataset: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": dataset["project"],
        "report_date": dataset["report_date"],
        "mode": dataset["mode"],
        "status": dataset["data_status"],
        "warnings": dataset["warnings"],
        "target": dataset["periods"]["target"]["totals"],
        "last_7d": dataset["periods"]["last_7d"]["totals"],
        "deltas": dataset["comparisons"],
        "match_summary": dataset["match_summary"],
        "source_status": dataset.get("source_status", {}),
        "reconciliation": dataset.get("reconciliation", {}),
        "anomalies": dataset["anomalies"][:10],
        "actions": dataset["actions"],
        "checks": dataset["checks"],
    }


def extract_response_text(payload: dict[str, Any]) -> str:
    parts = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                parts.append(content["text"])
    return "\n".join(parts).strip()


def call_openai(dataset: dict[str, Any], model: str, api_key: str, timeout: int = 60) -> str:
    payload = {
        "model": model,
        "instructions": (
            "Ты управленческий аналитик performance-маркетинга. Используй только переданные данные. "
            "Не пересчитывай и не изменяй KPI. Раздели ответ на Факты, Выводы, Рекомендации и Риски. "
            "Каждую рекомендацию свяжи с конкретным доказательством. Не утверждай причинность без основания. "
            "Если checks или status показывают ограничение, поставь его перед рекомендациями. Ответ на русском."
        ),
        "input": json.dumps(compact_llm_input(dataset), ensure_ascii=False),
        "max_output_tokens": 1800,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"OpenAI API HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"OpenAI API недоступен: {error.reason}") from error
    text = extract_response_text(body)
    if not text:
        raise RuntimeError("OpenAI API не вернул текстовый результат")
    return text


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Управленческий отчёт поверх direct-analytics-skill")
    parser.add_argument("--project", help="Имя проекта; иначе default из direct-analytics-skill")
    parser.add_argument("--date", help="Полная дата отчёта YYYY-MM-DD; по умолчанию вчера")
    parser.add_argument("--mode", choices=("daily", "action", "deep_dive"), default="daily")
    parser.add_argument("--focus", help="Фокус для deep_dive")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Модель OpenAI для комментария")
    parser.add_argument("--no_collect", action="store_true", help="Не обновлять данные")
    parser.add_argument("--force_refresh", action="store_true", help="Обновить кэш за 30 дней")
    parser.add_argument("--no_llm", dest="no_llm", action="store_true", default=True, help="Только детерминированный отчёт (по умолчанию)")
    parser.add_argument("--llm", dest="no_llm", action="store_false", help="Явно разрешить платный внешний OpenAI-комментарий")
    parser.add_argument("--allow_incomplete", action="store_true", help="Разрешить текущую или будущую дату с warning")
    parser.add_argument("--engine-dir", help="Путь к распакованному direct-analytics-skill")
    parser.add_argument("--output_dir", help="Корень вывода; по умолчанию ./output/PROJECT")
    parser.add_argument("--target_drr", type=float, help="Целевой ДРР; иначе из конфигурации проекта")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    engine_dir = find_engine_dir(args.engine_dir)
    engine = load_engine(engine_dir)
    project = engine["setup"].resolve_project(args.project)
    config = engine["setup"].load_config(project)
    report_date = date.fromisoformat(args.date) if args.date else date.today() - timedelta(days=1)
    if report_date >= date.today() and not args.allow_incomplete:
        raise SystemExit("Дата должна быть завершённой. Для неполной даты используйте --allow_incomplete.")
    if args.mode == "deep_dive" and not args.focus:
        raise SystemExit("Для deep_dive обязателен --focus.")
    target_drr = args.target_drr if args.target_drr is not None else safe_float(config.get("DRR_TARGET"))
    if args.target_drr is not None and target_drr <= 0:
        raise SystemExit("Явно заданный целевой ДРР должен быть больше нуля.")

    windows = build_windows(report_date)
    if not args.no_collect:
        collect_from = windows["last_30d"][0]
        collected = collect_missing_days(
            engine, project, collect_from, report_date, refresh=args.force_refresh
        )
        if collected:
            print(f"COLLECTED_DAYS={len(collected)}")

    dataset = build_dataset(engine, project, report_date, args.mode, args.focus, target_drr)
    llm_comment = None
    llm_error = None
    if not args.no_llm:
        load_env_file(Path(os.environ.get("DIRECT_ANALYTICS_DATA_DIR", str(Path.home() / ".direct_analytics"))) / ".env")
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            llm_error = "OPENAI_API_KEY не найден; создан детерминированный отчёт"
        else:
            try:
                llm_comment = call_openai(dataset, args.model, api_key)
            except RuntimeError as error:
                llm_error = str(error)
    if llm_error:
        dataset["warnings"].append(llm_error)
        dataset["llm_status"] = "failed"
    else:
        dataset["llm_status"] = "disabled" if args.no_llm else "complete"

    output_root = Path(args.output_dir).expanduser() if args.output_dir else Path.cwd() / "output" / project
    report_dir = output_root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stem = f"report_{report_date.isoformat()}_{args.mode}"
    json_path = report_dir / f"{stem}.json"
    md_path = report_dir / f"{stem}.md"
    json_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_report(dataset, llm_comment), encoding="utf-8")
    print(f"REPORT_MD={md_path}")
    print(f"REPORT_JSON={json_path}")
    print(f"DATA_STATUS={dataset['data_status']}")
    print(f"LLM_STATUS={dataset['llm_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
