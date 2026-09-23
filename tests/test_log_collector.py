from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.collectors.log_collector import SessionCollector, calc_cost


@pytest.fixture
def session_jsonl(tmp_path: Path) -> Path:
    f = tmp_path / "rollout-2026-06-12T10-00-00-session-id.jsonl"
    meta = {
        "timestamp": "2026-06-12T10:00:00Z",
        "type": "session_meta",
        "payload": {"id": "019eb4b9-163f-76c2-831a-fb7c8d250875"},
    }
    events = [
        {
            "timestamp": "2026-06-12T10:00:00Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "model": "gpt-5.4",
                    "last_token_usage": {
                        "input_tokens": 100,
                        "output_tokens": 200,
                        "cached_input_tokens": 50,
                        "reasoning_output_tokens": 0,
                    },
                },
            },
        },
        {
            "timestamp": "2026-06-12T10:05:00Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "model": "gpt-5.5",
                    "last_token_usage": {
                        "input_tokens": 500,
                        "output_tokens": 1000,
                        "cached_input_tokens": 0,
                        "reasoning_output_tokens": 50,
                    },
                },
            },
        },
        {
            "timestamp": "2026-06-12T10:10:00Z",
            "type": "event_msg",
            "payload": {"type": "other_event"},
        },
    ]
    f.write_text("\n".join(json.dumps(e) for e in [meta] + events), encoding="utf-8")
    return f


@pytest.mark.asyncio
async def test_collector_parses_token_usage(tmp_path: Path, session_jsonl: Path):
    collector = SessionCollector([tmp_path], wsl_discovery=False)
    entries = await collector.collect()
    assert len(entries) == 2

    e1 = entries[0]
    assert e1.session_id == "019eb4b9-163f-76c2-831a-fb7c8d250875"
    assert e1.model == "gpt-5.4"
    assert e1.input_tokens == 100
    assert e1.output_tokens == 200
    assert e1.cached_input_tokens == 50
    assert e1.reasoning_tokens == 0
    assert e1.estimated_cost_usd == calc_cost("gpt-5.4", 100, 200, 50)

    e2 = entries[1]
    assert e2.model == "gpt-5.5"
    assert e2.input_tokens == 500
    assert e2.output_tokens == 1000
    assert e2.reasoning_tokens == 50


@pytest.mark.asyncio
async def test_collector_empty_dir(tmp_path: Path):
    collector = SessionCollector([tmp_path], wsl_discovery=False)
    entries = await collector.collect()
    assert entries == []


@pytest.mark.asyncio
async def test_collector_no_valid_events(tmp_path: Path):
    f = tmp_path / "empty-session.jsonl"
    meta = {"timestamp": "2026-06-12T10:00:00Z", "type": "session_meta", "payload": {"id": "s1"}}
    f.write_text(
        json.dumps(meta) + "\n"
        '{"timestamp":"2026-06-12T10:01:00Z","type":"event_msg","payload":{"type":"user_message"}}\n'
        '{"timestamp":"2026-06-12T10:02:00Z","type":"event_msg","payload":{"type":"task_started"}}',
        encoding="utf-8",
    )
    collector = SessionCollector([tmp_path], wsl_discovery=False)
    entries = await collector.collect()
    assert len(entries) == 0


@pytest.mark.asyncio
async def test_collector_multiple_dirs(tmp_path: Path, session_jsonl: Path):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()

    f1 = dir_a / "session-a.jsonl"
    f1.write_text(
        json.dumps({"timestamp": "2026-06-12T10:00:00Z", "type": "session_meta", "payload": {"id": "sess-a"}}) + "\n"
        '{"timestamp":"2026-06-12T10:01:00Z","type":"event_msg","payload":{"type":"token_count","info":{"model":"gpt-5.4","last_token_usage":{"input_tokens":10,"output_tokens":20,"cached_input_tokens":0,"reasoning_output_tokens":0}}}}',
        encoding="utf-8",
    )
    f2 = dir_b / "session-b.jsonl"
    f2.write_text(
        json.dumps({"timestamp": "2026-06-12T10:00:00Z", "type": "session_meta", "payload": {"id": "sess-b"}}) + "\n"
        '{"timestamp":"2026-06-12T10:02:00Z","type":"event_msg","payload":{"type":"token_count","info":{"model":"gpt-5.5","last_token_usage":{"input_tokens":30,"output_tokens":40,"cached_input_tokens":5,"reasoning_output_tokens":1}}}}',
        encoding="utf-8",
    )

    collector = SessionCollector([dir_a, dir_b], wsl_discovery=False)
    entries = await collector.collect()
    assert len(entries) == 2

    ids = {e.session_id for e in entries}
    assert ids == {"sess-a", "sess-b"}


@pytest.mark.asyncio
async def test_collector_wsl_discovery_graceful(tmp_path: Path, session_jsonl: Path):
    """wsl_discovery=True 时不应报错，且至少能采到显式配置的目录。"""
    collector = SessionCollector([tmp_path], wsl_discovery=True)
    entries = await collector.collect()
    # 至少包含测试 fixture 的 2 条记录（WSL 如果有会话会额外追加）
    assert len(entries) >= 2
    # 确认测试 fixture 的记录存在
    models = {e.model for e in entries}
    assert "gpt-5.4" in models


def test_calc_cost():
    cost = calc_cost("gpt-5.4", 1_000_000, 1_000_000, 500_000)
    # uncached = 1M - 0.5M = 0.5M
    expected = (
        500_000 / 1_000_000 * 2.50
        + 1_000_000 / 1_000_000 * 15.00
        + 500_000 / 1_000_000 * 0.25
    )
    assert cost == expected


def test_calc_cost_gpt6_family():
    # gpt-6-sol: input 2.00, cached 0.20, output 10.00
    assert calc_cost("gpt-6-sol", 1_000_000, 1_000_000, 500_000) == (
        500_000 / 1_000_000 * 2.00 + 1_000_000 / 1_000_000 * 10.00 + 500_000 / 1_000_000 * 0.20
    )
    # gpt-6-luna: input 0.10, cached 0.01, output 0.50
    assert calc_cost("gpt-6-luna", 1_000_000, 1_000_000, 0) == pytest.approx(0.60)


def test_has_pricing():
    from app.collectors.log_collector import has_pricing

    assert has_pricing("gpt-6-sol")
    assert not has_pricing("totally-unknown")
    # alias 解析后也算数
    assert has_pricing("codex-auto-review", {"codex-auto-review": "gpt-5.4"})
    assert not has_pricing("codex-auto-review")


def test_cost_factor():
    from app.collectors.log_collector import cost_factor

    assert cost_factor("gpt-5.4") == 1.0
    assert cost_factor("gpt-5.4", None, {}) == 1.0
    assert cost_factor("gpt-5.4", None, {"gpt-5.4": 0.5}) == 0.5
    # 没列出的型号 → 1.0
    assert cost_factor("gpt-6-sol", None, {"gpt-5.4": 0.5}) == 1.0
    # 按 alias 解析后的型号查也行
    assert cost_factor("codex-auto-review", {"codex-auto-review": "gpt-5.4"}, {"gpt-5.4": 0.2}) == 0.2
    # 非法值回退 1.0
    assert cost_factor("gpt-5.4", None, {"gpt-5.4": "oops"}) == 1.0


@pytest.mark.asyncio
async def test_collector_applies_cost_multiplier(tmp_path: Path, session_jsonl: Path):
    """采集写入的费用 = 定价 × 按型号折扣系数。"""
    collector = SessionCollector(
        [tmp_path], wsl_discovery=False, model_multipliers={"gpt-5.4": 0.5}
    )
    entries = await collector.collect()
    assert entries[0].estimated_cost_usd == pytest.approx(calc_cost("gpt-5.4", 100, 200, 50) * 0.5)
    # 未列出的型号不打折
    assert entries[1].estimated_cost_usd == pytest.approx(calc_cost("gpt-5.5", 500, 1000, 0))


def test_calc_cost_unknown_model():
    cost = calc_cost("unknown-model", 1000, 1000, 0)
    assert cost == 0.0
