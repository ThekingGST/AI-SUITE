from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from config import DATA_DIR, ensure_directories


def setup_logging() -> logging.Logger:
    ensure_directories()
    logger = logging.getLogger("jarvis")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        DATA_DIR / "jarvis.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


LOGGER = setup_logging()
