from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.collectors.base import Collector
from app.models import TokenUsage

logger = logging.getLogger("codex_usage_monitor")


def _no_window() -> subprocess.STARTUPINFO:
    """Windows CREATE_NO_WINDOW 标志，防止子进程弹控制台窗口。"""
    si = subprocess.STARTUPINFO()
    try:
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    except AttributeError:
        pass
    return si

# Price per 1M tokens. Two tiers: short context (default) and long context.
# cache_writes is the upstream 5-min TTL write price; if entry is None it means
# same price as regular input (i.e. no separate cache-write surcharge).
MODEL_PRICING: dict[str, dict[str, dict[str, float | None]]] = {
    "gpt-5.6-sol": {
        "short": {"input": 5.00,  "cached_input": 0.50, "cache_writes": 6.25,  "output": 30.00},
        "long":  {"input": 10.00, "cached_input": 1.00, "cache_writes": 12.50, "output": 45.00},
    },
    "gpt-5.6-terra": {
        "short": {"input": 2.50,  "cached_input": 0.25, "cache_writes": 3.125, "output": 15.00},
        "long":  {"input": 5.00,  "cached_input": 0.50, "cache_writes": 6.25,  "output": 22.50},
    },
    "gpt-5.6-luna": {
        "short": {"input": 1.00,  "cached_input": 0.10, "cache_writes": 1.25,  "output": 6.00},
        "long":  {"input": 2.00,  "cached_input": 0.20, "cache_writes": 2.50,  "output": 9.00},
    },
    "gpt-5.5": {
        "short": {"input": 5.00,  "cached_input": 0.50, "cache_writes": None,   "output": 30.00},
        "long":  {"input": 10.00, "cached_input": 1.00, "cache_writes": None,   "output": 45.00},
    },
    # Legacy models (single tier only)
    "gpt-5.4":      {"short": {"input": 2.50,  "cached_input": 0.25, "cache_writes": None,  "output": 15.00}},
    "gpt-5.4-mini": {"short": {"input": 0.75,  "cached_input": 0.075, "cache_writes": None, "output": 4.50}},
}


def calc_cost(
    model: str,
    input_t: int,
    output_t: int,
    cached_t: int,
    model_aliases: dict[str, str] | None = None,
    *,
    long_context: bool = False,
) -> float:
    resolved = (model_aliases or {}).get(model, model)
    tiers = MODEL_PRICING.get(resolved)
    if tiers is None:
        logger.warning("No pricing for model %s (resolved=%s) — set model_aliases in config", model, resolved)
        return 0.0
    tier = "long" if long_context else "short"
    pricing = tiers.get(tier) or tiers["short"]
    uncached_t = max(0, input_t - cached_t)
    return (
        uncached_t / 1_000_000 * pricing["input"]
        + output_t / 1_000_000 * pricing["output"]
        + cached_t / 1_000_000 * pricing["cached_input"]
    )


class SessionCollector(Collector):
    def __init__(self, sessions_dirs: list[Path], default_model: str = "unknown", model_aliases: dict[str, str] | None = None, wsl_discovery: bool = True):
        self.sessions_dirs = sessions_dirs
        self.default_model = default_model
        self.model_aliases = model_aliases or {}
        self.wsl_discovery = wsl_discovery
        # 增量解析状态：path -> {mtime, size, offset}
        self._file_state: dict[str, dict] = {}
        # 解析逻辑版本号，变更时强制全量重解析已有文件
        self._parse_version = 5
        # WSL 自动发现的目录（发现一次后缓存），每项 (label, path)
        self._wsl_dirs: list[tuple[str, Path]] | None = None

    @staticmethod
    def _discover_wsl_dirs() -> list[tuple[str, Path]]:
        """自动发现所有 WSL distro 中的 ~/.codex/sessions 目录。

        返回 (label, path) 列表，label 如 "WSL: Debian"。
        """
        dirs: list[tuple[str, Path]] = []
        try:
            r = subprocess.run(["wsl.exe", "-l", "-q"], capture_output=True, timeout=10, startupinfo=_no_window())
            if r.returncode != 0:
                return dirs
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return dirs

        # wsl.exe -l -q 输出 UTF-16LE，含嵌入 null 字节
        raw = r.stdout.replace(b"\x00", b"")
        for line in raw.decode("utf-8", errors="replace").splitlines():
            distro = line.strip()
            if not distro:
                continue
            try:
                r2 = subprocess.run(
                    ["wsl.exe", "-d", distro, "bash", "-c", "wslpath -w ~/.codex/sessions"],
                    capture_output=True, timeout=10,
                    startupinfo=_no_window(),
                )
                if r2.returncode == 0:
                    p = Path(r2.stdout.replace(b"\x00", b"").decode("utf-8", errors="replace").strip())
                    if p.is_dir():
                        dirs.append((f"WSL: {distro}", p))
            except (subprocess.TimeoutExpired, OSError):
                continue
        return dirs

    async def collect(self) -> list[TokenUsage]:
        # 全量读取 + 解析 sessions 目录是纯同步 IO，放线程池避免阻塞事件循环
        return await asyncio.to_thread(self._collect_sync)

    def _collect_sync(self) -> list[TokenUsage]:
        results: list[TokenUsage] = []

        # 构建扫描源列表：(label, path)
        sources: list[tuple[str, Path]] = [("Host", p) for p in self.sessions_dirs]
        if self.wsl_discovery:
            if self._wsl_dirs is None:
                self._wsl_dirs = self._discover_wsl_dirs()
                if self._wsl_dirs:
                    logger.info("Discovered WSL sessions: %s", [f"{lb}: {p}" for lb, p in self._wsl_dirs])
            # 去重：避免 WSL 路径与手动配置重复
            existing = {str(p.resolve()) for _, p in sources if p.exists()}
            for label, wsl_path in self._wsl_dirs:
                if str(wsl_path.resolve()) not in existing:
                    sources.append((label, wsl_path))
                    existing.add(str(wsl_path.resolve()))

        # 按源分别采集，分别打日志
        for label, sessions_dir in sources:
            try:
                entries = self._collect_dir(sessions_dir, label)
                if entries:
                    total_tokens = sum(
                        e.input_tokens + e.output_tokens + e.cached_input_tokens + e.reasoning_tokens
                        for e in entries
                    )
                    total_cost = sum(e.estimated_cost_usd or 0 for e in entries)
                    logger.info(
                        "[%s] Collected %d entries (%d tokens, $%.4f)",
                        label, len(entries), total_tokens, total_cost,
                    )
                results.extend(entries)
            except Exception as e:
                logger.error("[%s] Failed to scan: %s", label, e)

        return results

    def _collect_dir(self, sessions_dir: Path, source: str = "") -> list[TokenUsage]:
        """扫描单个 sessions 目录下的所有 .jsonl 文件。"""
        results: list[TokenUsage] = []
        if not sessions_dir.is_dir():
            logger.debug("Sessions dir not found: %s", sessions_dir)
            return results

        for jsonl_file in sessions_dir.rglob("*.jsonl"):
            try:
                stat = jsonl_file.stat()
                key = str(jsonl_file)
                prev = self._file_state.get(key)
                # 解析逻辑版本变化或文件有修改 → 从头重解析
                cache_valid = (
                    prev
                    and prev.get("ver") == self._parse_version
                    and prev["mtime"] == stat.st_mtime
                    and prev["size"] == stat.st_size
                )
                if cache_valid:
                    continue
                is_new = prev is None
                offset = 0 if is_new else prev["offset"]
                # 版本变化时强制从头解析
                if prev and prev.get("ver") != self._parse_version:
                    offset = 0
                # 增量解析时沿用上次解析到的型号，避免新 token_count 出现在 turn_context 之前
                cached_model = prev.get("current_model") if prev else None
                parsed, last_model = self._parse_file(
                    jsonl_file, offset=offset, start_model=cached_model or self.default_model
                )
                if source:
                    for entry in parsed:
                        entry.source = source
                results.extend(parsed)
                # 更新状态（保存最后型号供下次增量解析使用）
                self._file_state[key] = {
                    "mtime": stat.st_mtime,
                    "size": stat.st_size,
                    "offset": stat.st_size,
                    "ver": self._parse_version,
                    "current_model": last_model,
                }
            except Exception as e:
                logger.error("Failed to parse %s: %s", jsonl_file.name, e)
        return results

    def _parse_file(self, path: Path, offset: int = 0, start_model: str | None = None) -> tuple[list[TokenUsage], str]:
        """解析 session 文件，返回 (TokenUsage 列表, 最后解析到的型号)。"""
        entries: list[TokenUsage] = []
        session_id = self._extract_session_id(path)
        current_model = start_model or self.default_model

        with open(path, encoding="utf-8") as f:
            if offset > 0:
                f.seek(offset)
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Track model from turn_context events
                event_model = self._extract_event_model(event)
                if event_model:
                    current_model = event_model

                token_usage = self._extract_token_usage(event, session_id, current_model)
                if token_usage:
                    entries.append(token_usage)

        return entries, current_model

    @staticmethod
    def _extract_event_model(event: dict) -> str | None:
        t = event.get("type")
        payload = event.get("payload") or {}
        pt = payload.get("type")
        if t == "response_item" and pt == "message":
            model = payload.get("model")
            if model:
                return model
        if t == "turn_context":
            # 新格式可能直接在 payload 下有 model
            model = payload.get("model")
            if model:
                return model
            # 旧格式在 collaboration_mode.settings 下
            cm = payload.get("collaboration_mode") or {}
            settings = cm.get("settings") or {}
            model = settings.get("model")
            if model:
                return model
        return None

    @staticmethod
    def _extract_session_id(path: Path) -> str:
        try:
            with open(path, encoding="utf-8") as f:
                first_line = f.readline().strip()
            if first_line:
                event = json.loads(first_line)
                sid = event.get("payload", {}).get("id")
                if sid:
                    return sid
        except Exception:
            pass
        return path.stem

    def _extract_token_usage(self, event: dict, session_id: str, current_model: str) -> TokenUsage | None:
        if event.get("type") != "event_msg":
            return None
        payload = event.get("payload") or {}
        if payload.get("type") != "token_count":
            return None
        info = payload.get("info") or {}
        usage = info.get("last_token_usage")
        if not usage:
            return None

        input_t = int(usage.get("input_tokens", 0) or 0)
        output_t = int(usage.get("output_tokens", 0) or 0)
        cached_t = int(usage.get("cached_input_tokens", 0) or 0)
        reasoning_t = int(usage.get("reasoning_output_tokens", 0) or 0)

        if input_t == 0 and output_t == 0:
            return None

        model = (
            info.get("model")
            or usage.get("model")
            or event.get("model")
            or current_model
        )

        event_time_str = event.get("timestamp")
        event_time = (
            datetime.fromisoformat(event_time_str.replace("Z", "+00:00"))
            if event_time_str
            else datetime.now(timezone.utc)
        )

        cost = calc_cost(model, input_t, output_t, cached_t, self.model_aliases)

        return TokenUsage(
            event_time=event_time,
            session_id=session_id,
            model=model,
            input_tokens=input_t,
            output_tokens=output_t,
            cached_input_tokens=cached_t,
            reasoning_tokens=reasoning_t,
            estimated_cost_usd=cost,
            # raw_json 只写不读：不再序列化存储，避免每行写放大与 DB 无界膨胀。
            # session 源文件本身就是 raw 数据，需要重解析时直接读磁盘（见 _parse_version）。
            raw_json=None,
        )
