#!/usr/bin/env python3
"""Explainable monthly trend detector for Wordstat-style absolute volumes."""

import argparse
import json
import math
import statistics
from datetime import datetime
from pathlib import Path

try:
    from trend_storage import TrendStorage, detect_deltas
except ImportError:  # Allows importing this module directly in tests.
    TrendStorage = None
    detect_deltas = None


def pct(new, old):
    return None if old <= 0 else (new / old - 1.0) * 100.0


def avg(xs):
    return statistics.fmean(xs) if xs else 0.0


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def theil_sen_slope(xs):
    """Robust median slope; intentionally has no third-party dependency."""
    slopes = [(xs[j] - xs[i]) / (j - i) for i in range(len(xs)) for j in range(i + 1, len(xs))]
    return statistics.median(slopes) if slopes else 0.0


def month_distance(left, right):
    return (right.year - left.year) * 12 + right.month - left.month


def quality_flags(points, run_at=None):
    flags = []
    seen, parsed = set(), []
    for point in points:
        raw_date = point.get("date")
        try:
            date = datetime.strptime(raw_date, "%Y-%m")
        except (TypeError, ValueError):
            flags.append("invalid_month")
            continue
        if raw_date in seen:
            flags.append("duplicate_month")
        seen.add(raw_date)
        try:
            value = float(point.get("value"))
        except (TypeError, ValueError):
            flags.append("invalid_value")
            value = 0.0
        if value < 0:
            flags.append("negative_value")
        if point.get("complete") is False:
            flags.append("incomplete_month")
        parsed.append(date)
    parsed = sorted(set(parsed))
    if any(month_distance(left, right) > 1 for left, right in zip(parsed, parsed[1:])):
        flags.append("non_contiguous_history")
    if run_at and parsed:
        marker = datetime.strptime(run_at[:7], "%Y-%m")
        if parsed[-1].year == marker.year and parsed[-1].month == marker.month:
            flags.append("possibly_incomplete_current_month")
    return sorted(set(flags))


def median_seasonal_adjust(dates, values):
    # Normalize within each calendar year first, otherwise a monotonic trend is
    # incorrectly treated as a January-to-December seasonal pattern.
    yearly = {}
    for date, value in zip(dates, values):
        yearly.setdefault(date.year, []).append(value)
    year_medians = {year: statistics.median(items) or 1.0 for year, items in yearly.items()}
    buckets = {month: [] for month in range(1, 13)}
    for date, value in zip(dates, values):
        buckets[date.month].append(value / year_medians[date.year])
    indexes = {month: clamp(statistics.median(items) if items else 1.0, 0.25, 4.0) for month, items in buckets.items()}
    return [value / indexes[date.month] for date, value in zip(dates, values)], indexes, "median_seasonal"


def seasonal_adjust(dates, values, eligible):
    if not eligible:
        return values[:], {month: 1.0 for month in range(1, 13)}, "none"
    # A strictly monotonic multi-year series has no observable recurring
    # seasonal cycle in this data. Do not manufacture one from its trend.
    if all(right >= left for left, right in zip(values, values[1:])) or all(right <= left for left, right in zip(values, values[1:])):
        return values[:], {month: 1.0 for month in range(1, 13)}, "none_monotonic"
    try:
        from statsmodels.tsa.seasonal import STL
        result = STL(values, period=12, robust=True).fit()
        adjusted = [max(0.0, value - seasonal) for value, seasonal in zip(values, result.seasonal)]
        if all(math.isfinite(value) for value in adjusted):
            return adjusted, None, "robust_stl"
    except (ImportError, ValueError, TypeError):
        pass
    return median_seasonal_adjust(dates, values)


def confidence(values, current, min_volume, agreement, history_months, flags):
    history = clamp((history_months - 6) / 18, 0, 1)
    volume = clamp(math.log1p(current) / math.log1p(max(min_volume * 10, 10)), 0, 1)
    mean = avg(values) or 1.0
    volatility = statistics.pstdev(values) / mean if len(values) > 1 else 1.0
    stability = 1.0 - clamp(volatility / 1.5, 0, 1)
    score = 0.30 * history + 0.25 * volume + 0.30 * agreement + 0.15 * stability
    if flags:
        score -= min(0.25, 0.05 * len(flags))
    return clamp(score, 0, 1)


def direction_agreement(period, yoy, slope):
    values = [value for value in (period, yoy, slope) if value is not None]
    signs = [1 if value > 3 else -1 if value < -3 else 0 for value in values]
    return max(signs.count(1), signs.count(-1), signs.count(0)) / len(signs) if signs else 0.0


def fmt(value):
    return "н/д" if value is None else f"{value:+.1f}%"


def analyze(cluster, min_volume, run_at=None):
    points = sorted(cluster.get("series", []), key=lambda point: point.get("date", ""))
    flags = quality_flags(points, run_at)
    valid = []
    for point in points:
        try:
            date = datetime.strptime(point["date"], "%Y-%m")
            value = float(point["value"])
            if value >= 0:
                valid.append((date, value))
        except (KeyError, TypeError, ValueError):
            pass
    dates, values = zip(*valid) if valid else ([], [])
    dates, values = list(dates), list(values)
    active_values = [value for value in values if value > 0]
    active_months = len(active_values)
    base = {"id": cluster.get("id"), "label": cluster.get("label"), "months": len(values), "active_months": active_months, "data_quality_flags": flags}
    if len(values) < 6:
        return {**base, "signal": "insufficient_data", "confidence": 0.0, "reason": "Нужно минимум 6 полных месяцев", "forecast_3m_direction": "неопределённо"}

    cur, prev = avg(values[-3:]), avg(values[-6:-3])
    period = pct(cur, prev)
    yoy = pct(cur, avg(values[-15:-12])) if len(values) >= 15 else None
    first_active = next((index for index, value in enumerate(values) if value > 0), len(values))
    observed_after_launch = values[first_active:]
    active_history = sum(value > 0 for value in observed_after_launch)
    seasonal_eligible = active_history >= 24 and "non_contiguous_history" not in flags
    adjusted, indexes, decomposition = seasonal_adjust(dates, values, seasonal_eligible)
    recent = adjusted[-6:]
    slope = (theil_sen_slope(recent) / (avg(recent) or 1.0)) * 100
    moves = [pct(adjusted[index], adjusted[index - 1]) for index in range(max(1, len(adjusted) - 3), len(adjusted))]
    up, down = sum(value is not None and value > 3 for value in moves), sum(value is not None and value < -3 for value in moves)
    agreement = direction_agreement(period, yoy, slope)
    conf = confidence(adjusted, cur, min_volume, agreement, active_history, flags)
    if active_history < 18:
        conf = min(conf, 0.55)
    new_demand = prev <= max(1.0, min_volume * 0.05) and cur >= min_volume
    seasonal = seasonal_eligible and period is not None and abs(period) >= 20 and yoy is not None and abs(yoy) < 15 and abs(slope) < 2
    structural_decline = bool(yoy is not None and yoy <= -20 and slope <= -1 and len(values) >= 27 and cur < avg(values[-27:-24]))

    signal = "stable"
    if conf < 0.45 or cur < min_volume:
        signal = "watch"
    elif seasonal:
        signal = "seasonal_rise" if period > 0 else "seasonal_fall"
    elif new_demand and conf >= 0.45:
        signal = "breakout"
    elif period is not None and period > 5000 and conf >= 0.55:
        signal = "breakout"
    elif active_history < 18 and period is not None and period >= 50 and cur >= min_volume:
        signal = "emerging"
    elif active_history < 18:
        signal = "watch"
    elif conf >= 0.60:
        positive = sum([period is not None and period >= 10, yoy is not None and yoy >= 20, slope >= 1, up >= 2])
        negative = sum([period is not None and period <= -10, yoy is not None and yoy <= -20, slope <= -1, down >= 2])
        if period is not None and period >= 30 and yoy is not None and yoy >= 100:
            signal = "rapid_growth"
        elif structural_decline:
            signal = "structural_decline"
        elif positive >= 2 and yoy is not None and yoy >= 20:
            signal = "growing"
        elif negative >= 2 and yoy is not None and yoy <= -20 and (period is None or period <= 3) and slope <= 0:
            signal = "declining"
        elif max(positive, negative) >= 2:
            signal = "watch"

    strength = clamp(max(abs(period or 0), abs(yoy or 0), abs(slope * 6)) / 100, 0, 1)
    relevance = clamp(float(cluster.get("business_relevance", 0.5)), 0, 1)
    coverage = cluster.get("coverage", {})
    coverage_status = coverage.get("status", "gap")
    coverage_weight = {"gap": 1.0, "partial": 0.8, "covered_content": 0.45, "covered_product": 0.55, "irrelevant": 0.0}.get(coverage_status, 0.5)
    if signal in ("declining", "structural_decline") and coverage_status in ("covered_product", "covered_content", "partial"):
        coverage_weight = 1.0
    volume_weight = clamp(math.log1p(cur) / math.log1p(max(min_volume * 100, 100)), 0, 1)
    opportunity = round(100 * strength * relevance * coverage_weight * conf * volume_weight)
    direction = "неопределённо" if conf < 0.55 else "вверх" if slope >= 1 else "вниз" if slope <= -1 else "без выраженного изменения"

    return {
        **base, "signal": signal, "current_3m_avg": round(cur, 2), "period_change_pct": None if period is None else round(period, 2),
        "yoy_change_pct": None if yoy is None else round(yoy, 2), "deseasonalized_slope_pct_month": round(slope, 2),
        "slope_method": "theil_sen", "decomposition_method": decomposition, "persistence_up": up, "persistence_down": down,
        "new_demand": new_demand, "structural_decline": structural_decline, "confidence": round(conf, 2),
        "opportunity_score": opportunity, "forecast_3m_direction": direction, "coverage": coverage,
        "seasonal_indexes": {str(key): round(value, 3) for key, value in indexes.items()} if indexes and seasonal_eligible else None,
    }


def markdown(project, results):
    labels = {"breakout": "Прорывной рост", "emerging": "Новый рост", "rapid_growth": "Быстрый рост", "growing": "Рост", "declining": "Падение", "structural_decline": "Структурное падение", "seasonal_rise": "Сезонный рост", "seasonal_fall": "Сезонное падение", "stable": "Стабильно", "watch": "Наблюдать", "insufficient_data": "Недостаточно данных"}
    lines = [f"# Радар спроса: {project.get('name', 'Проект')}", "", "| Кластер | Сигнал | Спрос 3м | 3м/3м | Год к году | Наклон/мес | Уверенность | Балл |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for result in sorted(results, key=lambda item: item.get("opportunity_score", 0), reverse=True):
        lines.append(f"| {result.get('label')} | {labels.get(result['signal'], result['signal'])} | {result.get('current_3m_avg', 'н/д')} | {fmt(result.get('period_change_pct'))} | {fmt(result.get('yoy_change_pct'))} | {fmt(result.get('deseasonalized_slope_pct_month'))} | {result.get('confidence', 0):.0%} | {result.get('opportunity_score', 0)} |")
    return "\n".join(lines + ["", "> Это сигналы поискового спроса, а не точный прогноз продаж."]) + "\n"


def persist(project, clusters, results, db_path, run_at):
    storage = TrendStorage(db_path)
    run_id = storage.start_run(project, run_at)
    storage.store_cluster_series(project, clusters)
    previous = storage.previous_classifications(project.get("id"), run_id)
    deltas = detect_deltas(previous, results)
    for result in results:
        result["delta_status"] = deltas.get(result.get("id"), "unchanged")
    storage.store_classifications(run_id, results)
    storage.close()
    return run_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--json", dest="json_out")
    parser.add_argument("--markdown", dest="md_out")
    parser.add_argument("--history-db", help="SQLite history database; optional")
    parser.add_argument("--run-at", help="ISO timestamp for a reproducible run")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    project, clusters = data.get("project", {}), data.get("clusters", [])
    run_at = args.run_at or data.get("run_at")
    results = [analyze(cluster, float(project.get("min_volume", 30)), run_at) for cluster in clusters]
    output = {"project": project, "results": results}
    if args.history_db:
        output["run_id"] = persist(project, clusters, results, args.history_db, run_at)
    encoded = json.dumps(output, ensure_ascii=False, indent=2)
    if args.json_out:
        Path(args.json_out).write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)
    if args.md_out:
        Path(args.md_out).write_text(markdown(project, results), encoding="utf-8")


if __name__ == "__main__":
    main()
