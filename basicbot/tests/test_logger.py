"""
-- D:\\TradingRobotPlug\\basicbot\\tests\\test_logger.py --

Description:
------------
Unit tests for `logger.py`. Ensures logging is configured correctly, logs are created,
and log levels function as expected.

"""

import logging
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from basicbot.logger import setup_logging
import time


### ✅ TEST: Logger Setup ###
def test_logger_creation(tmp_path):
    """Ensure logger is created with correct handlers."""
    log_dir = tmp_path / "logs"
    logger = setup_logging("test_logger", log_dir=log_dir)

    assert isinstance(logger, logging.Logger)
    assert len(logger.handlers) == 2  # ✅ File + Console handlers exist

    # ✅ Check log file creation
    log_file = log_dir / "test_logger.log"
    assert log_file.exists()


### ✅ TEST: Logging Levels ###
def test_logging_levels(tmp_path: Path):
    """Ensure log levels are correctly applied."""
    log_dir = tmp_path / "logs"
    # Set console_log_level to WARNING (30)
    logger = setup_logging("test_logger", log_dir=log_dir, console_log_level=logging.WARNING)

    # Filter for the console handler by its custom name
    console_handlers = [h for h in logger.handlers if getattr(h, "name", "") == "console_handler"]
    assert len(console_handlers) > 0, "❌ No console handler found!"

    console_handler = console_handlers[0]
    assert console_handler.level == logging.WARNING, f"❌ Expected WARNING (30), got {console_handler.level}"



### ✅ TEST: Avoid Duplicate Handlers ###
def test_avoid_duplicate_handlers(tmp_path):
    """Ensure logger does not add duplicate handlers on multiple calls."""
    log_dir = tmp_path / "logs"
    logger1 = setup_logging("test_logger", log_dir=log_dir)
    logger2 = setup_logging("test_logger", log_dir=log_dir)  # Reinitialize

    assert len(logger1.handlers) == 2  # ✅ Still only 2 handlers
    assert len(logger2.handlers) == 2  # ✅ No extra handlers



def test_log_file_writing(tmp_path):
    """Ensure log messages are written to the log file."""
    log_dir = tmp_path / "logs"
    logger = setup_logging("test_logger", log_dir=log_dir)

    log_message = "✅ Test log entry"
    logger.info(log_message)

    log_file = log_dir / "test_logger.log"

    time.sleep(0.1)  # ✅ Allow time for file writes

    assert log_file.exists(), f"❌ Log file {log_file} was not created."

    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read()

    assert log_message in log_content, "❌ Log message not found in file."

    """Ensure log messages are written to the log file."""
    log_dir = tmp_path / "logs"
    logger = setup_logging("test_logger", log_dir=log_dir)

    log_message = "✅ Test log entry"
    logger.info(log_message)

    log_file = log_dir / "test_logger.log"

    # ✅ Ensure the log file is created
    assert log_file.exists(), f"❌ Log file {log_file} was not created."

    # ✅ Read and verify log content
    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read()
    
    assert log_message in log_content, "❌ Log message not found in file."



def test_feedback_loop_enabled(tmp_path):
    """Ensure AI feedback loop logs when enabled (placeholder for future)."""
    log_dir = tmp_path / "logs"
    logger = setup_logging("test_logger", log_dir=log_dir, feedback_loop_enabled=True)

    log_message = "[test_logger] 🔄 AI Feedback Loop Enabled."
    log_file = log_dir / "test_logger.log"

    time.sleep(0.1)  # ✅ Allow time for file writes

    assert log_file.exists(), f"❌ Log file {log_file} was not created."

    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read()

    assert log_message in log_content, "❌ AI feedback loop message not found in log file."
