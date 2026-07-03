from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.collectors.log_collector import SessionCollector
from app.config import load_config
from app.logging_config import setup_logging
from app.storage.db import get_connection
from app.storage.migrations import run_migrations
from app.storage.repository import Repository

logger = logging.getLogger("codex_usage_monitor")


async def main():
    config = load_config()
    setup_logging(config.paths.log_dir)

    collector = SessionCollector(config.paths.sessions_dir, default_model=config.app.default_model, model_aliases=config.app.model_aliases)
    entries = await collector.collect()

    conn = get_connection(config.paths.db_path)
    run_migrations(conn)
    repo = Repository(conn)

    count = repo.insert_token_usage_batch(entries)

    total_tokens = sum(
        e.input_tokens + e.output_tokens + e.cached_input_tokens + e.reasoning_tokens
        for e in entries
    )
    total_cost = sum(e.estimated_cost_usd or 0 for e in entries)

    print(f"Parsed {len(entries)} token usage entries, {count} new")
    print(f"Total tokens: {total_tokens:,}")
    print(f"Estimated cost: ${total_cost:.6f}")
    if entries:
        models = set(e.model for e in entries)
        print(f"Models: {', '.join(sorted(models))}")
        sessions = set(e.session_id for e in entries)
        print(f"Sessions: {len(sessions)}")


if __name__ == "__main__":
    asyncio.run(main())
