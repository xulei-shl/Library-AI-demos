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

def init_logging(runtime_dir: str = "runtime/logs", level: int = logging.INFO) -> None:
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED:
        return
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