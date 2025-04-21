import os
import time
import logging
import re
from typing import List, Dict, Optional, Any

# --- Selenium Imports ---
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc 
# -------------------------

# Import the driver manager
from .core.UnifiedDriverManager import UnifiedDriverManager
# Import the new Locators class
from .chatgpt_locators import ChatGPTLocators 

# Still need project config for logging level
# Try importing relative to this file location (src/)
try:
    from .. import config as project_config 
except ImportError:
    # Fallback if run directly or config is elsewhere?
    try:
        from dreamscape_generator import config as project_config
    except ImportError:
        # Last resort default
        class MockConfig: LOG_LEVEL = logging.INFO
        project_config = MockConfig()

logger = logging.getLogger(__name__)
# Ensure logger level is set if config was loaded
if hasattr(project_config, 'LOG_LEVEL'):
    logger.setLevel(project_config.LOG_LEVEL)
else:
    logger.setLevel(logging.INFO)


class ChatGPTScraper:
    """Handles interaction with the ChatGPT web UI using Selenium/undetected-chromedriver."""

    # --- Selectors Removed - Now using ChatGPTLocators ---
    # LOGIN_CHECK_SELECTOR = 'nav[aria-label=\"Chat history\"]' 
    # PROMPT_INPUT_SELECTOR = \"div.ProseMirror[contenteditable='true']\"
    # RESPONSE_CONTAINER_SELECTOR = \"div[data-testid^='conversation-turn-']\"
    # RESPONSE_MARKDOWN_SELECTOR = \".markdown\"
    # STOP_GENERATING_BUTTON_SELECTOR = \"button[aria-label='Stop generating']\"
    # REGENERATE_BUTTON_SELECTOR = \"button.btn-secondary > div:contains('Regenerate')\"

    def __init__(self, manager: UnifiedDriverManager, stable_timeout: int = 10, poll_interval: float = 0.5):
        """Initialize with the driver manager."""
        if not isinstance(manager, UnifiedDriverManager):
             raise TypeError("Manager must be an instance of UnifiedDriverManager")
        self.manager = manager
        self.driver: Optional[uc.Chrome] = None # Driver will be fetched from manager
        self.stable_timeout = stable_timeout # Seconds response must be stable
        self.poll_interval = poll_interval # How often to check response
        logger.info("ChatGPTScraper initialized (using UnifiedDriverManager).")

    def _get_driver(self) -> Optional[uc.Chrome]:
        """Helper to get the driver instance from the manager."""
        # Ensure driver is fetched only when needed and is potentially refreshed
        self.driver = self.manager.get_driver() 
        return self.driver

    def send_prompt(self, prompt: str, *, model="gpt-4o", reverse=False) -> str:
        """Sends prompt using Selenium/UC, waits for stable response."""
        logger.info(f"send_prompt(): Using Selenium/UC. Model='{model}', Reverse='{reverse}'")
        
        try:
            driver = self._get_driver()
            if not driver:
                 logger.error("Failed to get WebDriver instance from manager.")
                 return "[ERROR] Failed to get WebDriver instance."

            # 1 --- Check login status (uses manager's method) --- 
            # --- Skip login check if running headless ---
            if not self.manager.headless:
                 if not self.manager.is_logged_in():
                      logger.error("Login check failed. Please ensure you are logged into ChatGPT manually or cookies are valid.")
                      return "[ERROR] Login required or verification failed. Please log in via browser first."
            # -------------------------------------------
            # else:
                 # Ensure we are on the main chat page if already logged in
                 # if not driver.current_url.startswith(self.manager.CHATGPT_URL):
                 #      logger.info("Not on main chat page, navigating...")
                 #      driver.get(self.manager.CHATGPT_URL)
                 #      time.sleep(2) # Wait for page load
                 # else:
                 #      logger.info("Already on main chat page.")

            # 2 --- Navigate to Correct Model URL --- 
            # Construct target URL with model parameter
            # Ensure base URL in manager doesn't have trailing slash for clean join
            base_url = self.manager.CHATGPT_URL.rstrip('/')
            target_url = f"{base_url}/?model={model}"
            
            # Navigate to the specific model URL
            logger.info(f"Navigating to model-specific URL: {target_url}")
            driver.get(target_url)
            # Wait for page load or prompt element after navigation
            post_nav_wait = WebDriverWait(driver, 30) # Increased timeout to 30s
            try:
                 # Wait for the prompt area to be ready after navigation
                 post_nav_wait.until(EC.element_to_be_clickable(ChatGPTLocators.TEXT_INPUT_AREA))
                 logger.info("Page loaded for the selected model.")
            except TimeoutException:
                 logger.error(f"Timeout waiting for page/prompt area after navigating to {target_url}")
                 return f"[ERROR] Timeout loading page for model {model}."
            # -------------------------------------

            # --- Remove old Model Selection Logic --- 
            # wait = WebDriverWait(driver, self.manager.wait_timeout)
            # try:
                # Find the button indicating the current model
                # ... (removed all the button/menu clicking logic) ...
            # except Exception as model_err:
            #      logger.error(f"Error during model selection for '{model}': {model_err}", exc_info=True)
            #      logger.warning("Proceeding with potentially incorrect model due to selection error.")
            # -------------------------

            # 3 --- Find input, clear if needed, send prompt --- 
            logger.info(f"Waiting for prompt input using locator: {ChatGPTLocators.TEXT_INPUT_AREA}")
            # wait = WebDriverWait(driver, self.manager.wait_timeout) # Wait already defined
            input_box = post_nav_wait.until(
                EC.element_to_be_clickable(ChatGPTLocators.TEXT_INPUT_AREA) # Use locator
            )
            # input_box.clear() # Clear existing text if necessary, can be slow/unreliable
            input_box.click() # Ensure focus
            logger.info("Sending prompt keys...")
            # ---> Log the exact prompt being sent <--- 
            logger.debug(f"PROMPT_CONTENT_TO_SEND:\n---\n{prompt}\n---") 
            # --- Send whole prompt at once for reliability ---
            # Replace newlines with spaces, as seen in quorum_web_simulation
            prompt_to_send = prompt.replace('\n', ' ')
            input_box.send_keys(prompt_to_send) 
            # --- Remove character-by-character loop ---
            # for char in prompt:
            #      input_box.send_keys(char)
            #      time.sleep(0.01) # Small delay
            # ---------------------------------------------
            # Ensure focus again before sending Enter?
            input_box.send_keys(Keys.ENTER)
            logger.info("Prompt submitted.")

            # 4 --- Wait for stable response --- 
            response = self._wait_for_stable_response(driver)
            return response
            
        except TimeoutException as te:
             logger.error(f"Timeout interacting with ChatGPT UI: {te}", exc_info=True)
             return f"[ERROR] Timeout: {te}"
        except Exception as e:
            logger.error(f"Error during send_prompt: {e}", exc_info=True)
            return f"[ERROR] Interaction failed: {e}"
        # Note: Driver quitting is handled by the UnifiedDriverManager

    def _fetch_latest_response_text(self, driver: uc.Chrome) -> Optional[str]:
        """Gets the text content of the last response message block."""
        try:
            # Find all response markdown blocks directly using the new locator
            logger.debug(f"Fetching response elements using: {ChatGPTLocators.ASSISTANT_MESSAGE_SELECTOR}")
            response_elements = driver.find_elements(*ChatGPTLocators.ASSISTANT_MESSAGE_SELECTOR) # Use locator with *
            
            if not response_elements:
                 return None # No response markdown found

            last_response_text = response_elements[-1].text.strip()
            return last_response_text

        except NoSuchElementException:
             logger.warning("Could not find assistant message element.")
             return None # Element structure changed?
        except Exception as e:
             logger.warning(f"Error fetching latest response text: {e.__class__.__name__}")
             return None

    def _wait_for_stable_response(self, driver: uc.Chrome) -> str:
        """Waits until the response text stops changing or timeout occurs."""
        logger.info("Waiting for stable ChatGPT response...")
        start_time = time.time()
        last_response: Optional[str] = None
        stable_start_time: Optional[float] = None
        
        # Wait briefly for submission to register before first check
        time.sleep(1.0) 

        # Adjust overall timeout based on manager settings? 
        overall_timeout = max(self.manager.wait_timeout * 8, 120) # e.g., 8x wait_timeout or 120s min
        
        while time.time() - start_time < overall_timeout:
            is_generating = False
            # Check if the 'Stop generating' or 'Regenerate' button is present and visible
            try:
                 # Check for stop button first
                 logger.debug(f"Checking for stop button using: {ChatGPTLocators.STOP_GENERATING_BUTTON}")
                 stop_button = driver.find_element(*ChatGPTLocators.STOP_GENERATING_BUTTON) # Use locator with *
                 if stop_button.is_displayed():
                      is_generating = True
                 else:
                    # If stop not visible, check for regenerate button (appears when finished)
                     try:
                          logger.debug(f"Checking for regenerate button using: {ChatGPTLocators.REGENERATE_BUTTON}")
                          regen_button = driver.find_element(*ChatGPTLocators.REGENERATE_BUTTON) # Use locator with *
                          if regen_button.is_displayed():
                               is_generating = False # Found regenerate, so it stopped
                     except NoSuchElementException:
                          logger.debug("Neither Stop nor Regenerate button found.")
                          is_generating = False 
                                 
            except NoSuchElementException:
                 is_generating = False
            except Exception as btn_err:
                 logger.warning(f"Error checking generation state buttons: {btn_err}")
                 is_generating = False 

            if is_generating:
                 stable_start_time = None # Reset stability timer while generating
                 logger.debug("Response still generating (stop button visible)...")
                 time.sleep(self.poll_interval * 2) # Longer sleep if generating
                 continue # Check buttons again
            
            # --- If not generating, check response text --- 
            current_response = self._fetch_latest_response_text(driver)

            if current_response is None:
                 # No response found yet
                 if last_response is None and (time.time() - start_time) > 20:
                     logger.warning("No response element found after 20s. Structure change?")
                 time.sleep(self.poll_interval)
                 continue

            # Normalize whitespace for comparison?
            current_norm = " ".join(current_response.split())
            last_norm = " ".join(last_response.split()) if last_response is not None else None

            # Check for stability
            if current_norm != last_norm:
                # Response changed, update and reset timer
                logger.debug(f"Response changed (Length: {len(current_response)}). Resetting stability timer.")
                last_response = current_response
                stable_start_time = time.time()
            elif stable_start_time and (time.time() - stable_start_time) >= self.stable_timeout:
                # Response has been stable for the required duration
                logger.info(f"Response stabilized after {time.time() - stable_start_time:.2f}s (Total length: {len(last_response)}).")
                return last_response # Return the stable response
            elif stable_start_time is None:
                 # Response hasn't changed, but timer wasn't started (first stable check)
                 stable_start_time = time.time()
                 
            # Wait before next poll
            time.sleep(self.poll_interval)

        # Timeout reached
        logger.warning(f"Response stabilization timeout ({overall_timeout}s) reached.")
        if last_response:
             logger.warning("Returning last fetched response (might be incomplete).")
             return last_response
        else:
             logger.error("No response fetched before timeout.")
             return "[ERROR] Timeout waiting for response."


# --- Keep scraping methods below, marked as needing rewrite ---

    def get_all_chat_titles(self) -> List[Dict[str, str]]:
        # logger.warning("get_all_chat_titles NEEDS rewrite for Selenium/UC!")
        # TODO: Implement using locators from ChatGPTLocators
        # return [] 
        # --- Implementation --- 
        logger.info("Attempting to fetch all chat titles...")
        chat_list = []
        driver = self._get_driver()
        if not driver:
            logger.error("Driver not available for fetching chat titles.")
            return chat_list

        # This requires non-headless and likely logged in state
        if self.manager.headless:
            logger.warning("Cannot fetch chat history in headless mode.")
            return chat_list
        if not self.manager.is_logged_in():
            logger.warning("Not logged in, cannot fetch chat history.")
            # Optionally trigger manual login prompt here? For now, just return empty.
            return chat_list
            
        try:
            # Ensure we are on the main page
            if not driver.current_url.startswith(self.manager.CHATGPT_URL):
                 driver.get(self.manager.CHATGPT_URL)
                 time.sleep(3) # Wait for redirects/load
                 
            # Wait for the history sidebar to be present
            wait = WebDriverWait(driver, self.manager.wait_timeout)
            history_sidebar = wait.until(
                EC.presence_of_element_located(ChatGPTLocators.HISTORY_SIDEBAR)
            )
            logger.debug("History sidebar found.")

            # --- Find the specific scrollable container --- 
            try:
                scroll_container = history_sidebar.find_element(*ChatGPTLocators.HISTORY_SCROLL_CONTAINER)
                logger.debug("Scroll container identified.")
            except NoSuchElementException:
                 logger.warning("Could not find specific scroll container, attempting scroll on sidebar nav itself.")
                 scroll_container = history_sidebar # Fallback to original element
            # -------------------------------------------
            
            # --- Implement Scrolling --- 
            found_links = set() # Keep track of unique hrefs
            chat_list_temp = [] # Temporary list to hold results during scrape
            last_link_count = -1 # Use -1 to ensure the first loop runs
            scroll_attempts_without_new = 0
            max_scroll_stalls = 3 # Stop if no new links found for this many scrolls
            
            while scroll_attempts_without_new < max_scroll_stalls:
                # Find all link elements currently within the sidebar (still use sidebar to find links)
                link_elements = history_sidebar.find_elements(*ChatGPTLocators.HISTORY_LINK_ITEM)
                
                current_loop_found_new = False
                for link_element in link_elements:
                    try:
                        href = link_element.get_attribute('href')
                        # Check if we already processed this link
                        if href and href not in found_links:
                            found_links.add(href) # Add to set immediately
                            current_loop_found_new = True # Mark that we found something new overall
                            
                            # Try to get the title
                            try:
                                title_div = link_element.find_element(*ChatGPTLocators.HISTORY_TITLE_TEXT)
                                title = title_div.text.strip()
                                if title:
                                    chat_list_temp.append({'title': title, 'link': href})
                                    logger.debug(f"  -> Found New: '{title}' ({href})")
                                else:
                                    logger.debug(f"  -> Skipping new href with empty title: {href}")
                            except NoSuchElementException:
                                logger.debug(f"  -> Skipping href, could not find title div relative to link: {href}")
                                
                    except Exception as item_err:
                         # Log error for specific item but continue scraping others
                         logger.warning(f"Error processing a potential chat history item: {item_err}")

                # Check if the total count of unique links has increased
                if len(found_links) > last_link_count:
                    logger.info(f"Scrolling history... Found {len(found_links)} unique chats so far.")
                    last_link_count = len(found_links)
                    scroll_attempts_without_new = 0 # Reset stall counter
                    
                    # Execute scroll on the identified container
                    try:
                         driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container) # <-- Use scroll_container
                    except Exception as scroll_err:
                         logger.error(f"Error executing scroll script: {scroll_err}")
                         break # Stop if scrolling fails
                    time.sleep(1.5) # Wait for items to load after scroll
                
                else:
                    # No new links found since last check
                    scroll_attempts_without_new += 1
                    logger.info(f"No new links found on scroll attempt {scroll_attempts_without_new}/{max_scroll_stalls}.")
                    if scroll_attempts_without_new >= max_scroll_stalls:
                         logger.info("Finished scrolling history sidebar (max scroll stalls reached).")
                         break
                    else:
                        # Optionally scroll again even if nothing new found
                        try:
                            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container) # <-- Use scroll_container
                            time.sleep(1.0)
                        except Exception as scroll_err:
                             logger.error(f"Error executing scroll script (retry): {scroll_err}")
                             break # Stop if scrolling fails during retry
            # --- End Scrolling Loop --- 

        except TimeoutException:
            logger.error("Timeout waiting for chat history sidebar.")
        except Exception as e:
            logger.error(f"Error fetching chat titles: {e}", exc_info=True)
            
        logger.info(f"Fetched {len(chat_list_temp)} chat titles with scroll.")
        return chat_list_temp # Return the scraped list

    def scrape_current_chat_messages(self) -> List[Dict[str, str]]:
        logger.warning("scrape_current_chat_messages NEEDS rewrite for Selenium/UC!")
        # TODO: Implement using locators from ChatGPTLocators (e.g., MESSAGE_TURN_SELECTOR)
        return []

__all__ = ["ChatGPTScraper"] 