# Codex Usage Monitor

[中文文档](README_zh.md)

Local-first Windows desktop app for tracking OpenAI Codex token usage and cost.

## Features

- **Real-time dashboard** — tkinter GUI with system tray; opens in browser at `http://127.0.0.1:8765`
- **Token tracking** — parses `~/.codex/sessions/*.jsonl` to collect per-call token usage
- **Quota monitoring** — polls ChatGPT usage API for 5-hour and weekly quota windows, plan type, and reset time
- **Cost estimation** — hard-coded pricing table with per-model rates (GPT-5.5, GPT-5.4, GPT-5.4-mini, GPT-5.6 family)
- **Model distribution** — pie/bar charts showing break-down by model
- **Trend analysis** — hourly or daily aggregation with cost overlay
- **Configurable refresh** — independent intervals for token polling, quota polling, and frontend refresh

> **Note:** Cost figures are estimates derived from session logs. They do not include Codex cache-write surcharges (relevant for GPT-5.6 and newer models). Refer to the OpenAI billing dashboard for exact charges.

## Requirements

- Python >= 3.11
- A Codex or ChatGPT Plus/Pro subscription with access to `~/.codex/sessions/`
- Windows (tkinter + pystray; tested on Windows 10/11)

## Install

```bash
git clone https://github.com/MrLinda/codex-usage-monitor.git
cd codex-usage-monitor
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Run

```bash
# GUI mode (tkinter + system tray)
python -m app.main

# Headless mode (command-line only, no GUI)
python -m app.main --headless
```

The dashboard is served at `http://127.0.0.1:8765`.

On first launch the app:

1. Creates a SQLite database at `%APPDATA%\CodexUsageMonitor\usage.sqlite`
2. Starts scanning `~/.codex/sessions/*.jsonl` incrementally
3. Polls `https://chatgpt.com/backend-api/wham/usage` for quota data

## Configuration

Settings are stored in `%APPDATA%\CodexUsageMonitor\config.toml`.

| Key | Default | Description |
|-----|---------|-------------|
| `app.poll_interval_seconds` | `600` | How often to re-scan session files |
| `app.quota_interval_minutes` | `10` | How often to poll the ChatGPT usage API |
| `app.host` | `127.0.0.1` | Bind address for the FastAPI server |
| `app.port` | `8765` | Bind port for the FastAPI server |
| `app.default_model` | `unknown` | Fallback model name when a session file contains no model info |
| `app.model_aliases` | `{"codex-auto-review": "gpt-5.4"}` | Map internal model slugs to pricing keys |
| `paths.data_dir` | `%APPDATA%\CodexUsageMonitor` | Directory for DB and logs |
| `paths.db_path` | `%APPDATA%\CodexUsageMonitor\usage.sqlite` | SQLite database path |
| `paths.sessions_dir` | `~/.codex/sessions` | Codex session directory |
| `paths.log_dir` | `%APPDATA%\CodexUsageMonitor\logs` | Log file directory |

## Build (PyInstaller)

```bash
pyinstaller codex-backend.spec --distpath dist-backend --noconfirm
```

Produces a self-contained `dist-backend\codex-backend.exe`.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ Codex       │────▶│ Session      │────▶│ SQLite (WAL)    │
│ sessions/   │     │ Collector    │     │                 │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                  │
┌─────────────┐     ┌──────────────┐     ┌────────▼────────┐
│ ChatGPT     │────▶│ Quota        │────▶│ FastAPI +       │
│ usage API   │     │ Collector    │     │ Dashboard (HTML)│
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                  │
                                           ┌──────▼──────┐
                                           │ tkinter GUI │
                                           │ + pystray   │
                                           └─────────────┘
```

- **Backend**: FastAPI + Uvicorn, SQLite in WAL mode
- **Frontend**: Single HTML page with Chart.js (bundled locally, CDN fallback)
- **GUI**: tkinter window + pystray system tray
- **Scheduling**: `Poller` drives both collectors on independent timers

## Development

```bash
python -m ruff check app/
python -m pytest tests/ -q
```

## Pricing Data

Model prices are hard-coded in `app/collectors/log_collector.py` (`MODEL_PRICING`). They are not fetched from the OpenAI API. Update manually when OpenAI publishes new rates.

Current models covered:

| Model | Short input | Cached input | Cache writes | Output |
|-------|-------------|--------------|--------------|--------|
| gpt-5.6-sol  | $5.00 | $0.50 | $6.25 | $30.00 |
| gpt-5.6-terra | $2.50 | $0.25 | $3.125 | $15.00 |
| gpt-5.6-luna  | $1.00 | $0.10 | $1.25 | $6.00 |
| gpt-5.5       | $5.00 | $0.50 | — | $30.00 |
| gpt-5.4       | $2.50 | $0.25 | — | $15.00 |
| gpt-5.4-mini  | $0.75 | $0.075 | — | $4.50 |

GPT-5.6 models also have a "long context" tier (inputs above the threshold cost more). See the `MODEL_PRICING` source for exact values.

## Troubleshooting

- **"费用为 $0"** — The model slug from your session file doesn't match any pricing key. Add a mapping to `app.model_aliases` in `config.toml`.
- **Tray popup not opening on left-click** — Known pystray limitation on some Windows setups; right-click the tray icon instead.
- **Quota stays empty** — Make sure `~/.codex/auth.json` contains a valid `access_token`.

## License

MIT
