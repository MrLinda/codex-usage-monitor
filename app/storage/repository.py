from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from typing import Any, Iterable

from app.models import TokenUsage, QuotaSample


class Repository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._write_lock = threading.Lock()
        # 全表聚合缓存：key -> (token, 结果)。token = (data_version, 本连接写计数)。
        # - PRAGMA data_version 在“其它连接”提交后变化 → 采集器（poller 连接）写库后，
        #   API 连接下次读到的值就变了，缓存自动失效（生产是读写分离的两条连接）。
        # - data_version 对“同一连接”自己的写入不变，故再叠一个本连接写计数兜底，
        #   保证单连接读写（如测试）也能正确失效。
        self._agg_cache: dict[str, tuple[tuple[int, int], Any]] = {}
        self._local_writes = 0

    def _agg_token(self) -> tuple[int, int]:
        """聚合缓存失效令牌。调用方必须已持有 _write_lock（会访问 self.conn）。"""
        dv = self.conn.execute("PRAGMA data_version").fetchone()[0]
        return (dv, self._local_writes)

    def insert_token_usage_batch(self, usages: Iterable[TokenUsage]) -> int:
        """批量插入并自动去重，返回实际新增行数。

        - INSERT OR IGNORE 配合 (event_time, session_id, model) 唯一索引，
           重复行直接被 SQLite 跳过，避免 N+1 SELECT 去重。
        - 整批一个事务、一次 commit，相比逐条 commit 节省大量 fsync。
        - 通过 _write_lock 序列化写入，避免多线程并发导致 InterfaceError。
        """
        rows = [
            (
                u.event_time.isoformat(),
                u.session_id,
                u.model,
                u.input_tokens,
                u.output_tokens,
                u.cached_input_tokens,
                u.reasoning_tokens,
                u.estimated_cost_usd,
                u.raw_json,
            )
            for u in usages
        ]
        if not rows:
            return 0
        with self._write_lock:
            before = self.conn.total_changes
            with self.conn:
                self.conn.executemany(
                    """INSERT OR IGNORE INTO token_usage_logs
                       (event_time, session_id, model, input_tokens, output_tokens,
                        cached_input_tokens, reasoning_tokens, estimated_cost_usd, raw_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    rows,
                )
            changed = self.conn.total_changes - before
            if changed:
                self._local_writes += 1  # 使本连接的聚合缓存失效
            return changed

    def get_token_usage(
        self, from_dt: datetime | None = None, to_dt: datetime | None = None,
        limit: int = 10000, daily: bool = False,
    ) -> list[dict[str, Any]]:
        params: list[str] = []
        conditions = []
        if from_dt:
            conditions.append("event_time >= ?")
            params.append(from_dt.isoformat())
        if to_dt:
            conditions.append("event_time <= ?")
            params.append(to_dt.isoformat())
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        if daily:
            # event_time 存的是 UTC ISO 串，按天聚合用 localtime 折算到本地日界，
            # 否则 UTC+8 下"一天"是从早上 8 点到次日 8 点
            # 按 date + model 双维度分组，保留模型信息供前端展示
            query = f"""SELECT DATE(event_time, 'localtime') as event_time, '' as session_id, model,
                SUM(input_tokens) as input_tokens, SUM(output_tokens) as output_tokens,
                SUM(cached_input_tokens) as cached_input_tokens, SUM(reasoning_tokens) as reasoning_tokens,
                SUM(estimated_cost_usd) as estimated_cost_usd
                FROM token_usage_logs{where} GROUP BY DATE(event_time, 'localtime'), model ORDER BY event_time ASC"""
        else:
            # 不取 raw_json：调用方（API/CSV 导出）用不到，且它是每行最大的字段
            query = f"""SELECT event_time, session_id, model, input_tokens, output_tokens,
                cached_input_tokens, reasoning_tokens, estimated_cost_usd
                FROM token_usage_logs{where} ORDER BY event_time ASC"""
            if not from_dt and not to_dt and limit:
                query += f" LIMIT {limit}"
        with self._write_lock:
            rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_summary(self) -> dict[str, Any]:
        with self._write_lock:
            token = self._agg_token()
            hit = self._agg_cache.get("summary")
            if hit and hit[0] == token:
                return hit[1]
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
            result = dict(row)
            self._agg_cache["summary"] = (token, result)
        return result

    def get_model_breakdown(self) -> list[dict[str, Any]]:
        with self._write_lock:
            token = self._agg_token()
            hit = self._agg_cache.get("model_breakdown")
            if hit and hit[0] == token:
                return hit[1]
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
            result = [dict(r) for r in rows]
            self._agg_cache["model_breakdown"] = (token, result)
        return result

    def insert_event(self, event_at: datetime, event_type: str, message: str) -> int:
        with self._write_lock:
            cur = self.conn.execute(
                "INSERT INTO usage_events (event_at, event_type, message) VALUES (?, ?, ?)",
                (event_at.isoformat(), event_type, message),
            )
            self.conn.commit()
            return cur.lastrowid

    def get_events(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._write_lock:
            rows = self.conn.execute(
                "SELECT * FROM usage_events ORDER BY event_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_rolling_usage(self, hours: float) -> dict[str, Any]:
        from datetime import datetime, timezone, timedelta
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        with self._write_lock:
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
        with self._write_lock:
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

    def insert_quota_sample(self, sample: QuotaSample) -> int:
        with self._write_lock:
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
        with self._write_lock:
            row = self.conn.execute(
                "SELECT * FROM quota_samples ORDER BY captured_at DESC LIMIT 1"
            ).fetchone()
        return dict(row) if row else None

    def get_quota_history(self, limit: int = 500, from_dt: datetime | None = None, to_dt: datetime | None = None, daily: bool = False) -> list[dict[str, Any]]:
        params: list[str | int] = []
        conditions = []
        if from_dt:
            conditions.append("captured_at >= ?")
            params.append(from_dt.isoformat())
        if to_dt:
            conditions.append("captured_at <= ?")
            params.append(to_dt.isoformat())
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        if daily:
            fh_filter = "five_hour_used_pct > 0 AND five_hour_reset_at IS NOT NULL AND five_hour_window_seconds IS NOT NULL"
            full_where = f"{where} AND {fh_filter}" if where else f" WHERE {fh_filter}"
            # 与 token 按天聚合一致，"每日末条"按本地日界取
            query = f"""SELECT q.* FROM quota_samples q
                INNER JOIN (SELECT DATE(captured_at, 'localtime') AS day, MAX(captured_at) AS max_at
                    FROM quota_samples{full_where} GROUP BY DATE(captured_at, 'localtime')
                ) latest ON q.captured_at = latest.max_at ORDER BY q.captured_at ASC"""
        elif from_dt or to_dt:
            query = f"SELECT * FROM quota_samples{where} ORDER BY captured_at ASC"
        else:
            query = f"SELECT * FROM (SELECT * FROM quota_samples{where} ORDER BY captured_at DESC LIMIT ?) ORDER BY captured_at ASC"
            params.append(limit)
        with self._write_lock:
            rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_cumulative_cost(self, from_dt: datetime, to_dt: datetime) -> float:
        with self._write_lock:
            row = self.conn.execute(
                """SELECT COALESCE(SUM(estimated_cost_usd), 0) as total_cost
                   FROM token_usage_logs
                   WHERE event_time >= ? AND event_time <= ?""",
                (from_dt.isoformat(), to_dt.isoformat()),
            ).fetchone()
        return float(row["total_cost"])
