# Codex Usage Monitor - Agents Guide

## Rules

- **NEVER commit or push without explicit user confirmation.**
- Always inspect `git status`, `git diff`, and recent commits before staging.
- Write concise commit messages that match the repo style (conventional commits: `feat:`, `fix:`, `chore:`, `docs:`).
- Do NOT update git config, skip hooks, use interactive `-i`, force-push, create empty commits, or amend commits unless explicitly requested.
- Run lint + tests after changes and report the result to the user.
- Ask before adding any files outside code edits (documentation, config, etc.).

## Lint & Test

```bash
python -m ruff check app/
python -m pytest tests/ -q
```

## Run

```bash
# GUI 模式（tkinter 窗口 + 系统托盘）
python -m app.main

# 无头模式（纯命令行，无 GUI）
python -m app.main --headless
```

## Build

```bash
pyinstaller codex-backend.spec --distpath dist-backend --noconfirm
```

## Architecture

### Tech Stack
- **Backend**: Python FastAPI + Uvicorn, SQLite (WAL mode)
- **Frontend**: 单页 HTML dashboard (Chart.js), 内嵌在 FastAPI 的 static_dashboard.py 里
- **GUI**: tkinter 窗口 + pystray 系统托盘
- **打包**: PyInstaller

### Data Flow
1. `SessionCollector` 解析 `~/.codex/sessions/*.jsonl` 提取 token 用量
2. `QuotaCollector` 调用 ChatGPT API (`/backend-api/wham/usage`) 获取配额信息
3. `Poller` 按间隔定时采集，存入 SQLite
4. FastAPI 提供 REST API，前端 dashboard 通过 fetch 轮询刷新

### Key Files
- `app/main.py` - 入口，支持 GUI/headless 模式，后端线程 + tkinter 主线程
- `app/gui.py` - tkinter GUI，系统托盘，弹窗显示额度
- `app/server/api.py` - FastAPI 路由
- `app/server/static_dashboard.py` - 前端 HTML/JS/CSS（单文件）
- `app/scheduler/poller.py` - 定时采集调度器
- `app/collectors/log_collector.py` - Token 用量采集，含定价表
- `app/collectors/quota_collector.py` - ChatGPT 配额 API 采集
- `app/storage/repository.py` - SQLite CRUD
- `app/storage/migrations.py` - 数据库 schema，支持增量迁移
- `app/models.py` - 数据模型 (TokenUsage, QuotaSample)

### Dashboard Pages
- **概览**: 配额仪表盘 + 用量卡片 + 模型分布图 + 趋势图（按小时/按天切换）
- **配额**: 配额趋势图 + 估算金额线 + 重置竖线 + 时间段筛选
- **用量**: 自定义时段查询（近24h/近7天/今天/这周）
- **事件**: 采集事件日志

### Frontend Refresh Controls (右上角)
- **限额刷新**: 控制配额采集间隔 (5m/10m/15m/30m)
- **token刷新**: 控制前端轮询间隔 (10s/30s/1m)
- **全部刷新**: 手动触发一次完整采集 + 刷新图表

### Key Design Decisions
- 配额估算金额：当 token 用量为 0 时返回 null，前端用灰色虚线延续上一个有效值
- 配额重置竖线：检测 `reset_at` 字段变化，2 分钟容差过滤抖动，连续 3 次确认或时间差 ≥2 小时才画线
- 模型定价表硬编码在 `log_collector.py` 的 `MODEL_PRICING` 字典
- model_aliases 配置支持别名映射（如 codex-auto-review → gpt-5.4）
- 采集用的同步 IO（requests 请求、sessions 文件解析）都通过 `asyncio.to_thread` 放线程池，避免阻塞与 uvicorn 共享的事件循环
- 时区约定：DB 统一存 UTC ISO 串；"今日"按本地 0 点转 UTC 查询，按天聚合用 SQLite `DATE(..., 'localtime')` 折算本地日界
- Chart.js 打包在 `app/server/static/` 本地伺服（离线可用），文件缺失时 `/static/chart.umd.min.js` 回退 CDN

### Known Issues
- pystray 左键单击弹窗在某些环境下不生效（`on_click` 回调未触发），需进一步调试

### Dependencies
- Python: fastapi, uvicorn, pydantic, tomli-w, requests, pystray, Pillow
- Dev: pytest, pytest-asyncio, ruff, pyinstaller
