from __future__ import annotations

from datetime import datetime, timezone

from app.collectors.quota_collector import _parse_window


def test_parse_window_none():
    assert _parse_window(None) == (None, None, None, None)


def test_parse_window_basic():
    used, remaining, reset_at, window_sec = _parse_window({
        "used_percent": 40.0,
        "percent_left": 60.0,
        "reset_at": 1750000000,
        "limit_window_seconds": 18000,
    })
    assert used == 40.0
    assert remaining == 60.0
    assert reset_at == datetime.fromtimestamp(1750000000, tz=timezone.utc)
    assert window_sec == 18000


def test_parse_window_zero_percent_left_without_used():
    # percent_left=0.0 是合法值（额度耗尽），不能被 or 链当成缺失
    used, remaining, _, _ = _parse_window({"percent_left": 0.0})
    assert used is None
    assert remaining == 0.0


def test_parse_window_remaining_computed_from_used():
    _, remaining, _, _ = _parse_window({"used_percent": 30.0})
    assert remaining == 70.0


def test_parse_window_millisecond_timestamp():
    _, _, reset_at, _ = _parse_window({"reset_at": 1750000000000})
    assert reset_at == datetime.fromtimestamp(1750000000, tz=timezone.utc)
