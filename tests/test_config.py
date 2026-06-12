from __future__ import annotations

import tempfile
from pathlib import Path

from app.config import Config, load_config, save_config


def test_config_defaults():
    cfg = Config()
    assert cfg.app.poll_interval_minutes == 10
    assert cfg.app.host == "127.0.0.1"
    assert cfg.app.port == 8765
    assert "usage.sqlite" in cfg.paths.db_path
    assert cfg.paths.sessions_dir.endswith(".codex/sessions") or cfg.paths.sessions_dir.endswith(".codex\\sessions")
    assert "CodexUsageMonitor" in cfg.paths.log_dir


def test_save_and_load():
    cfg = Config()
    cfg.app.poll_interval_minutes = 5
    cfg.app.port = 9999

    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False, mode="w") as f:
        tmp_path = Path(f.name)

    try:
        save_config(cfg, tmp_path)
        loaded = load_config(tmp_path)
        assert loaded.app.poll_interval_minutes == 5
        assert loaded.app.port == 9999
        assert loaded.paths.sessions_dir == cfg.paths.sessions_dir
    finally:
        tmp_path.unlink(missing_ok=True)
