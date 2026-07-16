from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class TokenUsage:
    event_time: datetime
    session_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    reasoning_tokens: int
    estimated_cost_usd: float | None = None
    raw_json: str | None = None
    source: str | None = None


@dataclass
class QuotaSample:
    captured_at: datetime
    plan_type: str
    email: str = ""
    five_hour_used_pct: float | None = None
    five_hour_remaining_pct: float | None = None
    five_hour_reset_at: datetime | None = None
    five_hour_window_seconds: int | None = None
    weekly_used_pct: float | None = None
    weekly_remaining_pct: float | None = None
    weekly_reset_at: datetime | None = None
    weekly_window_seconds: int | None = None
    has_credits: bool = False
    credits_balance: str = "0"
    raw_json: dict[str, Any] | None = None
