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
    collector = SessionCollector(tmp_path)
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
    collector = SessionCollector(tmp_path)
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
    collector = SessionCollector(tmp_path)
    entries = await collector.collect()
    assert len(entries) == 0


def test_calc_cost():
    cost = calc_cost("gpt-5.4", 1_000_000, 1_000_000, 500_000)
    # uncached = 1M - 0.5M = 0.5M
    expected = (
        500_000 / 1_000_000 * 2.50
        + 1_000_000 / 1_000_000 * 15.00
        + 500_000 / 1_000_000 * 0.25
    )
    assert cost == expected


def test_calc_cost_unknown_model():
    cost = calc_cost("unknown-model", 1000, 1000, 0)
    assert cost == 0.0
