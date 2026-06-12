from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class StatusResponse(BaseModel):
    latest_sample: dict[str, Any] | None = None
    burn_rate: dict[str, float | None] = {}
    forecast: dict[str, float | None] = {}
    sample_count: int = 0


class SampleOut(BaseModel):
    captured_at: datetime
    five_hour_remaining_pct: float | None = None
    weekly_remaining_pct: float | None = None
    source: str | None = None


class EventOut(BaseModel):
    event_at: datetime
    event_type: str
    message: str | None = None
    sample_id: int | None = None


class CollectNowResponse(BaseModel):
    status: str
    sample_id: int | None = None
    message: str | None = None


class SettingsUpdate(BaseModel):
    poll_interval_minutes: int | None = None
    five_hour_warning_pct: int | None = None
    weekly_warning_pct: int | None = None
