import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

_LOGGER_INITIALIZED = False

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _kv_formatter() -> logging.Formatter:
    fmt = "ts=%(asctime)s level=%(levelname)s module=%(name)s msg=%(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    return logging.Formatter(fmt=fmt, datefmt=datefmt)

def init_logging(runtime_dir: Optional[str] = None, level: Optional[int] = None) -> None:
    """
    Initialize logging system:
    - Reads logs_dir and level from config/settings.yaml if not provided
    - Sets up console and daily rotating file handlers
    """
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED:
        return

    # Load settings from config/settings.yaml if available
    try:
        import yaml
        from pathlib import Path
        settings_path = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
        with open(settings_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        paths_cfg = cfg.get("paths", {})
        log_cfg = cfg.get("logging", {})
    except Exception:
        paths_cfg = {}
        log_cfg = {}

    runtime_dir = runtime_dir or paths_cfg.get("logs_dir", "runtime/logs")
    level = level or getattr(logging, str(log_cfg.get("level", "INFO")).upper(), logging.INFO)

    _ensure_dir(runtime_dir)

    logger = logging.getLogger()
    logger.setLevel(level)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(_kv_formatter())
    logger.addHandler(ch)

    # File handler - daily rotation, keep 7 days
    fh = TimedRotatingFileHandler(
        filename=os.path.join(runtime_dir, "app.log"),
        when="D",
        interval=1,
        backupCount=7,
        encoding="utf-8",
        utc=False,
    )
    fh.setLevel(level)
    fh.setFormatter(_kv_formatter())
    logger.addHandler(fh)

    _LOGGER_INITIALIZED = True

def get_logger(name: Optional[str] = None) -> logging.Logger:
    if not _LOGGER_INITIALIZED:
        init_logging()
    return logging.getLogger(name)