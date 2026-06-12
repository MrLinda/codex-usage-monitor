from __future__ import annotations

import asyncio
import logging

import uvicorn

from app.config import load_config
from app.logging_config import setup_logging
from app.scheduler.poller import Poller

logger = logging.getLogger("codex_usage_monitor")


async def main():
    config = load_config()
    setup_logging(config.paths.log_dir)

    poller = Poller(config)

    logger.info("Starting Codex Usage Monitor v0.1.0")
    logger.info("Dashboard: http://%s:%d", config.app.host, config.app.port)

    async def run_server():
        config_obj = uvicorn.Config(
            "app.server.api:app",
            host=config.app.host,
            port=config.app.port,
            log_level="info",
        )
        server = uvicorn.Server(config_obj)
        await server.serve()

    await asyncio.gather(run_server(), poller.poll_loop())


if __name__ == "__main__":
    asyncio.run(main())
