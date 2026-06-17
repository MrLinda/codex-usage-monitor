from __future__ import annotations

import asyncio
import logging
import sys
import threading

import uvicorn

from app.config import load_config
from app.logging_config import setup_logging
from app.scheduler.poller import Poller

logger = logging.getLogger("codex_usage_monitor")


def run_backend(config):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    poller = Poller(config)

    import app.server.api as api_module
    api_module._poller = poller

    async def run():
        config_obj = uvicorn.Config(
            "app.server.api:app",
            host=config.app.host,
            port=config.app.port,
            log_level="info",
        )
        server = uvicorn.Server(config_obj)
        await asyncio.gather(server.serve(), poller.poll_loop())

    loop.run_until_complete(run())


def main():
    config = load_config()
    setup_logging(config.paths.log_dir)

    logger.info("Starting Codex Usage Monitor v0.1.0")
    logger.info("Dashboard: http://%s:%d", config.app.host, config.app.port)

    if "--headless" in sys.argv:
        asyncio.run(_async_main(config))
    else:
        backend_thread = threading.Thread(target=run_backend, args=(config,), daemon=True)
        backend_thread.start()

        from app.gui import App
        app = App(config=config)
        app.run()


async def _async_main(config):
    poller = Poller(config)

    import app.server.api as api_module
    api_module._poller = poller

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
    main()
