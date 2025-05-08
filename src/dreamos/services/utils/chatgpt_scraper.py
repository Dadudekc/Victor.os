"""
ChatGPT Web Scraper - Automated chat history extraction tool.
Uses undetected-chromedriver to avoid detection and provides robust session management.
"""
# EDIT START: Add missing import sys
import sys
# EDIT END
import os
import time
import pickle
import logging
import shutil
import re
import json
from datetime import datetime
from typing import Optional, Tuple, Any, List

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys  # <-- Added missing import
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager

from jinja2 import Template  # Jinja2 integrated for templated output
from dreamos.utils.ai_output_logger import log_ai_output  # Corrected import assuming location within dreamos.utils

# EDIT START: Add specific Selenium exceptions
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, NoSuchElementException, ElementNotInteractableException, NoSuchWindowException
# EDIT END

# --- DEBUG PRINTS ---
print(f"DEBUG: chatgpt_scraper.py CWD: {os.getcwd()}", file=sys.stderr)
print(f"DEBUG: chatgpt_scraper.py sys.path: {sys.path}", file=sys.stderr)
# --- END DEBUG PRINTS ---

# Configure logging (ensure this is defined before use or handled if script context)
# Ensure logger is defined if used before this point, or use default print for early debug
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s") # Comment out if it causes issues before full init
logger = logging.getLogger(__name__)
# EDIT START: Ensure logger is configured for detailed output if not already
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s", stream=sys.stderr) # Log to stderr for visibility
    logger.info("Logger configured by chatgpt_scraper.py itself.")
# EDIT END

# ---------------------------
# Configuration & Constants
# ---------------------------
# Fallback for PROFILE_DIR if not defined by AppConfig or similar
# This is just to prevent NameError if the script relies on it before AppConfig load
if 'PROFILE_DIR' not in globals():
    PROFILE_DIR = None 
if 'CHATGPT_URL' not in globals():
    # REVERTED: Set URL back to chat.openai.com/chat for response scraping
    CHATGPT_URL = "https://chat.openai.com/chat" 
    logger.info(f"CHATGPT_URL is now set to: {CHATGPT_URL}")
    # EDIT END

PROFILE_DIR = os.path.join(os.getcwd(), "chrome_profile", "openai")
COOKIE_FILE = os.path.join(os.getcwd(), "cookies", "openai.pkl")
CONTENT_LOG_DIR = os.path.join(os.getcwd(), "chat_mate", "content_logs")

os.makedirs(CONTENT_LOG_DIR, exist_ok=True)

# ADDED: List of selectors for the chat input box
# EDIT START: Update CHAT_INPUT_SELECTORS to include the new p[data-placeholder] selector and prioritize it.
CHAT_INPUT_SELECTORS = [
    'p[data-placeholder="Ask anything"]',      # New primary selector based on user feedback
    'textarea[data-id="chat-input"]',           # Old selector
    'textarea[placeholder="Send a message"]',   # Old selector
    'textarea[aria-label="Chat input"]',        # Old selector
    # Add other selectors as needed
]
# EDIT END

# ADDED: Selectors for the Send button
SEND_BUTTON_SELECTORS = [
    "button[data-testid=\"send-button\"]", # Primary test ID
    "button[class*=\"send\"]",             # Class name containing 'send'
    "button[aria-label*=\"Send\"]",        # Aria label containing 'Send'
    "//button[.//span[text()='Send message']]" # XPath for button containing specific text (fallback)
]

# ---------------------------
# Hybrid Response Handler Class
# ---------------------------
class HybridResponseHandler:
    """
    Parses a hybrid response that includes both narrative text and a MEMORY_UPDATE JSON block.
    Returns a tuple of (text_part, memory_update_json).
    """

    def parse_hybrid_response(self, raw_response: str) -> Tuple[str, dict]:
        logger.info("Parsing hybrid response for narrative text and MEMORY_UPDATE JSON.")
        # Regex to capture JSON block between ```json and ```
        json_pattern = r'''```json(.*?)```'''
        match = re.search(json_pattern, raw_response, re.DOTALL)

        if match:
            json_content = match.group(1).strip()
            try:
                memory_update = json.loads(json_content)
                logger.info("Successfully parsed MEMORY_UPDATE JSON.")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                memory_update = {}
        else:
            logger.warning("No JSON block found in the response.")
            memory_update = {}

        # Remove the JSON block from the raw response to extract pure narrative text.
        text_part = re.sub(json_pattern, '', raw_response, flags=re.DOTALL).strip()

        return text_part, memory_update

# ---------------------------
# Core Response Handler Class
# ---------------------------
class ResponseHandler:
    """
    Handles sending prompts, fetching, and stabilizing ChatGPT responses.
    Now includes hybrid response processing: it will extract narrative text and MEMORY_UPDATE JSON.
    Also hooks into the AI output logger for reinforcement training.
    """

    def __init__(self, driver: Optional[uc.Chrome] = None, timeout: int = 180, stable_period: int = 10, poll_interval: int = 5) -> None:
        logger.info("ResponseHandler.__init__ called.")
        self.driver = driver or self._init_driver()
        self.timeout = timeout
        self.stable_period = stable_period
        self.poll_interval = poll_interval
        self._last_msg_count = 0
        # Store primary message selectors
        self._message_elements_selector_primary = ".markdown.prose.w-full.break-words" 
        self._message_elements_selector_fallback = "div[class*='markdown prose']"
        # Note: CHAT_INPUT_SELECTORS defined above
        logger.info(f"ResponseHandler initialized.")

    # ---------------------------
    # Driver Initialization
    # ---------------------------
    def _init_driver(self) -> uc.Chrome:
        # EDIT START: Log driver initialization steps
        logger.info("ResponseHandler._init_driver called.")
        options = uc.ChromeOptions()
        # options.add_argument("--headless") # Optional: for running without a visible browser window
        logger.info("ChromeOptions initialized.")
        options.add_argument("--start-maximized")
        # EDIT START: Temporarily disable using specific profile directory
        # if PROFILE_DIR:
        #     logger.info(f"Attempting to use profile directory: {PROFILE_DIR}")
        #     options.add_argument(f"--user-data-dir={PROFILE_DIR}")
        # else:
        #     logger.warning("PROFILE_DIR not set, not using user-data-dir.")
        logger.info("Temporarily NOT using specific user-data-dir for this test.")
        # EDIT END

        cached_driver_path = os.path.join(os.getcwd(), "drivers", "chromedriver.exe")
        logger.info(f"Looking for cached ChromeDriver at: {cached_driver_path}")
        
        if os.path.exists(cached_driver_path):
            driver_path = cached_driver_path
            logger.info(f"Using cached ChromeDriver: {driver_path}")
        else:
            logger.warning("No cached ChromeDriver found. Attempting to download latest via ChromeDriverManager...")
            try:
                driver_path = ChromeDriverManager().install()
                logger.info(f"ChromeDriver downloaded/installed by ChromeDriverManager to: {driver_path}")
                os.makedirs(os.path.dirname(cached_driver_path), exist_ok=True)
                shutil.copyfile(driver_path, cached_driver_path) # Cache it for next time
                driver_path = cached_driver_path # Use the cached path
                logger.info(f"Copied downloaded ChromeDriver to cache: {driver_path}")
            except Exception as e:
                logger.error(f"Error during ChromeDriver download/install: {e}", exc_info=True)
                raise

        logger.info(f"Initializing uc.Chrome with driver_executable_path: {driver_path}")
        try:
            driver = uc.Chrome(options=options, driver_executable_path=driver_path)
            logger.info("uc.Chrome driver initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing uc.Chrome: {e}", exc_info=True)
            raise
        # EDIT END
        return driver

    # ---------------------------
    # Authentication Helpers
    # ---------------------------
    def save_cookies(self, domain: Optional[str] = None) -> None:
        try:
            os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
            all_cookies = self.driver.get_cookies()
            cookies_to_save = []
            if domain:
                logger.info(f"Filtering cookies for domain: {domain}")
                for cookie in all_cookies:
                    # Basic domain matching (can be improved for subdomains)
                    if domain in cookie.get('domain', ''):
                        cookies_to_save.append(cookie)
            else:
                cookies_to_save = all_cookies
            
            if not cookies_to_save:
                 logger.warning(f"No cookies found to save" + (f" for domain {domain}" if domain else ""))
                 return

            with open(COOKIE_FILE, "wb") as f:
                pickle.dump(cookies_to_save, f)
            logger.info(f"Saved {len(cookies_to_save)} cookies to: {COOKIE_FILE}" + (f" (filtered for {domain})" if domain else ""))
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}", exc_info=True)

    def load_cookies(self, domain: Optional[str] = None) -> bool:
        logger.info(f"Attempting to load cookies from: {COOKIE_FILE}")
        if not os.path.exists(COOKIE_FILE):
            logger.warning("No cookie file found.")
            return False
        try:
            with open(COOKIE_FILE, "rb") as f:
                cookies = pickle.load(f)
            
            loaded_count = 0
            skipped_count = 0
            current_domain = None
            try: # Get current domain to ensure cookies are valid for it
                 current_domain = urlparse(self.driver.current_url).netloc
            except Exception:
                 logger.warning("Could not determine current domain for cookie validation.")
                 # Proceed cautiously

            logger.info(f"Applying cookies (Target domain filter: {domain}, Current browser domain: {current_domain})")
            for cookie in cookies:
                 cookie_domain = cookie.get('domain', '')
                 # Filter based on requested domain if specified
                 if domain and domain not in cookie_domain:
                      skipped_count += 1
                      continue
                 # Basic check: ensure cookie domain matches current browser domain context if possible
                 # This helps prevent InvalidCookieDomainException
                 if current_domain and not cookie_domain.endswith(current_domain) and not current_domain.endswith(cookie_domain):
                      logger.warning(f"Skipping cookie for domain '{cookie_domain}' - may not match current context '{current_domain}'")
                      skipped_count += 1
                      continue
                 
                 # Remove SameSite if needed (depends on browser/driver version)
                 cookie.pop("sameSite", None) 
                 try:
                     self.driver.add_cookie(cookie)
                     loaded_count += 1
                 except Exception as e_add:
                      logger.warning(f"Could not add cookie: {cookie.get('name')} for domain {cookie_domain}. Error: {e_add}")
                      skipped_count += 1
            
            logger.info(f"Finished applying cookies. Added: {loaded_count}, Skipped/Failed: {skipped_count}.")
            if loaded_count > 0:
                 logger.info("Refreshing page to apply loaded cookies...")
                 self.driver.refresh()
                 time.sleep(5) # Wait for refresh
                 return True
            else:
                 logger.warning("No cookies were successfully loaded.")
                 return False

        except Exception as e:
            logger.error(f"Failed to load or process cookies: {e}", exc_info=True)
            return False

    def is_logged_in(self) -> bool:
        # EDIT START: Modify is_logged_in to check current page first, navigate if not on chatgpt.com, and increase timeout.
        logger.info(f"----- Checking login status -----")
        current_url_for_check = "Unknown"
        try:
            current_url_for_check = self.driver.current_url
            if "chatgpt.com" not in current_url_for_check:
                logger.info(f"Not on a chatgpt.com URL ('{current_url_for_check}'). Navigating to https://chatgpt.com/ for login check.")
                self.driver.get("https://chatgpt.com/")
                time.sleep(3) # Allow redirects/load
                current_url_for_check = self.driver.current_url # Update
        except Exception as e:
            logger.warning(f"Could not get current URL or navigate for login check: {e}. Attempting fallback navigation to https://chatgpt.com/")
            try:
                self.driver.get("https://chatgpt.com/")
                time.sleep(3)
                current_url_for_check = self.driver.current_url
            except Exception as e_nav:
                logger.error(f"Failed navigating to https://chatgpt.com/ for login check: {e_nav}")
                return False

        logger.info(f"Checking for chat input box on {current_url_for_check}...")
        try:
            # Use WebDriverWait with the helper method, increased timeout
            WebDriverWait(self.driver, 20).until(self._chat_box_present) # Increased timeout to 20s
            logger.info(f"LOGIN_CHECK: Chat input detected on {self.driver.current_url} - session appears active.")
            return True
        except TimeoutException:
            logger.warning(f"LOGIN_CHECK: Chat input NOT detected on {self.driver.current_url} after 20s - session likely inactive or page issue.")
            try: logger.warning(f"LOGIN_CHECK: (Timeout) Final URL was {self.driver.current_url}")
            except: pass
            return False
        # EDIT END

    # ADDED: Helper method to check for chat input box using multiple selectors
    def _chat_box_present(self, driver) -> bool:
        """Checks if any known chat input box selector finds an element."""
        # EDIT START: Modify _chat_box_present to use find_elements and check list length
        for css_selector in CHAT_INPUT_SELECTORS: # Use the updated list
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, css_selector)
                if elements: # Check if the list of found elements is not empty
                    logger.debug(f"_chat_box_present: Found element(s) with selector: {css_selector}")
                    return True
            except Exception as e: # Catch potential errors during find_elements, though it usually returns empty list
                logger.debug(f"_chat_box_present: Selector {css_selector} check failed with error: {e}")
                continue # Try next selector
        logger.debug("_chat_box_present: No chat input box found with any selector.")
        # EDIT END
        return False

    # ADDED: New method to ensure driver is on the correct chat page
    def ensure_chat_page(self, chat_url: str):
        """
        Make sure the driver is on *chat_url* or a sub-path; if not, navigate and wait.
        Raises TimeoutException if navigation or confirmation fails.
        """
        # EDIT START: Add check for closed window
        if not self.driver.window_handles:
            logger.error("ensure_chat_page: Browser window is closed. Cannot proceed.")
            raise NoSuchWindowException("Browser window is closed (detected in ensure_chat_page).")
        # EDIT END
        logger.info(f"Ensuring browser is on target URL (or subpath): {chat_url}")
        try:
            current_url = self.driver.current_url
            if not isinstance(current_url, str) or not current_url.startswith(chat_url):
                logger.info(f"Current URL '{current_url}' does not start with target '{chat_url}'. Navigating...")
                self.driver.get(chat_url)
                
                # ADDED: Intermediate logging and longer sleep
                logger.info("Waiting for 5 seconds after self.driver.get() for initial load...")
                time.sleep(5)
                try:
                    post_get_url = self.driver.current_url
                    logger.info(f"DEBUG_NAV: URL immediately after get() and 5s sleep: {post_get_url}")
                    # page_source_sample = self.driver.page_source[:1000] # Get a larger sample
                    # logger.info(f"DEBUG_NAV: Page source sample (first 1000 chars):\n{page_source_sample}")
                except Exception as e_debug:
                    logger.error(f"DEBUG_NAV: Error getting URL/page source after get(): {e_debug}")

                # MODIFIED: Wait for URL to START WITH the target, increase timeout
                # EDIT START: Relax the check to only ensure the base conversation URL path is loaded
                # Construct the base URL part (without query parameters)
                base_chat_url = chat_url.split('?')[0]
                logger.info(f"Waiting up to 60s for URL to start with BASE path {base_chat_url}...")
                WebDriverWait(self.driver, 60).until(lambda d: d.current_url.startswith(base_chat_url))
                # logger.info(f"Waiting up to 60s for URL to start with {chat_url}...")
                # WebDriverWait(self.driver, 60).until(lambda d: d.current_url.startswith(chat_url))
                logger.info(f"Successfully navigated to URL starting with base path: {self.driver.current_url}")
                # EDIT END
            else:
                logger.info(f"Browser already on target URL or a sub-path: {current_url}")
        except Exception as e:
            logger.error(f"Failed to ensure browser is on {chat_url} or subpath: {e}", exc_info=True)
            raise # Re-raise exception to signal failure

    # EDIT START: Add new method for one-time login setup
    def ensure_login_session(self) -> bool:
        target_url = "https://chatgpt.com/"
        logger.info(f"Ensuring login session on {target_url}...")

        current_url = ""
        try:
            current_url = self.driver.current_url
        except Exception as e:
            logger.warning(f"Could not get current URL: {e}. Proceeding with navigation.")

        if not isinstance(current_url, str) or not current_url.startswith(target_url):
            logger.info(f"Current URL '{current_url}' is not target. Navigating to {target_url}...")
            try:
                self.driver.get(target_url)
                time.sleep(3) # Basic wait for page load
            except Exception as e_nav:
                logger.error(f"Failed to navigate to {target_url}: {e_nav}. Aborting login attempt.")
                return False
        else:
            logger.info(f"Already on a {target_url} page: {current_url}")

        # Try loading cookies for chatgpt.com
        cookies_loaded = False
        try:
            if self.load_cookies(domain="chatgpt.com"): # load_cookies returns True if cookies were loaded and page refreshed
                logger.info("Cookies loaded for chatgpt.com domain. Session might be active.")
                cookies_loaded = True
                # load_cookies itself should refresh; add a small wait for page to settle
                time.sleep(3) # Wait for page to settle after potential refresh from load_cookies
            else:
                logger.info("Cookie load failed or no relevant cookies found for chatgpt.com.")
                # If cookies didn't load, ensure we are on the base page if navigation happened inside load_cookies or it failed
                # Defensive navigation if not sure about state after cookie load
                if not self.driver.current_url.startswith(target_url):
                    self.driver.get(target_url)
                    time.sleep(3)
        except Exception as e_cookie_load:
            logger.error(f"Exception during cookie loading: {e_cookie_load}. Proceeding without cookie-based session.")
            if not self.driver.current_url.startswith(target_url): # Ensure navigation if error
                try:
                    self.driver.get(target_url)
                    time.sleep(3)
                except Exception as e_nav_retry:
                    logger.error(f"Failed to navigate to {target_url} after cookie error: {e_nav_retry}. Aborting.")
                    return False
        
        # Check login status using the is_logged_in method (which internally uses _chat_box_present and handles waits)
        # The is_logged_in method itself will navigate to target_url if not already there and wait.
        if self.is_logged_in():
            logger.info("Session active on chatgpt.com (verified by is_logged_in).")
            logger.info("Attempting to save cookies (for chatgpt.com domain)...")
            self.save_cookies(domain="chatgpt.com") # Save potentially updated cookies
            return True
        
        # If not logged in, prompt for manual login
        logger.warning(f"Session not active. MANUAL LOGIN NEEDED. Please log in on {self.driver.current_url} (should be {target_url} or its login page).")
        # Using existing manual login prompt logic
        input_message = (
            f">> Browser should be at {target_url} (or its login page). <<\\n"
            f">> Please complete login MANUALLY in the browser. <<\\n"
            f">> Press ENTER in this console ONLY AFTER you see the main chat input box. <<\\n"
        )
        try:
            manual_login_input = input(input_message)
            logger.info(f"User pressed Enter. Input (if any): '{manual_login_input}'")
        except EOFError: # Handle non-interactive environment
            logger.error("EOFError: Cannot prompt for manual login in non-interactive environment.")
            return False

        logger.info("Verifying login status via is_logged_in() after manual action...")
        time.sleep(2) # Brief pause for user actions to reflect
        
        if self.is_logged_in(): # is_logged_in will re-verify thoroughly
            logger.info("Login confirmed by is_logged_in() on chatgpt.com after manual step.")
            logger.info("Attempting to save cookies (for chatgpt.com domain)...")
            self.save_cookies(domain="chatgpt.com") # Save cookies after successful manual login
            return True
        else:
            logger.error("is_logged_in() check failed after manual intervention.")
            return False
    # EDIT END

    # ---------------------------
    # Prompt Submission
    # ---------------------------
    # EDIT START: Rewritten send_prompt with retries and updated logic
    def send_prompt(self, prompt: str) -> bool:
        # EDIT START: Add check for closed window
        if not self.driver.window_handles:
            logger.error("send_prompt: Browser window is closed. Cannot send prompt.")
            return False
        # EDIT END
        logger.info(f"Attempting to send prompt (first 60 chars): {prompt[:60]}...")
        try: self._last_msg_count = len(self._get_message_elements())
        except Exception as e: logger.error(f"Error getting initial msg count: {e}"); self._last_msg_count = 0
        logger.info(f"Messages count before sending: {self._last_msg_count}")

        max_attempts = 3
        for attempt in range(max_attempts):
            logger.info(f"Send prompt attempt {attempt + 1}/{max_attempts} on {self.driver.current_url}")
            input_box = None
            for css in CHAT_INPUT_SELECTORS:
                try:
                    # Wait for presence first
                    candidate = WebDriverWait(self.driver, 5).until(
                         EC.presence_of_element_located((By.CSS_SELECTOR, css))
                    )
                    # Then wait for clickability (might be needed for dynamic elements)
                    input_box = WebDriverWait(self.driver, 5).until(
                         EC.element_to_be_clickable((By.CSS_SELECTOR, css))
                    )
                    logger.debug(f"Found interactable input box with selector: {css}")
                    break # Found a working selector
                except (NoSuchElementException, TimeoutException):
                     logger.debug(f"Input box selector failed: {css}")
                     continue # Try next selector
            
            if not input_box:
                 logger.error(f"Attempt {attempt+1}: Could not find interactable input box with any known selector.")
                 if attempt < max_attempts - 1: time.sleep(2); continue
                 else: return False # All attempts failed to find input box
            
            # Found the input box, try sending keys
            try:
                input_box.click()
                time.sleep(0.3) # Small delay after click before sending keys
                
                sanitized_prompt = prompt.encode('ascii', 'ignore').decode('ascii')
                if len(sanitized_prompt) < len(prompt):
                    logger.warning(f"Prompt was sanitized due to non-BMP characters. Original length: {len(prompt)}, Sanitized length: {len(sanitized_prompt)}")

                # EDIT START: Use JavaScript for non-textarea elements to set text content
                if input_box.tag_name.lower() != 'textarea':
                    logger.debug(f"Input element is '{input_box.tag_name}', using JavaScript to set innerText.")
                    self.driver.execute_script("arguments[0].innerText = arguments[1];", input_box, sanitized_prompt)
                    # Also ensure focus for subsequent send button click or UI reactivity
                    self.driver.execute_script("arguments[0].focus();", input_box)
                    time.sleep(0.2) # Small delay after setting text and focusing
                else:
                    logger.debug("Input element is textarea, using send_keys for prompt text.")
                    input_box.send_keys(sanitized_prompt)
                    time.sleep(0.2) # Small delay after sending keys
                # EDIT END

                # Check tag type to determine submission method
                if input_box.tag_name.lower() == 'textarea':
                    logger.debug("Input element is textarea, sending Keys.RETURN to submit.")
                    input_box.send_keys(Keys.RETURN)
                else:
                    logger.debug(f"Input element is {input_box.tag_name}, attempting to click Send button to submit.")
                    send_button_clicked = False
                    for btn_css in SEND_BUTTON_SELECTORS:
                        try:
                            # Check if selector is XPath
                            find_method = By.XPATH if btn_css.startswith("//") else By.CSS_SELECTOR
                            send_button = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((find_method, btn_css))
                            )
                            send_button.click()
                            logger.debug(f"Clicked Send button using selector: {btn_css}")
                            send_button_clicked = True
                            break # Button clicked successfully
                        except (NoSuchElementException, TimeoutException, ElementNotInteractableException):
                            logger.debug(f"Send button selector failed or not interactable: {btn_css}")
                            continue # Try next selector
                    
                    if not send_button_clicked:
                        logger.error("Could not find or click the Send button after sending prompt text.")
                        # Optionally try RETURN as a last resort even for non-textarea?
                        # input_box.send_keys(Keys.RETURN)
                        # logger.warning("Falling back to sending Keys.RETURN as Send button failed.")
                        return False # Consider it a failure if button isn't clicked

                logger.info(f"Prompt sent successfully: {prompt[:60]}...")
                return True # Success!
            except StaleElementReferenceException as e_stale:
                 logger.warning(f"Attempt {attempt + 1} failed: StaleElementReferenceException during send_keys/click. Retrying...")
                 if attempt < max_attempts - 1: time.sleep(2); continue
                 else: logger.error("StaleElementReferenceException on final attempt."); return False
            except Exception as e_send:
                 logger.error(f"Attempt {attempt + 1} failed during send_keys/click: {type(e_send).__name__}", exc_info=True)
                 if attempt < max_attempts - 1: time.sleep(2); continue
                 else: return False
        return False # Should not be reached
    # EDIT END

    # ---------------------------
    # Response Fetching and Stabilization
    # ---------------------------
    # EDIT START: Modified fetch_response to be pure DOM scrape based on _last_msg_count
    def fetch_response(self) -> str:
        logger.debug("ResponseHandler.fetch_response() called. Assuming browser is on the correct page.")
        # No navigation, relies on caller (e.g., BridgeLoop via ensure_chat_page)
        
        try:
            all_message_elements = self._get_message_elements()
            current_message_count = len(all_message_elements)
            logger.debug(f"fetch_response: current_message_count={current_message_count}, self._last_msg_count={self._last_msg_count}")

            if current_message_count > self._last_msg_count:
                # New messages are present since the prompt was sent (or last response was processed)
                newest_message_element = all_message_elements[-1]
                response_text = newest_message_element.text.strip()
                logger.debug(f"Fetched NEW response candidate (msg count {self._last_msg_count} -> {current_message_count}): '{response_text[:100]}...'")
                return response_text
            elif current_message_count > 0 and current_message_count == self._last_msg_count:
                # No new messages structurally, but content of last message might be changing (streaming)
                # or it's the same stable last message.
                last_message_text = all_message_elements[-1].text.strip()
                logger.debug(f"No new messages structurally (count {current_message_count}). Returning current last message text for stability check: '{last_message_text[:100]}...'")
                return last_message_text
            elif current_message_count == 0 :
                logger.debug("fetch_response: No messages found on page.")
                return ""
            else: # current_message_count < self._last_msg_count
                  # This case (e.g. messages deleted from UI) is unusual.
                logger.warning(f"fetch_response: Message count decreased from {self._last_msg_count} to {current_message_count}. Returning empty.")
                return ""
        except Exception as e:
            logger.error(f"Error during fetch_response: {e}", exc_info=True)
            return ""
    # EDIT END

    # EDIT START: Modified wait_for_stable_response to update _last_msg_count correctly
    def wait_for_stable_response(self) -> str:
        logger.info("Waiting for stable ChatGPT response...")
        start_time = time.time()
        last_response_text = ""
        # Get initial response to compare against.
        # _last_msg_count should be set by send_prompt before this is called.
        # We call fetch_response, which might return the prompt itself if it appears as a message,
        # or an empty string if no new messages yet.
        
        # Initialize last_response_text with the current state, which might be empty or the prompt text.
        # The goal is to see this change to the actual AI response.
        initial_messages = self._get_message_elements()
        if len(initial_messages) > self._last_msg_count:
            last_response_text = initial_messages[-1].text.strip()
            logger.debug(f"wait_for_stable_response: Initial last_response_text from newest message (if any beyond prompt): '{last_response_text[:100]}...'")
        elif initial_messages: # E.g. _last_msg_count includes the prompt, so no "new" yet.
             last_response_text = initial_messages[-1].text.strip()
             logger.debug(f"wait_for_stable_response: Initial last_response_text (likely prompt): '{last_response_text[:100]}...'")


        stable_start_time = None

        while time.time() - start_time < self.timeout:
            time.sleep(self.poll_interval)
            current_response_text = self.fetch_response() # This now gets newest message if count > _last_msg_count

            if current_response_text != last_response_text:
                logger.info(f"Response text changed. Old: '{last_response_text[:60]}...' New: '{current_response_text[:60]}...'. Resetting stability timer.")
                last_response_text = current_response_text
                stable_start_time = time.time()
                
                # Crucially, update _last_msg_count to reflect that we've processed this new state.
                # This ensures that the *next* call to fetch_response within this loop
                # will correctly identify if *another, newer* message appears or if this one streams more content.
                # We update based on the messages that formed current_response_text.
                current_message_elements_for_count = self._get_message_elements()
                if current_message_elements_for_count and current_message_elements_for_count[-1].text.strip() == current_response_text:
                    if len(current_message_elements_for_count) > self._last_msg_count : # only update if it is indeed a new message element structurally
                        logger.debug(f"Updating _last_msg_count from {self._last_msg_count} to {len(current_message_elements_for_count)} as new response text is being processed.")
                        self._last_msg_count = len(current_message_elements_for_count)
                    else:
                        logger.debug(f"Response text changed but message count ({len(current_message_elements_for_count)}) not greater than _last_msg_count ({self._last_msg_count}). Likely streaming into existing last message.")
                else:
                    logger.debug("Could not confirm message elements for count update after response text change. _last_msg_count remains unchanged.")


            elif stable_start_time and (time.time() - stable_start_time) >= self.stable_period:
                logger.info(f"Response stabilized after {time.time() - stable_start_time:.2f}s: '{last_response_text[:100]}...'")
                # Final update to _last_msg_count to ensure it reflects the count of the stable response.
                final_message_elements = self._get_message_elements()
                if final_message_elements and final_message_elements[-1].text.strip() == last_response_text:
                     self._last_msg_count = len(final_message_elements)
                     logger.debug(f"Final _last_msg_count set to {self._last_msg_count} for stable response.")

                cleaned_response = self.clean_response(last_response_text)
                # MODIFIED: Call log_ai_output with correct signature
                log_metadata_success = {
                    "tags": ["stable_response"], 
                    "result": "success",
                    "stability_check_duration_s": time.time() - stable_start_time if stable_start_time else -1
                }
                log_ai_output(
                    prompt="<prompt not available in this context>", 
                    response=cleaned_response, 
                    raw_response=last_response_text, # Use last observed text as raw
                    metadata=log_metadata_success
                )
                return cleaned_response

        logger.warning(f"Response stabilization timeout after {self.timeout}s. Returning last observed response: '{last_response_text[:100]}...'")
        # Final update to _last_msg_count even on timeout.
        final_message_elements_timeout = self._get_message_elements()
        if final_message_elements_timeout and final_message_elements_timeout[-1].text.strip() == last_response_text:
                self._last_msg_count = len(final_message_elements_timeout)
                logger.debug(f"Final _last_msg_count set to {self._last_msg_count} on timeout.")
        
        cleaned_response_timeout = self.clean_response(last_response_text)
        # MODIFIED: Call log_ai_output with correct signature
        log_metadata_timeout = {
            "tags": ["stable_response", "timeout"], 
            "result": "partial",
            "timeout_duration_s": self.timeout
        }
        log_ai_output(
            prompt="<prompt not available in this context>", 
            response=cleaned_response_timeout, 
            raw_response=last_response_text, # Use last observed text as raw
            metadata=log_metadata_timeout
        )
        return cleaned_response_timeout
    # EDIT END

    @staticmethod
    def clean_response(response: str) -> str:
        return response.strip()

    # ---------------------------
    # Hybrid Response Processing with Jinja Template
    # ---------------------------
    def handle_hybrid_response(self, raw_response: str, prompt_manager: Any, chat_title: str = "Unknown Chat") -> None:
        """
        Parses the raw response to extract narrative text and a MEMORY_UPDATE JSON block.
        Uses Jinja2 to render a formatted archival report.
        - Archives the formatted report to a content log.
        - Passes the MEMORY_UPDATE JSON to the prompt manager for persistent memory updates.
        """
        logger.info("Handling hybrid response...")
        hybrid_handler = HybridResponseHandler()
        narrative_text, memory_update_json = hybrid_handler.parse_hybrid_response(raw_response)

        # Define a Jinja2 template for the archival report.
        archive_template_str = (
            "--- Hybrid Response Archive ---"
            "Timestamp: {{ timestamp }}"
            "Chat Title: {{ chat_title }}"
            ""
            "=== Narrative Text ==="
            "{{ narrative_text }}"
            ""
            "=== MEMORY_UPDATE JSON ==="
            "{{ memory_update_json | tojson(indent=2) }}"
            "-------------------------------"
        )
        template = Template(archive_template_str)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rendered_report = template.render(
            timestamp=timestamp,
            chat_title=chat_title,
            narrative_text=narrative_text,
            memory_update_json=memory_update_json
        )

        # Archive the rendered report to a content log file.
        archive_file = os.path.join(CONTENT_LOG_DIR, f"hybrid_response_{timestamp}.txt")
        with open(archive_file, 'w', encoding='utf-8') as f:
            f.write(rendered_report)
        logger.info(f"Archived hybrid response to: {archive_file}")

        # Update persistent memory using the MEMORY_UPDATE JSON.
        if memory_update_json:
            try:
                prompt_manager.parse_memory_updates(memory_update_json)
                logger.info("Persistent memory updated via hybrid response.")
            except Exception as e:
                logger.error(f"Failed to update persistent memory: {e}")
        else:
            logger.warning("No MEMORY_UPDATE JSON found in the response.")

    # ---------------------------
    # Single Prompt Cycle with Rate Limiting
    # ---------------------------
    def execute_prompt_cycle(self, prompt: str, rate_limit: int = 2) -> str:
        # REVISED: Replace manual login with ensure_login_session call
        if not self.ensure_login_session():
            logger.error("Automated login failed. Aborting prompt cycle.")
            return "" # Return empty string as per existing error handling
        
        # Ensure login session should leave us on the correct page
        logger.info(f"Login confirmed, proceeding to send prompt on current page: {self.driver.current_url}")

        if not self.send_prompt(prompt):
            logger.error("Prompt submission failed. Cycle aborted.")
            return ""

        response = self.wait_for_stable_response()
        
        time.sleep(rate_limit)
        
        return response

    # ---------------------------
    # Run Prompts on Multiple Chats with Rate Limiting
    # ---------------------------
    def execute_prompts_on_all_chats(self, prompts: list, chat_list: list, rate_limit: int = 2) -> dict:
        # REVISED: Replace manual login with ensure_login_session call
        if not self.ensure_login_session():
            logger.error("Automated login failed. Aborting multi-chat prompt execution.")
            return {} # Return empty dict as per existing error handling / success path with no results
        
        # Ensure login session should leave us on the correct page (chat.openai.com/chat)
        logger.info(f"Login confirmed, proceeding with multi-chat execution from page: {self.driver.current_url}")

        results = {}
        for chat_info in chat_list:
            chat_title = chat_info["title"]
            chat_url = chat_info["link"]

            # Ensure chat_url is based on the correct domain if needed
            # Assuming chat_list contains URLs like https://chat.openai.com/c/...
            # If they are chatgpt.com URLs, they might need adjustment or the logic below might fail
            if not chat_url.startswith("https://chat.openai.com/"):
                 logger.warning(f"Chat URL {chat_url} does not start with https://chat.openai.com/. Skipping or potential error.")
                 # continue # Optionally skip if URL domain is wrong

            logger.info(f"--- Accessing chat '{chat_title}' ({chat_url}) ---")
            self.driver.get(chat_url)
            time.sleep(3)

            chat_responses = []
            for idx, prompt_text in enumerate(prompts, start=1):
                logger.info(f"Sending prompt #{idx} to chat '{chat_title}'")
                if not self.send_prompt(prompt_text):
                    logger.error(f"Failed to send prompt #{idx} to chat '{chat_title}'.")
                    chat_responses.append("")
                    continue
                stable_resp = self.wait_for_stable_response()
                chat_responses.append(stable_resp)
                time.sleep(rate_limit)
            results[chat_title] = chat_responses

        return results

    # ---------------------------
    # Graceful Shutdown
    # ---------------------------
    def shutdown(self) -> None:
        # EDIT START: Log shutdown
        logger.info("ResponseHandler.shutdown called.")
        # EDIT END
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser driver quit successfully.")
            except Exception as e:
                # EDIT START: Log shutdown error
                logger.error(f"Error during driver.quit(): {e}", exc_info=True)
                # EDIT END
        # EDIT START: Log end of shutdown
        logger.info("ResponseHandler.shutdown completed.")
        # EDIT END

    # EDIT START: New internal method to get message elements with fallback
    def _get_message_elements(self) -> List[Any]:
        """Fetches chat message elements from the page, trying primary then fallback selectors."""
        message_elements = []
        try:
            # Try primary selector
            message_elements = self.driver.find_elements(By.CSS_SELECTOR, self._message_elements_selector_primary)
            if message_elements:
                logger.debug(f"_get_message_elements: Found {len(message_elements)} messages with primary selector ('{self._message_elements_selector_primary}').")
                return message_elements

            # Try fallback selector if primary fails
            logger.debug(f"_get_message_elements: Primary selector ('{self._message_elements_selector_primary}') found no messages. Trying fallback ('{self._message_elements_selector_fallback}').")
            message_elements = self.driver.find_elements(By.CSS_SELECTOR, self._message_elements_selector_fallback)
            if message_elements:
                logger.debug(f"_get_message_elements: Found {len(message_elements)} messages with fallback selector ('{self._message_elements_selector_fallback}').")
            else:
                logger.debug(f"_get_message_elements: No messages found with fallback selector either.")
            
        except Exception as e:
            logger.error(f"_get_message_elements: Error finding message elements: {e}", exc_info=True)
        return message_elements
    # EDIT END

    # ————————————————————————————————————————————
    # ADDED: Conversation Content Scraping
    # ————————————————————————————————————————————
    def get_conversation_content(self) -> str:
        """Extracts the text content of all messages currently visible on the page."""
        logger.info("Attempting to scrape current conversation content...")
        all_text = []
        try:
            message_elements = self._get_message_elements() # Reuse existing helper
            if not message_elements:
                logger.warning("No message elements found to scrape content.")
                return ""
            
            for element in message_elements:
                try:
                    # Attempt to get text, handle potential stale elements during iteration
                    all_text.append(element.text.strip())
                except StaleElementReferenceException:
                    logger.warning("StaleElementReferenceException while getting text from a message element, skipping it.")
                    continue
            
            full_content = "\n\n---\n\n".join(all_text) # Join messages with a separator
            logger.info(f"Successfully scraped conversation content (total length: {len(full_content)}).")
            return full_content

        except Exception as e:
            logger.error(f"Error scraping conversation content: {e}", exc_info=True)
            return "<SCRAPE_ERROR>"

    # ————————————————————————————————————————————
    # ADDED: Sidebar History Scraping
    # ————————————————————————————————————————————
    def get_conversation_links(self, timeout: int = 20) -> List[dict]:
        """Scrapes conversation links and titles from the sidebar history."""
        logger.info("Attempting to scrape conversation links from sidebar...")
        conversations = []
        # EDIT START: Define selector for the scrollable history pane (nav containing the list)
        # We aim for the nav element that is an ancestor of the ol inside div#history
        # A robust selector for the scrollable navigation pane might be the nav tag itself if it's structured that way,
        # or a specific div with overflow properties. Let's try to find a nav element that is an ancestor of the history list.
        history_list_selector = "div#history ol" # This is for the list itself
        # Try to find the NAV element that is an ancestor of the history_list_selector
        # This assumes the <nav> tag is the scrollable container for the history items.
        scrollable_pane_selector = "nav"
        # A more specific selector based on common ChatGPT structure, if the above is too broad:
        # scrollable_pane_selector = "div[class*='overflow-y-auto'] div#history ol" - this would scroll the ol, we need parent
        # Let's try to find the NAV element that contains the div#history or a div acting as the scrollable container
        # A common pattern: a NAV element that directly contains the scrollable list area.
        # We will try to find a nav element first. If that's problematic, we might need a more specific div.
        # For now, let's assume the nav containing the history list is the scrollable part.
        # The user provided a very long selector, the end of which is: ... > nav > div.flex-col.flex-1...overflow-y-auto
        # Let's try to use a more general part of that as a primary candidate for scrolling:
        # scrollable_history_pane_selector = "nav > div[class*='overflow-y-auto']" # A div inside nav
        # Let's try to scroll the specific div the user pointed to if we can select it robustly
        # Based on user's selector, this is a good candidate for the scrollable element:
        # "div.flex-col.flex-1.transition-opacity.duration-500.relative.pe-3.overflow-y-auto"
        # Simplified: "div[class*='overflow-y-auto'][class*='flex-col']" inside the sidebar nav structure.
        # Let's try a specific selector for the scrollable div inside the nav based on common patterns.
        # Typically, the element with `overflow-y-auto` is what we need to scroll.
        # Let's find the NAV element first, then the scrollable div within it.
        # General approach: Find the NAV, then find a scrollable div within it.
        sidebar_nav_selector = "nav[aria-label*='Chat history']" # More semantic selector if available
        # If the above doesn't work, a structural one might be needed, e.g. the one derived from user input.
        # For now, let's use a simplified version of the user's one for the scrollable pane directly.
        # The user's provided selector: body > ... > nav > div.flex-col.flex-1...overflow-y-auto
        # Let's use this specific class combination for the scrollable element:
        scrollable_element_selector = "div.flex-col.flex-1.transition-opacity.duration-500.relative.pe-3.overflow-y-auto"

        # Link selector targets 'a' tags directly within list items that have an href starting with /c/
        link_selector = f"{history_list_selector} li a[href^='/c/']"

        try:
            # 1. Wait for the scrollable element to be present
            logger.info(f"Waiting for the scrollable history pane: {scrollable_element_selector}")
            scrollable_element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, scrollable_element_selector))
            )
            logger.info("Scrollable history pane found. Attempting to scroll it down.")

            # 2. Scroll the pane down completely
            last_height = self.driver.execute_script("return arguments[0].scrollHeight", scrollable_element)
            while True:
                self.driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", scrollable_element)
                time.sleep(0.75) # Increased pause for content loading during scroll
                new_height = self.driver.execute_script("return arguments[0].scrollHeight", scrollable_element)
                if new_height == last_height:
                    logger.info("Reached bottom of history pane.")
                    break
                last_height = new_height
            time.sleep(0.5) # Final pause after scrolling
            # EDIT END

            # 3. Wait for the history list container (ol) to be present *within* the now scrolled view
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, history_list_selector))
            )
            logger.debug(f"History list container found ('{history_list_selector}'). Searching for links...")

            # Find all conversation link elements
            link_elements = self.driver.find_elements(By.CSS_SELECTOR, link_selector)
            logger.info(f"Found {len(link_elements)} potential conversation link elements.")

            for element in link_elements:
                try:
                    href = element.get_attribute('href')
                    title = element.text.strip()
                    if href and title:
                        # Extract conversation ID from href (e.g., https://chatgpt.com/c/conv_id_123 -> conv_id_123)
                        conv_id = href.split('/c/')[-1].split('?')[0] # Handle potential query params
                        conversations.append({
                            'title': title,
                            'id': conv_id,
                            'url': href # Store the original URL as well
                        })
                    else:
                        logger.warning(f"Skipping history element: Missing href ('{href}') or title ('{title}')")
                except StaleElementReferenceException:
                    logger.warning("StaleElementReferenceException while processing a history link, skipping it.")
                    continue
                except Exception as e_link:
                    logger.error(f"Error processing individual history link: {e_link}", exc_info=False) # Keep log clean

            logger.info(f"Successfully extracted {len(conversations)} conversation links.")

        except TimeoutException:
            logger.error(f"Timeout waiting for history list container ('{history_list_selector}') after {timeout}s.")
        except Exception as e:
            logger.error(f"Error scraping conversation links: {e}", exc_info=True)

        return conversations

    # ————————————————————————————————————————————
    # ADDED: Model Discovery & Selection Helpers (as Methods)
    # ————————————————————————————————————————————
    def get_available_models(self) -> List[str]:
        """Scrape the in-UI model dropdown and return a list of model names."""
        models = []
        try:
            logger.info("Attempting to discover available models...")
            # Try clicking known model selector buttons/patterns
            model_button_selectors = [
                "button[id='model-selector']", # Specific ID if known
                "button > div[class*='items-center'] > span", # Common pattern: Button > Div > Span with name
                "button[class*='text-token-text-primary'][aria-haspopup='menu']" # Button styled as primary text with a menu
            ]
            model_button = None
            for selector in model_button_selectors:
                try:
                    candidate = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    button_text = candidate.text.lower()
                    # Basic check if button text looks like a model selector
                    if 'gpt' in button_text or '4' in button_text or '3.5' in button_text or 'o' in button_text or 'model' in button_text:
                        model_button = candidate
                        logger.debug(f"Found potential model selector button with selector: {selector}")
                        break
                except TimeoutException:
                    logger.debug(f"Model selector button not found/clickable with CSS: {selector}")
                    continue
            
            if not model_button:
                logger.error("Could not find or click the model selector button using known patterns.")
                try: self.driver.find_element(By.TAG_NAME, "body").click() # Close potential menus
                except: pass
                return [] 

            model_button.click()
            logger.debug("Clicked model selector button.")
            time.sleep(0.5) # Short pause for menu to render

            # Try finding menu items
            dropdown_item_selector = "div[role='menu'] li button span" # Common pattern
            try:
                items = WebDriverWait(self.driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, dropdown_item_selector)))
                models = [span.text.strip() for span in items if span.text.strip()]
                if not models: # If primary failed, try simpler li span
                     logger.debug("Primary dropdown selector yielded no models, trying fallback 'li span'")
                     items = WebDriverWait(self.driver, 3).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li span")))
                     models = [span.text.strip() for span in items if span.text.strip()]
                logger.info(f"Discovered models from dropdown: {models}")
            except TimeoutException:
                 logger.error(f"Could not find model list items using selectors.")
                 models = []

            # Attempt to close dropdown by clicking button again (safer)
            try:
                logger.debug("Attempting to close dropdown by clicking button again.")
                model_button.click() 
            except Exception as close_e:
                logger.warning(f"Minor error clicking model button to close dropdown: {close_e}. Trying body click.")
                try: self.driver.find_element(By.TAG_NAME, "body").click()
                except: logger.warning("Body click also failed to close dropdown.")

            return models
        except Exception as e:
            logger.error(f"General error during get_available_models: {e}", exc_info=True)
            try: self.driver.find_element(By.TAG_NAME, "body").click() # Cleanup click
            except: pass
            return []

    def select_model(self, model_name: str) -> bool:
        """Select a model by name from the UI dropdown."""
        try:
            logger.info(f"Attempting to select model: {model_name}")
            # 1) Open dropdown (reuse discovery logic)
            model_button_selectors = [
                "button[id='model-selector']", 
                "button > div[class*='items-center'] > span", 
                "button[class*='text-token-text-primary'][aria-haspopup='menu']"
            ]
            model_button = None
            # Find the button first to click it again later if needed
            for selector in model_button_selectors:
                 try:
                     candidate = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                     button_text = candidate.text.lower()
                     if 'gpt' in button_text or '4' in button_text or '3.5' in button_text or 'o' in button_text or 'model' in button_text:
                          model_button = candidate
                          logger.debug(f"Found model selector button for selection using: {selector}")
                          break
                 except TimeoutException: continue
            
            if not model_button:
                logger.error("Could not find model selector button to open for selection.")
                return False

            logger.debug("Clicking model selector button to open.")
            model_button.click()
            time.sleep(0.5)

            # 2) Find and click the specific model item using XPath contains text
            xpath_safe_model_name = model_name.replace("'", "\\'").replace("\"", "\\\"")
            # More robust XPath looking for button within LI containing the span
            model_xpath = f"//div[@role='menu']//li//button[.//span[normalize-space()='{xpath_safe_model_name}']]"
            try:
                 model_element = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, model_xpath)))
                 logger.debug(f"Found model element using XPath: {model_xpath}")
                 model_element.click()
                 logger.info(f"Clicked model element for: {model_name}")
                 time.sleep(1.5) # Wait for UI to update
                 # Verify selection change (optional but recommended)
                 # try: 
                 #    current_selection_text = model_button.text 
                 #    if model_name in current_selection_text: logger.info("Selection visually confirmed.")
                 #    else: logger.warning("Selection visually NOT confirmed on button.")
                 # except: logger.warning("Could not visually confirm selection.")
                 return True
            except TimeoutException:
                 logger.error(f"Model '{model_name}' not found/clickable with XPath: {model_xpath}")
                 # Attempt to close dropdown before failing
                 try: 
                     logger.debug("Closing dropdown after failed selection attempt.")
                     model_button.click() 
                 except: pass 
                 return False

        except Exception as e:
            logger.error(f"Error during select_model for '{model_name}': {e}", exc_info=True)
            try: self.driver.find_element(By.TAG_NAME, "body").click() # Cleanup click
            except: pass
            return False

    def is_rate_limited(self) -> bool:
        """Check for common rate limit / capacity banners."""
        try:
            # Case-insensitive XPath check
            rate_limit_xpath = "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'too many requests') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'at capacity') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'limit reached')]"
            banners = self.driver.find_elements(By.XPATH, rate_limit_xpath)
            rate_limited = False
            for banner in banners:
                try:
                    if banner.is_displayed():
                        logger.warning(f"Rate limit or capacity banner detected: '{banner.text[:100]}...'")
                        rate_limited = True
                        break # Found one, no need to check others
                except StaleElementReferenceException: continue 
            if not rate_limited: logger.debug("No rate limit banners detected.")
            return rate_limited
        except Exception as e:
            logger.error(f"Error checking for rate limit banners: {e}", exc_info=True)
            return False 


    # ————————————————————————————————————————————
    # ADDED: Unified Prompt + Fail-Over Method
    # ————————————————————————————————————————————
    def prompt_with_fallback(self, prompt: str, preferred_models: List[str] = None, queue_fn=None):
        """
        Attempts to send a prompt using a prioritized list of models, handling discovery and rate limits.
        """
        logger.info("Executing prompt_with_fallback...")
        if preferred_models is None:
            preferred_models = ["GPT-4o", "GPT-4", "GPT-3.5"] # Default preferences

        # Default queue function
        if queue_fn is None:
            def default_queue_fn(p): logger.error(f"QUEUE_FN (Default): Dropping prompt: {p[:100]}...")
            queue_fn = default_queue_fn

        # 1) Discover available models
        available_models = self.get_available_models()
        if not available_models:
            logger.error("prompt_with_fallback: Could not discover any available models.")
            queue_fn(prompt)
            return ""
        
        # Create mapping for case-insensitive matching if needed
        available_models_lower = {m.lower(): m for m in available_models}
        preferred_models_lower = [p.lower() for p in preferred_models]

        # 2) Build priority list
        priority_list_actual_case = []
        for pref_lower in preferred_models_lower:
            if pref_lower in available_models_lower:
                priority_list_actual_case.append(available_models_lower[pref_lower])
                del available_models_lower[pref_lower] # Remove from available to avoid duplication
        # Add remaining available models (those not in preferred list)
        priority_list_actual_case.extend(available_models_lower.values())
        
        if not priority_list_actual_case:
             logger.error("prompt_with_fallback: No usable models found after filtering.")
             queue_fn(prompt)
             return ""

        logger.info(f"Effective model priority list: {priority_list_actual_case}")

        # 3) Try each model
        for model_name in priority_list_actual_case:
            logger.info(f"--- Attempting model: {model_name} ---")
            if not self.select_model(model_name):
                logger.warning(f"Failed to select model '{model_name}'. Skipping.")
                continue 

            if self.is_rate_limited():
                logger.warning(f"Model '{model_name}' appears rate-limited. Skipping.")
                continue 

            logger.info(f"Attempting to send prompt using '{model_name}'...")
            if not self.send_prompt(prompt): 
                logger.error(f"Failed to send prompt using '{model_name}'. Skipping.")
                continue 

            logger.info(f"Prompt sent with '{model_name}'. Waiting for stable response...")
            response = self.wait_for_stable_response() 
            
            if response:
                logger.info(f"SUCCESS: Received non-empty response from '{model_name}'.")
                # Log successful model choice? 
                # log_metadata = {"model_used": model_name, ...}
                # log_ai_output(..., metadata=log_metadata) # Needs change in wait_for_stable_response
                return response 

            logger.warning(f"Model '{model_name}' returned empty response. Trying next...")

        # 4) All models failed
        logger.error("All attempted models failed to provide a response.")
        queue_fn(prompt) 
        return ""

    # ————————————————————————————————————————————
    # ADDED: Scrolling Utility
    # ————————————————————————————————————————————
    def scroll_to_bottom(self, pause_time: float = 0.5):
        """Scrolls the window to the bottom and pauses briefly."""
        logger.debug("Scrolling to bottom of page...")
        try:
            # Get initial scroll height
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            while True:
                 # Scroll down to bottom
                 self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                 # Wait to load page
                 time.sleep(pause_time)
                 # Calculate new scroll height and compare with last scroll height
                 new_height = self.driver.execute_script("return document.body.scrollHeight")
                 if new_height == last_height:
                      logger.debug("Reached bottom of page.")
                      break
                 last_height = new_height
            # One final scroll just in case
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.2)
        except Exception as e:
            logger.error(f"Error during scroll_to_bottom: {e}", exc_info=True)


# ---------------------------
# Example CLI Usage
# ---------------------------
if __name__ == "__main__":
    handler = ResponseHandler(timeout=180, stable_period=10)

    # Example single prompt usage
    single_prompt = (
        "You are my devlog assistant. Summarize the recent development work with a focus on challenges overcome and what's next."
    )
    single_response = handler.execute_prompt_cycle(single_prompt, rate_limit=2)
    if single_response:
        logger.info(f"\n--- Single Prompt Response ---\n{single_response}\n")
        # If the response is hybrid, pass it to your prompt manager (assuming it's defined)
        # e.g., handler.handle_hybrid_response(single_response, prompt_manager_instance, chat_title="Devlog Chat")
    else:
        logger.warning("No stable response received for single prompt.")

    # Example multi-chat usage: define example chats
    chat_list = [
        {"title": "Chat #1", "link": "https://chatgpt.com/c/67d7521e-acf0-8009-aed6-2748b3b49249"},
        {"title": "Chat #2", "link": "https://chatgpt.com/c/67d774ad-8bfc-8009-a488-6b5392f1326f"}
    ]

    prompts_to_send = [
        "What are the main project goals?",
        "How can we improve the architecture further?"
    ]

    all_chat_results = handler.execute_prompts_on_all_chats(prompts=prompts_to_send, chat_list=chat_list, rate_limit=2)
    for chat_name, responses in all_chat_results.items():
        logger.info(f"\n--- Chat '{chat_name}' Responses ---")
        for i, resp in enumerate(responses, start=1):
            logger.info(f"Prompt #{i} response:\n{resp}\n")

    handler.shutdown()