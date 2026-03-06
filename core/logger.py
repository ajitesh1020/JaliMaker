# -*- coding: utf-8 -*-
"""Centralised logging setup for JaliMaker."""

import logging
import sys
from pathlib import Path
from datetime import datetime

LOG_DIR = Path(__file__).parent.parent / "logs"


def setup_logger(dev_mode: bool = False) -> logging.Logger:
    """
    Configure root logger.
    Dev mode → DEBUG to console + file.
    Production → INFO to file only.
    """
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"jalimaker_{datetime.now().strftime('%Y%m%d')}.log"

    level = logging.DEBUG if dev_mode else logging.INFO
    fmt = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    handlers = [logging.FileHandler(log_file, encoding="utf-8")]
    if dev_mode:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(level=level, format=fmt, datefmt=date_fmt, handlers=handlers)

    logger = logging.getLogger("JaliMaker")
    logger.info(f"Logging initialised → {log_file}  (dev_mode={dev_mode})")
    return logger
