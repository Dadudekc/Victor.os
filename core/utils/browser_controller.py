# utils/browser_controller.py

import logging
import os
from typing import Optional

import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By

class BrowserController:
    """Provides a shared, potentially stealthy browser interface using undetected_chromedriver."""

    DEFAULT_WAIT_TIMEOUT_SECONDS = 10

    def __init__(self, 
                 headless: bool = True, 
                 user_agent: Optional[str] = None, 
                 user_data_dir: Optional[str] = None, 
                 chrome_version: Optional[int] = None):
        """
        Initializes the BrowserController.

        Args:
            headless (bool): Run in headless mode. Defaults to True.
            user_agent (Optional[str]): Custom user agent string. Defaults to None.
            user_data_dir (Optional[str]): Path to Chrome user data directory. Defaults to None.
            chrome_version (Optional[int]): Specific Chrome major version. Defaults to None (auto-detect).
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.headless = headless
        self.user_agent = user_agent
        self.user_data_dir = user_data_dir
        self.chrome_version = chrome_version
        self.driver: Optional[uc.Chrome] = None
        self._setup_browser()

    def _setup_browser(self):
        options = uc.ChromeOptions()
        
        # Stealth options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # Standard options
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage") # Often needed in containers

        if self.headless:
            options.add_argument("--headless=new") # Modern headless
            options.add_argument("--disable-gpu") # Often needed for headless

        if self.user_agent:
            options.add_argument(f"user-agent={self.user_agent}")

        if self.user_data_dir:
            abs_user_data_dir = os.path.abspath(self.user_data_dir)
            self.logger.info(f"Using user data directory: {abs_user_data_dir}")
            options.add_argument(f"--user-data-dir={abs_user_data_dir}")
            # Optional: Specify profile directory within user_data_dir if needed
            # options.add_argument('--profile-directory=Default') 

        try:
            log_details = {"step": "Initializing undetected ChromeDriver"}
            if self.chrome_version:
                log_details["chrome_version_target"] = self.chrome_version
            else:
                log_details["chrome_version_target"] = "Auto-detect"
            self.logger.info(f"{log_details['step']} (Target: {log_details['chrome_version_target']})")
            
            # Initialize uc.Chrome, specifying version if provided
            self.driver = uc.Chrome(options=options, version_main=self.chrome_version) 
            
            # Additional step after driver init to prevent detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info("Undetected ChromeDriver initialized successfully.")
            
        except WebDriverException as wde:
            error_msg = f"WebDriverException initializing ChromeDriver: {wde.msg}"
            self.logger.error(
                f"{error_msg} - Check Chrome/ChromeDriver compatibility (Target: {self.chrome_version or 'Auto'}).", 
                exc_info=True
            )
            if self.driver:
                try: self.driver.quit() 
                except Exception: pass
                self.driver = None
            raise # Re-raise the exception after logging
        except Exception as e:
            self.logger.error(f"Unexpected error initializing ChromeDriver: {e}", exc_info=True)
            if self.driver:
                try: self.driver.quit() 
                except Exception: pass
                self.driver = None
            raise # Re-raise the exception

    def get(self, url: str):
        """Navigate to the specified URL."""
        if not self.driver:
            self.logger.error("Browser driver not initialized. Cannot navigate.")
            raise RuntimeError("Browser driver not initialized.")
        self.logger.info(f"Navigating to: {url}")
        self.driver.get(url)

    def find_element(self, by: By, value: str, timeout: int = DEFAULT_WAIT_TIMEOUT_SECONDS):
        """Find a single element, waiting up to the timeout."""
        if not self.driver:
             self.logger.error("Browser driver not initialized. Cannot find element.")
             raise RuntimeError("Browser driver not initialized.")
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            self.logger.warning(f"Element not found or timed out for locator ({by}, {value}) after {timeout}s.")
            return None
        except NoSuchElementException: # Should be caught by TimeoutException, but good practice
             self.logger.warning(f"Element not found for locator ({by}, {value}).")
             return None
        except Exception as e:
            self.logger.error(f"Error finding element ({by}, {value}): {e}", exc_info=True)
            return None # Or re-raise depending on desired strictness

    def find_elements(self, by: By, value: str, timeout: int = DEFAULT_WAIT_TIMEOUT_SECONDS):
         """Find multiple elements, waiting up to the timeout for at least one to be present."""
         if not self.driver:
             self.logger.error("Browser driver not initialized. Cannot find elements.")
             raise RuntimeError("Browser driver not initialized.")
         try:
             # Wait for at least one element to be present before returning the list
             WebDriverWait(self.driver, timeout).until(
                 EC.presence_of_element_located((by, value)) 
             )
             # Then find all matching elements
             elements = self.driver.find_elements(by, value)
             return elements
         except TimeoutException:
             self.logger.warning(f"No elements found or timed out for locator ({by}, {value}) after {timeout}s.")
             return [] # Return empty list if none found
         except Exception as e:
            self.logger.error(f"Error finding elements ({by}, {value}): {e}", exc_info=True)
            return [] # Return empty list on other errors

    def wait_and_click(self, by: By, value: str, timeout: int = DEFAULT_WAIT_TIMEOUT_SECONDS) -> bool:
        """Waits for an element to be clickable and then clicks it."""
        if not self.driver:
            self.logger.error("Browser driver not initialized. Cannot click.")
            return False
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            element.click()
            self.logger.debug(f"Clicked element located by ({by}, {value})")
            return True
        except TimeoutException:
            self.logger.warning(f"Element not clickable or timed out for locator ({by}, {value}) after {timeout}s.")
            return False
        except Exception as e:
            self.logger.error(f"Error clicking element ({by}, {value}): {e}", exc_info=True)
            return False

    def wait_and_send_keys(self, by: By, value: str, text: str, clear_first: bool = True, timeout: int = DEFAULT_WAIT_TIMEOUT_SECONDS) -> bool:
        """Waits for an element to be visible, optionally clears it, and then sends keys."""
        if not self.driver:
             self.logger.error("Browser driver not initialized. Cannot send keys.")
             return False
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            if clear_first:
                element.clear()
            element.send_keys(text)
            self.logger.debug(f"Sent keys to element located by ({by}, {value})")
            return True
        except TimeoutException:
            self.logger.warning(f"Element not visible or timed out for locator ({by}, {value}) after {timeout}s.")
            return False
        except Exception as e:
            self.logger.error(f"Error sending keys to element ({by}, {value}): {e}", exc_info=True)
            return False

    def screenshot(self, path: str):
        """Capture a screenshot to the specified file path."""
        if self.driver:
            try:
                self.driver.save_screenshot(path)
                self.logger.info(f"Screenshot saved to {path}")
            except Exception as e:
                 self.logger.error(f"Failed to save screenshot to {path}: {e}", exc_info=True)
        else:
             self.logger.error("Browser driver not initialized. Cannot take screenshot.")

    def get_current_url(self) -> Optional[str]:
        """Returns the current URL of the browser."""
        if self.driver:
            try:
                return self.driver.current_url
            except Exception as e:
                self.logger.error(f"Failed to get current URL: {e}", exc_info=True)
                return None
        else:
            self.logger.warning("Browser driver not initialized. Cannot get URL.")
            return None

    def get_page_source(self) -> Optional[str]:
         """Returns the full HTML source of the current page."""
         if self.driver:
             try:
                 return self.driver.page_source
             except Exception as e:
                 self.logger.error(f"Failed to get page source: {e}", exc_info=True)
                 return None
         else:
             self.logger.warning("Browser driver not initialized. Cannot get page source.")
             return None

    def quit(self):
        """Cleanly shut down the browser."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Browser session terminated.")
            except Exception as e:
                self.logger.error(f"Error during browser quit: {e}", exc_info=True)
            finally:
                 self.driver = None # Ensure driver is set to None even if quit fails

    def __del__(self):
        # Ensure browser is closed when the object is garbage collected
        self.quit()
