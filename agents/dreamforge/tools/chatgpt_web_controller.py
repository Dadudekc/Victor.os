\"\"\"
Controller for interacting with the ChatGPT web UI using Selenium.

Adapted from core_bak/utils_to_merge/browser_controller.py
\"\"\"
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException,
    ElementClickInterceptedException
)
import time
import json
import random
import os
import traceback
import logging # Use standard logging

# TODO: Resolve this import - either create browser_utils or integrate get_undetected_driver here
try:
    from .browser_utils import get_undetected_driver
except ImportError:
    # Placeholder if browser_utils doesn't exist yet
    logging.warning(\"Could not import get_undetected_driver from .browser_utils. Using basic uc.Chrome.\")
    def get_undetected_driver(user_data_dir=None, headless=True):
         options = uc.ChromeOptions()
         if headless:
             options.add_argument('--headless')
         # Add other options as needed
         return uc.Chrome(options=options, user_data_dir=user_data_dir)


logger = logging.getLogger(__name__) # Standard Python logger

AGENT_ID = \"ChatGPTWebController\" # Identify this controller in logs

class ChatGPTWebController:
    def __init__(self, user_data_dir=\"chrome_user_data\", headless=True, cookies_path=\"openai_cookies.json\"):
        \"\"\"Initializes the browser controller.\"\"\"
        self.driver = None
        self.user_data_dir = os.path.abspath(user_data_dir) # Use absolute path
        self.headless = headless
        self.cookies_path = cookies_path

        logger.info(f\"[{AGENT_ID}] Initializing. Headless: {headless}, Cookies: {cookies_path}, User Data Dir: {self.user_data_dir}\")

        # Common CSS Selectors (Review and update if ChatGPT UI changes)
        self.selectors = {
            \"textarea\": \"#prompt-textarea\",
            \"send_button\": \'[data-testid=\"send-button\"]\',
            \"response_block\": \"//div[contains(@class, \'text-message\')]//div[contains(@class, \'markdown\')]\", # Specific XPath
            \"chat_list_item\": \"//nav//a[contains(@href, \'/c/\')]/div[1]\", # XPath for chat titles
            \"login_page_indicator\": \'button[contains(text(), "Log in")]\' # XPath
        }

    def _initialize_driver(self):
        \"\"\"Initializes the undetected ChromeDriver.\"\"\"
        if not self.driver:
            logger.info(f\"[{AGENT_ID}] Initializing WebDriver (Headless: {self.headless}, User Data: {self.user_data_dir})...\")
            try:
                # Ensure user_data_dir exists or is handled by get_undetected_driver
                if self.user_data_dir and not os.path.exists(self.user_data_dir):
                     logger.warning(f\"[{AGENT_ID}] User data directory specified but not found: {self.user_data_dir}. uc.Chrome might create it.\")
                self.driver = get_undetected_driver(user_data_dir=self.user_data_dir, headless=self.headless)
                logger.info(f\"[{AGENT_ID}] WebDriver initialized.\")
            except Exception as e:
                logger.error(f\"[{AGENT_ID}] Error initializing WebDriver: {e}\", exc_info=True)
                raise # Re-raise as this is critical
        return self.driver

    def _load_cookies(self):
        \"\"\"Loads cookies from the specified file.\"\"\"
        if not os.path.exists(self.cookies_path):
            logger.warning(f\"[{AGENT_ID}] Cookies file not found at {self.cookies_path}. Cannot load cookies.\")
            return False

        try:
            with open(self.cookies_path, \'r\') as f:
                cookies = json.load(f)
            for cookie in cookies:
                # Handle potential SameSite attribute issues if needed
                if \'sameSite\' in cookie and cookie[\'sameSite\'] not in [\'Strict\', \'Lax\', \'None\']:\
                     logger.debug(f\"[{AGENT_ID}] Adjusting invalid SameSite attribute \'{cookie['sameSite']}\' to \'Lax\' for cookie: {cookie['name']}\")
                     cookie[\'sameSite\'] = \'Lax\' # Default adjustment
                try:
                    self.driver.add_cookie(cookie)
                except Exception as cookie_err:
                     logger.warning(f\"[{AGENT_ID}] Failed to add cookie: {cookie.get('name', 'N/A')}. Error: {cookie_err}\")

            logger.info(f\"[{AGENT_ID}] Attempted to load {len(cookies)} cookies from {self.cookies_path}.\")
            return True
        except Exception as e:
            logger.error(f\"[{AGENT_ID}] Error loading cookies from {self.cookies_path}: {e}\", exc_info=True)
            return False

    def login_to_chatgpt(self, login_url=\"https://chat.openai.com/\"):
        \"\"\"Navigates to ChatGPT and uses cookies to authenticate.\"\"\"
        logger.info(f\"[{AGENT_ID}] Attempting login to {login_url}...\")
        self._initialize_driver()
        self.driver.get(login_url)
        time.sleep(3) # Allow initial page load

        if not self._load_cookies():
            logger.warning(f\"[{AGENT_ID}] Proceeding without loading cookies. Manual login might be required or session may be invalid.\")
            # Don't necessarily return False here, let the check below determine success

        logger.info(f\"[{AGENT_ID}] Refreshing page to apply cookies...\")
        self.driver.refresh()
        time.sleep(6) # Increase wait after refresh for potential redirects/JS execution

        # Check if login was successful (presence of textarea is a good indicator)
        try:
            WebDriverWait(self.driver, 20).until( # Increased wait
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors[\"textarea\"]))
            )
            logger.info(f\"[{AGENT_ID}] Login check successful (textarea found).\")
            return True
        except TimeoutException:
            logger.warning(f\"[{AGENT_ID}] Login check failed: Textarea not found after cookie load and refresh.\")
            # Optional: Check for explicit login page elements
            try:
                 self.driver.find_element(By.XPATH, self.selectors[\"login_page_indicator\"])
                 logger.warning(f\"[{AGENT_ID}] Detected elements indicating a login page. Cookies likely invalid or expired.\")
            except NoSuchElementException:
                 logger.warning(f\"[{AGENT_ID}] Could not confirm if on login page, but login seems to have failed.\")
            return False
        except Exception as e:
             logger.error(f\"[{AGENT_ID}] Unexpected error during login check: {e}\", exc_info=True)
             return False

    def find_and_click_chat(self, title_keyword):
        \"\"\"Finds and clicks on a chat based on a keyword in its title.\"\"\"
        logger.info(f\"[{AGENT_ID}] Searching for chat containing keyword: \'{title_keyword}\'...\")
        try:
            # Wait for chat list items (using the chat title selector directly)
            chat_elements = WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located((By.XPATH, self.selectors[\"chat_list_item\"]))
            )
            logger.info(f\"[{AGENT_ID}] Found {len(chat_elements)} potential chats in the sidebar.\")

            matched_element = None
            for chat_element in chat_elements:
                try:
                    # Get title text, handle potential stale elements
                    title = chat_element.text
                    # logger.debug(f\"Checking chat: {title}\") # Uncomment for debugging
                    if title_keyword.lower() in title.lower():
                        logger.info(f\"[{AGENT_ID}] Match found: \'{title}\'\")
                        matched_element = chat_element
                        break
                except StaleElementReferenceException:
                    logger.warning(f\"[{AGENT_ID}] Stale element reference encountered while checking chat list. Retrying find.\")
                    # Optionally re-fetch elements here if needed, or just continue
                    return self.find_and_click_chat(title_keyword) # Simple retry
                except Exception as e:
                    logger.warning(f\"[{AGENT_ID}] Error processing chat element: {e}\")
                    continue # Skip this element

            if matched_element:
                logger.info(f\"[{AGENT_ID}] Clicking matched chat: \'{matched_element.text}\'\")
                try:
                    matched_element.click()
                    time.sleep(3) # Wait for chat content to load
                    return True
                except ElementClickInterceptedException:
                     logger.warning(f\"[{AGENT_ID}] Click intercepted for chat \'{matched_element.text}\'. Trying JS click.\")
                     self.driver.execute_script(\"arguments[0].click();\", matched_element)
                     time.sleep(3)
                     return True
                except Exception as e:
                    logger.error(f\"[{AGENT_ID}] Failed to click chat \'{matched_element.text}\': {e}\", exc_info=True)
                    return False
            else:
                 logger.info(f\"[{AGENT_ID}] Keyword \'{title_keyword}\' not found in visible chats. Selecting the latest chat.\")
                 if chat_elements:
                      try:
                           latest_chat = chat_elements[0]
                           logger.info(f\"[{AGENT_ID}] Clicking latest chat: \'{latest_chat.text}\'\")
                           latest_chat.click()
                           time.sleep(3)
                           return True
                      except ElementClickInterceptedException:
                           logger.warning(f\"[{AGENT_ID}] Click intercepted for latest chat \'{latest_chat.text}\'. Trying JS click.\")
                           self.driver.execute_script(\"arguments[0].click();\", latest_chat)
                           time.sleep(3)
                           return True
                      except Exception as e:
                           logger.error(f\"[{AGENT_ID}] Failed to click latest chat \'{latest_chat.text}\': {e}\", exc_info=True)
                           return False
                 else:
                      logger.warning(f\"[{AGENT_ID}] Chat keyword not found, and no chats available in the list.\")
                      return False

        except TimeoutException:
             logger.error(f\"[{AGENT_ID}] Could not find chat list items (Timeout). Is the page loaded correctly and sidebar visible?\")
             return False
        except Exception as e:
            logger.error(f\"[{AGENT_ID}] An error occurred while searching for/clicking chat: {e}\", exc_info=True)
            return False

    def send_message(self, message, type_speed=0.03):
        \"\"\"Sends a message to the currently open chat.\"\"\"
        logger.info(f\"[{AGENT_ID}] Sending message (Length: {len(message)})...\")
        try:
            # Ensure textarea is present and clear it first
            textarea = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors[\"textarea\"]))
            )
            textarea.clear()
            # Add a small delay after clearing
            time.sleep(0.2)

            if type_speed > 0:
                 logger.debug(f\"[{AGENT_ID}] Simulating typing...\")
                 for char in message:
                     textarea.send_keys(char)
                     time.sleep(random.uniform(type_speed * 0.6, type_speed * 1.4))
                 time.sleep(0.5) # Pause after typing
            else:
                 logger.debug(f\"[{AGENT_ID}] Sending instantly...\")
                 textarea.send_keys(message)
                 time.sleep(0.2) # Small delay even for instant send

            # Find and click the send button
            send_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors[\"send_button\"]))
            )
            # Ensure button is not disabled (often indicates message sending isn't allowed yet)
            if not send_button.is_enabled():
                 logger.warning(f\"[{AGENT_ID}] Send button found but is not enabled. Waiting briefly...\")
                 time.sleep(1) # Wait a moment and re-check
                 send_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors[\"send_button\"]))
                 )
                 if not send_button.is_enabled():
                      raise Exception(\"Send button remained disabled.\")

            send_button.click()
            logger.info(f\"[{AGENT_ID}] Message sent successfully.\")
            return True

        except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as e:
             logger.error(f\"[{AGENT_ID}] Send message failed: Textarea or Send button not found/clickable/enabled: {e}\", exc_info=True)
             return False
        except Exception as e:
            logger.error(f\"[{AGENT_ID}] An unexpected error occurred while sending message: {e}\", exc_info=True)
            return False

    def get_latest_response(self, timeout=180): # Increased default timeout
        \"\"\"Waits for and retrieves the latest response text from ChatGPT.\"\"\"
        logger.info(f\"[{AGENT_ID}] Waiting for response (Timeout: {timeout}s)...\")
        start_time = time.time()
        try:
            # Wait until the response generation seems complete
            # Primary check: Send button is clickable again
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.selectors[\"send_button\"]))
            )
            logger.debug(f\"[{AGENT_ID}] Send button became clickable after {time.time() - start_time:.2f}s.\")

            # Secondary check: Ensure no "Stop generating" button is visible (more robust)
            # This requires a short wait as the stop button might disappear slightly after send enables
            time.sleep(0.5)
            try:
                stop_button = self.driver.find_element(By.XPATH, \"//button[contains(., 'Stop generating')]\")
                if stop_button.is_displayed():
                     logger.warning(f\"[{AGENT_ID}] Send button clickable, but 'Stop generating' still visible. Waiting longer...\")
                     WebDriverWait(self.driver, timeout - (time.time() - start_time)).until_not(
                          EC.visibility_of_element_located((By.XPATH, \"//button[contains(., 'Stop generating')]\"))
                     )
                     logger.debug(f\"[{AGENT_ID}] 'Stop generating' button disappeared after {time.time() - start_time:.2f}s.\")
            except NoSuchElementException:
                 logger.debug(f\"[{AGENT_ID}] 'Stop generating' button not found (expected).\")
                 pass # Expected case

            # Give a brief moment for the final content to settle after generation stops
            time.sleep(1.5) # Slightly longer settle time

            # Find all response blocks
            response_blocks = self.driver.find_elements(By.XPATH, self.selectors[\"response_block\"])

            if not response_blocks:
                 logger.warning(f\"[{AGENT_ID}] No response blocks found after waiting for generation to complete.\")
                 return None

            # Get the text from the last response block
            last_response_element = response_blocks[-1]
            response_text = last_response_element.text
            duration = time.time() - start_time
            logger.info(f\"[{AGENT_ID}] Response received successfully (Took {duration:.2f}s).\")
            return response_text

        except TimeoutException:
            duration = time.time() - start_time
            logger.error(f\"[{AGENT_ID}] Timed out waiting for response completion (>{duration:.1f}s). Send button may not have re-enabled or 'Stop generating' persisted.\")
            # Attempt recovery check
            try:
                response_blocks = self.driver.find_elements(By.XPATH, self.selectors[\"response_block\"])
                if response_blocks:
                    logger.warning(f\"[{AGENT_ID}] Found a response block after timeout, attempting to retrieve.\")
                    return response_blocks[-1].text
            except Exception as recovery_e:
                 logger.error(f\"[{AGENT_ID}] Error during response recovery attempt after timeout: {recovery_e}\")
            return None
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f\"[{AGENT_ID}] An unexpected error occurred while getting response (after {duration:.1f}s): {e}\", exc_info=True)
            return None

    def close(self):
        \"\"\"Closes the browser.\"\"\"
        if self.driver:
            logger.info(f\"[{AGENT_ID}] Closing browser...\")
            try:
                self.driver.quit()
                logger.info(f\"[{AGENT_ID}] Browser closed.\")
            except Exception as e:
                 logger.error(f\"[{AGENT_ID}] Error encountered while quitting WebDriver: {e}\", exc_info=True)
            self.driver = None

    def __enter__(self):
        \"\"\"Context manager entry: initializes driver.\"\"\"
        self._initialize_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        \"\"\"Context manager exit: closes driver.\"\"\"
        self.close() 