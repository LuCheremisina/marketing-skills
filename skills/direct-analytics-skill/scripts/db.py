#!/usr/bin/env python3
"""SQLite cache and immutable diagnostic records for direct-analytics-skill.

The cache deliberately stores one payload per source, scope and completed day.
This prevents a range-level Metrika payload from being reused as if it were a
daily fact, and keeps media and business facts separate until reconciliation.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS direct_campaigns (
    project TEXT NOT NULL,
    fetched_date TEXT NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (project, fetched_date)
);

CREATE TABLE IF NOT EXISTS direct_adgroups (
    project TEXT NOT NULL,
    fetched_date TEXT NOT NULL,
    campaign_id INTEGER NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (project, fetched_date, campaign_id)
);

CREATE TABLE IF NOT EXISTS direct_ads (
    project TEXT NOT NULL,
    fetched_date TEXT NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (project, fetched_date)
);

-- Legacy tables are retained so existing project caches remain readable.
CREATE TABLE IF NOT EXISTS direct_stats (
    project TEXT NOT NULL,
    stat_date TEXT NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (project, stat_date)
);
CREATE TABLE IF NOT EXISTS metrika_sessions (
    project TEXT NOT NULL,
    stat_date TEXT NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (project, stat_date)
);
CREATE TABLE IF NOT EXISTS metrika_ecommerce (
    project TEXT NOT NULL,
    stat_date TEXT NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (project, stat_date)
);
CREATE TABLE IF NOT EXISTS matched_results (
    project TEXT NOT NULL,
    stat_date TEXT NOT NULL,
    data TEXT NOT NULL,
    match_summary TEXT,
    PRIMARY KEY (project, stat_date)
);

CREATE TABLE IF NOT EXISTS fact_cache (
    project TEXT NOT NULL,
    source TEXT NOT NULL,
    scope TEXT NOT NULL,
    stat_date TEXT NOT NULL,
    data TEXT NOT NULL,
    status TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (project, source, scope, stat_date)
);

CREATE TABLE IF NOT EXISTS diagnosis_runs (
    run_id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    created_at TEXT NOT NULL,
    record TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS diagnosis_feedback (
    run_id TEXT PRIMARY KEY,
    verdict TEXT NOT NULL CHECK(verdict IN ('confirmed', 'partial', 'refuted')),
    actual_cause TEXT NOT NULL,
    action_outcome TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES diagnosis_runs(run_id)
);

CREATE TABLE IF NOT EXISTS cache_meta (
    project TEXT NOT NULL,
    table_name TEXT NOT NULL,
    stat_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project, table_name, stat_date)
);
"""


LEGACY_DAY_TABLES = {
    "direct_stats",
    "metrika_sessions",
    "metrika_ecommerce",
    "matched_results",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CacheDB:
    def __init__(self, project: str, base_dir: Path | None = None):
        self.project = project
        if base_dir is None:
            base_dir = Path(os.environ.get("DIRECT_ANALYTICS_DATA_DIR", str(Path.home() / ".direct_analytics"))).expanduser()
        project_dir = base_dir / project
        project_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = project_dir / "cache.db"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    @staticmethod
    def completed_dates(date_from: date, date_to: date) -> list[str]:
        """Return each cacheable date; current date is never treated as final."""
        today = date.today()
        values: list[str] = []
        current = date_from
        while current <= date_to:
            if current < today:
                values.append(current.isoformat())
            current += timedelta(days=1)
        return values

    # -- Fact cache ---------------------------------------------------------

    def missing_fact_dates(
        self, source: str, scope: str, date_from: date, date_to: date
    ) -> list[str]:
        wanted = self.completed_dates(date_from, date_to)
        if not wanted:
            return []
        placeholders = ",".join("?" for _ in wanted)
        rows = self.conn.execute(
            "SELECT stat_date, status FROM fact_cache WHERE project=? AND source=? "
            f"AND scope=? AND stat_date IN ({placeholders})",
            [self.project, source, scope, *wanted],
        ).fetchall()
        present = {
            row["stat_date"] for row in rows
            if json.loads(row["status"]).get("complete", False)
        }
        return [value for value in wanted if value not in present]

    def save_fact(
        self,
        source: str,
        scope: str,
        stat_date: str,
        data: object,
        status: dict[str, Any] | None = None,
    ) -> None:
        payload_status = dict(status or {})
        payload_status.setdefault("source", source)
        payload_status.setdefault("scope", scope)
        payload_status.setdefault("stat_date", stat_date)
        payload_status.setdefault("complete", True)
        fetched_at = utc_now()
        self.conn.execute(
            "INSERT OR REPLACE INTO fact_cache "
            "(project, source, scope, stat_date, data, status, fetched_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                self.project,
                source,
                scope,
                stat_date,
                json.dumps(data, ensure_ascii=False),
                json.dumps(payload_status, ensure_ascii=False),
                fetched_at,
            ),
        )
        self.conn.execute(
            "INSERT OR REPLACE INTO cache_meta VALUES (?,?,?,?)",
            (self.project, f"fact:{source}:{scope}", stat_date, fetched_at),
        )
        self.conn.commit()

    def load_facts(
        self, source: str, scope: str, date_from: str, date_to: str
    ) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT stat_date, data FROM fact_cache WHERE project=? AND source=? "
            "AND scope=? AND stat_date BETWEEN ? AND ? ORDER BY stat_date",
            (self.project, source, scope, date_from, date_to),
        ).fetchall()
        records: list[dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row["data"])
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if isinstance(item, dict):
                    item = dict(item)
                    item.setdefault("Date", row["stat_date"])
                records.append(item)
        return records

    def fact_status(
        self, source: str, scope: str, date_from: str, date_to: str
    ) -> dict[str, dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT stat_date, status, fetched_at FROM fact_cache WHERE project=? "
            "AND source=? AND scope=? AND stat_date BETWEEN ? AND ? ORDER BY stat_date",
            (self.project, source, scope, date_from, date_to),
        ).fetchall()
        return {
            row["stat_date"]: {
                **json.loads(row["status"]),
                "fetched_at": row["fetched_at"],
            }
            for row in rows
        }

    def coverage(
        self,
        requirements: list[tuple[str, str]],
        date_from: date,
        date_to: date,
    ) -> dict[str, Any]:
        wanted = self.completed_dates(date_from, date_to)
        sources: dict[str, Any] = {}
        complete = bool(wanted)
        for source, scope in requirements:
            present = self.fact_status(source, scope, wanted[0], wanted[-1]) if wanted else {}
            missing = [day for day in wanted if day not in present or not present[day].get("complete", False)]
            key = f"{source}:{scope}"
            sources[key] = {
                "coverage": len(wanted) - len(missing),
                "expected": len(wanted),
                "missing_dates": missing,
                "failed_dates": {
                    day: present[day].get("error")
                    for day in wanted
                    if day in present and not present[day].get("complete", False) and present[day].get("error")
                },
                "latest_fetched_at": max(
                    (item.get("fetched_at", "") for item in present.values()), default=None
                ),
            }
            complete = complete and not missing
        return {"complete": complete, "sources": sources, "date_from": date_from.isoformat(), "date_to": date_to.isoformat()}

    def invalidate_facts(
        self, date_from: str, date_to: str, source: str | None = None, scope: str | None = None
    ) -> None:
        clauses = ["project=?", "stat_date BETWEEN ? AND ?"]
        values: list[Any] = [self.project, date_from, date_to]
        if source:
            clauses.append("source=?")
            values.append(source)
        if scope:
            clauses.append("scope=?")
            values.append(scope)
        self.conn.execute(f"DELETE FROM fact_cache WHERE {' AND '.join(clauses)}", values)
        self.conn.commit()

    # -- Diagnostic feedback ------------------------------------------------

    def save_diagnosis(self, record: dict[str, Any]) -> str:
        run_id = record.get("run_id") or uuid.uuid4().hex
        stored = dict(record)
        stored["run_id"] = run_id
        self.conn.execute(
            "INSERT OR REPLACE INTO diagnosis_runs VALUES (?,?,?,?)",
            (run_id, self.project, utc_now(), json.dumps(stored, ensure_ascii=False)),
        )
        self.conn.commit()
        return run_id

    def load_diagnosis(self, run_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT record FROM diagnosis_runs WHERE run_id=? AND project=?", (run_id, self.project)
        ).fetchone()
        return json.loads(row["record"]) if row else None

    def save_feedback(
        self, run_id: str, verdict: str, actual_cause: str, action_outcome: str | None = None
    ) -> None:
        if verdict not in {"confirmed", "partial", "refuted"}:
            raise ValueError("verdict must be confirmed, partial, or refuted")
        if not self.load_diagnosis(run_id):
            raise KeyError(f"diagnosis run '{run_id}' was not found")
        self.conn.execute(
            "INSERT OR REPLACE INTO diagnosis_feedback VALUES (?,?,?,?,?)",
            (run_id, verdict, actual_cause, action_outcome, utc_now()),
        )
        self.conn.commit()

    def feedback_records(self, date_from: str | None = None, date_to: str | None = None) -> list[dict[str, Any]]:
        clauses = ["r.project=?"]
        values: list[Any] = [self.project]
        if date_from:
            clauses.append("r.created_at >= ?")
            values.append(date_from)
        if date_to:
            clauses.append("r.created_at <= ?")
            values.append(date_to)
        rows = self.conn.execute(
            "SELECT r.run_id, r.created_at, r.record, f.verdict, f.actual_cause, f.action_outcome, f.created_at AS feedback_created_at "
            "FROM diagnosis_runs r LEFT JOIN diagnosis_feedback f ON f.run_id=r.run_id "
            f"WHERE {' AND '.join(clauses)} ORDER BY r.created_at",
            values,
        ).fetchall()
        result = []
        for row in rows:
            result.append({
                "run_id": row["run_id"], "created_at": row["created_at"],
                "record": json.loads(row["record"]), "verdict": row["verdict"],
                "actual_cause": row["actual_cause"], "action_outcome": row["action_outcome"],
                "feedback_created_at": row["feedback_created_at"],
            })
        return result

    # -- Backwards-compatible legacy cache API ------------------------------

    def missing_stat_dates(self, table: str, date_from: date, date_to: date) -> list[str]:
        if table not in LEGACY_DAY_TABLES:
            raise ValueError(f"Unsupported legacy table: {table}")
        wanted = self.completed_dates(date_from, date_to)
        if not wanted:
            return []
        placeholders = ",".join("?" for _ in wanted)
        rows = self.conn.execute(
            f"SELECT stat_date FROM {table} WHERE project=? AND stat_date IN ({placeholders})",
            [self.project, *wanted],
        ).fetchall()
        present = {row["stat_date"] for row in rows}
        return [day for day in wanted if day not in present]

    def has_structure(self, fetched_date: str) -> bool:
        return bool(self.conn.execute(
            "SELECT 1 FROM direct_campaigns WHERE project=? AND fetched_date=?",
            (self.project, fetched_date),
        ).fetchone())

    def save(self, table: str, stat_date: str, data: object, extra: dict | None = None) -> None:
        if table not in LEGACY_DAY_TABLES | {"direct_campaigns", "direct_ads", "direct_adgroups"}:
            raise ValueError(f"Unsupported legacy table: {table}")
        now = utc_now()
        payload = json.dumps(data, ensure_ascii=False)
        if table == "direct_adgroups":
            campaign_id = int((extra or {}).get("campaign_id", 0))
            self.conn.execute("INSERT OR REPLACE INTO direct_adgroups VALUES (?,?,?,?)", (self.project, stat_date, campaign_id, payload))
        elif table == "matched_results":
            self.conn.execute("INSERT OR REPLACE INTO matched_results VALUES (?,?,?,?)", (self.project, stat_date, payload, json.dumps(extra or {}, ensure_ascii=False)))
        else:
            self.conn.execute(f"INSERT OR REPLACE INTO {table} VALUES (?,?,?)", (self.project, stat_date, payload))
        self.conn.execute("INSERT OR REPLACE INTO cache_meta VALUES (?,?,?,?)", (self.project, table, stat_date, now))
        self.conn.commit()

    def load(self, table: str, date_from: str, date_to: str) -> list[dict[str, Any]]:
        if table not in LEGACY_DAY_TABLES | {"direct_campaigns", "direct_ads"}:
            raise ValueError(f"Unsupported legacy table: {table}")
        date_column = "fetched_date" if table in {"direct_campaigns", "direct_ads"} else "stat_date"
        rows = self.conn.execute(
            f"SELECT {date_column}, data FROM {table} WHERE project=? AND {date_column} BETWEEN ? AND ? ORDER BY {date_column}",
            (self.project, date_from, date_to),
        ).fetchall()
        records: list[dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row["data"])
            records.extend(payload if isinstance(payload, list) else [payload])
        return records

    def load_matched(self, date_from: str, date_to: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT stat_date, data, match_summary FROM matched_results WHERE project=? "
            "AND stat_date BETWEEN ? AND ? ORDER BY stat_date", (self.project, date_from, date_to)
        ).fetchall()
        records: list[dict[str, Any]] = []
        summaries: dict[str, Any] = {}
        for row in rows:
            records.extend(json.loads(row["data"]))
            if row["match_summary"]:
                summaries[row["stat_date"]] = json.loads(row["match_summary"])
        return records, summaries

    def invalidate_all(self, date_from: str, date_to: str) -> None:
        for table in LEGACY_DAY_TABLES | {"direct_campaigns", "direct_ads", "direct_adgroups"}:
            column = "fetched_date" if table in {"direct_campaigns", "direct_ads", "direct_adgroups"} else "stat_date"
            self.conn.execute(f"DELETE FROM {table} WHERE project=? AND {column} BETWEEN ? AND ?", (self.project, date_from, date_to))
        self.invalidate_facts(date_from, date_to)
        self.conn.execute("DELETE FROM cache_meta WHERE project=? AND stat_date BETWEEN ? AND ?", (self.project, date_from, date_to))
        self.conn.commit()

    def cache_info(self) -> dict[str, Any]:
        rows = self.conn.execute(
            "SELECT source, scope, COUNT(*) cnt, MIN(stat_date) min_d, MAX(stat_date) max_d "
            "FROM fact_cache WHERE project=? GROUP BY source, scope ORDER BY source, scope", (self.project,)
        ).fetchall()
        facts = {
            f"{row['source']}:{row['scope']}": {"days": row["cnt"], "from": row["min_d"], "to": row["max_d"]}
            for row in rows
        }
        return {"project": self.project, "db_path": str(self.db_path), "facts": facts}

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "CacheDB":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
