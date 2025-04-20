import os
import time
import logging
import re
from typing import List, Dict, Optional, Any
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout

# Remove Selenium imports if no longer needed by other methods
# from selenium.common.exceptions import (...)
# from selenium.webdriver.common.by import By
# from selenium.webdriver.remote.webdriver import WebDriver
# from selenium.webdriver.remote.webelement import WebElement
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.support.ui import WebDriverWait

from dreamscape_generator import config as project_config

# Remove driver manager stub import
# from .driver_manager_stub import StubUnifiedDriverManager

# Import the login helper
from .core.login_utils import ensure_login

logger = logging.getLogger(__name__)
logger.setLevel(project_config.LOG_LEVEL)

class ChatGPTScraper:
    """Handles interaction with the ChatGPT web UI.
       Initially focused on scraping, now includes sending prompts via Playwright.
    """

    DEFAULT_CHATGPT_URL = "https://chat.openai.com/"
    # Keep selectors if needed for scraping methods, otherwise remove
    SIDEBAR_SELECTOR = "div.flex-col.flex-1.transition-opacity.duration-500.relative.pr-3.overflow-y-auto"
    CHAT_LINK_SELECTOR = 'nav[aria-label="Chat history"] a'
    MESSAGE_CONTAINER_SELECTOR = "div[data-testid^='conversation-turn-']"
    MESSAGE_ROLE_SELECTOR = "div[data-message-author-role]"
    MESSAGE_CONTENT_SELECTOR = "div.markdown"

    # Simplify __init__ - remove driver-related params
    def __init__(self, chatgpt_url: Optional[str] = None):
        self.chatgpt_url = chatgpt_url or self.DEFAULT_CHATGPT_URL
        # No driver initialization here anymore
        logger.info("ChatGPTScraper initialized (Playwright used in methods).")

    # Remove driver property and shutdown method
    # @property
    # def driver(self) -> WebDriver: ...
    # def shutdown_driver(self): ...

    # Remove Selenium-based login checks/methods if converting fully
    # def is_logged_in(self) -> bool: ...
    # def login(self): ...

    # Keep scraping methods if they are still needed (may need Playwright rewrite later)
    def get_all_chat_titles(self) -> List[Dict[str, str]]:
        logger.warning("get_all_chat_titles currently uses Selenium - NEEDS Playwright rewrite!")
        # Placeholder: return empty list or raise NotImplementedError
        return [] # Or implement using Playwright

    def scrape_current_chat_messages(self) -> List[Dict[str, str]]:
        logger.warning("scrape_current_chat_messages currently uses Selenium - NEEDS Playwright rewrite!")
        # Placeholder: return empty list or raise NotImplementedError
        return [] # Or implement using Playwright

    # Replace send_prompt stub with Playwright version
    def send_prompt(self, prompt: str, *, model="gpt-4o", reverse=False, headless=True):
        """Playwright implementation: log in if needed, send prompt, return reply text."""
        logger.info(f"send_prompt(): Playwright headless={headless}")

        try:
            with sync_playwright() as p:
                # Use persistent context for session/cookie caching
                user_data_path = "playwright_profile"
                logger.info(f"Launching persistent Playwright context (profile: {user_data_path})...")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=user_data_path,
                    headless=headless,
                    # Consider adding args like --no-sandbox on Linux if needed
                    # args=["--no-sandbox"]
                )
                page = context.new_page()
                try:
                    # 1 --- Guarantee login using the helper --- 
                    logger.info("Ensuring login status for ChatGPT...")
                    ensure_login(page, service="chatgpt")
                    logger.info("Login check/flow complete.")

                    # --- Handle potential post-login pop-ups/modals --- 
                    logger.info("Checking for post-login modals...")
                    popup_buttons = [
                        page.get_by_role("button", name="Okay, let's go"),
                        page.get_by_role("button", name="Next"),
                        page.get_by_role("button", name="Done")
                    ]
                    for btn in popup_buttons:
                        try:
                            # Use a short timeout, as these might not exist
                            if btn.is_visible(timeout=2000): 
                                logger.info(f"Clicking popup button: {btn.text_content()}")
                                btn.click(timeout=5000)
                                time.sleep(0.5) # Brief pause after click
                        except PlaywrightTimeout:
                            pass # Button not visible within timeout, continue
                        except Exception as popup_err:
                            logger.warning(f"Error trying to click popup button: {popup_err}")
                    logger.info("Finished checking for modals.")
                    # -----------------------------------------------------
                    
                    # 2 --- (Optional) Pick model via UI --- 
                    if model != "gpt-4o": # Assuming gpt-4o is the default UI selection
                        logger.info(f"Attempting to select model: {model}")
                        try:
                            # Adjust selector if needed for model switching button/dropdown
                            model_button_selector = f"button:has-text('{model}')" # Example selector
                            page.click(model_button_selector, timeout=5_000)
                            logger.info(f"Clicked model selection button for '{model}'.")
                        except PlaywrightTimeout:
                            logger.warning(f"Could not find or click model button '{model}' within timeout; using default.")
                        except Exception as model_err:
                            logger.warning(f"Error trying to select model '{model}': {model_err}")

                    # 3 --- Paste prompt & send --- 
                    textarea_selector = "textarea#prompt-textarea"
                    logger.info(f"Waiting for textarea: {textarea_selector}")
                    # Explicitly wait for the selector to be visible *before* filling
                    page.wait_for_selector(textarea_selector, state="visible", timeout=30000) 
                    logger.info("Filling prompt textarea...")
                    # Use the specific selector for fill
                    page.fill(textarea_selector, prompt)
                    logger.info("Submitting prompt (pressing Enter)...")
                    page.keyboard.press("Enter") # Use keyboard.press for reliability
                    logger.info("Prompt submitted.")

                    # 4 --- Wait for response & return text --- 
                    response_selector = f"{self.MESSAGE_CONTAINER_SELECTOR}:not(:has(textarea)) {self.MESSAGE_CONTENT_SELECTOR}"
                    logger.info(f"Waiting for response selector: {response_selector}")
                    page.wait_for_selector(response_selector, state="visible", timeout=120_000)
                    logger.info("Response element detected.")
                    time.sleep(0.5) # Brief pause
                    reply = page.locator(response_selector).last.text_content() or ""
                    logger.info(f"Response extracted (length: {len(reply)}).")

                except Exception as interaction_err:
                    logger.error(f"Playwright interaction failed: {interaction_err}", exc_info=True)
                    # page.screenshot(path="playwright_error.png") # Optional: save screenshot
                    reply = f"[ERROR] Playwright interaction failed: {interaction_err}"
                finally:
                    logger.info("Closing Playwright context...")
                    context.close()
                    logger.info("Playwright context closed.")
                
            return reply
        except Exception as pw_err:
            logger.error(f"Playwright setup/context manager failed: {pw_err}", exc_info=True)
            return f"[ERROR] Playwright setup failed: {pw_err}"


__all__ = ["ChatGPTScraper"] 