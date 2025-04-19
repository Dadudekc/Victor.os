import os
import time
import logging
import re
from typing import List, Dict, Optional, Any

from selenium.common.exceptions import (NoSuchElementException, TimeoutException,
                                        StaleElementReferenceException)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Use project config for URL etc.
import config as project_config

# Assuming a basic driver manager stub exists for now
# In a full implementation, replace with actual UnifiedDriverManager if it exists
from .external_stubs import StubUnifiedDriverManager

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(project_config.LOG_LEVEL)

class ChatGPTScraper:
    """Handles interaction with the ChatGPT web UI for scraping history."""

    DEFAULT_CHATGPT_URL = "https://chat.openai.com/"
    SIDEBAR_SELECTOR = "div.flex-col.flex-1.transition-opacity.duration-500.relative.pr-3.overflow-y-auto" # Main scrollable sidebar
    CHAT_LINK_SELECTOR = 'nav[aria-label="Chat history"] a' # Links within the sidebar nav
    # Selectors for message content - THESE ARE LIKELY TO CHANGE WITH UI UPDATES
    # Common pattern: Look for divs with specific data-testid or class structure
    MESSAGE_CONTAINER_SELECTOR = "div[data-testid^='conversation-turn-']" # General container for a turn
    MESSAGE_ROLE_SELECTOR = "div[data-message-author-role]" # Div indicating 'user' or 'assistant'
    MESSAGE_CONTENT_SELECTOR = "div.markdown" # Div containing the actual message markdown

    def __init__(self,
                 driver_options: Optional[Dict[str, Any]] = None,
                 scroll_pause: float = 1.5,
                 headless: bool = False,
                 chatgpt_url: Optional[str] = None):

        self.scroll_pause = scroll_pause
        self.chatgpt_url = chatgpt_url or self.DEFAULT_CHATGPT_URL

        # Initialize UnifiedDriverManager with options
        drv_opts = driver_options or {}
        if headless:
            drv_opts["headless"] = True
        # Use the stub for now
        self.driver_manager = StubUnifiedDriverManager(drv_opts)
        self._driver: Optional[WebDriver] = None
        logger.info("ChatGPTScraper initialized.")

    @property
    def driver(self) -> WebDriver:
        """Lazy initializes and returns the WebDriver instance."""
        if self._driver is None:
            logger.info("Initializing WebDriver...")
            self._driver = self.driver_manager.get_driver()
        return self._driver

    def shutdown_driver(self):
        """Safely quit the WebDriver."""
        self.driver_manager.quit()
        self._driver = None
        logger.info("WebDriver has been shut down.")

    def is_logged_in(self) -> bool:
        """Checks if the user appears to be logged into ChatGPT."""
        logger.info(f"Checking login status at {self.chatgpt_url}...")
        try:
            self.driver.get(self.chatgpt_url)
            # Look for a key element that only appears when logged in, like the sidebar nav
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.CHAT_LINK_SELECTOR))
            )
            logger.info("Login check successful: Chat history navigation element found.")
            return True
        except TimeoutException:
            logger.warning("Login check failed: Timed out waiting for sidebar element. User might be logged out or UI changed.")
            # You might want to check for login page elements here too
            # e.g., EC.presence_of_element_located((By.ID, "username"))
            return False
        except Exception as e:
            # Catch other potential errors (network, driver issues)
            logger.error(f"Login check failed due to an unexpected error: {e}", exc_info=True)
            return False

    def get_all_chat_titles(self) -> List[Dict[str, str]]:
        """Retrieves all chat titles and their links from the sidebar, handling scrolling."""
        logger.info("Retrieving all chat titles from sidebar...")
        if not self.is_logged_in():
             logger.error("Cannot retrieve chat titles: Not logged in.")
             return []

        # Ensure we are on the main page after login check
        if self.DEFAULT_CHATGPT_URL not in self.driver.current_url:
            self.driver.get(self.DEFAULT_CHATGPT_URL)
            time.sleep(2) # Allow page load

        try:
            # Wait for the main scrollable sidebar div to be present
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.SIDEBAR_SELECTOR))
            )
            logger.debug("Chat sidebar container located.")
        except TimeoutException:
            logger.error("Failed to locate chat sidebar container. Cannot retrieve chats.")
            return []
        except Exception as e:
            logger.error(f"Error waiting for sidebar: {e}", exc_info=True)
            return []

        chat_links: Dict[str, str] = {}
        same_height_count = 0
        max_same_height = 3 # Stop scrolling if height doesn't change for a few cycles
        last_height = -1

        while same_height_count < max_same_height:
            # Get current scroll height
            try:
                current_height = self.driver.execute_script(
                    f"return document.querySelector('{self.SIDEBAR_SELECTOR}').scrollHeight"
                )
                if current_height == last_height:
                    same_height_count += 1
                    logger.debug(f"Scroll height unchanged ({current_height}). Count: {same_height_count}")
                else:
                    same_height_count = 0
                last_height = current_height
            except Exception as e:
                logger.warning(f"Could not get scroll height: {e}. Stopping scroll.")
                break

            # Find chat links within the currently visible part of the sidebar
            try:
                chat_elements = self.driver.find_elements(By.CSS_SELECTOR, self.CHAT_LINK_SELECTOR)
                logger.debug(f"Found {len(chat_elements)} potential chat link elements in current view.")
            except Exception as e:
                 logger.error(f"Error finding chat link elements: {e}")
                 break # Stop if we can't find elements

            stale_elements_found = False
            for chat_element in chat_elements:
                try:
                    # Check if element is still attached to the DOM
                    if not chat_element.is_displayed(): continue

                    title = chat_element.text.strip()
                    href = chat_element.get_attribute("href")

                    if title and href and title not in chat_links:
                        # Basic validation of href
                        if href.startswith(self.DEFAULT_CHATGPT_URL) or href.startswith("/"):
                             # Prepend base URL if href is relative
                             full_href = href if href.startswith("http") else self.DEFAULT_CHATGPT_URL.strip('/') + href
                             chat_links[title] = full_href
                             logger.debug(f"Collected chat: '{title}' -> {full_href}")
                        else:
                             logger.warning(f"Skipping chat '{title}' due to unexpected href: {href}")

                except StaleElementReferenceException:
                    # This is expected during dynamic loading/scrolling
                    stale_elements_found = True
                    logger.debug("Encountered stale element reference, will retry finding elements.")
                    break # Break inner loop to re-fetch elements after scroll
                except Exception as e:
                    logger.warning(f"Error processing a chat element: {e}")
                    continue # Skip this element

            if stale_elements_found:
                 logger.debug("Re-fetching elements after stale reference.")
                 time.sleep(0.5) # Brief pause before re-querying
                 continue # Go to next iteration of while loop to re-find elements

            # Scroll down if not at the bottom yet
            if same_height_count < max_same_height:
                try:
                    self.driver.execute_script(
                        f"document.querySelector('{self.SIDEBAR_SELECTOR}').scrollTop += document.querySelector('{self.SIDEBAR_SELECTOR}').clientHeight * 0.8;"
                    )
                    logger.debug("Scrolled sidebar down.")
                    time.sleep(self.scroll_pause) # Wait for content to potentially load
                except Exception as e:
                    logger.error(f"Error executing scroll script: {e}. Stopping scroll.")
                    break
            else:
                 logger.debug("Max same scroll height reached. Assuming end of list.")

        # --- Final Conversion to List[Dict] ---
        result_list = []
        for title, link in chat_links.items():
             # Can add extra filtering here if needed (e.g., exclude by pattern)
             result_list.append({"title": title, "link": link})

        logger.info(f"Finished retrieving chat titles. Total unique chats collected: {len(result_list)}")
        return result_list

    def scrape_current_chat_messages(self) -> List[str]:
        """Scrapes all messages (user and assistant) from the currently loaded chat page."""
        messages: List[str] = []
        logger.info("Scraping messages from current chat page...")

        try:
            # Wait briefly for message containers to likely be present
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.MESSAGE_CONTAINER_SELECTOR))
            )
            logger.debug("Message containers found.")
        except TimeoutException:
            logger.warning("Timed out waiting for message containers. No messages found or UI structure changed.")
            return messages # Return empty list
        except Exception as e:
            logger.error(f"Error waiting for message containers: {e}")
            return messages

        try:
            message_turns = self.driver.find_elements(By.CSS_SELECTOR, self.MESSAGE_CONTAINER_SELECTOR)
            logger.info(f"Found {len(message_turns)} potential message turns.")

            for turn_element in message_turns:
                try:
                    # Determine role (User or Assistant)
                    role_element = turn_element.find_element(By.CSS_SELECTOR, self.MESSAGE_ROLE_SELECTOR)
                    role = role_element.get_attribute('data-message-author-role') or 'unknown'
                    role_prefix = "User: " if role == "user" else "Assistant: "

                    # Find content element(s) within the turn
                    # Sometimes content might be split, find all markdown divs
                    content_elements = turn_element.find_elements(By.CSS_SELECTOR, self.MESSAGE_CONTENT_SELECTOR)
                    if not content_elements:
                         # Handle cases where content might be directly in the turn or different structure
                         # Try getting text directly from turn element as a fallback
                         content_text = turn_element.text.strip()
                         logger.debug(f"No specific content element found in turn, using direct text (Role: {role})")
                    else:
                         # Concatenate text from all found content elements
                         content_parts = [elem.text.strip() for elem in content_elements]
                         content_text = "\n".join(content_parts).strip()

                    if content_text:
                        messages.append(f"{role_prefix}{content_text}")
                    else:
                        logger.warning(f"Empty content found for a message turn (Role: {role}).")

                except NoSuchElementException:
                    # Handle cases where role or content selector might not match for certain turns (e.g., system messages?)
                    logger.warning("Could not find expected role/content structure in a message turn. Skipping.")
                    # Log outerHTML for debugging if needed: logger.debug(f"Problematic turn HTML: {turn_element.get_attribute('outerHTML')[:200]}")
                    continue
                except StaleElementReferenceException:
                    logger.warning("Encountered stale element reference while processing messages. Results may be incomplete.")
                    # Decide whether to retry finding turns or just return what was found
                    break # Stop processing messages for this chat if staleness occurs
                except Exception as e:
                    logger.error(f"Error processing a message turn: {e}", exc_info=True)
                    continue # Skip this turn

        except Exception as e:
            logger.error(f"Failed to find or process message turns: {e}", exc_info=True)

        logger.info(f"Finished scraping messages. Found {len(messages)} messages.")
        return messages

    # --- Helper to navigate safely ---
    def safe_get(self, url: str) -> bool:
        """Attempts to navigate to a URL with basic error handling."""
        try:
            self.driver.get(url)
            # Optional: Add a wait for page readiness
            # WebDriverWait(self.driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            time.sleep(1) # Simple pause
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to URL {url}: {e}")
            return False

__all__ = ["ChatGPTScraper"] 