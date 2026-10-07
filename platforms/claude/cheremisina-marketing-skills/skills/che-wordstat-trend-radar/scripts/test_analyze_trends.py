#!/usr/bin/env python3
import importlib.util
import unittest
from datetime import date
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("analyze_trends.py")
SPEC = importlib.util.spec_from_file_location("analyze_trends", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def months(count, value_fn, start_year=2023, start_month=1):
    result = []
    year, month = start_year, start_month
    for i in range(count):
        result.append({"date": date(year, month, 1).strftime("%Y-%m"), "value": round(value_fn(i, month), 2)})
        month += 1
        if month == 13:
            year += 1
            month = 1
    return result


def cluster(series):
    return {
        "id": "test",
        "label": "Тест",
        "business_relevance": 1,
        "coverage": {"status": "gap"},
        "series": series,
    }


class TrendTests(unittest.TestCase):
    def test_sustained_growth(self):
        result = MOD.analyze(cluster(months(36, lambda i, m: 100 * (1.05 ** i))), 30)
        self.assertEqual(result["signal"], "growing")

    def test_sustained_decline(self):
        result = MOD.analyze(cluster(months(36, lambda i, m: 600 * (0.96 ** i))), 30)
        self.assertIn(result["signal"], ("declining", "structural_decline"))

    def test_repeating_season_is_not_structural_growth(self):
        factors = {1: 1.4, 2: 1.2, 3: 1.0, 4: 0.9, 5: 0.8, 6: 0.7, 7: 0.7, 8: 0.8, 9: 0.9, 10: 1.1, 11: 1.5, 12: 2.0}
        result = MOD.analyze(cluster(months(36, lambda i, m: 100 * factors[m])), 30)
        self.assertIn(result["signal"], ("seasonal_rise", "seasonal_fall"))
        self.assertNotIn(result["signal"], ("growing", "declining"))

    def test_material_new_demand_is_breakout(self):
        series = months(30, lambda i, m: 0 if i < 27 else 120)
        result = MOD.analyze(cluster(series), 30)
        self.assertEqual(result["signal"], "breakout")
        self.assertTrue(result["new_demand"])

    def test_short_history_can_be_marked_as_emerging_but_not_high_confidence(self):
        result = MOD.analyze(cluster(months(8, lambda i, m: 10 + i * 10)), 30)
        self.assertEqual(result["signal"], "emerging")
        self.assertLessEqual(result["confidence"], 0.55)

    def test_zero_padded_history_does_not_fake_seasonal_history(self):
        result = MOD.analyze(cluster(months(36, lambda i, m: 0 if i < 24 else 50 + (i - 24) * 20)), 30)
        self.assertEqual(result["signal"], "watch")
        self.assertEqual(result["active_months"], 12)
        self.assertIsNone(result["seasonal_indexes"])
        self.assertLessEqual(result["confidence"], 0.55)

    def test_rapid_growth_is_distinct_from_regular_growth(self):
        result = MOD.analyze(cluster(months(36, lambda i, m: 20 * (1.12 ** i))), 30)
        self.assertEqual(result["signal"], "rapid_growth")

    def test_structural_decline_requires_same_period_history(self):
        result = MOD.analyze(cluster(months(36, lambda i, m: 1200 * (0.92 ** i))), 30)
        self.assertEqual(result["signal"], "structural_decline")
        self.assertTrue(result["structural_decline"])

    def test_bad_series_is_flagged_without_crashing(self):
        series = months(8, lambda i, m: 100)
        series[2]["value"] = -10
        series.append({"date": series[-1]["date"], "value": 10})
        result = MOD.analyze(cluster(series), 30, "2026-07-01T00:00:00Z")
        self.assertIn("negative_value", result["data_quality_flags"])
        self.assertIn("duplicate_month", result["data_quality_flags"])
        self.assertEqual(result["slope_method"], "theil_sen")

    def test_recent_recovery_is_not_labelled_as_declining(self):
        series = months(36, lambda i, m: 500 - i * 10 if i < 30 else 120 + (i - 30) * 30)
        result = MOD.analyze(cluster(series), 30)
        self.assertNotEqual(result["signal"], "declining")
        self.assertGreater(result["period_change_pct"], 3)


if __name__ == "__main__":
    unittest.main()
