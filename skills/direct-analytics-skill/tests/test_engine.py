from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

from analyze import aggregate, total_row
from collect import DIRECT_SCOPE_SPECS, _metrika_filter, _partition_by_date, fetch_campaigns, reconcile_campaign_day
from dashboard import validate_report_spec
from db import CacheDB
from diagnose import build_diagnosis
from monitor import build_monitor_record
from shadow_gate import evaluate_shadow


def status(source: str, scope: str) -> dict:
    return {"source": source, "scope": scope, "complete": True}


def campaign(day: str, cost: float, clicks: int = 10, impressions: int = 100) -> dict:
    return {
        "Date": day, "CampaignId": "1", "CampaignName": "Alpha", "CampaignStatus": "ON",
        "Cost": cost, "Clicks": clicks, "Impressions": impressions,
    }


def reconciled(day: str, cost: float, revenue: float = 0, transactions: float = 0) -> dict:
    item = campaign(day, cost)
    item.update({
        "MetrikaRevenue": revenue, "MetrikaTransactions": transactions,
        "attribution_level": "exact", "match_confidence": 1.0,
    })
    return item


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = CacheDB("test", Path(self.tmp.name))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_fact_cache_requires_every_completed_day_and_retries_incomplete(self):
        self.db.save_fact("direct", "campaign", "2020-01-01", [], {"complete": True})
        self.db.save_fact("direct", "campaign", "2020-01-02", [], {"complete": False, "error": "timeout"})
        missing = self.db.missing_fact_dates("direct", "campaign", date(2020, 1, 1), date(2020, 1, 3))
        self.assertEqual(missing, ["2020-01-02", "2020-01-03"])
        coverage = self.db.coverage([("direct", "campaign")], date(2020, 1, 1), date(2020, 1, 3))
        self.assertFalse(coverage["complete"])
        self.assertEqual(coverage["sources"]["direct:campaign"]["missing_dates"], ["2020-01-02", "2020-01-03"])
        self.assertEqual(coverage["sources"]["direct:campaign"]["failed_dates"], {"2020-01-02": "timeout"})

    def test_only_compatible_scopes_are_defined(self):
        self.assertNotIn("Criterion", DIRECT_SCOPE_SPECS["campaign"][1])
        self.assertIn("Criterion", DIRECT_SCOPE_SPECS["keyword"][1])
        self.assertIn("AdId", DIRECT_SCOPE_SPECS["ad"][1])

    def test_campaigns_get_paginates_with_limited_by(self):
        pages = [
            {"result": {"Campaigns": [{"Id": 1}], "LimitedBy": 1}},
            {"result": {"Campaigns": [{"Id": 2}]}},
        ]
        with patch("collect.direct_request", side_effect=pages) as request:
            self.assertEqual(fetch_campaigns("token", "login"), [{"Id": 1}, {"Id": 2}])
        self.assertEqual(request.call_args_list[0].args[1]["params"]["Page"], {"Limit": 10000, "Offset": 0})
        self.assertEqual(request.call_args_list[1].args[1]["params"]["Page"], {"Limit": 10000, "Offset": 1})

    def test_metrika_filter_and_daily_partition_preserve_source_and_day(self):
        self.assertEqual(_metrika_filter({"UTM_SOURCE": "yandex", "UTM_MEDIUM": "cpc"}), "ym:s:UTMSource=='yandex' AND ym:s:UTMMedium=='cpc'")
        partitioned = _partition_by_date(
            [{"ym:s:date": "2020-01-01", "value": 1}, {"ym:s:date": "2020-01-02", "value": 2}],
            ["2020-01-01", "2020-01-02"],
            "ym:s:date",
        )
        self.assertEqual([row["value"] for row in partitioned["2020-01-02"]], [2])

    def test_reconciliation_does_not_allocate_unattributed_revenue(self):
        records, summary = reconcile_campaign_day(
            [campaign("2020-01-01", 100)],
            [
                {"ym:s:UTMCampaign": "1", "ym:s:ecommerceRevenue": 500, "ym:s:ecommercePurchases": 2},
                {"ym:s:UTMCampaign": "unknown", "ym:s:ecommerceRevenue": 300, "ym:s:ecommercePurchases": 1},
            ],
            {"UTM_CAMPAIGN_MAPPING": "campaign_id"},
        )
        self.assertEqual(records[0]["MetrikaRevenue"], 500)
        self.assertEqual(records[0]["attribution_level"], "exact")
        self.assertEqual(summary["unattributed_metrika_revenue"], 300)
        self.assertEqual(summary["allocation"], "none")
        self.assertNotIn("L3", str(records))

    def test_legacy_name_match_is_explicitly_estimated(self):
        records, summary = reconcile_campaign_day(
            [campaign("2020-01-01", 100)],
            [{"ym:s:UTMCampaign": "Alpha", "ym:s:ecommerceRevenue": 500, "ym:s:ecommercePurchases": 2}],
            {"UTM_CAMPAIGN_MAPPING": "campaign_id", "ALLOW_LEGACY_CAMPAIGN_NAME_MATCH": True},
        )
        self.assertEqual(records[0]["attribution_level"], "estimated")
        self.assertEqual(summary["estimated_campaigns"], 1)

    def test_cross_source_roas_uses_only_matched_direct_cost(self):
        first = reconciled("2020-01-01", 100, 500, 2)
        second = campaign("2020-01-01", 100)
        second.update({"MetrikaRevenue": None, "MetrikaTransactions": None, "attribution_level": "unpaired_direct"})
        total = total_row([first, second])
        self.assertEqual(total["matched_direct_cost"], 100)
        self.assertEqual(total["CrossSourceROAS"], 500.0)
        self.assertEqual(total["attribution_coverage"], 0.5)

    def test_diagnosis_is_saved_and_feedback_requires_human_verdict(self):
        config = {"REPORT_TIMEZONE": "Europe/Moscow", "ATTRIBUTION_MODE": "parallel"}
        for day, cost, revenue in (("2020-01-07", 100, 1000), ("2020-01-08", 200, 700)):
            self.db.save_fact("direct", "campaign", day, [campaign(day, cost)], status("direct", "campaign"))
            self.db.save_fact("metrika", "sessions", day, [{"Date": day, "ym:s:visits": 10, "ym:s:goal1reaches": 2}], status("metrika", "sessions"))
            self.db.save_fact("metrika", "ecommerce", day, [], status("metrika", "ecommerce"))
            self.db.save_fact("reconciliation", "campaign", day, [reconciled(day, cost, revenue, 2)], status("reconciliation", "campaign"))
        record = build_diagnosis(self.db, "test", config, "MetrikaRevenue", date(2020, 1, 8), date(2020, 1, 8), "prev_period")
        run_id = self.db.save_diagnosis(record)
        self.db.save_feedback(run_id, "partial", "Checkout conversion mix changed", "No campaign change made")
        stored = self.db.feedback_records()
        self.assertEqual(stored[0]["verdict"], "partial")
        self.assertTrue(record["read_only"])
        self.assertTrue(record["hypotheses"])

    def test_monitor_requires_four_comparable_baseline_days_and_materiality(self):
        config = {"MONITOR_METRICS": ["Cost"], "GUARDRAILS": {"Cost": {"min_abs_delta": 20}}, "REPORT_TIMEZONE": "Europe/Moscow"}
        for day, cost in (("2020-01-01", 100), ("2020-01-08", 101), ("2020-01-15", 99), ("2020-01-22", 100), ("2020-01-29", 200)):
            self.db.save_fact("reconciliation", "campaign", day, [reconciled(day, cost, 0, 0)], status("reconciliation", "campaign"))
            self.db.save_fact("direct", "campaign", day, [campaign(day, cost)], status("direct", "campaign"))
            self.db.save_fact("metrika", "sessions", day, [], status("metrika", "sessions"))
            self.db.save_fact("metrika", "ecommerce", day, [], status("metrika", "ecommerce"))
        record = build_monitor_record(self.db, "test", config, date(2020, 1, 29))
        self.assertEqual(record["baseline_status"], "ready")
        self.assertEqual(record["metrics"][0]["severity"], "high")

    def test_monitor_suppresses_alert_when_a_baseline_day_is_incomplete(self):
        config = {"MONITOR_METRICS": ["Cost"], "GUARDRAILS": {"Cost": {"min_abs_delta": 20}}, "REPORT_TIMEZONE": "Europe/Moscow"}
        for day, cost in (("2020-01-01", 100), ("2020-01-08", 101), ("2020-01-15", 99), ("2020-01-22", 100), ("2020-01-29", 200)):
            self.db.save_fact("reconciliation", "campaign", day, [reconciled(day, cost, 0, 0)], status("reconciliation", "campaign"))
            self.db.save_fact("direct", "campaign", day, [campaign(day, cost)], status("direct", "campaign"))
            self.db.save_fact("metrika", "sessions", day, [], status("metrika", "sessions"))
            self.db.save_fact("metrika", "ecommerce", day, [], status("metrika", "ecommerce"))
        self.db.save_fact("metrika", "sessions", "2020-01-08", [], {"source": "metrika", "scope": "sessions", "complete": False})
        record = build_monitor_record(self.db, "test", config, date(2020, 1, 29))
        self.assertEqual(record["baseline_status"], "baseline_insufficient")
        self.assertEqual(record["metrics"][0]["severity"], "suppressed")

    def test_report_spec_is_constrained(self):
        valid = validate_report_spec({"dimension": "campaign", "metrics": ["Cost", "MetrikaRevenue"], "period": "7d", "chart": "bar"})
        self.assertEqual(valid["chart"], "bar")
        with self.assertRaises(ValueError):
            validate_report_spec({"dimension": "campaign", "metrics": ["SQL"], "period": "7d"})

    def test_shadow_gate_requires_ten_complete_evidence_backed_verdicts(self):
        for index in range(10):
            record = {
                "data_status": {"complete": True}, "trigger": {"priority": "high" if index < 2 else "normal"},
                "funnel": [{"metric": "Cost"}], "confirmed_causes": [{"evidence": "Direct status"}] if index == 0 else [],
                "likely_drivers": [{"delta": -10}], "hypotheses": [{"statement": "Verify landing"}],
            }
            run_id = self.db.save_diagnosis(record)
            self.db.save_feedback(run_id, "confirmed", "Analyst verdict")
        report = evaluate_shadow(self.db.feedback_records())
        self.assertEqual(report["gate"], "passed")
        self.assertEqual(report["metrics"]["confirmed_cause_rate"], 1.0)
        self.assertEqual(report["metrics"]["high_priority_precision"], 1.0)

    def test_documented_interfaces_exist(self):
        documentation = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for command in ("collect.py --project", "diagnose.py --project", "monitor.py --project", "dashboard.py --project", "shadow_gate.py --project"):
            self.assertIn(command, documentation)
        self.assertIn("keyword", documentation)
        self.assertIn("read-only", documentation)


if __name__ == "__main__":
    unittest.main()
