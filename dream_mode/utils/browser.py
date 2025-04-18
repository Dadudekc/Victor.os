# dream_mode/utils/browser.py

import time
import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

logger = logging.getLogger("BrowserUtils")
_driver = None

def launch_browser(headless=False):
    """Launch or return a singleton undetected Chrome driver."""
    global _driver
    if _driver is not None:
        try:
            _ = _driver.window_handles
            logger.debug("Browser already running.")
            return _driver
        except Exception:
            logger.warning("Browser was not reachable, relaunching.")
            _driver = None

    options = uc.ChromeOptions()
    # Temporarily disable headless mode for debugging
    # if headless:
    #     options.add_argument("--headless")
    #     options.add_argument("--disable-gpu")
    #     options.add_argument("--window-size=1920,1080")
    headless = False # Force non-headless
    logger.info("Browser launching in NON-HEADLESS mode for debugging.") # Add log

    try:
        logger.info("🚀 Launching new browser instance...")
        _driver = uc.Chrome(options=options)
        logger.info("✅ Browser launched.")
        return _driver
    except Exception as e:
        logger.error(f"❌ Failed to launch browser: {e}", exc_info=True)
        _driver = None
        return None

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
    driver = launch_browser()
    if not driver:
        logger.error("Browser not available, cannot wait for login.")
        return False
        
    logger.info("⏳ Waiting for login confirmation...")
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        prompt_visible = False
        login_button_visible = False
        signup_button_visible = False

        try:
            driver.find_element(By.ID, "prompt-textarea")
            prompt_visible = True
            logger.debug("Found prompt textarea.")
        except NoSuchElementException:
            logger.debug("Prompt textarea not found.")
            prompt_visible = False
        except Exception as e:
            logger.warning(f"Error checking for prompt textarea: {e}")
            prompt_visible = False

        try:
            login_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Log in')]")
            login_button_visible = any(b.is_displayed() for b in login_buttons)
            if login_button_visible:
                logger.debug("Found 'Log in' button.")
        except Exception as e:
             logger.warning(f"Error checking for 'Log in' button: {e}")
             login_button_visible = True 

        try:
            signup_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Sign up')]")
            signup_button_visible = any(b.is_displayed() for b in signup_buttons)
            if signup_button_visible:
                logger.debug("Found 'Sign up' button.")
        except Exception as e:
             logger.warning(f"Error checking for 'Sign up' button: {e}")
             signup_button_visible = True

        if prompt_visible and not login_button_visible and not signup_button_visible:
            logger.info("✅ Login confirmed: Prompt visible, login/signup buttons absent.")
            return True
        elif login_button_visible or signup_button_visible:
            logger.info("Still seeing login/signup buttons, not logged in yet...")
        elif not prompt_visible:
             logger.info("Prompt textarea not visible, assuming not logged in or page loading...")
        
        logger.debug(f"Waiting... (Elapsed: {time.time() - start_time:.1f}s)")
        time.sleep(5)

    logger.error(f"❌ Login check timeout ({timeout_seconds}s) exceeded.")
    return False

def close_browser():
    global _driver
    if _driver:
        logger.info("🛑 Closing browser...")
        try:
            _driver.quit()
        except Exception as e:
             logger.error(f"Error closing browser: {e}", exc_info=True)
        finally:
            _driver = None 