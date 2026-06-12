from __future__ import annotations


def compute_burn_rate(prev_pct: float, curr_pct: float, elapsed_hours: float) -> float | None:
    if elapsed_hours <= 0:
        return None
    if curr_pct > prev_pct + 50:
        return None
    consumed = prev_pct - curr_pct
    if consumed < 0:
        return None
    return consumed / elapsed_hours


def is_likely_reset(prev_pct: float | None, curr_pct: float | None) -> bool:
    if prev_pct is None or curr_pct is None:
        return False
    return curr_pct - prev_pct >= 50
