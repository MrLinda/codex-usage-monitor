# Codex Usage Monitor

本地优先的 Windows 桌面应用，用于追踪 OpenAI Codex 的 token 用量和费用。

## 功能

- **实时仪表盘** — tkinter GUI + 系统托盘；浏览器访问 `http://127.0.0.1:8765`
- **Token 追踪** — 解析 `~/.codex/sessions/*.jsonl`，采集每次调用的 token 用量
- **配额监控** — 轮询 ChatGPT usage API，获取 5 小时和每周配额窗口、套餐类型、重置时间
- **费用估算** — 内置定价表，支持 GPT-5.5、GPT-5.4、GPT-5.4-mini、GPT-5.6 系列
- **模型分布** — 饼图/柱状图按模型展示用量占比
- **趋势分析** — 按小时或按天聚合，叠加费用曲线
- **可配置刷新** — token 采集、配额采集、前端刷新各自独立间隔

> **注意：** 费用为基于 session 日志的估算值，未含 Codex cache write 溢价（GPT-5.6 及更新模型）。准确金额请以 OpenAI 官方 Dashboard 为准。

## 环境要求

- Python >= 3.11
- 拥有可访问 `~/.codex/sessions/` 的 Codex 或 ChatGPT Plus/Pro 订阅
- Windows（tkinter + pystray；在 Windows 10/11 上测试通过）

## 安装

```bash
git clone https://github.com/MrLinda/codex-usage-monitor.git
cd codex-usage-monitor
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## 运行

```bash
# GUI 模式（tkinter + 系统托盘）
python -m app.main

# 无头模式（纯命令行，无 GUI）
python -m app.main --headless
```

仪表盘默认运行在 `http://127.0.0.1:8765`。

首次启动时应用会：

1. 在 `%APPDATA%\CodexUsageMonitor\usage.sqlite` 创建 SQLite 数据库
2. 开始增量扫描 `~/.codex/sessions/*.jsonl`
3. 轮询 `https://chatgpt.com/backend-api/wham/usage` 获取配额数据

## 配置

配置文件位于 `%APPDATA%\CodexUsageMonitor\config.toml`。

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `app.poll_interval_seconds` | `600` | session 文件重新扫描间隔（秒） |
| `app.quota_interval_minutes` | `10` | ChatGPT usage API 轮询间隔（分钟） |
| `app.host` | `127.0.0.1` | FastAPI 绑定地址 |
| `app.port` | `8765` | FastAPI 绑定端口 |
| `app.default_model` | `unknown` | session 文件无型号信息时的回退值 |
| `app.model_aliases` | `{"codex-auto-review": "gpt-5.4"}` | 内部型号别名到定价 key 的映射 |
| `paths.data_dir` | `%APPDATA%\CodexUsageMonitor` | 数据库和日志目录 |
| `paths.db_path` | `%APPDATA%\CodexUsageMonitor\usage.sqlite` | SQLite 数据库路径 |
| `paths.sessions_dir` | `~/.codex/sessions` | Codex session 目录 |
| `paths.log_dir` | `%APPDATA%\CodexUsageMonitor\logs` | 日志文件目录 |

## 打包（PyInstaller）

```bash
pyinstaller codex-backend.spec --distpath dist-backend --noconfirm
```

生成独立可执行文件 `dist-backend\codex-backend.exe`。

## 架构

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

- **后端**: FastAPI + Uvicorn，SQLite WAL 模式
- **前端**: 单页 HTML + Chart.js（本地打包，CDN 兜底）
- **GUI**: tkinter 窗口 + pystray 系统托盘
- **调度**: `Poller` 驱动两个采集器各自独立运行

## 开发

```bash
python -m ruff check app/
python -m pytest tests/ -q
```

## 定价表

模型价格硬编码在 `app/collectors\log_collector.py` 的 `MODEL_PRICING` 字典中，不会从 OpenAI API 拉取。OpenAI 发布新价格时需手动更新。

当前覆盖的模型：

| 模型 | 短上下文输入 | 缓存读取 | 缓存写入 | 输出 |
|------|-------------|----------|----------|------|
| gpt-5.6-sol  | $5.00 | $0.50 | $6.25 | $30.00 |
| gpt-5.6-terra | $2.50 | $0.25 | $3.125 | $15.00 |
| gpt-5.6-luna  | $1.00 | $0.10 | $1.25 | $6.00 |
| gpt-5.5       | $5.00 | $0.50 | — | $30.00 |
| gpt-5.4       | $2.50 | $0.25 | — | $15.00 |
| gpt-5.4-mini  | $0.75 | $0.075 | — | $4.50 |

GPT-5.6 系列还有"长上下文"档位（超过阈值的输入价格更高），详见 `MODEL_PRICING` 源码。

## 常见问题

- **"费用为 $0"** — session 文件中的型号与定价表不匹配。在 `config.toml` 的 `app.model_aliases` 中添加映射。
- **托盘左键点击无响应** — pystray 在某些 Windows 环境下的已知限制；请右键点击托盘图标。
- **配额一直为空** — 确认 `~/.codex/auth.json` 中包含有效的 `access_token`。

## License

MIT
