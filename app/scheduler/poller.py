from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.collectors.log_collector import SessionCollector
from app.collectors.quota_collector import QuotaCollector
from app.config import Config
from app.storage.db import get_connection
from app.storage.migrations import run_migrations
from app.storage.repository import Repository

logger = logging.getLogger("codex_usage_monitor")


class Poller:
    def __init__(self, config: Config):
        self.config = config
        self.session_collector = SessionCollector(config.paths.sessions_dir, default_model=config.app.default_model, model_aliases=config.app.model_aliases)
        self.quota_collector = QuotaCollector()
        conn = get_connection(config.paths.db_path)
        run_migrations(conn)
        self.repo = Repository(conn)
        self._running = False
        self.quota_interval_minutes = config.app.quota_interval_minutes

    async def collect_once(self) -> int:
        entries = await self.session_collector.collect()
        count = 0
        for entry in entries:
            existing = self.repo.get_token_usage(
                from_dt=entry.event_time, to_dt=entry.event_time, limit=1
            )
            if not existing:
                self.repo.insert_token_usage(entry)
                count += 1

        now = datetime.now(timezone.utc)
        if entries:
            total_tokens = sum(
                e.input_tokens + e.output_tokens + e.cached_input_tokens + e.reasoning_tokens
                for e in entries
            )
            total_cost = sum(e.estimated_cost_usd or 0 for e in entries)
            logger.info(
                "Collected %d new entries (%d tokens, $%.4f)",
                count, total_tokens, total_cost,
            )
            if count > 0:
                self.repo.insert_event(
                    now, "token_collected",
                    f"Collected {count} entries ({total_tokens} tokens, ${total_cost:.4f})",
                )
        else:
            logger.info("No new token usage entries found")

        return count

    async def collect_quota_once(self) -> None:
        sample = await self.quota_collector.collect()
        if sample is not None:
            self.repo.insert_quota_sample(sample)
            self.repo.insert_event(
                datetime.now(timezone.utc), "quota_collected",
                f"Quota collected: plan={sample.plan_type}, 5h remaining={sample.five_hour_remaining_pct}%",
            )

    async def poll_loop(self):
        self._running = True
        logger.info("Polling started (interval=%d sec, quota_interval=%d min)", self.config.app.poll_interval_seconds, self.quota_interval_minutes)
        self.repo.insert_event(datetime.now(timezone.utc), "monitor_started", "Polling started")
        # 首次延迟与 elapsed 都用当前 step；之后每轮重新读取 config，支持热更新
        step = min(self.config.app.poll_interval_seconds, self.quota_interval_minutes * 60)
        elapsed = step
        while self._running:
            await asyncio.sleep(step)
            elapsed += step
            try:
                await self.collect_once()
            except Exception as e:
                logger.error("Token poll cycle failed: %s", e)
                self.repo.insert_event(
                    datetime.now(timezone.utc), "token_error", str(e),
                )
            if elapsed >= self.quota_interval_minutes * 60:
                try:
                    await self.collect_quota_once()
                except Exception as e:
                    logger.error("Quota poll cycle failed: %s", e)
                    self.repo.insert_event(
                        datetime.now(timezone.utc), "quota_error", str(e),
                    )
                elapsed = 0
            # 每轮重算 step，让设置面板修改后的间隔尽快生效
            step = min(self.config.app.poll_interval_seconds, self.quota_interval_minutes * 60)

    def stop(self):
        self._running = False
