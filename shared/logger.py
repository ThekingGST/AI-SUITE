"""Unified structured logger for the AI Suite ecosystem.

Every application (JARVIS, FRIDAY, EDITH) should use this logger to ensure
consistent formatting and centralized log management.

Usage::

    from shared.logger import get_logger
    log = get_logger("friday")
    log.info("Application started")
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from shared.config import ConfigManager
from shared.config.deployment import DeploymentMode


_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_INITIALIZED: dict[str, logging.Logger] = {}


def get_logger(
    name: str,
    *,
    log_dir: Path | None = None,
    level: int = logging.INFO,
    max_bytes: int = 2 * 1024 * 1024,
    backup_count: int = 3,
) -> logging.Logger:
    """Get or create a named logger with console and optional file output.

    Parameters
    ----------
    name:
        Logger name (e.g. ``"friday"``, ``"jarvis"``).
    log_dir:
        Directory for log files.  When *None*, only console output is used.
    level:
        Minimum logging level.
    max_bytes:
        Maximum log file size before rotation.
    backup_count:
        Number of rotated log files to keep.

    Returns
    -------
    logging.Logger
        Configured logger instance.  Subsequent calls with the same *name*
        return the cached logger.
    """
    if name in _INITIALIZED:
        return _INITIALIZED[name]
        
    if log_dir is None:
        log_dir = ConfigManager.LOG_DIR

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler - suppress in packaged mode
    if ConfigManager.mode != DeploymentMode.PACKAGED:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        logger.addHandler(console)

    # File handler — only when a log directory is provided.
    if log_dir is not None:
        from logging.handlers import RotatingFileHandler

        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / f"{name}.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _INITIALIZED[name] = logger
    return logger
