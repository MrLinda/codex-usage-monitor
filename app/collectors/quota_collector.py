from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests

from app.collectors.base import Collector
from app.models import QuotaSample

logger = logging.getLogger("codex_usage_monitor")

AUTH_PATH = Path.home() / ".codex" / "auth.json"
USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"


def _get_credentials() -> tuple[str, str] | None:
    if not AUTH_PATH.is_file():
        logger.warning("auth.json not found at %s", AUTH_PATH)
        return None
    try:
        data = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
        token = data.get("tokens", {}).get("access_token")
        account_id = data.get("tokens", {}).get("account_id")
        if token and account_id:
            return token, account_id
        logger.warning("auth.json missing access_token or account_id")
        return None
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Failed to read auth.json: %s", e)
        return None


def _parse_window(window: dict | None) -> tuple[float | None, float | None, datetime | None, int | None]:
    if not window:
        return None, None, None, None

    used = window.get("used_percent")
    # 不能用 or 链：percent_left 为 0.0（额度耗尽）是合法值，or 会把它当缺失跳过
    remaining = window.get("percent_left")
    if remaining is None:
        remaining = window.get("remaining_percent")
    if remaining is None and used is not None:
        remaining = max(0.0, 100.0 - float(used))

    reset_at = None
    raw_reset = window.get("reset_at")
    if raw_reset is not None:
        try:
            t = int(raw_reset)
            if t > 10**11:
                t = t // 1000
            reset_at = datetime.fromtimestamp(t, tz=timezone.utc)
        except (ValueError, TypeError, OSError):
            pass

    window_sec = window.get("limit_window_seconds")

    used_f = float(used) if used is not None else None
    remaining_f = float(remaining) if remaining is not None else None

    return used_f, remaining_f, reset_at, window_sec


RESET_CREDITS_URL = "https://chatgpt.com/backend-api/wham/rate-limit-reset-credits"


class QuotaCollector(Collector):
    def __init__(self) -> None:
        self._reset_credits_cache: dict = {}

    async def collect(self) -> QuotaSample | None:
        creds = _get_credentials()
        if not creds:
            return None

        token, account_id = creds
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "ChatGPT-Account-Id": account_id,
            "Origin": "https://chatgpt.com",
            "Referer": "https://chatgpt.com/",
            "User-Agent": "Mozilla/5.0",
        }

        captured_at = datetime.now(timezone.utc)

        try:
            # requests 是同步库，放线程池执行，避免卡住与 uvicorn 共享的事件循环
            response = await asyncio.to_thread(requests.get, USAGE_URL, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error("Quota API request failed: %s", e)
            return None

        rate_limit = data.get("rate_limit") or data.get("rate_limits") or {}
        primary = rate_limit.get("primary_window") or rate_limit.get("five_hour") or rate_limit.get("five_hour_limit") or {}
        secondary = rate_limit.get("secondary_window") or rate_limit.get("weekly") or rate_limit.get("weekly_limit") or {}

        fh_used, fh_remaining, fh_reset, fh_window = _parse_window(primary)
        wk_used, wk_remaining, wk_reset, wk_window = _parse_window(secondary)

        credits = data.get("credits") or {}
        has_credits = bool(credits.get("has_credits", False))
        credits_balance = str(credits.get("balance", "0"))

        logger.info(
            "Quota: 5h used=%s%% remaining=%s%% | weekly used=%s%% remaining=%s%%",
            fh_used, fh_remaining, wk_used, wk_remaining,
        )

        return QuotaSample(
            captured_at=captured_at,
            plan_type=data.get("plan_type", "?"),
            email=data.get("email", ""),
            five_hour_used_pct=fh_used,
            five_hour_remaining_pct=fh_remaining,
            five_hour_reset_at=fh_reset,
            five_hour_window_seconds=fh_window,
            weekly_used_pct=wk_used,
            weekly_remaining_pct=wk_remaining,
            weekly_reset_at=wk_reset,
            weekly_window_seconds=wk_window,
            has_credits=has_credits,
            credits_balance=credits_balance,
            raw_json=data,
        )

    def get_reset_credits(self) -> dict:
        return self._reset_credits_cache or {"credits": [], "available_count": 0}

    async def fetch_reset_credits(self) -> dict:
        creds = _get_credentials()
        if not creds:
            return {"error": "auth.json not found", "credits": [], "available_count": 0}
        token, _ = creds
        try:
            resp = await asyncio.to_thread(
                requests.get,
                RESET_CREDITS_URL,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                timeout=10,
            )
            resp.raise_for_status()
            self._reset_credits_cache = resp.json()
            logger.info("Reset credits fetched: %d available", self._reset_credits_cache.get("available_count", 0))
        except requests.RequestException as e:
            logger.error("Failed to fetch reset credits: %s", e)
        return self._reset_credits_cache
