from __future__ import annotations

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
    remaining = window.get("percent_left") or window.get("remaining_percent")
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


class QuotaCollector(Collector):
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
            response = requests.get(USAGE_URL, headers=headers, timeout=30)
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
