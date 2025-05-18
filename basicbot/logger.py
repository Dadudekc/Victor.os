"""
logger.py - Centralized Logging Configuration

This module provides a consistent logging setup for all BasicBot components.
It configures console and file loggers with customizable formatting and levels.

Usage:
    from basicbot.logger import setup_logging
    logger = setup_logging('component_name')
    logger.info('This is an info message')
    logger.error('This is an error')
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Handle both package and standalone imports
try:
    from basicbot.config import config
except ImportError:
    # If running standalone, try to import from local path
    try:
        from config import config
    except ImportError:
        # Create a minimal config for standalone operation
        class MockConfig:
            LOG_LEVEL = 'INFO'
            LOG_DIR = 'logs'

        config = MockConfig()


def setup_logging(
    name: str,
    log_level: Optional[str] = None,
    log_dir: Optional[str] = None,
    console: bool = True,
    file: bool = True,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """
    Set up a logger with console and file handlers.
    
    Args:
        name: Name of the logger (used for logger instance and log file)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory where log files will be stored
        console: Enable console logging
        file: Enable file logging
        format_string: Custom log format string
        
    Returns:
        Configured logger instance
    """
    # Get settings from parameters or config
    log_level = log_level or config.LOG_LEVEL
    log_dir = log_dir or config.LOG_DIR
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Convert log level string to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Default format string
    if not format_string:
        format_string = (
            "%(asctime)s | %(levelname)-8s | %(name)-12s | "
            "%(filename)s:%(lineno)d | %(message)s"
        )
    
    formatter = logging.Formatter(format_string)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if file:
        # Create log directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Generate log filename with date
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = log_path / f"{name}_{today}.log"
        
        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Add a first message to the log
    logger.debug(f"Logger '{name}' initialized with level={log_level}")
    
    return logger


def get_all_loggers() -> Dict[str, logging.Logger]:
    """
    Get a dictionary of all active loggers.
    
    Returns:
        Dictionary mapping logger names to logger instances
    """
    return logging.root.manager.loggerDict


# For testing
if __name__ == "__main__":
    # Example usage
    logger = setup_logging(
        "test_logger",
        log_level="DEBUG",
        log_dir="logs",
        console=True,
        file=True
    )
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    # List all active loggers
    print("\nActive loggers:")
    for logger_name, logger_obj in get_all_loggers().items():
        if isinstance(logger_obj, logging.Logger):
            print(f"  {logger_name} (level={logging.getLevelName(logger_obj.level)})") 