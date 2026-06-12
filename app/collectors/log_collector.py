from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.collectors.base import Collector
from app.models import TokenUsage

logger = logging.getLogger("codex_usage_monitor")

MODEL_PRICING = {
    "gpt-5.5":      {"input": 5.00,   "output": 30.00,  "cached_input": 0.50},
    "gpt-5.4":      {"input": 2.50,   "output": 15.00,  "cached_input": 0.25},
    "gpt-5.4-mini": {"input": 0.75,   "output": 4.50,   "cached_input": 0.075},
}


def calc_cost(model: str, input_t: int, output_t: int, cached_t: int, model_aliases: dict[str, str] | None = None) -> float:
    resolved = (model_aliases or {}).get(model, model)
    pricing = MODEL_PRICING.get(resolved)
    if pricing is None:
        logger.warning("No pricing for model %s (resolved=%s) — set model_aliases in config", model, resolved)
        return 0.0
    uncached_t = max(0, input_t - cached_t)
    return (
        uncached_t / 1_000_000 * pricing["input"]
        + output_t / 1_000_000 * pricing["output"]
        + cached_t / 1_000_000 * pricing["cached_input"]
    )


class SessionCollector(Collector):
    def __init__(self, sessions_dir: str | Path, default_model: str = "gpt-4o", model_aliases: dict[str, str] | None = None):
        self.sessions_dir = Path(sessions_dir)
        self.default_model = default_model
        self.model_aliases = model_aliases or {}

    async def collect(self) -> list[TokenUsage]:
        results: list[TokenUsage] = []
        if not self.sessions_dir.is_dir():
            logger.warning("Sessions dir not found: %s", self.sessions_dir)
            return results

        files = sorted(self.sessions_dir.rglob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
        for jsonl_file in files:
            try:
                parsed = self._parse_file(jsonl_file)
                results.extend(parsed)
            except Exception as e:
                logger.error("Failed to parse %s: %s", jsonl_file.name, e)

        logger.info("Collected %d token usage entries from %d session files", len(results), len(files))
        return results

    def _parse_file(self, path: Path) -> list[TokenUsage]:
        entries: list[TokenUsage] = []
        session_id = self._extract_session_id(path)
        current_model = self.default_model

        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Track model from response_item / turn_context events
            event_model = self._extract_event_model(event)
            if event_model:
                current_model = event_model

            token_usage = self._extract_token_usage(event, session_id, current_model)
            if token_usage:
                entries.append(token_usage)

        return entries

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
            cm = payload.get("collaboration_mode") or {}
            settings = cm.get("settings") or {}
            model = settings.get("model")
            if model:
                return model
        return None

    @staticmethod
    def _extract_session_id(path: Path) -> str:
        try:
            text = path.read_text(encoding="utf-8")
            first_line = text.splitlines()[0].strip()
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
            raw_json=json.dumps(event, ensure_ascii=False),
        )
