"""Logging utilities for Dream.OS."""

import logging
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: str = "INFO",
    format_str: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
) -> logging.Logger:
    """Set up logger with file and console handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Create formatters and add it to the handlers
    formatter = logging.Formatter(format_str)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Create file handler if log_file is provided
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
