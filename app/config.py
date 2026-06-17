from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import tomli_w

APP_NAME = "CodexUsageMonitor"
DEFAULT_CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home() / ".config")) / APP_NAME
DEFAULT_SESSIONS_DIR = Path.home() / ".codex" / "sessions"


@dataclass
class AppConfig:
    poll_interval_seconds: int = 600
    quota_interval_minutes: int = 10
    host: str = "127.0.0.1"
    port: int = 8765
    default_model: str = "gpt-4o"
    model_aliases: dict[str, str] = field(default_factory=lambda: {"codex-auto-review": "gpt-5.4"})


@dataclass
class PathsConfig:
    data_dir: str = str(DEFAULT_CONFIG_DIR)
    db_path: str = str(DEFAULT_CONFIG_DIR / "usage.sqlite")
    sessions_dir: str = str(DEFAULT_SESSIONS_DIR)
    log_dir: str = str(DEFAULT_CONFIG_DIR / "logs")


@dataclass
class Config:
    app: AppConfig = field(default_factory=AppConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)


def load_config(config_path: Path | None = None) -> Config:
    if config_path is None:
        config_path = DEFAULT_CONFIG_DIR / "config.toml"

    cfg = Config()

    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        if "app" in data:
            app_data = dict(data["app"])
            # 向后兼容：旧字段 poll_interval_minutes 转成秒
            if "poll_interval_minutes" in app_data and "poll_interval_seconds" not in app_data:
                try:
                    app_data["poll_interval_seconds"] = int(app_data["poll_interval_minutes"]) * 60
                except (TypeError, ValueError):
                    pass
                app_data.pop("poll_interval_minutes", None)
            for k, v in app_data.items():
                if hasattr(cfg.app, k):
                    setattr(cfg.app, k, v)
        if "paths" in data:
            for k, v in data["paths"].items():
                if hasattr(cfg.paths, k):
                    setattr(cfg.paths, k, v)

    return cfg


def save_config(cfg: Config, config_path: Path | None = None) -> None:
    if config_path is None:
        config_path = DEFAULT_CONFIG_DIR / "config.toml"

    config_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "app": {"poll_interval_seconds": cfg.app.poll_interval_seconds, "quota_interval_minutes": cfg.app.quota_interval_minutes, "host": cfg.app.host, "port": cfg.app.port, "default_model": cfg.app.default_model, "model_aliases": cfg.app.model_aliases},
        "paths": {
            "data_dir": cfg.paths.data_dir,
            "db_path": cfg.paths.db_path,
            "sessions_dir": cfg.paths.sessions_dir,
            "log_dir": cfg.paths.log_dir,
        },
    }

    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)
