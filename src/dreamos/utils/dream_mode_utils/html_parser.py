# dream_mode/utils/html_parser.py

import logging

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

logger = logging.getLogger("HTMLParser")

# Placeholder selector for the 'Stop generating' button or similar indicator
# This might need adjustment based on actual ChatGPT/Custom GPT interface
STOP_GENERATING_SELECTOR = (
    By.XPATH,
    "//button[contains(., 'Stop generating')] | //button[contains(@aria-label, 'Stop generating')] | //textarea[@disabled]",
)


def is_still_generating(driver) -> bool:
    """Checks if ChatGPT appears to be actively generating a response."""
    try:
        # Check if the 'Stop generating' button exists and is displayed
        # OR if the prompt textarea is disabled (another common indicator)
        stop_elements = driver.find_elements(*STOP_GENERATING_SELECTOR)
        for element in stop_elements:
            if element.is_displayed():
                # Check tag name for specific handling if needed
                if element.tag_name == "button":
                    logger.debug("Stop generating button is visible.")
                    return True
                elif element.tag_name == "textarea" and element.get_attribute(
                    "disabled"
                ):
                    logger.debug("Prompt textarea is disabled.")
                    return True

        logger.debug("No active 'still generating' indicator found.")
        return False
    except NoSuchElementException:
        # If the element doesn't exist, it's not generating
        logger.debug("'Stop generating' indicator element not found.")
        return False
    except Exception as e:
        # Handle potential errors gracefully
        logger.warning(f"Error checking for 'still generating' indicator: {e}")
        # Conservatively assume it might be generating if we can't check
        return True


def extract_latest_reply(driver):
    """
    Extracts the last visible ChatGPT message from the DOM,
    only if the assistant is not currently generating a response.
    Returns the message text, or None if generating or no message found.
    """
    try:
        # Check if the assistant is still typing/generating
        if is_still_generating(driver):
            logger.info("⏳ Assistant is still generating response...")
            return None  # Indicate still generating, not ready to parse

        # This selector may vary — this one works for ChatGPT as of 2024
        containers = driver.find_elements(
            By.CSS_SELECTOR, "div[data-message-author-role='assistant']"
        )

        if not containers:
            logger.warning("No ChatGPT assistant messages found.")
            return None

        # Get the last one with non-empty content
        for div in reversed(containers):
            text = div.text.strip()
            if text:
                logger.info(
                    "✅ Latest assistant reply extracted (generation finished)."
                )
                return text

        logger.warning("All assistant messages were empty.")
        return None
    except Exception as e:
        logger.error(f"❌ Error during reply extraction: {e}", exc_info=True)
        return None
