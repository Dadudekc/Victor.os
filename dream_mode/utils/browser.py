# dream_mode/utils/browser.py

import time
import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import json
from pathlib import Path
import sys, os
from typing import Optional

# ---------------------------
# Import UnifiedDriverManager from Digital Dreamscape project
# ---------------------------
dds_src = Path(__file__).parent.parent.parent / "social" / "digital_dreamscape" / "dreamscape_generator" / "src"
if str(dds_src) not in sys.path:
    sys.path.insert(0, str(dds_src))
from core.UnifiedDriverManager import UnifiedDriverManager

logger = logging.getLogger("BrowserUtils")
_manager: Optional[UnifiedDriverManager] = None

def launch_browser(headless=False):
    """Launch or return a browser driver via UnifiedDriverManager."""
    global _manager
    if _manager is None or _manager.headless != headless:
        _manager = UnifiedDriverManager(headless=headless)
    return _manager.get_driver()

def navigate_to_page(url):
    driver = launch_browser()
    if driver:
        logger.info(f"🌍 Navigating to {url}")
        try:
            driver.get(url)
            time.sleep(5)
        except Exception as e:
            logger.error(f"❌ Failed to navigate to {url}: {e}", exc_info=True)

def wait_for_login(timeout_seconds=180):
    """Delegate login verification to UnifiedDriverManager."""
    global _manager
    if _manager is None:
        logger.error("Browser manager not initialized, cannot wait for login.")
        return False
    # Use UnifiedDriverManager's is_logged_in logic
    return _manager.is_logged_in(retries=int(timeout_seconds / _manager.wait_timeout))

def close_browser():
    """Quit the browser via UnifiedDriverManager."""
    global _manager
    if _manager:
        _manager.quit_driver()
        _manager = None 