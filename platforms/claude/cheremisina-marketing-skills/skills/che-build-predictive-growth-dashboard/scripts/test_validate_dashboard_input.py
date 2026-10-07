#!/usr/bin/env python3
"""Regression tests for validate_dashboard_input.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from validate_dashboard_input import calculate_fingerprint, validate_document


AS_OF = date(2026, 7, 22)


def iso(day: date) -> str:
    return day.isoformat()


def candidate(
    model_id: str,
    method: str,
    complexity: str,
    wape_7: float,
    wape_30: float,
) -> dict:
    return {
        "id": model_id,
        "method": method,
        "complexity": complexity,
        "parameters": {"lag": 7},
        "eligible": True,
        "metrics": [
            {
                "horizon": 7,
                "wape": wape_7,
                "mae": wape_7,
                "mase": wape_7 / 10,
                "bias": -wape_7,
            },
            {
                "horizon": 30,
                "wape": wape_30,
                "mae": wape_30,
                "mase": wape_30 / 12,
                "bias": -wape_30,
            },
        ],
    }


def folds(model_id: str, errors_by_horizon: dict[int, float]) -> list[dict]:
    rows: list[dict] = []
    for horizon in (7, 30):
        for fold_number, offset in enumerate((120, 80, 40), start=1):
            cutoff = AS_OF - timedelta(days=offset)
            observations = []
            for day_number in range(1, horizon + 1):
                observation = {
                    "date": iso(cutoff + timedelta(days=day_number)),
                    "actual": 100,
                    "forecast": 100 - errors_by_horizon[horizon],
                }
                if model_id == "selected":
                    observation["p10"] = 80
                    observation["p90"] = 105
                observations.append(observation)
            rows.append(
                {
                    "fold_id": f"{model_id}-{horizon}-{fold_number}",
                    "model_id": model_id,
                    "cutoff": iso(cutoff),
                    "horizon": horizon,
                    "observations": observations,
                }
            )
    return rows


def make_valid_package() -> dict:
    history_start = AS_OF - timedelta(days=179)
    actual_series = [
        {
            "date": iso(history_start + timedelta(days=index)),
            "actual": 100,
            "adjusted": 100,
            "adjustment_ids": [],
        }
        for index in range(180)
    ]
    forecast_days = [AS_OF + timedelta(days=index) for index in range(1, 31)]
    daily_forecast = [
        {
            "date": iso(day),
            "p10": 90,
            "p50": 100,
            "p90": 110,
            "pessimistic": 99,
            "base": 100,
            "optimistic": 101,
        }
        for day in forecast_days
    ]
    scenario_totals = []
    for horizon, values in (
        (7, {"pessimistic": 693, "base": 700, "optimistic": 707}),
        (30, {"pessimistic": 2970, "base": 3000, "optimistic": 3030}),
    ):
        for scenario, value in values.items():
            scenario_totals.append(
                {"horizon": horizon, "scenario": scenario, "value": value}
            )

    package = {
        "meta": {
            "schema_version": "2.0",
            "project": "Тестовый проект",
            "domain": "example.ru",
            "as_of": iso(AS_OF),
            "target_metric": "organic_visits",
            "target_unit": "visits",
            "timezone": "Asia/Novosibirsk",
            "status": "complete",
        },
        "forecast_run": {
            "run_id": "run-2026-07-22",
            "generated_at": datetime(
                2026, 7, 23, 9, 0, tzinfo=timezone(timedelta(hours=7))
            ).isoformat(),
            "previous_run_id": None,
        },
        "metric_definition": {
            "name": "Органические визиты",
            "formula": "Сумма визитов из поисковых систем",
            "grain": "day",
            "source_of_truth": "yandex_metrika",
            "inclusions": ["Яндекс", "Google"],
            "exclusions": ["боты"],
            "aggregation": "sum",
        },
        "sources": [
            {
                "name": "yandex_metrika",
                "role": "actual_traffic",
                "status": "ok",
                "required_for_target": True,
                "freshness_date": iso(AS_OF),
                "coverage_from": iso(history_start),
                "coverage_to": iso(AS_OF),
                "grain": "day",
                "units": "visits",
                "notes": "",
            }
        ],
        "actual_series": actual_series,
        "adjustments_log": [],
        "events_calendar": [],
        "regime": {
            "training_from": iso(history_start),
            "training_to": iso(AS_OF),
            "detection_method": "PELT + проверка событий",
            "change_points": [],
            "excluded_periods": [],
            "rationale": "Сопоставимый режим измерения",
        },
        "data_fingerprint": {},
        "horizons": [7, 30],
        "scenario_totals": scenario_totals,
        "uncertainty_totals": [
            {"horizon": 7, "p10": 630, "p50": 700, "p90": 770},
            {"horizon": 30, "p10": 2700, "p50": 3000, "p90": 3300},
        ],
        "daily_forecast": daily_forecast,
        "model": {
            "selected_model_id": "selected",
            "baseline_model_id": "baseline",
            "training_from": iso(history_start),
            "training_to": iso(AS_OF),
            "minimum_lift_pct": 5,
            "selection_reason": "Устойчивая победа на обоих горизонтах",
            "candidate_models": [
                candidate("baseline", "seasonal_naive", "baseline", 10, 12),
                candidate("selected", "weekday_trend", "simple", 8, 9),
            ],
            "backtest_folds": folds("baseline", {7: 10, 30: 12})
            + folds("selected", {7: 8, 30: 9}),
            "backtest_summary": [
                {
                    "horizon": 7,
                    "wape": 8,
                    "mae": 8,
                    "mase": 0.8,
                    "bias": -8,
                    "wape_std": 0,
                    "baseline_wape": 10,
                    "lift_vs_baseline_pct": 20,
                    "interval_coverage_pct": 100,
                    "folds": 3,
                },
                {
                    "horizon": 30,
                    "wape": 9,
                    "mae": 9,
                    "mase": 0.75,
                    "bias": -9,
                    "wape_std": 0,
                    "baseline_wape": 12,
                    "lift_vs_baseline_pct": 25,
                    "interval_coverage_pct": 100,
                    "folds": 3,
                },
            ],
            "uncertainty_method": "conformal on rolling-origin residuals",
            "confidence": "high",
            "notes": "",
        },
        "scenario_confidence": {
            "base": "high",
            "pessimistic": "medium",
            "optimistic": "medium",
        },
        "drivers": [],
        "demand_signals": [],
        "blockers": [
            {
                "id": "risk-ctr",
                "severity": "medium",
                "metric": "organic_visits",
                "evidence": "Историческая волатильность CTR",
                "resolution": "Защитить ведущие сниппеты",
                "probability": 0.5,
                "expected_loss_by_horizon": {"7": 7, "30": 30},
                "daily_loss": [
                    {"date": iso(day), "expected_loss": 1} for day in forecast_days
                ],
            }
        ],
        "actions": [
            {
                "id": "action-snippets",
                "priority": "P1",
                "lever": "CTR",
                "metric": "organic_visits",
                "baseline": 100,
                "target": 101,
                "start_date": iso(forecast_days[0]),
                "lag_days": 0,
                "ramp_curve": "step",
                "completion_probability": 0.5,
                "outcome_probability": 1.0,
                "impact_cap": 60,
                "impact_unit": "visits",
                "expected_impact_by_horizon": {"7": 7, "30": 30},
                "impact_range_by_horizon": {
                    "7": {"low": 4, "high": 10},
                    "30": {"low": 20, "high": 40},
                },
                "daily_impact": [
                    {"date": iso(day), "expected_impact": 1} for day in forecast_days
                ],
                "evidence_level": "project_historical_analogue",
                "evidence_reference": "experiment-2026-05",
                "interaction_group": "snippets",
                "overlap_discount": 1.0,
                "cost": {"amount": 0, "currency": "RUB"},
                "resource": "SEO-редактор",
                "dependency": "Переобход Яндекса",
                "done_when": "Title и description опубликованы",
            }
        ],
        "business_registry": [
            {
                "product": "Аудит маркетинга",
                "audience": "Собственники бизнеса",
                "customer_job": "Понять, где теряются деньги",
                "intent_type": "commercial",
                "cluster_id": "audit-marketing",
                "url": "https://example.ru/audit",
                "cta": "Оставить заявку",
                "conversion_event": "audit_lead",
                "lead_quality_rule": "Компания с действующим маркетингом",
                "business_goal": "Квалифицированный лид",
                "deal_lag_days": 14,
                "visit_value_level": "high",
            }
        ],
        "search_funnel": {
            "status": "partial",
            "notes": "CRM не сверена",
            "stages": [
                {
                    "id": "visits",
                    "label": "Органические визиты",
                    "source": "yandex_metrika",
                    "metric": "organic_visits",
                    "unit": "visits",
                    "status": "ready",
                },
                {
                    "id": "leads",
                    "label": "Квалифицированные лиды",
                    "source": "crm",
                    "metric": "qualified_leads",
                    "unit": "leads",
                    "status": "readiness_gap",
                },
            ],
            "links": [
                {
                    "from": "visits",
                    "to": "leads",
                    "formula": "leads / visits",
                    "validated": False,
                }
            ],
            "forecasts": [
                {"horizon": 7, "stage_id": "visits", "value": 700, "status": "ready"},
                {"horizon": 30, "stage_id": "visits", "value": 3000, "status": "ready"},
                {
                    "horizon": 7,
                    "stage_id": "leads",
                    "value": None,
                    "status": "readiness_gap",
                },
                {
                    "horizon": 30,
                    "stage_id": "leads",
                    "value": None,
                    "status": "readiness_gap",
                },
            ],
        },
        "hierarchical_forecasts": [
            {
                "dimension": "intent_type",
                "status": "complete",
                "coverage_share": 1.0,
                "rows": [
                    {
                        "segment": "all",
                        "horizon": row["horizon"],
                        "scenario": row["scenario"],
                        "value": row["value"],
                    }
                    for row in scenario_totals
                ],
                "notes": "",
            }
        ],
        "learning_loop": {
            "status": "first_run",
            "evaluations": [],
            "action_outcomes": [],
        },
    }
    package["data_fingerprint"] = {
        "algorithm": "sha256",
        "value": calculate_fingerprint(package),
        "series_rows": len(actual_series),
    }
    return package


class DashboardInputValidationTests(unittest.TestCase):
    def test_valid_v2_package(self) -> None:
        errors, warnings = validate_document(make_valid_package())
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    def test_missing_actual_series_is_blocked(self) -> None:
        package = make_valid_package()
        package.pop("actual_series")
        errors, _ = validate_document(package)
        self.assertTrue(any("actual_series" in item for item in errors))

    def test_v1_package_gets_explicit_migration_error(self) -> None:
        errors, _ = validate_document(
            {
                "meta": {
                    "project": "Legacy",
                    "domain": "example.ru",
                    "as_of": iso(AS_OF),
                },
                "model": {"backtest_metric": "WAPE"},
            }
        )
        self.assertEqual(1, len(errors))
        self.assertIn("v1 устарел", errors[0])

    def test_high_confidence_rejects_weak_30_day_backtest(self) -> None:
        package = make_valid_package()
        package["model"]["backtest_summary"][1]["wape"] = 21
        errors, _ = validate_document(package)
        self.assertTrue(any("confidence=high" in item for item in errors))

    def test_backtest_metrics_must_match_fold_observations(self) -> None:
        package = make_valid_package()
        package["model"]["candidate_models"][1]["metrics"][0]["wape"] = 1
        errors, _ = validate_document(package)
        self.assertTrue(any("не сходится с observations" in item for item in errors))

    def test_high_confidence_requires_interval_coverage(self) -> None:
        package = make_valid_package()
        package["model"]["backtest_summary"][0]["interval_coverage_pct"] = 60
        errors, _ = validate_document(package)
        self.assertTrue(any("покрытие P10/P90" in item for item in errors))

    def test_daily_optimistic_must_follow_action_timing(self) -> None:
        package = make_valid_package()
        package["daily_forecast"][0]["optimistic"] = 100
        errors, _ = validate_document(package)
        self.assertTrue(any("daily_impact" in item for item in errors))

    def test_expert_assumption_forces_low_optimistic_confidence(self) -> None:
        package = make_valid_package()
        package["actions"][0]["evidence_level"] = "expert_assumption"
        errors, _ = validate_document(package)
        self.assertTrue(
            any("scenario_confidence.optimistic" in item for item in errors)
        )

    def test_fingerprint_mismatch_is_blocked(self) -> None:
        package = make_valid_package()
        package["actual_series"][0]["actual"] = 101
        errors, _ = validate_document(package)
        self.assertTrue(any("data_fingerprint.value" in item for item in errors))

    def test_complete_hierarchy_must_reconcile(self) -> None:
        package = make_valid_package()
        package["hierarchical_forecasts"][0]["rows"][0]["value"] = 1
        errors, _ = validate_document(package)
        self.assertTrue(any("не сходится с общим итогом" in item for item in errors))

    def test_cli_writes_fingerprint_and_validates(self) -> None:
        package = make_valid_package()
        package["data_fingerprint"]["value"] = "stale"
        validator = Path(__file__).with_name("validate_dashboard_input.py")
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "dashboard-input.json"
            input_path.write_text(
                json.dumps(package, ensure_ascii=False), encoding="utf-8"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(validator),
                    str(input_path),
                    "--write-fingerprint",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            updated = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(
                calculate_fingerprint(updated),
                updated["data_fingerprint"]["value"],
            )


if __name__ == "__main__":
    unittest.main()
