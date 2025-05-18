"""
Logging configuration for social media integrations.
"""

import os
import logging
from pathlib import Path

def setup_logging(name, log_dir=None, level=None):
    """
    Configure a logger with the specified name.
    
    Args:
        name: Logger name
        log_dir: Directory to store log files (optional)
        level: Logging level (default: INFO)
        
    Returns:
        Configured logger instance
    """
    # Set default level
    level = level or os.getenv("LOG_LEVEL", "INFO")
    level_num = getattr(logging, level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(f"dreamos.integrations.social.{name}")
    logger.setLevel(level_num)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level_num)
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    
    # Add console handler
    logger.addHandler(console_handler)
    
    # Add file handler if log_dir is specified
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_dir / f"{name}.log")
        file_handler.setLevel(level_num)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

if __name__ == "__main__":
    # Example usage
    test_logger = setup_logging(
        "test_logger",
        log_dir="logs/test",
        level=logging.DEBUG
    )
    
    test_logger.debug("This is a debug message")
    test_logger.info("This is an info message")
    test_logger.warning("This is a warning message")
    test_logger.error("This is an error message")
    test_logger.critical("This is a critical message")
