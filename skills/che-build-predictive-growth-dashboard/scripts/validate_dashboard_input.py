#!/usr/bin/env python3
"""Validate the reproducible input package for a predictive growth dashboard."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


ALLOWED_SOURCE_STATUS = {"ok", "partial", "blocked"}
ALLOWED_META_STATUS = {"complete", "partial"}
ALLOWED_SCENARIOS = {"pessimistic", "base", "optimistic"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_EVIDENCE = {
    "project_experiment",
    "project_historical_analogue",
    "comparable_pages",
    "external_benchmark",
    "expert_assumption",
}
ALLOWED_RAMP = {"step", "linear", "sigmoid", "custom"}
ALLOWED_HIERARCHY_STATUS = {"complete", "partial", "not_available"}
ALLOWED_FUNNEL_STATUS = {"ready", "partial", "blocked"}
ALLOWED_STAGE_STATUS = {"ready", "partial", "readiness_gap", "blocked"}
ALLOWED_LEARNING_STATUS = {"first_run", "pending", "active"}
ALLOWED_IDENTIFICATION = {"identified", "directional", "not_identified"}
REQUIRED_HORIZONS = (7, 30)
FINGERPRINT_FIELDS = (
    "actual_series",
    "adjustments_log",
    "events_calendar",
    "regime",
    "metric_definition",
    "sources",
)


def parse_iso_day(value: Any, label: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{label}: ожидается дата YYYY-MM-DD")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label}: некорректная дата {value!r}")
        return None


def parse_iso_datetime(value: Any, label: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str):
        errors.append(f"{label}: ожидается ISO datetime с часовым поясом")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label}: некорректный ISO datetime {value!r}")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{label}: требуется часовой пояс")
    return parsed


def finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def finite_nonnegative(value: Any) -> bool:
    return finite_number(value) and float(value) >= 0


def probability(value: Any) -> bool:
    return finite_number(value) and 0 <= float(value) <= 1


def close_enough(actual: float, expected: float, relative: float = 0.01) -> bool:
    tolerance = max(0.05, abs(expected) * relative)
    return abs(actual - expected) <= tolerance


def require_mapping(data: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key}: ожидается объект")
        return {}
    return value


def require_list(data: dict[str, Any], key: str, errors: list[str]) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        errors.append(f"{key}: ожидается массив")
        return []
    return value


def require_nonempty_string(
    mapping: dict[str, Any], key: str, label: str, errors: list[str]
) -> str | None:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}.{key}: требуется непустая строка")
        return None
    return value


def calculate_fingerprint(data: dict[str, Any]) -> str:
    payload = {key: data.get(key) for key in FINGERPRINT_FIELDS}
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_meta_and_run(
    data: dict[str, Any], errors: list[str]
) -> tuple[date | None, str | None]:
    meta = require_mapping(data, "meta", errors)
    if meta.get("schema_version") != "2.0":
        errors.append("meta.schema_version: ожидается строка '2.0'")
    for key in (
        "project",
        "domain",
        "target_metric",
        "target_unit",
        "timezone",
    ):
        require_nonempty_string(meta, key, "meta", errors)
    if meta.get("status") not in ALLOWED_META_STATUS:
        errors.append("meta.status: допустимы complete или partial")
    as_of = parse_iso_day(meta.get("as_of"), "meta.as_of", errors)

    run = require_mapping(data, "forecast_run", errors)
    run_id = require_nonempty_string(run, "run_id", "forecast_run", errors)
    parse_iso_datetime(run.get("generated_at"), "forecast_run.generated_at", errors)
    previous = run.get("previous_run_id")
    if previous is not None and (not isinstance(previous, str) or not previous.strip()):
        errors.append("forecast_run.previous_run_id: ожидается непустая строка или null")
    return as_of, run_id


def validate_metric_definition(data: dict[str, Any], errors: list[str]) -> None:
    metric = require_mapping(data, "metric_definition", errors)
    for key in ("name", "formula", "grain", "source_of_truth", "aggregation"):
        require_nonempty_string(metric, key, "metric_definition", errors)
    for key in ("inclusions", "exclusions"):
        values = metric.get(key)
        if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
            errors.append(f"metric_definition.{key}: ожидается массив строк")


def validate_sources(
    data: dict[str, Any],
    as_of: date | None,
    errors: list[str],
    warnings: list[str],
) -> list[str]:
    sources = require_list(data, "sources", errors)
    if not sources:
        errors.append("sources: требуется хотя бы один источник")
        return []
    names: set[str] = set()
    required_statuses: list[str] = []
    for index, source in enumerate(sources):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        name = require_nonempty_string(source, "name", label, errors)
        if name:
            if name in names:
                errors.append(f"{label}.name: дублирующийся источник {name!r}")
            names.add(name)
        for key in ("role", "grain", "units"):
            require_nonempty_string(source, key, label, errors)
        status = source.get("status")
        if status not in ALLOWED_SOURCE_STATUS:
            errors.append(f"{label}.status: допустимы ok, partial или blocked")
        required = source.get("required_for_target")
        if not isinstance(required, bool):
            errors.append(f"{label}.required_for_target: ожидается boolean")
        elif required:
            required_statuses.append(str(status))
            if status == "blocked":
                errors.append(f"{label}: обязательный источник не может быть blocked")

        freshness_value = source.get("freshness_date")
        if status == "blocked" and freshness_value in (None, ""):
            freshness = None
            if not isinstance(source.get("notes"), str) or not source["notes"].strip():
                errors.append(f"{label}.notes: укажите причину блокировки")
        else:
            freshness = parse_iso_day(
                freshness_value, f"{label}.freshness_date", errors
            )
        coverage_from = parse_iso_day(
            source.get("coverage_from"), f"{label}.coverage_from", errors
        )
        coverage_to = parse_iso_day(
            source.get("coverage_to"), f"{label}.coverage_to", errors
        )
        if coverage_from and coverage_to and coverage_from > coverage_to:
            errors.append(f"{label}: coverage_from позже coverage_to")
        if freshness and as_of:
            if freshness > as_of:
                errors.append(f"{label}.freshness_date: дата позже meta.as_of")
            elif (as_of - freshness).days > 3 and status == "ok":
                warnings.append(
                    f"{label}: источник помечен ok, но отстаёт от as_of более чем на 3 дня"
                )
    return required_statuses


def validate_actual_series(
    data: dict[str, Any], as_of: date | None, errors: list[str]
) -> dict[date, dict[str, Any]]:
    rows = require_list(data, "actual_series", errors)
    if len(rows) < 90:
        errors.append("actual_series: требуется минимум 90 дневных строк")
    parsed: dict[date, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        label = f"actual_series[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        day = parse_iso_day(row.get("date"), f"{label}.date", errors)
        actual = row.get("actual")
        adjusted = row.get("adjusted")
        ids = row.get("adjustment_ids")
        if not finite_nonnegative(actual):
            errors.append(f"{label}.actual: требуется неотрицательное число")
        if not finite_nonnegative(adjusted):
            errors.append(f"{label}.adjusted: требуется неотрицательное число")
        if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids):
            errors.append(f"{label}.adjustment_ids: ожидается массив строк")
            ids = []
        if (
            finite_nonnegative(actual)
            and finite_nonnegative(adjusted)
            and not close_enough(float(actual), float(adjusted), relative=0)
            and not ids
        ):
            errors.append(f"{label}: изменение actual → adjusted не связано с журналом")
        if day:
            if day in parsed:
                errors.append(f"{label}.date: дублируется дата {day}")
            parsed[day] = row

    days = sorted(parsed)
    for previous, current in zip(days, days[1:]):
        if current != previous + timedelta(days=1):
            errors.append(f"actual_series: разрыв между {previous} и {current}")
    if days and as_of and days[-1] != as_of:
        errors.append("actual_series: последняя дата должна совпадать с meta.as_of")
    return parsed


def validate_adjustments(
    data: dict[str, Any],
    actual_by_day: dict[date, dict[str, Any]],
    errors: list[str],
) -> None:
    rows = require_list(data, "adjustments_log", errors)
    adjustments: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        label = f"adjustments_log[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        adjustment_id = require_nonempty_string(row, "id", label, errors)
        if adjustment_id:
            if adjustment_id in adjustments:
                errors.append(f"{label}.id: дублируется {adjustment_id!r}")
            adjustments[adjustment_id] = row
        day = parse_iso_day(row.get("date"), f"{label}.date", errors)
        for key in ("original_value", "adjusted_value"):
            if not finite_nonnegative(row.get(key)):
                errors.append(f"{label}.{key}: требуется неотрицательное число")
        for key in ("reason", "method", "evidence"):
            require_nonempty_string(row, key, label, errors)
        if day and day not in actual_by_day:
            errors.append(f"{label}.date: даты нет в actual_series")

    for day, actual_row in actual_by_day.items():
        for adjustment_id in actual_row.get("adjustment_ids", []):
            adjustment = adjustments.get(adjustment_id)
            if not adjustment:
                errors.append(
                    f"actual_series[{day}]: неизвестный adjustment_id {adjustment_id!r}"
                )
                continue
            if adjustment.get("date") != day.isoformat():
                errors.append(
                    f"adjustments_log[{adjustment_id}]: дата не совпадает с actual_series"
                )
            original_value = adjustment.get("original_value")
            actual_value = actual_row.get("actual")
            if (
                finite_nonnegative(original_value)
                and finite_nonnegative(actual_value)
                and not close_enough(
                    float(original_value), float(actual_value), relative=0
                )
            ):
                errors.append(
                    f"adjustments_log[{adjustment_id}].original_value не совпадает с actual"
                )
            adjusted_value = adjustment.get("adjusted_value")
            series_adjusted = actual_row.get("adjusted")
            if (
                finite_nonnegative(adjusted_value)
                and finite_nonnegative(series_adjusted)
                and not close_enough(
                    float(adjusted_value), float(series_adjusted), relative=0
                )
            ):
                errors.append(
                    f"adjustments_log[{adjustment_id}].adjusted_value не совпадает с adjusted"
                )


def validate_events(data: dict[str, Any], errors: list[str]) -> None:
    events = require_list(data, "events_calendar", errors)
    seen: set[str] = set()
    for index, event in enumerate(events):
        label = f"events_calendar[{index}]"
        if not isinstance(event, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        event_id = require_nonempty_string(event, "id", label, errors)
        if event_id:
            if event_id in seen:
                errors.append(f"{label}.id: дублируется {event_id!r}")
            seen.add(event_id)
        start = parse_iso_day(event.get("date_from"), f"{label}.date_from", errors)
        end = parse_iso_day(event.get("date_to"), f"{label}.date_to", errors)
        if start and end and start > end:
            errors.append(f"{label}: date_from позже date_to")
        if event.get("status") not in {"observed", "confirmed", "planned"}:
            errors.append(f"{label}.status: допустимы observed, confirmed или planned")
        for key in ("type", "scope", "expected_direction", "evidence"):
            require_nonempty_string(event, key, label, errors)


def validate_regime(
    data: dict[str, Any],
    actual_by_day: dict[date, dict[str, Any]],
    as_of: date | None,
    errors: list[str],
) -> tuple[date | None, date | None, int]:
    regime = require_mapping(data, "regime", errors)
    training_from = parse_iso_day(
        regime.get("training_from"), "regime.training_from", errors
    )
    training_to = parse_iso_day(
        regime.get("training_to"), "regime.training_to", errors
    )
    require_nonempty_string(regime, "detection_method", "regime", errors)
    require_nonempty_string(regime, "rationale", "regime", errors)
    change_points = regime.get("change_points")
    if not isinstance(change_points, list):
        errors.append("regime.change_points: ожидается массив")
        change_points = []
    for index, change_point in enumerate(change_points):
        label = f"regime.change_points[{index}]"
        if not isinstance(change_point, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        parse_iso_day(change_point.get("date"), f"{label}.date", errors)
        for key in ("type", "evidence"):
            require_nonempty_string(change_point, key, label, errors)

    excluded_periods = regime.get("excluded_periods")
    if not isinstance(excluded_periods, list):
        errors.append("regime.excluded_periods: ожидается массив")
        excluded_periods = []
    for index, period in enumerate(excluded_periods):
        label = f"regime.excluded_periods[{index}]"
        if not isinstance(period, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        period_from = parse_iso_day(
            period.get("date_from"), f"{label}.date_from", errors
        )
        period_to = parse_iso_day(period.get("date_to"), f"{label}.date_to", errors)
        if period_from and period_to and period_from > period_to:
            errors.append(f"{label}: date_from позже date_to")
        require_nonempty_string(period, "reason", label, errors)
    history_days = 0
    if training_from and training_to:
        if training_from > training_to:
            errors.append("regime: training_from позже training_to")
        else:
            history_days = (training_to - training_from).days + 1
            if history_days < 90:
                errors.append("regime: сопоставимое обучающее окно короче 90 дней")
        if training_from not in actual_by_day or training_to not in actual_by_day:
            errors.append("regime: обучающее окно должно входить в actual_series")
    if training_to and as_of and training_to != as_of:
        errors.append("regime.training_to: должна совпадать с meta.as_of")
    return training_from, training_to, history_days


def validate_fingerprint(
    data: dict[str, Any], actual_rows: int, errors: list[str]
) -> None:
    fingerprint = require_mapping(data, "data_fingerprint", errors)
    if fingerprint.get("algorithm") != "sha256":
        errors.append("data_fingerprint.algorithm: ожидается sha256")
    value = fingerprint.get("value")
    expected = calculate_fingerprint(data)
    if not isinstance(value, str) or value != expected:
        errors.append(
            "data_fingerprint.value: не совпадает с воспроизводимым hash; "
            "запустите валидатор с --write-fingerprint"
        )
    if fingerprint.get("series_rows") != actual_rows:
        errors.append("data_fingerprint.series_rows: не совпадает с actual_series")


def validate_horizons(data: dict[str, Any], errors: list[str]) -> None:
    if data.get("horizons") != list(REQUIRED_HORIZONS):
        errors.append("horizons: ожидается массив [7, 30]")


def validate_scenario_totals(
    data: dict[str, Any], errors: list[str]
) -> dict[int, dict[str, float]]:
    rows = require_list(data, "scenario_totals", errors)
    totals: dict[int, dict[str, float]] = {7: {}, 30: {}}
    seen: set[tuple[int, str]] = set()
    for index, row in enumerate(rows):
        label = f"scenario_totals[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        horizon = row.get("horizon")
        scenario = row.get("scenario")
        value = row.get("value")
        if horizon not in REQUIRED_HORIZONS:
            errors.append(f"{label}.horizon: допустимы 7 или 30")
            continue
        if scenario not in ALLOWED_SCENARIOS:
            errors.append(f"{label}.scenario: неизвестный сценарий")
            continue
        if not finite_nonnegative(value):
            errors.append(f"{label}.value: требуется неотрицательное число")
            continue
        key = (horizon, scenario)
        if key in seen:
            errors.append(f"{label}: дублируется {horizon}/{scenario}")
            continue
        seen.add(key)
        totals[horizon][scenario] = float(value)

    expected = {(h, s) for h in REQUIRED_HORIZONS for s in ALLOWED_SCENARIOS}
    missing = sorted(expected - seen)
    if missing:
        errors.append(f"scenario_totals: отсутствуют комбинации {missing}")
    for horizon, values in totals.items():
        if set(values) == ALLOWED_SCENARIOS and not (
            values["pessimistic"] <= values["base"] <= values["optimistic"]
        ):
            errors.append(
                f"scenario_totals: нарушен порядок сценариев для горизонта {horizon}"
            )
    return totals


def validate_uncertainty_totals(
    data: dict[str, Any],
    scenario_totals: dict[int, dict[str, float]],
    errors: list[str],
) -> dict[int, dict[str, float]]:
    rows = require_list(data, "uncertainty_totals", errors)
    totals: dict[int, dict[str, float]] = {7: {}, 30: {}}
    seen: set[int] = set()
    for index, row in enumerate(rows):
        label = f"uncertainty_totals[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        horizon = row.get("horizon")
        if horizon not in REQUIRED_HORIZONS:
            errors.append(f"{label}.horizon: допустимы 7 или 30")
            continue
        if horizon in seen:
            errors.append(f"{label}.horizon: дублируется {horizon}")
        seen.add(horizon)
        values: dict[str, float] = {}
        for quantile in ("p10", "p50", "p90"):
            value = row.get(quantile)
            if not finite_nonnegative(value):
                errors.append(f"{label}.{quantile}: требуется неотрицательное число")
            else:
                values[quantile] = float(value)
        if len(values) == 3 and not (
            values["p10"] <= values["p50"] <= values["p90"]
        ):
            errors.append(f"{label}: нарушен порядок P10/P50/P90")
        base = scenario_totals.get(horizon, {}).get("base")
        if base is not None and "p50" in values and not close_enough(values["p50"], base):
            errors.append(f"{label}.p50: должна совпадать с base")
        totals[horizon] = values
    if seen != set(REQUIRED_HORIZONS):
        errors.append("uncertainty_totals: требуются горизонты 7 и 30")
    return totals


def validate_daily_forecast(
    data: dict[str, Any],
    as_of: date | None,
    totals: dict[int, dict[str, float]],
    errors: list[str],
) -> list[tuple[date, dict[str, float]]]:
    rows = require_list(data, "daily_forecast", errors)
    if len(rows) != 30:
        errors.append("daily_forecast: требуется ровно 30 дневных строк")
    parsed: list[tuple[date, dict[str, float]]] = []
    seen_dates: set[date] = set()
    fields = ("p10", "p50", "p90", "pessimistic", "base", "optimistic")
    for index, row in enumerate(rows):
        label = f"daily_forecast[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        day = parse_iso_day(row.get("date"), f"{label}.date", errors)
        values: dict[str, float] = {}
        for field in fields:
            value = row.get(field)
            if not finite_nonnegative(value):
                errors.append(f"{label}.{field}: требуется неотрицательное число")
            else:
                values[field] = float(value)
        if len(values) == len(fields):
            if not (values["p10"] <= values["p50"] <= values["p90"]):
                errors.append(f"{label}: нарушен порядок P10/P50/P90")
            if not close_enough(values["p50"], values["base"]):
                errors.append(f"{label}: p50 должна совпадать с base")
            if not (
                values["pessimistic"]
                <= values["base"]
                <= values["optimistic"]
            ):
                errors.append(f"{label}: нарушен порядок управленческих сценариев")
        if day:
            if day in seen_dates:
                errors.append(f"{label}.date: дублируется дата {day}")
            seen_dates.add(day)
            parsed.append((day, values))

    parsed.sort(key=lambda item: item[0])
    if parsed and as_of and parsed[0][0] != as_of + timedelta(days=1):
        errors.append("daily_forecast: первая дата должна следовать после meta.as_of")
    for previous, current in zip(parsed, parsed[1:]):
        if current[0] != previous[0] + timedelta(days=1):
            errors.append(f"daily_forecast: разрыв между {previous[0]} и {current[0]}")

    for horizon in REQUIRED_HORIZONS:
        if len(parsed) < horizon or set(totals.get(horizon, {})) != ALLOWED_SCENARIOS:
            continue
        for scenario in ALLOWED_SCENARIOS:
            daily_sum = sum(item[1].get(scenario, 0.0) for item in parsed[:horizon])
            declared = totals[horizon][scenario]
            if not close_enough(daily_sum, declared):
                errors.append(
                    f"scenario_totals {horizon}/{scenario}: {declared:g} "
                    f"не сходится с дневным рядом {daily_sum:g}"
                )
    return parsed


def validate_candidate_metric(
    metric: Any, label: str, errors: list[str]
) -> tuple[int | None, dict[str, float]]:
    if not isinstance(metric, dict):
        errors.append(f"{label}: ожидается объект")
        return None, {}
    horizon = metric.get("horizon")
    if horizon not in REQUIRED_HORIZONS:
        errors.append(f"{label}.horizon: допустимы 7 или 30")
        horizon = None
    values: dict[str, float] = {}
    for key in ("wape", "mae", "mase"):
        value = metric.get(key)
        if not finite_nonnegative(value):
            errors.append(f"{label}.{key}: требуется неотрицательное число")
        else:
            values[key] = float(value)
    bias = metric.get("bias")
    if not finite_number(bias):
        errors.append(f"{label}.bias: требуется конечное число")
    else:
        values["bias"] = float(bias)
    return horizon, values


def validate_model(
    data: dict[str, Any],
    training_from: date | None,
    training_to: date | None,
    history_days: int,
    required_statuses: list[str],
    errors: list[str],
) -> tuple[str | None, dict[int, dict[str, float]], dict[tuple[str, int], int]]:
    model = require_mapping(data, "model", errors)
    selected = require_nonempty_string(model, "selected_model_id", "model", errors)
    baseline = require_nonempty_string(model, "baseline_model_id", "model", errors)
    model_from = parse_iso_day(model.get("training_from"), "model.training_from", errors)
    model_to = parse_iso_day(model.get("training_to"), "model.training_to", errors)
    if model_from and training_from and model_from != training_from:
        errors.append("model.training_from: не совпадает с regime.training_from")
    if model_to and training_to and model_to != training_to:
        errors.append("model.training_to: не совпадает с regime.training_to")
    minimum_lift = model.get("minimum_lift_pct")
    if not finite_nonnegative(minimum_lift):
        errors.append("model.minimum_lift_pct: требуется неотрицательное число")
        minimum_lift = 0.0
    require_nonempty_string(model, "selection_reason", "model", errors)
    require_nonempty_string(model, "uncertainty_method", "model", errors)
    confidence = model.get("confidence")
    if confidence not in ALLOWED_CONFIDENCE:
        errors.append("model.confidence: допустимы high, medium или low")

    candidates = model.get("candidate_models")
    candidate_metrics: dict[str, dict[int, dict[str, float]]] = {}
    candidate_complexity: dict[str, str] = {}
    eligible_candidates: set[str] = set()
    if not isinstance(candidates, list) or len(candidates) < 2:
        errors.append("model.candidate_models: требуется минимум два кандидата")
        candidates = []
    for index, candidate in enumerate(candidates):
        label = f"model.candidate_models[{index}]"
        if not isinstance(candidate, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        candidate_id = require_nonempty_string(candidate, "id", label, errors)
        require_nonempty_string(candidate, "method", label, errors)
        complexity = candidate.get("complexity")
        if complexity not in {"baseline", "simple", "advanced"}:
            errors.append(f"{label}.complexity: допустимы baseline, simple, advanced")
        if not isinstance(candidate.get("parameters"), dict):
            errors.append(f"{label}.parameters: ожидается объект")
        if not isinstance(candidate.get("eligible"), bool):
            errors.append(f"{label}.eligible: ожидается boolean")
        metrics = candidate.get("metrics")
        if not isinstance(metrics, list):
            errors.append(f"{label}.metrics: ожидается массив")
            metrics = []
        by_horizon: dict[int, dict[str, float]] = {}
        for metric_index, metric in enumerate(metrics):
            horizon, values = validate_candidate_metric(
                metric, f"{label}.metrics[{metric_index}]", errors
            )
            if horizon:
                if horizon in by_horizon:
                    errors.append(f"{label}.metrics: дублируется горизонт {horizon}")
                by_horizon[horizon] = values
        if set(by_horizon) != set(REQUIRED_HORIZONS):
            errors.append(f"{label}.metrics: требуются горизонты 7 и 30")
        if candidate_id:
            if candidate_id in candidate_metrics:
                errors.append(f"{label}.id: дублируется {candidate_id!r}")
            candidate_metrics[candidate_id] = by_horizon
            candidate_complexity[candidate_id] = str(complexity)
            if candidate.get("eligible") is True:
                eligible_candidates.add(candidate_id)

    if selected and selected not in candidate_metrics:
        errors.append("model.selected_model_id: модель отсутствует в candidate_models")
    if baseline and baseline not in candidate_metrics:
        errors.append("model.baseline_model_id: модель отсутствует в candidate_models")
    if baseline and candidate_complexity.get(baseline) != "baseline":
        errors.append("model.baseline_model_id: кандидат должен иметь complexity=baseline")

    folds = model.get("backtest_folds")
    if not isinstance(folds, list):
        errors.append("model.backtest_folds: ожидается массив")
        folds = []
    fold_counts: dict[tuple[str, int], int] = defaultdict(int)
    fold_ids: set[str] = set()
    fold_cutoffs: dict[tuple[str, int], set[date]] = defaultdict(set)
    fold_calculations: dict[tuple[str, int], list[dict[str, float]]] = defaultdict(list)
    for index, fold in enumerate(folds):
        label = f"model.backtest_folds[{index}]"
        if not isinstance(fold, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        fold_id = require_nonempty_string(fold, "fold_id", label, errors)
        if fold_id:
            if fold_id in fold_ids:
                errors.append(f"{label}.fold_id: дублируется {fold_id!r}")
            fold_ids.add(fold_id)
        model_id = fold.get("model_id")
        if model_id not in candidate_metrics:
            errors.append(f"{label}.model_id: неизвестная модель")
        horizon = fold.get("horizon")
        if horizon not in REQUIRED_HORIZONS:
            errors.append(f"{label}.horizon: допустимы 7 или 30")
        cutoff = parse_iso_day(fold.get("cutoff"), f"{label}.cutoff", errors)
        observations = fold.get("observations")
        if not isinstance(observations, list):
            errors.append(f"{label}.observations: ожидается массив")
            observations = []
        elif horizon in REQUIRED_HORIZONS and len(observations) != horizon:
            errors.append(f"{label}.observations: число строк должно равняться horizon")
        previous_day: date | None = None
        fold_actuals: list[float] = []
        fold_forecasts: list[float] = []
        coverage_hits = 0
        coverage_count = 0
        for observation_index, observation in enumerate(observations):
            obs_label = f"{label}.observations[{observation_index}]"
            if not isinstance(observation, dict):
                errors.append(f"{obs_label}: ожидается объект")
                continue
            day = parse_iso_day(observation.get("date"), f"{obs_label}.date", errors)
            for key in ("actual", "forecast"):
                if not finite_nonnegative(observation.get(key)):
                    errors.append(f"{obs_label}.{key}: требуется неотрицательное число")
            if finite_nonnegative(observation.get("actual")) and finite_nonnegative(
                observation.get("forecast")
            ):
                fold_actuals.append(float(observation["actual"]))
                fold_forecasts.append(float(observation["forecast"]))
            if model_id == selected:
                p10 = observation.get("p10")
                p90 = observation.get("p90")
                if not finite_nonnegative(p10) or not finite_nonnegative(p90):
                    errors.append(
                        f"{obs_label}: для выбранной модели требуются p10 и p90"
                    )
                elif finite_nonnegative(observation.get("forecast")):
                    if not (
                        float(p10)
                        <= float(observation["forecast"])
                        <= float(p90)
                    ):
                        errors.append(f"{obs_label}: нарушен порядок p10/forecast/p90")
                    if finite_nonnegative(observation.get("actual")):
                        coverage_count += 1
                        if float(p10) <= float(observation["actual"]) <= float(p90):
                            coverage_hits += 1
            if day and cutoff and observation_index == 0 and day != cutoff + timedelta(days=1):
                errors.append(f"{obs_label}.date: должна следовать сразу после cutoff")
            if day and previous_day and day != previous_day + timedelta(days=1):
                errors.append(f"{obs_label}.date: разрыв внутри fold")
            if day:
                previous_day = day
        if (
            model_id in candidate_metrics
            and horizon in REQUIRED_HORIZONS
            and cutoff is not None
            and len(fold_actuals) == horizon
        ):
            actual_sum = sum(fold_actuals)
            if actual_sum <= 0:
                errors.append(f"{label}: WAPE не определён при нулевой сумме actual")
            else:
                abs_error = sum(
                    abs(actual - forecast)
                    for actual, forecast in zip(fold_actuals, fold_forecasts)
                )
                signed_error = sum(
                    forecast - actual
                    for actual, forecast in zip(fold_actuals, fold_forecasts)
                )
                key = (str(model_id), int(horizon))
                fold_counts[key] += 1
                fold_cutoffs[key].add(cutoff)
                fold_calculations[key].append(
                    {
                        "absolute_error": abs_error,
                        "actual_sum": actual_sum,
                        "count": float(horizon),
                        "signed_error": signed_error,
                        "wape": abs_error / actual_sum * 100,
                        "coverage_hits": float(coverage_hits),
                        "coverage_count": float(coverage_count),
                    }
                )

    required_fold_models = eligible_candidates | ({selected, baseline} - {None})
    for model_id in required_fold_models:
        for horizon in REQUIRED_HORIZONS:
            if fold_counts[(str(model_id), horizon)] < 3:
                errors.append(
                    f"model.backtest_folds: для {model_id}/{horizon} требуется минимум 3 folds"
                )
            if baseline and model_id != baseline:
                baseline_cutoffs = fold_cutoffs[(baseline, horizon)]
                model_cutoffs = fold_cutoffs[(str(model_id), horizon)]
                if model_cutoffs != baseline_cutoffs:
                    errors.append(
                        f"model.backtest_folds: {model_id}/{horizon} использует "
                        "другие cutoff, чем baseline"
                    )

    calculated_metrics: dict[tuple[str, int], dict[str, float]] = {}
    for key, fold_values in fold_calculations.items():
        absolute_error = sum(item["absolute_error"] for item in fold_values)
        actual_sum = sum(item["actual_sum"] for item in fold_values)
        count = sum(item["count"] for item in fold_values)
        signed_error = sum(item["signed_error"] for item in fold_values)
        calculated_metrics[key] = {
            "wape": absolute_error / actual_sum * 100,
            "mae": absolute_error / count,
            "bias": signed_error / count,
            "wape_std": statistics.pstdev(item["wape"] for item in fold_values),
        }
        coverage_count = sum(item["coverage_count"] for item in fold_values)
        if coverage_count:
            calculated_metrics[key]["interval_coverage_pct"] = (
                sum(item["coverage_hits"] for item in fold_values)
                / coverage_count
                * 100
            )
    if baseline:
        for model_id in required_fold_models:
            for horizon in REQUIRED_HORIZONS:
                calculated = calculated_metrics.get((str(model_id), horizon))
                baseline_calculated = calculated_metrics.get((baseline, horizon))
                if not calculated or not baseline_calculated:
                    continue
                baseline_mae = baseline_calculated["mae"]
                if baseline_mae == 0:
                    mase = 0.0 if calculated["mae"] == 0 else math.inf
                else:
                    mase = calculated["mae"] / baseline_mae
                calculated["mase"] = mase
                if not math.isfinite(mase):
                    errors.append(
                        f"model.backtest_folds: MASE не определён для {model_id}/{horizon}"
                    )

    for model_id in required_fold_models:
        for horizon in REQUIRED_HORIZONS:
            declared = candidate_metrics.get(str(model_id), {}).get(horizon, {})
            calculated = calculated_metrics.get((str(model_id), horizon), {})
            for metric_name in ("wape", "mae", "mase", "bias"):
                if (
                    metric_name in declared
                    and metric_name in calculated
                    and not close_enough(
                        declared[metric_name],
                        calculated[metric_name],
                        relative=0.02,
                    )
                ):
                    errors.append(
                        f"model.candidate_models[{model_id}].metrics[{horizon}]."
                        f"{metric_name}: не сходится с observations"
                    )

    summaries = model.get("backtest_summary")
    summary_by_horizon: dict[int, dict[str, float]] = {}
    if not isinstance(summaries, list):
        errors.append("model.backtest_summary: ожидается массив")
        summaries = []
    for index, summary in enumerate(summaries):
        label = f"model.backtest_summary[{index}]"
        if not isinstance(summary, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        horizon = summary.get("horizon")
        if horizon not in REQUIRED_HORIZONS:
            errors.append(f"{label}.horizon: допустимы 7 или 30")
            continue
        if horizon in summary_by_horizon:
            errors.append(f"{label}.horizon: дублируется {horizon}")
        values: dict[str, float] = {}
        for key in (
            "wape",
            "mae",
            "mase",
            "wape_std",
            "baseline_wape",
            "lift_vs_baseline_pct",
            "interval_coverage_pct",
        ):
            value = summary.get(key)
            if not finite_nonnegative(value):
                errors.append(f"{label}.{key}: требуется неотрицательное число")
            else:
                values[key] = float(value)
        if values.get("interval_coverage_pct", 0) > 100:
            errors.append(f"{label}.interval_coverage_pct: не может быть выше 100")
        bias = summary.get("bias")
        if not finite_number(bias):
            errors.append(f"{label}.bias: требуется конечное число")
        else:
            values["bias"] = float(bias)
        folds_declared = summary.get("folds")
        if not isinstance(folds_declared, int) or isinstance(folds_declared, bool):
            errors.append(f"{label}.folds: требуется целое число")
        elif selected and folds_declared != fold_counts[(selected, horizon)]:
            errors.append(f"{label}.folds: не совпадает с backtest_folds выбранной модели")
        if "wape" in values and "baseline_wape" in values:
            baseline_wape = values["baseline_wape"]
            expected_lift = (
                0.0
                if baseline_wape == 0
                else (baseline_wape - values["wape"]) / baseline_wape * 100
            )
            if "lift_vs_baseline_pct" in values and not close_enough(
                values["lift_vs_baseline_pct"], expected_lift, relative=0.02
            ):
                errors.append(f"{label}.lift_vs_baseline_pct: не сходится с WAPE")
        summary_by_horizon[horizon] = values

    if set(summary_by_horizon) != set(REQUIRED_HORIZONS):
        errors.append("model.backtest_summary: требуются горизонты 7 и 30")

    for horizon in REQUIRED_HORIZONS:
        summary = summary_by_horizon.get(horizon, {})
        selected_metric = candidate_metrics.get(selected or "", {}).get(horizon, {})
        baseline_metric = candidate_metrics.get(baseline or "", {}).get(horizon, {})
        calculated_selected = calculated_metrics.get((selected or "", horizon), {})
        calculated_baseline = calculated_metrics.get((baseline or "", horizon), {})
        for metric_name in (
            "wape",
            "mae",
            "mase",
            "bias",
            "wape_std",
            "interval_coverage_pct",
        ):
            if (
                metric_name in summary
                and metric_name in calculated_selected
                and not close_enough(
                    summary[metric_name],
                    calculated_selected[metric_name],
                    relative=0.02,
                )
            ):
                errors.append(
                    f"model.backtest_summary[{horizon}].{metric_name} "
                    "не сходится с observations"
                )
        if (
            "baseline_wape" in summary
            and "wape" in calculated_baseline
            and not close_enough(
                summary["baseline_wape"],
                calculated_baseline["wape"],
                relative=0.02,
            )
        ):
            errors.append(
                f"model.backtest_summary[{horizon}].baseline_wape "
                "не сходится с observations"
            )
        if "wape" in summary and "wape" in selected_metric and not close_enough(
            summary["wape"], selected_metric["wape"], relative=0.02
        ):
            errors.append(
                f"model.backtest_summary[{horizon}].wape не совпадает с выбранным кандидатом"
            )
        if "baseline_wape" in summary and "wape" in baseline_metric and not close_enough(
            summary["baseline_wape"], baseline_metric["wape"], relative=0.02
        ):
            errors.append(
                f"model.backtest_summary[{horizon}].baseline_wape не совпадает с baseline"
            )
        if (
            selected
            and baseline
            and selected != baseline
            and summary.get("lift_vs_baseline_pct", -1) < float(minimum_lift)
        ):
            errors.append(
                f"model: выбранная модель не проходит minimum_lift_pct на {horizon} дней"
            )

    if confidence == "high":
        if history_days < 180:
            errors.append("model.confidence=high: требуется минимум 180 дней истории")
        if any(value != "ok" for value in required_statuses):
            errors.append("model.confidence=high: все обязательные источники должны быть ok")
        if any(
            summary_by_horizon.get(horizon, {}).get("wape", math.inf) >= 10
            for horizon in REQUIRED_HORIZONS
        ):
            errors.append("model.confidence=high: WAPE 7 и 30 должны быть <10%")
        if any(
            summary_by_horizon.get(horizon, {}).get(
                "interval_coverage_pct", -math.inf
            )
            < 75
            for horizon in REQUIRED_HORIZONS
        ):
            errors.append(
                "model.confidence=high: фактическое покрытие P10/P90 "
                "должно быть не ниже 75%"
            )
    if confidence == "medium" and any(
        summary_by_horizon.get(horizon, {}).get("wape", math.inf) > 20
        for horizon in REQUIRED_HORIZONS
    ):
        errors.append("model.confidence=medium: WAPE 7 и 30 должны быть ≤20%")

    return confidence if isinstance(confidence, str) else None, summary_by_horizon, fold_counts


def validate_scenario_confidence(
    data: dict[str, Any], model_confidence: str | None, errors: list[str]
) -> dict[str, str]:
    confidence = require_mapping(data, "scenario_confidence", errors)
    result: dict[str, str] = {}
    for scenario in ALLOWED_SCENARIOS:
        value = confidence.get(scenario)
        if value not in ALLOWED_CONFIDENCE:
            errors.append(
                f"scenario_confidence.{scenario}: допустимы high, medium или low"
            )
        else:
            result[scenario] = value
    if model_confidence and result.get("base") != model_confidence:
        errors.append("scenario_confidence.base: должна совпадать с model.confidence")
    return result


def validate_horizon_mapping(
    value: Any, label: str, errors: list[str]
) -> dict[int, float]:
    if not isinstance(value, dict):
        errors.append(f"{label}: ожидается объект с ключами 7 и 30")
        return {}
    result: dict[int, float] = {}
    for horizon in REQUIRED_HORIZONS:
        raw = value.get(str(horizon))
        if not finite_nonnegative(raw):
            errors.append(f"{label}.{horizon}: требуется неотрицательное число")
        else:
            result[horizon] = float(raw)
    return result


def validate_actions(
    data: dict[str, Any],
    forecast_days: list[date],
    errors: list[str],
) -> tuple[dict[date, float], float, float]:
    actions = require_list(data, "actions", errors)
    if not actions:
        errors.append("actions: требуется хотя бы одно управленческое действие")
    valid_days = set(forecast_days)
    start_of_forecast = forecast_days[0] if forecast_days else None
    daily_total: dict[date, float] = defaultdict(float)
    expert_impact_30 = 0.0
    total_impact_30 = 0.0
    groups: dict[str, list[float]] = defaultdict(list)
    ids: set[str] = set()
    for index, action in enumerate(actions):
        label = f"actions[{index}]"
        if not isinstance(action, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        action_id = require_nonempty_string(action, "id", label, errors)
        if action_id:
            if action_id in ids:
                errors.append(f"{label}.id: дублируется {action_id!r}")
            ids.add(action_id)
        for key in (
            "priority",
            "lever",
            "metric",
            "baseline",
            "target",
            "impact_unit",
            "evidence_reference",
            "interaction_group",
            "resource",
            "dependency",
            "done_when",
        ):
            if action.get(key) in ("", None):
                errors.append(f"{label}.{key}: поле обязательно")
        start_date = parse_iso_day(action.get("start_date"), f"{label}.start_date", errors)
        lag_days = action.get("lag_days")
        if (
            not isinstance(lag_days, int)
            or isinstance(lag_days, bool)
            or lag_days < 0
        ):
            errors.append(f"{label}.lag_days: требуется неотрицательное целое число")
            lag_days = 0
        if action.get("ramp_curve") not in ALLOWED_RAMP:
            errors.append(f"{label}.ramp_curve: неизвестный тип кривой")
        completion = action.get("completion_probability")
        outcome = action.get("outcome_probability")
        overlap = action.get("overlap_discount")
        for key, value in (
            ("completion_probability", completion),
            ("outcome_probability", outcome),
            ("overlap_discount", overlap),
        ):
            if not probability(value):
                errors.append(f"{label}.{key}: требуется число от 0 до 1")
        cap = action.get("impact_cap")
        if not finite_nonnegative(cap):
            errors.append(f"{label}.impact_cap: требуется неотрицательное число")
            cap = 0.0
        evidence = action.get("evidence_level")
        if evidence not in ALLOWED_EVIDENCE:
            errors.append(f"{label}.evidence_level: неизвестный уровень")
        expected = validate_horizon_mapping(
            action.get("expected_impact_by_horizon"),
            f"{label}.expected_impact_by_horizon",
            errors,
        )
        ranges = action.get("impact_range_by_horizon")
        if not isinstance(ranges, dict):
            errors.append(f"{label}.impact_range_by_horizon: ожидается объект")
        else:
            for horizon in REQUIRED_HORIZONS:
                interval = ranges.get(str(horizon))
                interval_label = f"{label}.impact_range_by_horizon.{horizon}"
                if not isinstance(interval, dict):
                    errors.append(f"{interval_label}: ожидается объект low/high")
                    continue
                low = interval.get("low")
                high = interval.get("high")
                if not finite_nonnegative(low) or not finite_nonnegative(high):
                    errors.append(f"{interval_label}: low/high должны быть числами ≥0")
                elif float(low) > float(high):
                    errors.append(f"{interval_label}: low больше high")
                elif horizon in expected and not (
                    float(low) <= expected[horizon] <= float(high)
                ):
                    errors.append(f"{interval_label}: не содержит expected impact")

        cost = action.get("cost")
        if not isinstance(cost, dict):
            errors.append(f"{label}.cost: ожидается объект amount/currency")
        else:
            if not finite_nonnegative(cost.get("amount")):
                errors.append(f"{label}.cost.amount: требуется число ≥0")
            require_nonempty_string(cost, "currency", f"{label}.cost", errors)

        daily = action.get("daily_impact")
        if not isinstance(daily, list):
            errors.append(f"{label}.daily_impact: ожидается массив")
            daily = []
        action_daily: dict[date, float] = {}
        earliest_effect = (
            start_date + timedelta(days=lag_days)
            if start_date is not None
            else None
        )
        for impact_index, impact in enumerate(daily):
            impact_label = f"{label}.daily_impact[{impact_index}]"
            if not isinstance(impact, dict):
                errors.append(f"{impact_label}: ожидается объект")
                continue
            day = parse_iso_day(impact.get("date"), f"{impact_label}.date", errors)
            value = impact.get("expected_impact")
            if not finite_nonnegative(value):
                errors.append(f"{impact_label}.expected_impact: требуется число ≥0")
                continue
            if day:
                if day not in valid_days:
                    errors.append(f"{impact_label}.date: вне окна прогноза")
                if day in action_daily:
                    errors.append(f"{impact_label}.date: дублируется")
                if earliest_effect and float(value) > 0 and day < earliest_effect:
                    errors.append(f"{impact_label}: эффект начинается раньше start_date + lag")
                action_daily[day] = float(value)
                daily_total[day] += float(value)

        ordered = forecast_days
        for horizon in REQUIRED_HORIZONS:
            calculated = sum(action_daily.get(day, 0.0) for day in ordered[:horizon])
            if horizon in expected and not close_enough(calculated, expected[horizon]):
                errors.append(
                    f"{label}.expected_impact_by_horizon.{horizon}: "
                    f"{expected[horizon]:g} не сходится с daily_impact {calculated:g}"
                )
        adjusted_cap = (
            float(cap)
            * (float(completion) if probability(completion) else 0.0)
            * (float(outcome) if probability(outcome) else 0.0)
            * (float(overlap) if probability(overlap) else 0.0)
        )
        calculated_30 = sum(action_daily.values())
        if calculated_30 > adjusted_cap + max(0.05, adjusted_cap * 0.01):
            errors.append(f"{label}: daily_impact превышает probability-adjusted impact_cap")
        total_impact_30 += calculated_30
        if evidence == "expert_assumption":
            expert_impact_30 += calculated_30
        group = action.get("interaction_group")
        if isinstance(group, str) and probability(overlap):
            groups[group].append(float(overlap))
        if start_of_forecast and start_date and start_date < start_of_forecast - timedelta(days=30):
            errors.append(f"{label}.start_date: слишком далеко до окна прогноза")

    for group, discounts in groups.items():
        if len(discounts) > 1 and all(close_enough(item, 1.0, relative=0) for item in discounts):
            errors.append(
                f"actions: interaction_group {group!r} содержит несколько действий "
                "без overlap discount"
            )
    return daily_total, expert_impact_30, total_impact_30


def validate_blockers(
    data: dict[str, Any],
    forecast_days: list[date],
    errors: list[str],
    warnings: list[str],
) -> dict[date, float]:
    blockers = require_list(data, "blockers", errors)
    if not blockers:
        warnings.append("blockers: список пуст; подтвердите отсутствие измеримых рисков")
    valid_days = set(forecast_days)
    daily_total: dict[date, float] = defaultdict(float)
    ids: set[str] = set()
    for index, blocker in enumerate(blockers):
        label = f"blockers[{index}]"
        if not isinstance(blocker, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        blocker_id = require_nonempty_string(blocker, "id", label, errors)
        if blocker_id:
            if blocker_id in ids:
                errors.append(f"{label}.id: дублируется {blocker_id!r}")
            ids.add(blocker_id)
        for key in ("severity", "metric", "evidence", "resolution"):
            require_nonempty_string(blocker, key, label, errors)
        if not probability(blocker.get("probability")):
            errors.append(f"{label}.probability: требуется число от 0 до 1")
        expected = validate_horizon_mapping(
            blocker.get("expected_loss_by_horizon"),
            f"{label}.expected_loss_by_horizon",
            errors,
        )
        daily = blocker.get("daily_loss")
        if not isinstance(daily, list):
            errors.append(f"{label}.daily_loss: ожидается массив")
            daily = []
        blocker_daily: dict[date, float] = {}
        for loss_index, loss in enumerate(daily):
            loss_label = f"{label}.daily_loss[{loss_index}]"
            if not isinstance(loss, dict):
                errors.append(f"{loss_label}: ожидается объект")
                continue
            day = parse_iso_day(loss.get("date"), f"{loss_label}.date", errors)
            value = loss.get("expected_loss")
            if not finite_nonnegative(value):
                errors.append(f"{loss_label}.expected_loss: требуется число ≥0")
                continue
            if day:
                if day not in valid_days:
                    errors.append(f"{loss_label}.date: вне окна прогноза")
                if day in blocker_daily:
                    errors.append(f"{loss_label}.date: дублируется")
                blocker_daily[day] = float(value)
                daily_total[day] += float(value)
        for horizon in REQUIRED_HORIZONS:
            calculated = sum(
                blocker_daily.get(day, 0.0) for day in forecast_days[:horizon]
            )
            if horizon in expected and not close_enough(calculated, expected[horizon]):
                errors.append(
                    f"{label}.expected_loss_by_horizon.{horizon}: "
                    f"{expected[horizon]:g} не сходится с daily_loss {calculated:g}"
                )
    return daily_total


def validate_scenario_linkage(
    daily_forecast: list[tuple[date, dict[str, float]]],
    action_daily: dict[date, float],
    blocker_daily: dict[date, float],
    scenario_confidence: dict[str, str],
    expert_impact_30: float,
    total_impact_30: float,
    errors: list[str],
) -> None:
    for day, values in daily_forecast:
        if not {"base", "optimistic", "pessimistic"} <= set(values):
            continue
        expected_optimistic = values["base"] + action_daily.get(day, 0.0)
        expected_pessimistic = max(0.0, values["base"] - blocker_daily.get(day, 0.0))
        if not close_enough(
            values["optimistic"], expected_optimistic, relative=0.001
        ):
            errors.append(
                f"daily_forecast[{day}].optimistic: не связан с daily_impact действий"
            )
        if not close_enough(
            values["pessimistic"], expected_pessimistic, relative=0.001
        ):
            errors.append(
                f"daily_forecast[{day}].pessimistic: не связан с daily_loss рисков"
            )
    if (
        total_impact_30 > 0
        and expert_impact_30 / total_impact_30 > 0.5
        and scenario_confidence.get("optimistic") != "low"
    ):
        errors.append(
            "scenario_confidence.optimistic: должна быть low, если >50% эффекта "
            "основано на expert_assumption"
        )


def validate_business_registry(data: dict[str, Any], errors: list[str]) -> None:
    rows = require_list(data, "business_registry", errors)
    if not rows:
        errors.append("business_registry: требуется хотя бы одна подтверждённая связка")
    for index, row in enumerate(rows):
        label = f"business_registry[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        for key in (
            "product",
            "audience",
            "customer_job",
            "intent_type",
            "cluster_id",
            "url",
            "cta",
            "conversion_event",
            "lead_quality_rule",
            "business_goal",
        ):
            require_nonempty_string(row, key, label, errors)
        deal_lag = row.get("deal_lag_days")
        if not isinstance(deal_lag, int) or isinstance(deal_lag, bool) or deal_lag < 0:
            errors.append(f"{label}.deal_lag_days: требуется целое число ≥0")
        if row.get("visit_value_level") not in {"high", "medium", "low", "unknown"}:
            errors.append(f"{label}.visit_value_level: неизвестный уровень")


def validate_search_funnel(data: dict[str, Any], errors: list[str]) -> None:
    funnel = require_mapping(data, "search_funnel", errors)
    status = funnel.get("status")
    if status not in ALLOWED_FUNNEL_STATUS:
        errors.append("search_funnel.status: допустимы ready, partial или blocked")
    if status in {"partial", "blocked"}:
        require_nonempty_string(funnel, "notes", "search_funnel", errors)
    stages = funnel.get("stages")
    if not isinstance(stages, list):
        errors.append("search_funnel.stages: ожидается массив")
        stages = []
    stage_ids: set[str] = set()
    for index, stage in enumerate(stages):
        label = f"search_funnel.stages[{index}]"
        if not isinstance(stage, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        stage_id = require_nonempty_string(stage, "id", label, errors)
        if stage_id:
            if stage_id in stage_ids:
                errors.append(f"{label}.id: дублируется {stage_id!r}")
            stage_ids.add(stage_id)
        for key in ("label", "source", "metric", "unit"):
            require_nonempty_string(stage, key, label, errors)
        if stage.get("status") not in ALLOWED_STAGE_STATUS:
            errors.append(f"{label}.status: неизвестный статус")
    links = funnel.get("links")
    if not isinstance(links, list):
        errors.append("search_funnel.links: ожидается массив")
        links = []
    for index, link in enumerate(links):
        label = f"search_funnel.links[{index}]"
        if not isinstance(link, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        if link.get("from") not in stage_ids or link.get("to") not in stage_ids:
            errors.append(f"{label}: from/to должны ссылаться на stages")
        require_nonempty_string(link, "formula", label, errors)
        if not isinstance(link.get("validated"), bool):
            errors.append(f"{label}.validated: ожидается boolean")
    forecasts = funnel.get("forecasts")
    if not isinstance(forecasts, list):
        errors.append("search_funnel.forecasts: ожидается массив")
        forecasts = []
    for index, row in enumerate(forecasts):
        label = f"search_funnel.forecasts[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        if row.get("horizon") not in REQUIRED_HORIZONS:
            errors.append(f"{label}.horizon: допустимы 7 или 30")
        if row.get("stage_id") not in stage_ids:
            errors.append(f"{label}.stage_id: неизвестный этап")
        row_status = row.get("status")
        if row_status not in ALLOWED_STAGE_STATUS:
            errors.append(f"{label}.status: неизвестный статус")
        if row_status == "readiness_gap":
            if row.get("value") is not None:
                errors.append(f"{label}.value: для readiness_gap ожидается null")
        elif not finite_nonnegative(row.get("value")):
            errors.append(f"{label}.value: требуется неотрицательное число")


def validate_hierarchies(
    data: dict[str, Any],
    totals: dict[int, dict[str, float]],
    errors: list[str],
) -> None:
    hierarchies = require_list(data, "hierarchical_forecasts", errors)
    if not hierarchies:
        errors.append(
            "hierarchical_forecasts: добавьте полный, частичный или not_available разрез"
        )
    dimensions: set[str] = set()
    for index, hierarchy in enumerate(hierarchies):
        label = f"hierarchical_forecasts[{index}]"
        if not isinstance(hierarchy, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        dimension = require_nonempty_string(hierarchy, "dimension", label, errors)
        if dimension:
            if dimension in dimensions:
                errors.append(f"{label}.dimension: дублируется {dimension!r}")
            dimensions.add(dimension)
        status = hierarchy.get("status")
        if status not in ALLOWED_HIERARCHY_STATUS:
            errors.append(f"{label}.status: неизвестный статус")
        coverage = hierarchy.get("coverage_share")
        if not probability(coverage):
            errors.append(f"{label}.coverage_share: требуется число от 0 до 1")
            coverage = 0.0
        rows = hierarchy.get("rows")
        if not isinstance(rows, list):
            errors.append(f"{label}.rows: ожидается массив")
            rows = []
        if status == "complete" and not close_enough(float(coverage), 1.0, relative=0):
            errors.append(f"{label}.coverage_share: для complete ожидается 1")
        if status == "partial":
            if not (0 < float(coverage) < 1):
                errors.append(f"{label}.coverage_share: для partial ожидается 0 < x < 1")
            require_nonempty_string(hierarchy, "notes", label, errors)
        if status == "not_available":
            if float(coverage) != 0 or rows:
                errors.append(f"{label}: для not_available ожидаются coverage=0 и пустые rows")
            require_nonempty_string(hierarchy, "notes", label, errors)

        sums: dict[tuple[int, str], float] = defaultdict(float)
        seen_rows: set[tuple[str, int, str]] = set()
        for row_index, row in enumerate(rows):
            row_label = f"{label}.rows[{row_index}]"
            if not isinstance(row, dict):
                errors.append(f"{row_label}: ожидается объект")
                continue
            segment = require_nonempty_string(row, "segment", row_label, errors)
            horizon = row.get("horizon")
            scenario = row.get("scenario")
            value = row.get("value")
            if horizon not in REQUIRED_HORIZONS:
                errors.append(f"{row_label}.horizon: допустимы 7 или 30")
                continue
            if scenario not in ALLOWED_SCENARIOS:
                errors.append(f"{row_label}.scenario: неизвестный сценарий")
                continue
            if not finite_nonnegative(value):
                errors.append(f"{row_label}.value: требуется число ≥0")
                continue
            key = (str(segment), int(horizon), str(scenario))
            if key in seen_rows:
                errors.append(f"{row_label}: дублируется segment/horizon/scenario")
            seen_rows.add(key)
            sums[(int(horizon), str(scenario))] += float(value)
        if status == "complete":
            for horizon in REQUIRED_HORIZONS:
                for scenario in ALLOWED_SCENARIOS:
                    declared = totals.get(horizon, {}).get(scenario)
                    calculated = sums.get((horizon, scenario))
                    if declared is None or calculated is None:
                        errors.append(
                            f"{label}: отсутствует полный разрез {horizon}/{scenario}"
                        )
                    elif not close_enough(calculated, declared):
                        errors.append(
                            f"{label}: сумма {horizon}/{scenario} {calculated:g} "
                            f"не сходится с общим итогом {declared:g}"
                        )


def validate_learning_loop(
    data: dict[str, Any], run_id: str | None, errors: list[str]
) -> None:
    run = data.get("forecast_run", {})
    previous_run_id = run.get("previous_run_id") if isinstance(run, dict) else None
    loop = require_mapping(data, "learning_loop", errors)
    status = loop.get("status")
    if status not in ALLOWED_LEARNING_STATUS:
        errors.append("learning_loop.status: допустимы first_run, pending или active")
    evaluations = loop.get("evaluations")
    outcomes = loop.get("action_outcomes")
    if not isinstance(evaluations, list):
        errors.append("learning_loop.evaluations: ожидается массив")
        evaluations = []
    if not isinstance(outcomes, list):
        errors.append("learning_loop.action_outcomes: ожидается массив")
        outcomes = []
    if status == "first_run":
        if previous_run_id is not None or evaluations:
            errors.append("learning_loop.first_run: previous_run_id и evaluations должны быть пусты")
    if status == "pending":
        if not previous_run_id:
            errors.append("learning_loop.pending: требуется previous_run_id")
    if status == "active":
        if not previous_run_id:
            errors.append("learning_loop.active: требуется previous_run_id")
        if not evaluations:
            errors.append("learning_loop.active: требуется завершённая evaluation")
    for index, evaluation in enumerate(evaluations):
        label = f"learning_loop.evaluations[{index}]"
        if not isinstance(evaluation, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        previous = require_nonempty_string(evaluation, "run_id", label, errors)
        if previous and run_id and previous == run_id:
            errors.append(f"{label}.run_id: должен относиться к прошлому запуску")
        if evaluation.get("horizon") not in REQUIRED_HORIZONS:
            errors.append(f"{label}.horizon: допустимы 7 или 30")
        for key in ("forecast", "actual", "wape"):
            if not finite_nonnegative(evaluation.get(key)):
                errors.append(f"{label}.{key}: требуется число ≥0")
        if not finite_number(evaluation.get("bias")):
            errors.append(f"{label}.bias: требуется конечное число")
    for index, outcome in enumerate(outcomes):
        label = f"learning_loop.action_outcomes[{index}]"
        if not isinstance(outcome, dict):
            errors.append(f"{label}: ожидается объект")
            continue
        for key in ("action_id", "period", "execution_status", "evidence"):
            require_nonempty_string(outcome, key, label, errors)
        if outcome.get("identification_method") not in ALLOWED_IDENTIFICATION:
            errors.append(f"{label}.identification_method: неизвестный статус")
        actual_effect = outcome.get("actual_effect")
        if actual_effect is not None and not finite_number(actual_effect):
            errors.append(f"{label}.actual_effect: ожидается число или null")
        factor = outcome.get("updated_effect_factor")
        if factor is not None and not finite_nonnegative(factor):
            errors.append(f"{label}.updated_effect_factor: ожидается число ≥0 или null")


def validate_document(data: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["Корневое значение должно быть объектом"], warnings
    meta = data.get("meta")
    if (
        isinstance(meta, dict)
        and meta.get("schema_version") is None
        and "forecast_run" not in data
    ):
        return [
            "dashboard-input v1 устарел: пересоберите пакет по data-contract.md "
            "со schema_version=2.0; автоматическая миграция запрещена, потому что "
            "в v1 нет фактического ряда и воспроизводимых backtest-окон"
        ], warnings

    as_of, run_id = validate_meta_and_run(data, errors)
    validate_metric_definition(data, errors)
    required_statuses = validate_sources(data, as_of, errors, warnings)
    actual_by_day = validate_actual_series(data, as_of, errors)
    validate_adjustments(data, actual_by_day, errors)
    validate_events(data, errors)
    training_from, training_to, history_days = validate_regime(
        data, actual_by_day, as_of, errors
    )
    validate_fingerprint(data, len(actual_by_day), errors)
    validate_horizons(data, errors)
    totals = validate_scenario_totals(data, errors)
    validate_uncertainty_totals(data, totals, errors)
    daily_forecast = validate_daily_forecast(data, as_of, totals, errors)
    model_confidence, _, _ = validate_model(
        data,
        training_from,
        training_to,
        history_days,
        required_statuses,
        errors,
    )
    scenario_confidence = validate_scenario_confidence(
        data, model_confidence, errors
    )
    forecast_days = [day for day, _ in daily_forecast]
    action_daily, expert_impact_30, total_impact_30 = validate_actions(
        data, forecast_days, errors
    )
    blocker_daily = validate_blockers(data, forecast_days, errors, warnings)
    validate_scenario_linkage(
        daily_forecast,
        action_daily,
        blocker_daily,
        scenario_confidence,
        expert_impact_30,
        total_impact_30,
        errors,
    )
    for key in ("drivers", "demand_signals"):
        require_list(data, key, errors)
    validate_business_registry(data, errors)
    validate_search_funnel(data, errors)
    validate_hierarchies(data, totals, errors)
    validate_learning_loop(data, run_id, errors)
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Проверить dashboard-input.json для предиктивного дашборда"
    )
    parser.add_argument("input", type=Path, help="Путь к JSON-пакету")
    parser.add_argument(
        "--write-fingerprint",
        action="store_true",
        help="Рассчитать и записать воспроизводимый data_fingerprint перед проверкой",
    )
    args = parser.parse_args()

    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: файл не найден: {args.input}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"ERROR: некорректный JSON: {exc}", file=sys.stderr)
        return 2

    if args.write_fingerprint:
        if not isinstance(data, dict):
            print("ERROR: корневое значение должно быть объектом", file=sys.stderr)
            return 2
        actual_series = data.get("actual_series")
        data["data_fingerprint"] = {
            "algorithm": "sha256",
            "value": calculate_fingerprint(data),
            "series_rows": len(actual_series) if isinstance(actual_series, list) else 0,
        }
        args.input.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"UPDATED: data_fingerprint записан в {args.input}")

    errors, warnings = validate_document(data)
    for item in warnings:
        print(f"WARNING: {item}")
    for item in errors:
        print(f"ERROR: {item}", file=sys.stderr)

    if errors:
        print(
            f"FAIL: ошибок {len(errors)}, предупреждений {len(warnings)}",
            file=sys.stderr,
        )
        return 1
    print(f"OK: ошибок 0, предупреждений {len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
