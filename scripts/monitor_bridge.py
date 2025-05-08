#!/usr/bin/env python3
# scripts/monitor_bridge.py
"""Script to perform a single check of the Cursor Bridge components and log status."""
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add src to path to allow importing dreamos
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
SRC_DIR = SCRIPT_DIR / "src"
LOG_DIR = SCRIPT_DIR / "runtime" / "bridge"
LOG_FILE = LOG_DIR / "bridge_status.log"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from dreamos.tools.cursor_bridge import cursor_bridge
    from dreamos.core.config import AppConfig # Assuming base config loading is sufficient
except ImportError as e:
    print(f"Error importing DreamOS components: {e}. Ensure PYTHONPATH or script location is correct.", file=sys.stderr)
    sys.exit(1)

def setup_logging():
    """Sets up logging to file and console."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # File handler
    file_handler = logging.FileHandler(LOG_FILE, mode='a') # Append mode
    file_handler.setFormatter(log_formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    return root_logger

def run_bridge_check(logger):
    """Performs checks on bridge components."""
    logger.info("--- Starting Bridge Status Check ---")
    status = "OK"
    issues = []

    # 1. Check if Cursor window can be found
    try:
        logger.info(f"Checking for Cursor window (Title: {cursor_bridge.CURSOR_WINDOW_TITLE_SUBSTRING})...")
        window = cursor_bridge.find_and_focus_cursor_window()
        if window:
            logger.info(f"Cursor window found and focused: {window.title}")
        else:
            # Note: find_and_focus raises error if not found, so this else might not be reached
            status = "WARN"
            issues.append("Cursor window found but focus failed (unexpected state).")
            logger.warning("Cursor window found but find_and_focus did not raise error and returned None.")
    except cursor_bridge.CursorInjectError as e:
        status = "ERROR"
        issues.append(f"Finding/Focusing Cursor window failed: {e}")
        logger.error(f"Finding/Focusing Cursor window failed: {e}")
    except Exception as e:
        status = "ERROR"
        issues.append(f"Unexpected error during window check: {e}")
        logger.error(f"Unexpected error during window check: {e}", exc_info=True)

    # 2. Check OCR capability (if available)
    if cursor_bridge.PYTESSERACT_AVAILABLE:
        logger.info("Checking Tesseract OCR availability...")
        try:
            # Attempt a simple version check or use dummy image if possible
            # This is a proxy check; actual OCR depends on image quality
            # TODO: Implement a more robust check, maybe OCR a known small image?
            logger.info(f"Pytesseract library is available.") # Basic check
            # Potentially check tesseract command path from config here
            # conf = AppConfig.load() # Load config if needed for path
            # t_path = cursor_bridge.get_config("tools.tesseract.cmd_path", config_obj=conf)
            # logger.info(f"Configured Tesseract path: {t_path}")
        except ImportError:
             status = "ERROR"
             issues.append("Pytesseract import failed despite initial check.")
             logger.error("Pytesseract check failed unexpectedly after initial import success.")
        except Exception as e:
            status = "WARN"
            issues.append(f"Potential issue during OCR check: {e}")
            logger.warning(f"Potential issue during OCR check: {e}", exc_info=True)
    else:
        status = "WARN"
        issues.append("Pytesseract (OCR engine) is not installed or importable.")
        logger.warning("OCR support is unavailable (Pytesseract not found).")

    # 3. Log overall status
    final_message = f"Bridge Status: {status}. Issues: {'; '.join(issues) if issues else 'None'}"
    if status == "ERROR":
        logger.error(final_message)
    elif status == "WARN":
        logger.warning(final_message)
    else:
        logger.info(final_message)

    logger.info("--- Bridge Status Check Complete ---")
    return status

if __name__ == "__main__":
    logger = setup_logging()
    check_status = run_bridge_check(logger)
    # Exit code reflects status (0=OK, 1=WARN, 2=ERROR)
    if check_status == "ERROR":
        sys.exit(2)
    elif check_status == "WARN":
        sys.exit(1)
    else:
        sys.exit(0) 