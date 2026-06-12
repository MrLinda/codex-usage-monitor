from __future__ import annotations

import sqlite3


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

CREATE INDEX IF NOT EXISTS idx_token_usage_model
ON token_usage_logs(model);

CREATE TABLE IF NOT EXISTS usage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usage_events_event_at
ON usage_events(event_at);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quota_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    plan_type TEXT NOT NULL,
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
