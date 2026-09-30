"""
Guardian Drive AI - Logging Configuration
Structured rotating file logs with console output.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

_LOG_DIR = Path("logs")
_LOG_FILE = _LOG_DIR / "guardian.log"
_FORMATTER = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)


def setup_logging(level: str = "INFO", debug: bool = False) -> None:
    """Call once at startup to configure root logger."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else getattr(logging, level.upper(), logging.INFO))

    # Rotating file handler — max 5 MB × 3 files
    fh = logging.handlers.RotatingFileHandler(
        _LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(_FORMATTER)
    root.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(_FORMATTER)
    ch.setLevel(logging.DEBUG if debug else logging.INFO)
    root.addHandler(ch)

    # Suppress noisy third-party loggers
    for noisy in ("mediapipe", "absl"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
