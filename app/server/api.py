from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from app.config import Config, load_config
from app.server.static_dashboard import DASHBOARD_HTML
from app.storage.db import get_connection
from app.storage.migrations import run_migrations
from app.storage.repository import Repository

app = FastAPI(title="Codex Usage Monitor", version="0.1.0")

_config: Config | None = None
_repo: Repository | None = None
_poller = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_repo() -> Repository:
    global _repo
    if _repo is None:
        cfg = get_config()
        conn = get_connection(cfg.paths.db_path)
        run_migrations(conn)
        _repo = Repository(conn)
    return _repo


@app.on_event("startup")
def startup():
    cfg = get_config()
    conn = get_connection(cfg.paths.db_path)
    run_migrations(conn)
    global _repo
    _repo = Repository(conn)


@app.get("/api/status")
def api_status():
    repo = get_repo()
    summary = repo.get_summary()
    models = repo.get_model_breakdown()
    last_24h = repo.get_token_usage(
        from_dt=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
    )
    today_input = sum(r["input_tokens"] for r in last_24h)
    today_cached = sum(r["cached_input_tokens"] for r in last_24h)
    today_output = sum(r["output_tokens"] for r in last_24h)
    today_tokens = today_input + today_output
    today_cost = sum(r["estimated_cost_usd"] or 0 for r in last_24h)

    return {
        "summary": summary,
        "models": models,
        "today": {
            "total_tokens": today_tokens,
            "input_tokens": today_input,
            "cached_input_tokens": today_cached,
            "output_tokens": today_output,
            "estimated_cost_usd": round(today_cost, 4),
            "entries": len(last_24h),
        },
    }


@app.get("/api/token-usage")
def api_token_usage(
    from_dt: str | None = Query(None),
    to_dt: str | None = Query(None),
    limit: int = Query(10000),
):
    repo = get_repo()
    from_parsed = datetime.fromisoformat(from_dt) if from_dt else None
    to_parsed = datetime.fromisoformat(to_dt) if to_dt else None
    rows = repo.get_token_usage(from_dt=from_parsed, to_dt=to_parsed, limit=limit)
    return [
        {
            "event_time": r["event_time"],
            "session_id": r["session_id"],
            "model": r["model"],
            "input_tokens": r["input_tokens"],
            "output_tokens": r["output_tokens"],
            "cached_input_tokens": r["cached_input_tokens"],
            "reasoning_tokens": r["reasoning_tokens"],
            "estimated_cost_usd": r["estimated_cost_usd"],
        }
        for r in rows
    ]


@app.get("/api/events")
def api_events(limit: int = Query(100)):
    repo = get_repo()
    return repo.get_events(limit=limit)


@app.post("/api/collect-now")
async def api_collect_now():
    if _poller:
        token_count = await _poller.collect_once()
        await _poller.collect_quota_once()
        return {"status": "ok", "token_count": token_count}
    return {"status": "error", "message": "poller not available"}


class QuotaIntervalRequest(BaseModel):
    minutes: int


@app.get("/api/quota/interval")
def api_get_quota_interval():
    if _poller:
        return {"minutes": _poller.quota_interval_minutes}
    return {"minutes": 10}


@app.post("/api/quota/interval")
def api_set_quota_interval(req: QuotaIntervalRequest):
    global _poller
    if _poller:
        _poller.quota_interval_minutes = max(1, req.minutes)
        return {"minutes": _poller.quota_interval_minutes}
    return {"error": "poller not available"}


@app.get("/api/usage/rolling")
def api_rolling_usage():
    repo = get_repo()
    return {
        "last_5h": repo.get_rolling_usage(5),
        "last_7d": repo.get_rolling_usage(168),
    }


@app.get("/api/usage/windowed")
def api_usage_windowed():
    from datetime import timedelta
    repo = get_repo()
    latest = repo.get_latest_quota()
    result = {"five_hour": None, "weekly": None}

    if latest:
        fh_reset = latest.get("five_hour_reset_at")
        fh_window = latest.get("five_hour_window_seconds")
        if fh_reset and fh_window:
            reset_dt = datetime.fromisoformat(fh_reset)
            window_start = reset_dt - timedelta(seconds=fh_window)
            result["five_hour"] = {
                "window_start": window_start.isoformat(),
                "window_end": reset_dt.isoformat(),
                "usage": repo.get_windowed_usage(window_start, reset_dt),
            }

        wk_reset = latest.get("weekly_reset_at")
        wk_window = latest.get("weekly_window_seconds")
        if wk_reset and wk_window:
            reset_dt = datetime.fromisoformat(wk_reset)
            window_start = reset_dt - timedelta(seconds=wk_window)
            result["weekly"] = {
                "window_start": window_start.isoformat(),
                "window_end": reset_dt.isoformat(),
                "usage": repo.get_windowed_usage(window_start, reset_dt),
            }

    return result


@app.get("/api/quota/status")
def api_quota_status():
    repo = get_repo()
    latest = repo.get_latest_quota()
    return latest or {"error": "no quota data yet"}


@app.get("/api/quota/history")
def api_quota_history(
    limit: int = 500,
    from_dt: str | None = Query(None),
    to_dt: str | None = Query(None),
):
    repo = get_repo()
    from_parsed = datetime.fromisoformat(from_dt) if from_dt else None
    to_parsed = datetime.fromisoformat(to_dt) if to_dt else None
    return repo.get_quota_history(limit=limit, from_dt=from_parsed, to_dt=to_parsed)


@app.get("/api/quota/estimated-costs")
def api_quota_estimated_costs(
    limit: int = 500,
    from_dt: str | None = Query(None),
    to_dt: str | None = Query(None),
):
    from datetime import timedelta

    repo = get_repo()
    from_parsed = datetime.fromisoformat(from_dt) if from_dt else None
    to_parsed = datetime.fromisoformat(to_dt) if to_dt else None
    samples = repo.get_quota_history(limit=limit, from_dt=from_parsed, to_dt=to_parsed)
    result = []

    for s in samples:
        entry = {"captured_at": s["captured_at"], "five_hour_est_total": None, "weekly_est_total": None}
        captured = datetime.fromisoformat(s["captured_at"])

        fh_reset = s.get("five_hour_reset_at")
        fh_window = s.get("five_hour_window_seconds")
        fh_pct = s.get("five_hour_used_pct")
        if fh_reset and fh_window and fh_pct and fh_pct > 0:
            reset_dt = datetime.fromisoformat(fh_reset)
            window_start = reset_dt - timedelta(seconds=fh_window)
            cost = repo.get_cumulative_cost(window_start, captured)
            entry["five_hour_est_total"] = round(cost / (fh_pct / 100), 4)

        wk_reset = s.get("weekly_reset_at")
        wk_window = s.get("weekly_window_seconds")
        wk_pct = s.get("weekly_used_pct")
        if wk_reset and wk_window and wk_pct and wk_pct > 0:
            reset_dt = datetime.fromisoformat(wk_reset)
            window_start = reset_dt - timedelta(seconds=wk_window)
            cost = repo.get_cumulative_cost(window_start, captured)
            entry["weekly_est_total"] = round(cost / (wk_pct / 100), 4)

        result.append(entry)

    return result


@app.get("/api/export/token-usage.csv")
def api_export_csv():
    repo = get_repo()
    rows = repo.get_token_usage(limit=100000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "event_time", "session_id", "model",
        "input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens",
        "estimated_cost_usd",
    ])
    for r in rows:
        writer.writerow([
            r["event_time"], r["session_id"], r["model"],
            r["input_tokens"], r["output_tokens"], r["cached_input_tokens"], r["reasoning_tokens"],
            r["estimated_cost_usd"],
        ])
    return PlainTextResponse(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=token_usage.csv"},
    )


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD_HTML)
