from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from app.models import TokenUsage, QuotaSample


class Repository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert_token_usage(self, usage: TokenUsage) -> int:
        cur = self.conn.execute(
            """INSERT INTO token_usage_logs
               (event_time, session_id, model, input_tokens, output_tokens,
                cached_input_tokens, reasoning_tokens, estimated_cost_usd, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                usage.event_time.isoformat(),
                usage.session_id,
                usage.model,
                usage.input_tokens,
                usage.output_tokens,
                usage.cached_input_tokens,
                usage.reasoning_tokens,
                usage.estimated_cost_usd,
                usage.raw_json,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_token_usage(
        self, from_dt: datetime | None = None, to_dt: datetime | None = None, limit: int = 10000
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM token_usage_logs"
        params: list[str] = []
        conditions = []
        if from_dt:
            conditions.append("event_time >= ?")
            params.append(from_dt.isoformat())
        if to_dt:
            conditions.append("event_time <= ?")
            params.append(to_dt.isoformat())
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY event_time ASC"
        if limit:
            query += f" LIMIT {limit}"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_summary(self) -> dict[str, Any]:
        row = self.conn.execute(
            """SELECT
                COUNT(*) as total_entries,
                COALESCE(SUM(input_tokens + output_tokens), 0) as total_tokens,
                COALESCE(SUM(input_tokens), 0) as total_input,
                COALESCE(SUM(cached_input_tokens), 0) as total_cached,
                COALESCE(SUM(output_tokens), 0) as total_output,
                COALESCE(SUM(estimated_cost_usd), 0) as total_cost,
                COUNT(DISTINCT model) as model_count,
                COUNT(DISTINCT session_id) as session_count,
                MAX(event_time) as last_event
               FROM token_usage_logs"""
        ).fetchone()
        return dict(row)

    def get_model_breakdown(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """SELECT
                model,
                COUNT(*) as entries,
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(cached_input_tokens), 0) as cached_input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                COALESCE(SUM(reasoning_tokens), 0) as reasoning_tokens,
                COALESCE(SUM(estimated_cost_usd), 0) as total_cost
               FROM token_usage_logs
               GROUP BY model
               ORDER BY total_cost DESC"""
        ).fetchall()
        return [dict(r) for r in rows]

    def insert_event(self, event_at: datetime, event_type: str, message: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO usage_events (event_at, event_type, message) VALUES (?, ?, ?)",
            (event_at.isoformat(), event_type, message),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_events(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM usage_events ORDER BY event_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_rolling_usage(self, hours: float) -> dict[str, Any]:
        from datetime import datetime, timezone, timedelta
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        row = self.conn.execute(
            """SELECT
                COALESCE(SUM(input_tokens + output_tokens), 0) as total_tokens,
                COALESCE(SUM(input_tokens), 0) as total_input,
                COALESCE(SUM(cached_input_tokens), 0) as total_cached,
                COALESCE(SUM(output_tokens), 0) as total_output,
                COALESCE(SUM(estimated_cost_usd), 0) as total_cost,
                COUNT(*) as entries
               FROM token_usage_logs
               WHERE event_time >= ?""",
            (since,),
        ).fetchone()
        return dict(row)

    def get_windowed_usage(self, from_dt: datetime, to_dt: datetime) -> dict[str, Any]:
        row = self.conn.execute(
            """SELECT
                COALESCE(SUM(input_tokens + output_tokens), 0) as total_tokens,
                COALESCE(SUM(input_tokens), 0) as total_input,
                COALESCE(SUM(cached_input_tokens), 0) as total_cached,
                COALESCE(SUM(output_tokens), 0) as total_output,
                COALESCE(SUM(estimated_cost_usd), 0) as total_cost,
                COUNT(*) as entries
               FROM token_usage_logs
               WHERE event_time >= ? AND event_time <= ?""",
            (from_dt.isoformat(), to_dt.isoformat()),
        ).fetchone()
        return dict(row)

    def get_setting(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )
        self.conn.commit()

    def insert_quota_sample(self, sample: QuotaSample) -> int:
        cur = self.conn.execute(
            """INSERT INTO quota_samples
               (captured_at, plan_type, email,
                five_hour_used_pct, five_hour_remaining_pct, five_hour_reset_at, five_hour_window_seconds,
                weekly_used_pct, weekly_remaining_pct, weekly_reset_at, weekly_window_seconds,
                has_credits, credits_balance, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sample.captured_at.isoformat(),
                sample.plan_type,
                sample.email,
                sample.five_hour_used_pct,
                sample.five_hour_remaining_pct,
                sample.five_hour_reset_at.isoformat() if sample.five_hour_reset_at else None,
                sample.five_hour_window_seconds,
                sample.weekly_used_pct,
                sample.weekly_remaining_pct,
                sample.weekly_reset_at.isoformat() if sample.weekly_reset_at else None,
                sample.weekly_window_seconds,
                1 if sample.has_credits else 0,
                sample.credits_balance,
                json.dumps(sample.raw_json, ensure_ascii=False) if sample.raw_json else None,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_latest_quota(self) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM quota_samples ORDER BY captured_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def get_quota_history(self, limit: int = 500, from_dt: datetime | None = None, to_dt: datetime | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM quota_samples"
        params: list[str] = []
        conditions = []
        if from_dt:
            conditions.append("captured_at >= ?")
            params.append(from_dt.isoformat())
        if to_dt:
            conditions.append("captured_at <= ?")
            params.append(to_dt.isoformat())
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query = f"SELECT * FROM ({query} ORDER BY captured_at DESC LIMIT ?) ORDER BY captured_at ASC"
        params.append(limit)
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_cumulative_cost(self, from_dt: datetime, to_dt: datetime) -> float:
        row = self.conn.execute(
            """SELECT COALESCE(SUM(estimated_cost_usd), 0) as total_cost
               FROM token_usage_logs
               WHERE event_time >= ? AND event_time <= ?""",
            (from_dt.isoformat(), to_dt.isoformat()),
        ).fetchone()
        return float(row["total_cost"])
