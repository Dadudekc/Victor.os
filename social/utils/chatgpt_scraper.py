"""
ChatGPT Web Scraper - Automated chat history extraction tool.
Uses undetected-chromedriver to avoid detection and provides robust session management.
"""
import os
import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException
)
import undetected_chromedriver as uc
from .common import retry_on_exception
from .selenium_utils import wait_for_element, safe_click, safe_send_keys
from pathlib import Path
import asyncio # Import asyncio if not already present, for potential async helpers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ChatGPTScraper')

# Constants
COOKIE_FILE = "chatgpt_cookies.json"
CHATGPT_URL = "https://chat.openai.com"
JQUERY_URL = "https://code.jquery.com/jquery-3.6.0.min.js"
WAIT_TIMEOUT = 30
LOGIN_BUTTON_SELECTOR = (By.CSS_SELECTOR, "button[data-testid='login-button']")
EMAIL_INPUT_SELECTOR = (By.ID, "email-input")
PASSWORD_INPUT_SELECTOR = (By.NAME, "password")
SUBMIT_BUTTON_SELECTOR = (By.XPATH, "//button[@type='submit' and contains(text(), 'Continue')]")
POST_LOGIN_ELEMENT_SELECTOR = (By.ID, "prompt-textarea")

class ChatGPTScraper:
    """Manages ChatGPT web scraping operations with session persistence."""
    
    def __init__(self,
                 cookie_file: str = COOKIE_FILE,
                 headless: bool = False,
                 username: Optional[str] = None,
                 password: Optional[str] = None):
        """
        Initialize the scraper with configuration.
        
        Args:
            cookie_file: Path to store/load cookies
            headless: Whether to run in headless mode
            username: Optional ChatGPT username/email for login
            password: Optional ChatGPT password for login
        """
        self.cookie_file = cookie_file
        self.headless = headless
        self.username = username
        self.password = password
        self.driver = None
        self.wait = None
        logger.info("Initializing ChatGPT Scraper")

    def __enter__(self):
        """Context manager entry."""
        self.setup_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
        if exc_type:
            logger.error(f"Error during execution: {exc_type.__name__}: {exc_val}")
            return False
        return True

    @retry_on_exception(max_attempts=3, exceptions=(WebDriverException,))
    def setup_browser(self) -> None:
        """Initialize and configure the browser with retry mechanism."""
        try:
            options = uc.ChromeOptions()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--start-maximized")

            logger.info("Attempting to initialize uc.Chrome...")
            print("DEBUG: Attempting to initialize uc.Chrome...")
            self.driver = uc.Chrome(options=options)
            print("DEBUG: uc.Chrome initialized successfully.")
            logger.info("uc.Chrome initialized.")

            self.wait = WebDriverWait(self.driver, WAIT_TIMEOUT)
            logger.info("Browser setup completed successfully")
        except WebDriverException as e:
            logger.error(f"Failed to setup browser: {str(e)}")
            print(f"ERROR in setup_browser: {type(e).__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during browser setup: {str(e)}", exc_info=True)
            print(f"UNEXPECTED ERROR in setup_browser: {type(e).__name__}: {e}")
            raise

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser cleanup completed")
            except WebDriverException as e:
                logger.error(f"Error during browser cleanup: {str(e)}")

    def save_cookies(self) -> bool:
        """
        Save current session cookies to file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.driver:
            logger.error("Cannot save cookies: WebDriver not initialized.")
            return False

        # Resolve the cookie file path relative to the current working directory
        try:
            cookie_path = Path(self.cookie_file).resolve()
            logger.info(f"Attempting to save cookies to resolved path: {cookie_path}") # <<< Log resolved path
        except Exception as e:
            logger.error(f"Failed to resolve cookie file path '{self.cookie_file}': {e}")
            return False

        try:
            cookies = self.driver.get_cookies()
            # Ensure parent directory exists
            cookie_path.parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {cookie_path.parent}") # <<< Log directory creation

            with open(cookie_path, "w") as f:
                json.dump(cookies, f)
            logger.info(f"Cookies saved successfully to {cookie_path}")
            return True
        except (IOError, WebDriverException, TypeError, OSError) as e: # Added OSError
            logger.error(f"Failed to save cookies to {cookie_path}: {type(e).__name__} - {str(e)}")
            return False

    def load_cookies(self) -> bool:
        """
        Load cookies from file to restore session.
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Resolve path for loading as well
        try:
            cookie_path = Path(self.cookie_file).resolve()
            logger.info(f"Attempting to load cookies from resolved path: {cookie_path}") # <<< Log resolved path
        except Exception as e:
            logger.error(f"Failed to resolve cookie file path '{self.cookie_file}': {e}")
            return False

        if not cookie_path.exists():
            logger.info(f"Cookie file not found at: {cookie_path}")
            return False

        try:
            with open(cookie_path, "r") as f:
                cookies = json.load(f)
            # Ensure driver is ready before adding cookies
            if not self.driver:
                logger.error("Cannot load cookies: WebDriver not initialized.")
                return False
            # Navigate to the domain before adding cookies is often required
            domain = ".openai.com" # Adjust domain if necessary
            current_url = self.driver.current_url
            if not domain in current_url:
                logger.info(f"Navigating to domain {domain} before loading cookies.")
                # Attempt to navigate to a relevant page on the domain
                self.driver.get(CHATGPT_URL) 
                time.sleep(2) # Wait for navigation

            for cookie in cookies:
                # Remove domain if present and incompatible, let browser handle it
                if 'domain' in cookie:
                    del cookie['domain']
                # Skip cookies that might cause issues
                if 'expiry' in cookie: 
                     cookie['expiry'] = int(cookie['expiry'])
                # Handle sameSite attribute if needed (already present)
                if "sameSite" in cookie and cookie["sameSite"] not in ["Strict", "Lax", "None"]:
                    logger.warning(f"Removing invalid sameSite value: {cookie['sameSite']}")
                    del cookie['sameSite']
                try:
                    self.driver.add_cookie(cookie)
                except Exception as cookie_error:
                     logger.warning(f"Could not add cookie: {cookie.get('name', 'N/A')} - {cookie_error}")

            logger.info("Cookies loaded successfully from {cookie_path}")
            return True
        except (IOError, WebDriverException, json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to load cookies from {cookie_path}: {type(e).__name__} - {str(e)}")
            return False

    @retry_on_exception(max_attempts=3, exceptions=(WebDriverException, NoSuchElementException, TimeoutException))
    def _perform_login(self) -> bool:
        """Performs automated login using provided credentials."""
        if not self.username or not self.password:
            logger.warning("Login credentials not provided.")
            return False

        logger.info(f"Attempting login for user: {self.username}")
        try:
            # 1. Navigate to login (Might already be there, or click initial 'Log in' button if present)
            # Example: Check if email field is visible, if not, click main login button
            email_field = wait_for_element(self.driver, EMAIL_INPUT_SELECTOR, timeout=5, visible=False)
            if not email_field:
                logger.debug("Email field not immediately visible, looking for main login button...")
                login_button = wait_for_element(self.driver, LOGIN_BUTTON_SELECTOR, timeout=10)
                if login_button:
                    if not safe_click(self.driver, LOGIN_BUTTON_SELECTOR, timeout=5):
                         logger.error("Failed to click initial login button.")
                         return False
                    # Wait briefly after click
                    time.sleep(2)
                else:
                     logger.warning("Could not find initial login button or email field.")
                     # Continue, maybe email field appears later

            # 2. Enter Email
            logger.debug("Entering email...")
            if not safe_send_keys(self.driver, EMAIL_INPUT_SELECTOR, self.username, timeout=15):
                logger.error("Failed to enter email.")
                return False
            time.sleep(0.5) # Brief pause

            # 3. Click Continue/Submit after email (Selector might vary)
            logger.debug("Clicking continue after email...")
            # Use a generic submit button selector or adjust SUBMIT_BUTTON_SELECTOR if needed
            if not safe_click(self.driver, (By.XPATH, "//button[@type='submit']"), timeout=10):
                 logger.warning("Failed to click continue after email (trying common submit).")
                 # Fallback if specific text isn't found
                 if not safe_click(self.driver, SUBMIT_BUTTON_SELECTOR, timeout=10):
                     logger.error("Failed to click continue button after email.")
                     return False
            time.sleep(2) # Wait for password field to appear

            # 4. Enter Password
            logger.debug("Entering password...")
            if not safe_send_keys(self.driver, PASSWORD_INPUT_SELECTOR, self.password, timeout=15):
                logger.error("Failed to enter password.")
                return False
            time.sleep(0.5)

            # 5. Click Final Login/Submit Button
            logger.debug("Clicking final login button...")
            # Use a generic submit button selector again
            if not safe_click(self.driver, (By.XPATH, "//button[@type='submit']"), timeout=10):
                 logger.warning("Failed to click final login button (trying common submit).")
                 # Fallback if specific text isn't found
                 if not safe_click(self.driver, SUBMIT_BUTTON_SELECTOR, timeout=10): # Assuming it might be the same button text
                      logger.error("Failed to click final login button.")
                      return False

            # 6. Wait for confirmation element
            logger.debug("Waiting for post-login element...")
            if wait_for_element(self.driver, POST_LOGIN_ELEMENT_SELECTOR, timeout=WAIT_TIMEOUT):
                logger.info(f"Successfully logged in as {self.username}")
                return True
            else:
                logger.error("Login failed: Post-login element not found.")
                return False

        except Exception as e:
            logger.error(f"Error during login attempt: {str(e)}", exc_info=True)
            return False

    # Make run_scraper async to properly await async helpers
    async def run_scraper(self, model_append: str = "", output_file: str = "chatgpt_chats.json") -> bool:
        """
        Main scraping workflow. Includes automated login attempt.

        Args:
            model_append: URL parameter to specify ChatGPT model
            output_file: Path to save captured chat data

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Use __enter__ to setup browser via context manager if not already done
            # Note: __enter__ itself should ideally be async if setup_browser becomes async
            # For now, assuming setup_browser remains synchronous or handles its own async tasks
            if not self.driver:
                # setup_browser might need to become async or use asyncio.run if it uses await
                await asyncio.to_thread(self.setup_browser)
                if not self.driver: # Check if setup failed
                    return False

            logger.info(f"Navigating to {CHATGPT_URL + model_append}")
            # Use asyncio.to_thread for potentially blocking Selenium calls
            await asyncio.to_thread(self.driver.get, CHATGPT_URL + model_append)
            logger.info("Navigated to ChatGPT")
            await asyncio.sleep(3) # Use asyncio sleep

            login_successful = False
            # Use asyncio.to_thread for blocking load_cookies call
            cookies_loaded = await asyncio.to_thread(self.load_cookies)
            if cookies_loaded:
                logger.info("Session restored using cookies.")
                await asyncio.to_thread(self.driver.refresh) # Refresh to apply cookies
                await asyncio.sleep(5)
                # Verify login state after loading cookies (wait_for_element is likely blocking)
                post_login_elem = await asyncio.to_thread(wait_for_element, self.driver, POST_LOGIN_ELEMENT_SELECTOR, timeout=10)
                if post_login_elem:
                    logger.info("Login verified after loading cookies.")
                    login_successful = True
                else:
                    logger.warning("Cookies loaded, but login state not verified. Clearing cookies.")
                    await asyncio.to_thread(self.driver.delete_all_cookies)

            if not login_successful:
                logger.info("Attempting login...")
                # _perform_login likely needs adaptation if helper functions become async
                # For now, assume it remains mostly synchronous internally or uses asyncio.to_thread
                # If _perform_login becomes async def, it needs to be awaited here.
                login_attempt_success = await asyncio.to_thread(self._perform_login)
                if login_attempt_success:
                    login_successful = True
                    await asyncio.sleep(3) # Wait a bit after login
                    await asyncio.to_thread(self.save_cookies)
                else:
                    logger.warning("Automated login failed or no credentials provided.")
                    logger.info("Please log in manually in the browser window (waiting 30s)...")
                    await asyncio.sleep(30)
                    post_login_elem = await asyncio.to_thread(wait_for_element, self.driver, POST_LOGIN_ELEMENT_SELECTOR, timeout=5)
                    if post_login_elem:
                        logger.info("Manual login detected.")
                        login_successful = True
                        await asyncio.to_thread(self.save_cookies)
                    else:
                        logger.error("Manual login timeout or failed.")
                        return False

            if not login_successful:
                logger.error("Failed to establish a logged-in session.")
                return False

            logger.info("Login successful, proceeding with scraping.")
            # *** Await the async scroll_and_capture_chats method ***
            chats_data = await self.scroll_and_capture_chats()

            if not chats_data:
                logger.error("No chats captured")
                # return False # Optional

            # Save data (synchronous file I/O is okay in thread)
            try:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                # Use await asyncio.to_thread for file writing if it blocks significantly
                def write_json(): 
                    with open(output_path, "w", encoding='utf-8') as f:
                        json.dump(chats_data, f, indent=2, ensure_ascii=False)
                await asyncio.to_thread(write_json)
                logger.info(f"Chat data saved to {output_file}")
                return True
            except (IOError, TypeError) as e:
                logger.error(f"Failed to save chat data: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Scraper run failed: {str(e)}", exc_info=True)
            return False
        finally:
            # Ensure cleanup happens, even if called from async context
            # cleanup itself should ideally be synchronous or handle its own blocking calls
            await asyncio.to_thread(self.cleanup)

    @retry_on_exception(max_attempts=3, exceptions=(WebDriverException, NoSuchElementException, TimeoutException))
    def scrape_single_chat(self, chat_url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a single chat conversation by navigating to its URL.

        Args:
            chat_url: URL of the specific chat conversation

        Returns:
            Dict[str, Any]: Dictionary containing chat title and messages, or None on failure
        """
        logger.info(f"Scraping chat: {chat_url}")
        try:
            self.driver.get(chat_url)
            # Wait for messages to load
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-message-id]')))
            time.sleep(2) # Allow dynamic content to settle

            # Extract title (if needed, might rely on previous scrape)
            title = self.driver.title # or extract from a specific element if available

            # Extract messages
            messages_data = self.driver.execute_script("""
                const messages = [];
                document.querySelectorAll('div[data-message-id]').forEach(msg => {
                    const role = msg.querySelector('img[alt], [data-message-author-role]')?.alt || msg.querySelector('[data-message-author-role]')?.getAttribute('data-message-author-role') || 'unknown';
                    const contentElem = msg.querySelector('.markdown'); // Adjust selector based on actual structure
                    const content = contentElem ? contentElem.innerText : '[Content not found]';
                    messages.push({ role: role.toLowerCase(), content: content });
                });
                return messages;
            """)

            logger.info(f"Successfully scraped {len(messages_data)} messages from {chat_url}")
            return {"title": title, "messages": messages_data}

        except TimeoutException:
            logger.error(f"Timeout waiting for messages on {chat_url}")
            return None
        except WebDriverException as e:
            logger.error(f"Error scraping chat {chat_url}: {str(e)}")
            return None

    async def _scroll_history_to_top(self, timeout=60): # Add timeout for safety
        """Executes JS to scroll the chat history pane to the top until stable."""
        logger.info("Scrolling chat history to top...")
        script = """
            async function scrollToTopAndWaitForStability(containerSelector, timeout) {
                const container = document.querySelector(containerSelector);
                if (!container) {
                    console.error('Scroll container not found:', containerSelector);
                    return false;
                }

                let lastScrollTop = -1;
                let stableCount = 0;
                const startTime = Date.now();

                // Scroll to bottom first to ensure we are in the right scroll context
                container.scrollTo(0, container.scrollHeight);
                await new Promise(resolve => setTimeout(resolve, 200)); 

                while (stableCount < 3) {
                    if (Date.now() - startTime > timeout * 1000) {
                         console.error('Scrolling timed out after', timeout, 'seconds.');
                         return false; // Timeout
                    }
                    
                    const currentScrollTop = container.scrollTop;
                    // Scroll up instead of down to reach the top of history
                    container.scrollTo(0, 0); // Scroll to the top
                    await new Promise(resolve => setTimeout(resolve, 500)); // Wait for render/load
                    const newScrollTop = container.scrollTop;
                    
                    // Check if scroll position changed *after* scrolling up
                    // If it didn't change (or is 0), we might be at the top
                    if (newScrollTop === 0 || newScrollTop === currentScrollTop) {
                        stableCount++;
                        logger.debug(f"Scroll position stable ({stableCount}/3). scrollTop: {newScrollTop}")
                    } else {
                        stableCount = 0; // Reset if scroll position changed
                    }
                    lastScrollTop = newScrollTop; // Update for next check (though less relevant for scroll-to-top)
                }
                console.log('Scrolling finished and stable.');
                return true;
            }
            // Use appropriate selector for the scrollable history pane
            const containerSelector = '[aria-label="Chat history"]'; 
            return await scrollToTopAndWaitForStability(containerSelector, arguments[0]);
            """
        try:
            # Execute async JS, passing the timeout
            success = await asyncio.to_thread(self.driver.execute_async_script, script, timeout)
            # success = self.driver.execute_async_script(script, timeout) # Might work directly depending on Selenium version/setup
            if success:
                 logger.info("Chat history scrolled to top successfully.")
                 return True
            else:
                 logger.warning("Chat history scrolling did not complete successfully (JS returned false or timed out).")
                 return False
        except WebDriverException as e:
            logger.error(f"Error executing scroll script: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during scroll execution: {e}", exc_info=True)
            return False
            
    async def _wait_for_chat_items(self, timeout=15, min_count=1) -> Optional[List[Any]]:
        """Waits dynamically for chat items to appear after scrolling."""
        logger.info(f"Waiting for at least {min_count} chat item(s) to load (timeout: {timeout}s)...")
        start_time = time.time()
        last_error = None
        selector = (By.CSS_SELECTOR, '[data-testid="conversation-item"]') # Use the defined selector
        while time.time() - start_time < timeout:
            try:
                chats = self.driver.find_elements(*selector)
                if len(chats) >= min_count:
                    logger.info(f"Found {len(chats)} chat items.")
                    return chats
                else:
                    logger.debug(f"Found {len(chats)} chats, waiting for more...")
            except (NoSuchElementException, StaleElementReferenceException) as e:
                # Ignore transient errors while waiting
                logger.debug(f"Wait loop: Encountered {type(e).__name__}, retrying...")
                last_error = str(e)
            except WebDriverException as e:
                 logger.error(f"WebDriver error during wait for chat items: {e}")
                 last_error = str(e)
                 break # Don't retry on fundamental WebDriver errors
            
            await asyncio.sleep(1) # Use asyncio sleep in async context

        logger.error(f"Timeout waiting for chat items. Last count: {len(self.driver.find_elements(*selector)) if self.driver else 'N/A'}. Last error: {last_error}")
        return None # Indicate timeout/failure

    @retry_on_exception(max_attempts=3, exceptions=(WebDriverException, NoSuchElementException, TimeoutException))
    async def scroll_and_capture_chats(self) -> List[Dict[str, str]]: # <<< Make async
        """
        Scroll through chat history and capture all chat metadata using dynamic waits.

        Returns:
            List[Dict[str, str]]: List of chat metadata dictionaries
        """
        # No longer injecting jQuery
        # if not self.inject_jquery():
        #     logger.error("Failed to inject jQuery, proceeding with basic scrolling")

        logger.info("Starting stable chat capture")
        chats_data = []

        try:
            # 1. Scroll history pane to top until stable
            if not await self._scroll_history_to_top():
                logger.warning("Scrolling history failed or timed out. Captured chats may be incomplete.")
                # Continue anyway, try to capture what's visible

            # 2. Wait dynamically for chat items to load
            chat_tiles = await self._wait_for_chat_items(timeout=15, min_count=1) # Wait up to 15s for at least 1 item

            if not chat_tiles:
                 logger.error("No chat tiles found after scrolling and waiting.")
                 return [] # Return empty list if none found

            logger.info(f"Processing {len(chat_tiles)} chat tiles found...")
            # 3. Extract data from found items
            for tile in chat_tiles:
                try:
                    # Ensure the element is still valid
                    title = tile.text.strip()
                    link_elem = tile.find_element(By.TAG_NAME, 'a')
                    url = link_elem.get_attribute('href')
                    # Attempt to get timestamp, might not always be present
                    timestamp = ""
                    try:
                         # Example: Check parent or specific child if timestamp isn't direct attribute
                         time_elem = link_elem.find_element(By.XPATH, ".//div[contains(@class, 'text-xs')]") # Hypothetical selector
                         timestamp = time_elem.text 
                         # Or timestamp = link_elem.get_attribute('data-timestamp') if that exists
                    except NoSuchElementException:
                         logger.debug(f"Timestamp element not found for chat: {title[:30]}...")

                    chat_data = {
                        "title": title,
                        "url": url,
                        "timestamp": timestamp, # Store timestamp if found
                        "captured_at": datetime.now().isoformat()
                    }
                    chats_data.append(chat_data)
                except StaleElementReferenceException:
                    logger.warning("Chat tile became stale during processing, skipping.")
                    continue
                except NoSuchElementException:
                    logger.warning("Could not find expected sub-element (link) within chat tile, skipping.")
                    continue
                except Exception as inner_e:
                    logger.error(f"Error processing individual chat tile: {inner_e}", exc_info=False)
                    continue # Skip problematic tile

            logger.info(f"Successfully captured {len(chats_data)} chats")
            return chats_data

        except WebDriverException as e:
            logger.error(f"Error during chat capture: {str(e)}", exc_info=True)
            return [] # Return empty list on major error
        except Exception as e:
            logger.error(f"Unexpected error during chat capture: {e}", exc_info=True)
            return []

def main():
    """CLI entry point."""
    with ChatGPTScraper() as scraper:
        success = scraper.run_scraper(model_append="?model=gpt-4")
        if success:
            logger.info("Scraping completed successfully")
        else:
            logger.error("Scraping failed")
            return 1
    return 0

if __name__ == "__main__":
    exit(main()) 