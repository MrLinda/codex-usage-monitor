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
    count = repo.insert_token_usage_batch([usage])
    assert count == 1

    rows = repo.get_token_usage(limit=100)
    assert len(rows) == 1
    assert rows[0]["model"] == "gpt-4o"
    assert rows[0]["input_tokens"] == 100
    assert rows[0]["estimated_cost_usd"] == 0.0015


def test_summary(repo):
    base = datetime.now(timezone.utc)
    entries = [
        TokenUsage(
            event_time=base.replace(microsecond=i),
            session_id="s1",
            model="gpt-4o",
            input_tokens=100,
            output_tokens=200,
            cached_input_tokens=0,
            reasoning_tokens=0,
            estimated_cost_usd=0.001,
        )
        for i in range(3)
    ]
    count = repo.insert_token_usage_batch(entries)
    assert count == 3

    summary = repo.get_summary()
    assert summary["total_entries"] == 3
    assert summary["total_tokens"] == 900
    assert summary["model_count"] == 1
    assert summary["session_count"] == 1


def test_batch_insert_dedup(repo):
    """批量插入：相同 (event_time, session_id, model) 的行应被唯一索引去重。"""
    base = datetime.now(timezone.utc)
    entries = [
        TokenUsage(event_time=base, session_id="s1", model="gpt-4o",
                   input_tokens=100, output_tokens=200, cached_input_tokens=0,
                   reasoning_tokens=0, estimated_cost_usd=0.001),
        # 与第一条完全相同 → 应被去重
        TokenUsage(event_time=base, session_id="s1", model="gpt-4o",
                   input_tokens=100, output_tokens=200, cached_input_tokens=0,
                   reasoning_tokens=0, estimated_cost_usd=0.001),
        # 不同 session → 保留
        TokenUsage(event_time=base, session_id="s2", model="gpt-4o",
                   input_tokens=50, output_tokens=10, cached_input_tokens=0,
                   reasoning_tokens=0, estimated_cost_usd=0.0005),
    ]
    inserted = repo.insert_token_usage_batch(entries)
    assert inserted == 2
    assert repo.get_summary()["total_entries"] == 2


def test_model_breakdown(repo):
    now = datetime.now(timezone.utc)
    repo.insert_token_usage_batch([
        TokenUsage(event_time=now, session_id="s1", model="gpt-4o", input_tokens=100, output_tokens=200, cached_input_tokens=0, reasoning_tokens=0, estimated_cost_usd=0.001),
        TokenUsage(event_time=now, session_id="s2", model="o3", input_tokens=500, output_tokens=1000, cached_input_tokens=0, reasoning_tokens=0, estimated_cost_usd=0.02),
    ])

    models = repo.get_model_breakdown()
    assert len(models) == 2
    assert models[0]["model"] == "o3"  # higher cost first
    assert models[1]["model"] == "gpt-4o"


def test_get_used_models(repo):
    """历史模型列表：去重、升序；空表返回空。"""
    assert repo.get_used_models() == []

    now = datetime.now(timezone.utc)
    repo.insert_token_usage_batch([
        TokenUsage(event_time=now, session_id="s1", model="gpt-4o", input_tokens=1, output_tokens=1, cached_input_tokens=0, reasoning_tokens=0, estimated_cost_usd=0.001),
        TokenUsage(event_time=now, session_id="s1", model="o3", input_tokens=1, output_tokens=1, cached_input_tokens=0, reasoning_tokens=0, estimated_cost_usd=0.001),
        TokenUsage(event_time=now, session_id="s2", model="gpt-4o", input_tokens=1, output_tokens=1, cached_input_tokens=0, reasoning_tokens=0, estimated_cost_usd=0.001),
    ])
    # 3 行 2 个模型：去重后升序
    assert repo.get_used_models() == ["gpt-4o", "o3"]


def test_reprice_usage(repo):
    """重算：0 费用行补算、历史行随定价/系数缩放、未知型号不动、幂等。"""
    from app.analytics.pricing import pricing_fingerprint, reprice_usage

    now = datetime.now(timezone.utc)
    repo.insert_token_usage_batch([
        # 采集当年还没 gpt-6-sol 定价 → 存了 0
        TokenUsage(event_time=now, session_id="s1", model="gpt-6-sol",
                   input_tokens=1_000_000, output_tokens=1_000_000, cached_input_tokens=500_000,
                   reasoning_tokens=0, estimated_cost_usd=0.0),
        # 至今没定价的型号 → 保持不动
        TokenUsage(event_time=now.replace(microsecond=1), session_id="s2", model="totally-unknown",
                   input_tokens=100, output_tokens=200, cached_input_tokens=0,
                   reasoning_tokens=0, estimated_cost_usd=0.0),
        # 已有费用的行 → 按当前定价表收敛（历史数据也参与重算）
        TokenUsage(event_time=now.replace(microsecond=2), session_id="s3", model="gpt-5.4",
                   input_tokens=100, output_tokens=200, cached_input_tokens=0,
                   reasoning_tokens=0, estimated_cost_usd=0.5),
    ])

    assert reprice_usage(repo, {}) == 2
    rows = {r["model"]: r["estimated_cost_usd"] for r in repo.get_token_usage(limit=100)}
    # uncached 0.5M * 2.00 + output 1M * 10.00 + cached 0.5M * 0.20 = 11.10
    assert rows["gpt-6-sol"] == pytest.approx(11.10)
    assert rows["totally-unknown"] == 0.0
    # input 100 * 2.50/1M + output 200 * 15.00/1M = 0.00325
    assert rows["gpt-5.4"] == pytest.approx(0.00325)
    assert any(e["event_type"] == "pricing_reprice" for e in repo.get_events())

    # 幂等：配置没变，重算不再回写
    assert reprice_usage(repo, {}) == 0

    # 按型号折扣系数：gpt-6-sol 减半，其它型号不变（历史一起缩放）
    assert reprice_usage(repo, {}, {"gpt-6-sol": 0.5}) == 1
    rows = {r["model"]: r["estimated_cost_usd"] for r in repo.get_token_usage(limit=100)}
    assert rows["gpt-6-sol"] == pytest.approx(5.55)
    assert rows["gpt-5.4"] == pytest.approx(0.00325)
    assert rows["totally-unknown"] == 0.0

    # 补上 alias 后，之前没定价的型号也能算出来
    assert reprice_usage(repo, {"totally-unknown": "gpt-6-luna"}, {"gpt-6-sol": 0.5}) == 1
    rows = {r["model"]: r["estimated_cost_usd"] for r in repo.get_token_usage(limit=100)}
    # input 100 * 0.10/1M + output 200 * 0.50/1M = 0.00011
    assert rows["totally-unknown"] == pytest.approx(0.00011)
    assert rows["gpt-6-sol"] == pytest.approx(5.55)

    # 指纹：别名/系数任一变化都会不同，配置相同则稳定
    a = pricing_fingerprint({"m": "gpt-5.4"}, {"gpt-6-sol": 0.5})
    assert a == pricing_fingerprint({"m": "gpt-5.4"}, {"gpt-6-sol": 0.5})
    assert a != pricing_fingerprint({"m": "gpt-5.4"}, {"gpt-6-sol": 0.4})
    assert a != pricing_fingerprint({}, {"gpt-6-sol": 0.5})


def test_insert_event(repo):
    now = datetime.now(timezone.utc)
    event_id = repo.insert_event(now, "test_event", "test message")
    assert event_id is not None

    events = repo.get_events()
    assert len(events) == 1
    assert events[0]["event_type"] == "test_event"
