from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from app.models import TokenUsage
from app.storage.migrations import run_migrations
from app.storage.repository import Repository


@pytest.fixture
def repo():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    return Repository(conn)


def test_insert_and_retrieve(repo):
    now = datetime.now(timezone.utc)
    usage = TokenUsage(
        event_time=now,
        session_id="session-1",
        model="gpt-4o",
        input_tokens=100,
        output_tokens=200,
        cached_input_tokens=50,
        reasoning_tokens=0,
        estimated_cost_usd=0.0015,
    )
    insert_id = repo.insert_token_usage(usage)
    assert insert_id is not None

    rows = repo.get_token_usage(limit=100)
    assert len(rows) == 1
    assert rows[0]["model"] == "gpt-4o"
    assert rows[0]["input_tokens"] == 100
    assert rows[0]["estimated_cost_usd"] == 0.0015


def test_summary(repo):
    now = datetime.now(timezone.utc)
    for i in range(3):
        repo.insert_token_usage(TokenUsage(
            event_time=now,
            session_id="s1",
            model="gpt-4o",
            input_tokens=100,
            output_tokens=200,
            cached_input_tokens=0,
            reasoning_tokens=0,
            estimated_cost_usd=0.001,
        ))

    summary = repo.get_summary()
    assert summary["total_entries"] == 3
    assert summary["total_tokens"] == 900
    assert summary["model_count"] == 1
    assert summary["session_count"] == 1


def test_model_breakdown(repo):
    now = datetime.now(timezone.utc)
    repo.insert_token_usage(TokenUsage(event_time=now, session_id="s1", model="gpt-4o", input_tokens=100, output_tokens=200, cached_input_tokens=0, reasoning_tokens=0, estimated_cost_usd=0.001))
    repo.insert_token_usage(TokenUsage(event_time=now, session_id="s2", model="o3", input_tokens=500, output_tokens=1000, cached_input_tokens=0, reasoning_tokens=0, estimated_cost_usd=0.02))

    models = repo.get_model_breakdown()
    assert len(models) == 2
    assert models[0]["model"] == "o3"  # higher cost first
    assert models[1]["model"] == "gpt-4o"


def test_insert_event(repo):
    now = datetime.now(timezone.utc)
    event_id = repo.insert_event(now, "test_event", "test message")
    assert event_id is not None

    events = repo.get_events()
    assert len(events) == 1
    assert events[0]["event_type"] == "test_event"


def test_settings(repo):
    repo.set_setting("key1", "value1")
    assert repo.get_setting("key1") == "value1"
    assert repo.get_setting("nonexistent") is None
