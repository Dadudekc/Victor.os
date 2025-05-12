# D:\TradingRobotPlug\basicbot\logger.py

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging(
    script_name: str,
    log_dir: Path = None,
    max_log_size: int = 5 * 1024 * 1024,  # 5MB limit
    backup_count: int = 3,
    console_log_level: int = logging.INFO,
    file_log_level: int = logging.DEBUG,
    feedback_loop_enabled: bool = False
) -> logging.Logger:
    """
    Sets up a unified logger for TradingRobotPlug.
    
    - Supports both file & console logging.
    - Auto-creates log directories if missing.
    - Prevents duplicate handlers by resetting them on each call.
    
    :param script_name: Name of the script (used in logs).
    :param log_dir: Directory to store logs (default: logs/Utilities relative to project root).
    :param max_log_size: Max file size before rotating logs (default: 5MB).
    :param backup_count: Number of old log files to retain (default: 3).
    :param console_log_level: Console logging level (default: INFO).
    :param file_log_level: File logging level (default: DEBUG).
    :param feedback_loop_enabled: Future AI-driven feedback logging (default: False).
    :return: Configured logging.Logger instance.
    """

    logger = logging.getLogger(script_name)
    logger.setLevel(logging.DEBUG)  # Capture all logs

    # Clear existing handlers to ensure a clean logger instance
    logger.handlers = []

    # Determine log directory; if not provided, use default relative to project root
    if log_dir is None:
        project_root = Path(__file__).resolve().parents[1]
        log_dir = project_root / 'logs' / 'Utilities'
    
    log_dir.mkdir(parents=True, exist_ok=True)

    # Build log file path
    log_file = log_dir / f"{script_name}.log"

    # Setup File Handler (RotatingFileHandler)
    try:
        file_handler = RotatingFileHandler(
            str(log_file),
            maxBytes=max_log_size,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(file_log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"❌ Error setting up file handler: {e}")

    # Setup Console Handler
    console_handler = logging.StreamHandler()
    # Tag this handler as the console handler so tests can easily find it
    console_handler.name = "console_handler"
    console_handler.setLevel(console_log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if feedback_loop_enabled:
        logger.debug(f"[{script_name}] 🔄 AI Feedback Loop Enabled.")
    
    return logger

# Example Usage
if __name__ == "__main__":
    logger = setup_logging("test_logger")
    logger.info("✅ Logging system initialized successfully!")
