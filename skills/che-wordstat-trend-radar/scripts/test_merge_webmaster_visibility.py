#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("merge_webmaster_visibility.py")
SPEC = importlib.util.spec_from_file_location("merge_webmaster_visibility", PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class WebmasterTests(unittest.TestCase):
    def test_rising_gap_without_visibility_is_page_opportunity(self):
        report = {"results": [{"id": "cluster", "signal": "growing", "coverage": {"status": "gap"}}]}
        result = MOD.merge(report, [])
        self.assertEqual(result["results"][0]["visibility_action"], "market_rising_no_page")

    def test_good_position_low_ctr_requests_snippet_work(self):
        report = {"results": [{"id": "cluster", "signal": "growing", "coverage": {"status": "covered_content"}}]}
        rows = [{"query": "q", "cluster_id": "cluster", "url": "https://example.test/page", "impressions": 100, "clicks": 1, "position": 5}]
        result = MOD.merge(report, rows)
        self.assertEqual(result["results"][0]["visibility_action"], "improve_ctr")


if __name__ == "__main__":
    unittest.main()
