#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("trend_storage.py")
SPEC = importlib.util.spec_from_file_location("trend_storage", PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class StorageTests(unittest.TestCase):
    def test_persists_observations_with_full_dimension_key(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = MOD.TrendStorage(Path(directory) / "history.sqlite")
            project = {"id": "p", "region_id": 225, "devices": "all", "operator": "all"}
            storage.store_cluster_series(project, [{"id": "c", "canonical_phrase": "фраза", "series": [{"date": "2026-01", "value": 10}]}])
            storage.store_cluster_series(project, [{"id": "c", "canonical_phrase": "другая фраза", "series": [{"date": "2026-01", "value": 12}]}])
            count = storage.connection.execute("SELECT count(*) FROM observations").fetchone()[0]
            storage.close()
            self.assertEqual(count, 2)

    def test_delta_statuses(self):
        previous = {"a": {"signal": "stable", "deseasonalized_slope_pct_month": 0, "current_3m_avg": 100}, "b": {"signal": "declining", "deseasonalized_slope_pct_month": -2, "current_3m_avg": 100}}
        current = [{"id": "a", "signal": "growing", "deseasonalized_slope_pct_month": 3, "current_3m_avg": 110}, {"id": "b", "signal": "stable", "deseasonalized_slope_pct_month": 0, "current_3m_avg": 100}, {"id": "c", "signal": "breakout", "new_demand": True}]
        result = MOD.detect_deltas(previous, current)
        self.assertEqual(result["a"], "new_growth")
        self.assertEqual(result["b"], "recovered")
        self.assertEqual(result["c"], "new_demand")


if __name__ == "__main__":
    unittest.main()
