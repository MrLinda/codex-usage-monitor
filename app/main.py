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

_UVICORN_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "logging.Formatter",
            "fmt": "%(asctime)s [%(name)s] %(levelname)s - %(message)s",
        },
        "access": {
            "()": "logging.Formatter",
            "fmt": '%(asctime)s [%(name)s] %(levelname)s - %(client_addr)s - "%(request_line)s" %(status_code)s',
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
    },
}


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
            log_config=_UVICORN_LOG_CONFIG,
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
    import signal

    poller = Poller(config)

    import app.server.api as api_module
    api_module._poller = poller

    async def run_server():
        config_obj = uvicorn.Config(
            "app.server.api:app",
            host=config.app.host,
            port=config.app.port,
            log_level="info",
            log_config=_UVICORN_LOG_CONFIG,
        )
        server = uvicorn.Server(config_obj)
        await server.serve()

    main_task = asyncio.ensure_future(asyncio.gather(run_server(), poller.poll_loop()))

    def _shutdown(signame):
        logger.info("Received signal %s, shutting down...", signame)
        poller.stop()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown, sig.name)
        except NotImplementedError:
            pass  # Windows doesn't support add_signal_handler

    try:
        await main_task
    except asyncio.CancelledError:
        pass
    finally:
        poller.stop()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
