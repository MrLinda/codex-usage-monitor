from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger("codex_usage_monitor")


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS token_usage_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_time TEXT NOT NULL,
    session_id TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cached_input_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd REAL,
    raw_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_token_usage_event_time
ON token_usage_logs(event_time);

CREATE TABLE IF NOT EXISTS usage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usage_events_event_at
ON usage_events(event_at);

CREATE TABLE IF NOT EXISTS quota_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    plan_type TEXT NOT NULL,
    email TEXT NOT NULL DEFAULT '',
    five_hour_used_pct REAL,
    five_hour_remaining_pct REAL,
    five_hour_reset_at TEXT,
    five_hour_window_seconds INTEGER,
    weekly_used_pct REAL,
    weekly_remaining_pct REAL,
    weekly_reset_at TEXT,
    weekly_window_seconds INTEGER,
    has_credits INTEGER NOT NULL DEFAULT 0,
    credits_balance TEXT NOT NULL DEFAULT '0',
    raw_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_quota_samples_captured_at
ON quota_samples(captured_at);
"""


def run_migrations(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()

    _add_column_if_missing(conn, "quota_samples", "email", "TEXT NOT NULL DEFAULT ''")
    _ensure_token_usage_unique_index(conn)
    # idx_token_usage_model 单列索引现在意义不大（被复合唯一索引覆盖大多数 GROUP BY 场景）
    _drop_index_if_exists(conn, "idx_token_usage_model")


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, col_def: str) -> None:
    cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
        conn.commit()


def _drop_index_if_exists(conn: sqlite3.Connection, index_name: str) -> None:
    conn.execute(f"DROP INDEX IF EXISTS {index_name}")
    conn.commit()


def _ensure_token_usage_unique_index(conn: sqlite3.Connection) -> None:
    """token_usage_logs 上建 (event_time, session_id, model) 唯一索引。

    历史上若有重复数据先去重再建索引，否则旧库无法升级。
    """
    indexes = [row[1] for row in conn.execute("PRAGMA index_list(token_usage_logs)").fetchall()]
    if "uniq_token_usage" in indexes:
        return

    # 去重：每组保留最小 id，删掉余下行
    deleted = conn.execute(
        """DELETE FROM token_usage_logs
           WHERE id NOT IN (
               SELECT MIN(id) FROM token_usage_logs
               GROUP BY event_time, session_id, model
           )"""
    ).rowcount
    if deleted:
        logger.info("Migration: removed %d duplicate token_usage_logs rows before adding UNIQUE index", deleted)

    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uniq_token_usage "
        "ON token_usage_logs(event_time, session_id, model)"
    )
    conn.commit()
