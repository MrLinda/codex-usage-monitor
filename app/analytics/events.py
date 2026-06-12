from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def check_collection_events(
    entries_count: int,
    new_count: int,
    error: str | None = None,
    cost_threshold: float = 1.0,
    cooldown: timedelta = timedelta(hours=1),
    last_event_time: datetime | None = None,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    now = datetime.now()

    if last_event_time and (now - last_event_time) < cooldown:
        return events

    if error:
        events.append({
            "event_at": now.isoformat(),
            "event_type": "collection_error",
            "message": error,
        })
    elif entries_count > 0 and new_count == 0:
        events.append({
            "event_at": now.isoformat(),
            "event_type": "no_new_data",
            "message": f"Found {entries_count} entries, all already recorded",
        })

    return events
