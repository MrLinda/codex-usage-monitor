from __future__ import annotations


def forecast_empty_time(current_pct: float, burn_rate_pct_per_hour: float) -> float | None:
    if burn_rate_pct_per_hour <= 0:
        return None
    return current_pct / burn_rate_pct_per_hour
