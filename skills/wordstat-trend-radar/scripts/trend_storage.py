"""SQLite persistence and classification deltas for the Wordstat trend radar."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, run_at TEXT NOT NULL, project_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS observations (
  project_id TEXT NOT NULL, phrase TEXT NOT NULL, cluster_id TEXT NOT NULL, region_id TEXT NOT NULL,
  device TEXT NOT NULL, operator TEXT NOT NULL, month TEXT NOT NULL, value REAL NOT NULL,
  PRIMARY KEY (project_id, phrase, cluster_id, region_id, device, operator, month)
);
CREATE TABLE IF NOT EXISTS classifications (
  run_id TEXT NOT NULL, cluster_id TEXT NOT NULL, signal TEXT NOT NULL, metrics_json TEXT NOT NULL,
  PRIMARY KEY (run_id, cluster_id), FOREIGN KEY(run_id) REFERENCES runs(run_id)
);
CREATE INDEX IF NOT EXISTS classifications_project_idx ON classifications(cluster_id, run_id);
"""


class TrendStorage:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.connection.executescript(SCHEMA)

    def close(self):
        self.connection.commit()
        self.connection.close()

    def start_run(self, project, run_at=None):
        run_id = str(uuid.uuid4())
        timestamp = run_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        self.connection.execute("INSERT INTO runs VALUES (?, ?, ?, ?)", (run_id, project.get("id", "unknown"), timestamp, json.dumps(project, ensure_ascii=False)))
        return run_id

    def store_cluster_series(self, project, clusters):
        region = str(project.get("region_id", "all"))
        device, operator = str(project.get("devices", "all")), str(project.get("operator", "all"))
        for cluster in clusters:
            cluster_id = cluster.get("id", "unknown")
            phrase = cluster.get("canonical_phrase") or cluster.get("representative_phrase") or cluster_id
            for point in cluster.get("series", []):
                if point.get("date") and point.get("value") is not None:
                    self.connection.execute("INSERT OR REPLACE INTO observations VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (project.get("id", "unknown"), phrase, cluster_id, region, device, operator, point["date"], float(point["value"])))

    def store_classifications(self, run_id, results):
        for result in results:
            self.connection.execute("INSERT OR REPLACE INTO classifications VALUES (?, ?, ?, ?)", (run_id, result.get("id", "unknown"), result.get("signal", "watch"), json.dumps(result, ensure_ascii=False)))
        self.connection.commit()

    def previous_classifications(self, project_id, current_run_id):
        row = self.connection.execute("SELECT run_id FROM runs WHERE project_id = ? AND run_id != ? ORDER BY run_at DESC LIMIT 1", (project_id, current_run_id)).fetchone()
        if not row:
            return {}
        return {cluster_id: json.loads(metrics) for cluster_id, metrics in self.connection.execute("SELECT cluster_id, metrics_json FROM classifications WHERE run_id = ?", (row[0],))}


def detect_deltas(previous, current):
    positive = {"breakout", "emerging", "rapid_growth", "growing"}
    negative = {"declining", "structural_decline"}
    deltas = {}
    for item in current:
        old, new = previous.get(item.get("id")), item.get("signal")
        if old is None:
            deltas[item.get("id")] = "new_demand" if item.get("new_demand") else "new_growth" if new in positive else "new_decline" if new in negative else "new_cluster"
            continue
        old_signal = old.get("signal")
        old_slope, new_slope = old.get("deseasonalized_slope_pct_month", 0) or 0, item.get("deseasonalized_slope_pct_month", 0) or 0
        if old_signal not in positive and new in positive:
            deltas[item.get("id")] = "new_growth"
        elif old_signal not in negative and new in negative:
            deltas[item.get("id")] = "new_decline"
        elif old_signal in negative and new == "stable":
            deltas[item.get("id")] = "recovered"
        elif old.get("current_3m_avg", 0) >= item.get("current_3m_avg", 0) * 3 and item.get("current_3m_avg", 0) > 0:
            deltas[item.get("id")] = "lost_materiality"
        elif new_slope >= old_slope + 2:
            deltas[item.get("id")] = "accelerating"
        elif new_slope <= old_slope - 2:
            deltas[item.get("id")] = "decelerating"
        else:
            deltas[item.get("id")] = "unchanged"
    return deltas
