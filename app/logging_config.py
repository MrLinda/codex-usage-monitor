from __future__ import annotations

import logging
import re
from pathlib import Path

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def redact_email(text: str) -> str:
    return EMAIL_RE.sub("***@***", text)


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        return redact_email(msg)


def setup_logging(log_dir: str | Path, level: int = logging.INFO) -> None:
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("codex_usage_monitor")
    logger.setLevel(level)

    fh = logging.FileHandler(log_path / "monitor.log", encoding="utf-8")
    fh.setFormatter(RedactingFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(RedactingFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(ch)
