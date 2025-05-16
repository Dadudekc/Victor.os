"""Logging utilities for Dream.os."""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    format_str: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) -> logging.Logger:
    """Set up logging configuration.
    Args:
        log_file: Optional path to log file
        level: Logging level
        format_str: Log message format string
    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger("dream_os")
    logger.setLevel(level)
    formatter = logging.Formatter(format_str)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger
