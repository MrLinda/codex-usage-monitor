from __future__ import annotations

import csv
import io
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel

from app.config import Config, load_config
from app.server.static_dashboard import DASHBOARD_HTML
from app.storage.db import get_connection
from app.storage.migrations import run_migrations
from app.storage.repository import Repository

logger = logging.getLogger("codex_usage_monitor")




def _wrap_errors(func):
    """为 API 端点统一捕获异常，返回 JSON 错误而非 500 堆栈。"""
    import functools
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception("API error in %s: %s", func.__name__, e)
            return JSONResponse(
                status_code=500,
                content={"error": type(e).__name__, "message": str(e)},
            )
    return wrapper


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cfg = get_config()
    conn = get_connection(cfg.paths.db_path)
    run_migrations(conn)
    global _repo
    _repo = Repository(conn)
    try:
        yield
    finally:
        conn.close()
        logger.info("Database connection closed")


app = FastAPI(title="Codex Usage Monitor", version="0.1.0", lifespan=lifespan)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    logger.exception("Unhandled API exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": type(exc).__name__, "message": str(exc)},
    )

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


@app.get("/api/status")
@_wrap_errors
def api_status():
    repo = get_repo()
    summary = repo.get_summary()
    models = repo.get_model_breakdown()
    # DB 里 event_time 是 UTC ISO 串："今日"取本地时区 0 点再转 UTC，
    # 否则在 UTC+8 下会从早上 8 点才开始算
    local_midnight = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    today_rows = repo.get_token_usage(from_dt=local_midnight.astimezone(timezone.utc))
    today_input = sum(r["input_tokens"] for r in today_rows)
    today_cached = sum(r["cached_input_tokens"] for r in today_rows)
    today_output = sum(r["output_tokens"] for r in today_rows)
    today_tokens = today_input + today_output
    today_cost = sum(r["estimated_cost_usd"] or 0 for r in today_rows)

    return {
        "summary": summary,
        "models": models,
        "today": {
            "total_tokens": today_tokens,
            "input_tokens": today_input,
            "cached_input_tokens": today_cached,
            "output_tokens": today_output,
            "estimated_cost_usd": round(today_cost, 4),
            "entries": len(today_rows),
        },
        "quota": repo.get_latest_quota(),
        "reset_credits": _poller.quota_collector.get_reset_credits() if _poller else {},
    }


@app.get("/api/token-usage")
@_wrap_errors
def api_token_usage(
    from_dt: str | None = Query(None),
    to_dt: str | None = Query(None),
    limit: int = Query(10000),
    daily: bool = Query(False),
):
    repo = get_repo()
    from_parsed = datetime.fromisoformat(from_dt) if from_dt else None
    to_parsed = datetime.fromisoformat(to_dt) if to_dt else None
    rows = repo.get_token_usage(from_dt=from_parsed, to_dt=to_parsed, limit=limit, daily=daily)
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
@_wrap_errors
def api_events(limit: int = Query(50)):
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
        minutes = max(1, req.minutes)
        _poller.quota_interval_minutes = minutes
        # 同时写入 config.toml，让网页改动也被持久化（与 GUI 设置面板保持一致）
        try:
            from app.config import save_config
            _poller.config.app.quota_interval_minutes = minutes
            save_config(_poller.config)
        except Exception as e:
            logger.warning("save_config failed: %s", e)
        return {"minutes": minutes}
    return {"error": "poller not available"}


class PollIntervalRequest(BaseModel):
    seconds: int


@app.get("/api/poll/interval")
def api_get_poll_interval():
    """token 采集间隔（后端解析 sessions 写 DB 的频率），单位秒。"""
    if _poller:
        return {"seconds": _poller.config.app.poll_interval_seconds}
    return {"seconds": 600}


@app.post("/api/poll/interval")
def api_set_poll_interval(req: PollIntervalRequest):
    global _poller
    if _poller:
        seconds = max(10, req.seconds)
        _poller.config.app.poll_interval_seconds = seconds
        # 与 quota 一致：持久化到 config.toml，方便和 GUI 设置面板双向同步
        try:
            from app.config import save_config
            save_config(_poller.config)
        except Exception as e:
            logger.warning("save_config failed: %s", e)
        return {"seconds": seconds}
    return {"error": "poller not available"}


@app.get("/api/usage/rolling")
@_wrap_errors
def api_rolling_usage():
    repo = get_repo()
    return {
        "last_5h": repo.get_rolling_usage(5),
        "last_7d": repo.get_rolling_usage(168),
    }


@app.get("/api/usage/windowed")
@_wrap_errors
def api_usage_windowed():
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
@_wrap_errors
def api_quota_status():
    repo = get_repo()
    latest = repo.get_latest_quota()
    return latest or {"error": "no quota data yet"}


@app.get("/api/quota/refresh-and-status")
async def api_quota_refresh_and_status():
    """供托盘左键弹窗调用：同步触发一次配额 + token 采集，再返回最新状态。

    与 /api/collect-now 共用同一套采集逻辑，但额外把最新配额和两个窗口
    的 token 用量打包返回，省去前端再发一次请求。
    """
    if not _poller:
        return {"error": "poller not available"}

    try:
        await _poller.collect_once()
    except Exception as e:
        logger.error("refresh token collect failed: %s", e)
    try:
        await _poller.collect_quota_once()
    except Exception as e:
        logger.error("refresh quota collect failed: %s", e)

    repo = get_repo()
    latest = repo.get_latest_quota()
    if not latest:
        return {"quota": None, "usage": None}

    usage = {"five_hour": None, "weekly": None}
    fh_reset = latest.get("five_hour_reset_at")
    fh_window = latest.get("five_hour_window_seconds")
    if fh_reset and fh_window:
        reset_dt = datetime.fromisoformat(fh_reset)
        window_start = reset_dt - timedelta(seconds=fh_window)
        usage["five_hour"] = repo.get_windowed_usage(window_start, reset_dt)

    wk_reset = latest.get("weekly_reset_at")
    wk_window = latest.get("weekly_window_seconds")
    if wk_reset and wk_window:
        reset_dt = datetime.fromisoformat(wk_reset)
        window_start = reset_dt - timedelta(seconds=wk_window)
        usage["weekly"] = repo.get_windowed_usage(window_start, reset_dt)

    reset_credits = _poller.quota_collector.get_reset_credits() if _poller else {}
    return {"quota": latest, "usage": usage, "reset_credits": reset_credits}


@app.get("/api/quota/reset-credits")
async def api_quota_reset_credits(force: bool = Query(False)):
    if _poller and _poller.quota_collector:
        if force:
            await _poller.quota_collector.fetch_reset_credits()
        return _poller.quota_collector.get_reset_credits()
    return {"credits": [], "available_count": 0}


@app.get("/api/quota/history")
@_wrap_errors
def api_quota_history(
    limit: int = 500,
    from_dt: str | None = Query(None),
    to_dt: str | None = Query(None),
    daily: bool = Query(False),
):
    repo = get_repo()
    from_parsed = datetime.fromisoformat(from_dt) if from_dt else None
    to_parsed = datetime.fromisoformat(to_dt) if to_dt else None
    return repo.get_quota_history(limit=limit, from_dt=from_parsed, to_dt=to_parsed, daily=daily)


@app.get("/api/quota/estimated-costs")
@_wrap_errors
def api_quota_estimated_costs(
    limit: int = 500,
    from_dt: str | None = Query(None),
    to_dt: str | None = Query(None),
    daily: bool = Query(False),
):
    repo = get_repo()
    from_parsed = datetime.fromisoformat(from_dt) if from_dt else None
    to_parsed = datetime.fromisoformat(to_dt) if to_dt else None
    samples = repo.get_quota_history(limit=limit, from_dt=from_parsed, to_dt=to_parsed, daily=daily)
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
            if cost > 0:
                entry["five_hour_est_total"] = round(cost / (fh_pct / 100), 4)

        wk_reset = s.get("weekly_reset_at")
        wk_window = s.get("weekly_window_seconds")
        wk_pct = s.get("weekly_used_pct")
        if wk_reset and wk_window and wk_pct and wk_pct > 0:
            reset_dt = datetime.fromisoformat(wk_reset)
            window_start = reset_dt - timedelta(seconds=wk_window)
            cost = repo.get_cumulative_cost(window_start, captured)
            if cost > 0:
                entry["weekly_est_total"] = round(cost / (wk_pct / 100), 4)

        result.append(entry)

    return result


@app.get("/api/export/token-usage.csv")
@_wrap_errors
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


CHART_JS_PATH = Path(__file__).resolve().parent / "static" / "chart.umd.min.js"
CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"


@app.get("/static/chart.umd.min.js")
def chart_js():
    # 优先用打包进来的本地 Chart.js（离线可用）；文件缺失时回退 CDN
    if CHART_JS_PATH.is_file():
        return FileResponse(CHART_JS_PATH, media_type="application/javascript")
    return RedirectResponse(CHART_JS_CDN)
