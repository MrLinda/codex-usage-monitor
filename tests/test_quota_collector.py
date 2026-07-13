from __future__ import annotations

from datetime import datetime, timezone

from app.collectors.quota_collector import _parse_window, _classify_window, _extract_windows


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


# ---- _classify_window ----

def test_classify_five_hour():
    assert _classify_window({"limit_window_seconds": 18000}) == "five_hour"


def test_classify_weekly():
    assert _classify_window({"limit_window_seconds": 604800}) == "weekly"


def test_classify_five_hour_with_tolerance():
    # Api 返回的秒数可能略有偏差（如 17999 / 18005）
    assert _classify_window({"limit_window_seconds": 17999}) == "five_hour"
    assert _classify_window({"limit_window_seconds": 18300}) == "five_hour"


def test_classify_unknown():
    assert _classify_window({"limit_window_seconds": 3600}) is None
    assert _classify_window({}) is None


# ---- _extract_windows ----

def test_extract_both_windows_by_seconds():
    rate_limit = {
        "primary_window": {"used_percent": 10, "limit_window_seconds": 18000},
        "secondary_window": {"used_percent": 20, "limit_window_seconds": 604800},
    }
    windows = _extract_windows(rate_limit)
    assert "five_hour" in windows
    assert "weekly" in windows


def test_extract_only_weekly():
    # 接口可能只返回 7 天限额
    rate_limit = {
        "weekly": {"used_percent": 30, "limit_window_seconds": 604800},
    }
    windows = _extract_windows(rate_limit)
    assert "five_hour" not in windows
    assert "weekly" in windows


def test_extract_only_five_hour():
    rate_limit = {
        "five_hour": {"used_percent": 50, "limit_window_seconds": 18000},
    }
    windows = _extract_windows(rate_limit)
    assert "five_hour" in windows
    assert "weekly" not in windows


def test_extract_ignores_non_window_entries():
    rate_limit = {
        "some_string_field": "not a window",
        "primary_window": {"used_percent": 10, "limit_window_seconds": 18000},
        "credits_info": {"balance": 100},  # 没有 used_percent / limit_window_seconds
    }
    windows = _extract_windows(rate_limit)
    assert list(windows.keys()) == ["five_hour"]


def test_extract_empty_rate_limit():
    assert _extract_windows({}) == {}
