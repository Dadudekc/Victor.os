import logging
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# Assuming config might be needed for logging levels etc.
from dreamscape_generator import config as project_config

logger = logging.getLogger(__name__)
logger.setLevel(project_config.LOG_LEVEL)

# --- Define path for manually downloaded driver ---
# Assumes chromedriver.exe is placed in the workspace root
# Adjust this path if you place it elsewhere (e.g., 'drivers/chromedriver.exe')
MANUAL_DRIVER_PATH = "chromedriver.exe"
# --------------------------------------------------

class StubUnifiedDriverManager:
    """Basic placeholder for UnifiedDriverManager using Selenium ChromeDriver."""
    def __init__(self, options: dict = None):
        self._driver = None
        self.options = options or {}
        logger.info("Initialized StubUnifiedDriverManager")

    def get_driver(self):
        if self._driver is None:
            try:
                chrome_options = webdriver.ChromeOptions()
                headless_option = self.options.get("headless", False)
                logger.info(f"[DEBUG] Headless option received by get_driver: {headless_option}")
                if headless_option:
                    chrome_options.add_argument("--headless")
                    chrome_options.add_argument("--disable-gpu") # Often needed for headless
                    logger.info("Configuring WebDriver in headless mode.")
                # Add other options from self.options if needed
                chrome_options.add_argument("--log-level=3") # Suppress console noise

                # --- Use manual path if available --- 
                if os.path.exists(MANUAL_DRIVER_PATH):
                    logger.info(f"Using manually specified chromedriver: {os.path.abspath(MANUAL_DRIVER_PATH)}")
                    service = ChromeService(executable_path=MANUAL_DRIVER_PATH)
                else:
                    # Fallback to webdriver-manager (which is currently broken)
                    logger.warning(f"Manual chromedriver not found at '{MANUAL_DRIVER_PATH}'. Falling back to webdriver-manager (may fail).")
                    service = ChromeService(ChromeDriverManager().install())
                # -------------------------------------

                self._driver = webdriver.Chrome(
                    service=service,
                    options=chrome_options
                )
                logger.info("WebDriver initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize WebDriver: {e}", exc_info=True)
                raise
        return self._driver

    def quit(self):
        if self._driver:
            try:
                self._driver.quit()
                self._driver = None
                logger.info("WebDriver quit successfully.")
            except Exception as e:
                logger.error(f"Error quitting WebDriver: {e}", exc_info=True)

__all__ = ["StubUnifiedDriverManager"] 