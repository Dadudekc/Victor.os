# dream_mode/utils/html_parser.py

import logging
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger("HTMLParser")

# Placeholder selector for the 'Stop generating' button or similar indicator
# This might need adjustment based on actual ChatGPT/Custom GPT interface
STOP_GENERATING_SELECTOR = (
    By.XPATH,
    "//button[contains(., 'Stop generating')] | //button[contains(@aria-label, 'Stop generating')] | //textarea[@disabled]",  # noqa: E501
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


def extract_latest_reply(html_content: str) -> Optional[str]:
    """
    Extract the latest reply from ChatGPT's HTML content.

    Args:
        html_content: The HTML content from ChatGPT's response

    Returns:
        The latest reply text if found, None otherwise
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        # Find the last message group
        message_groups = soup.find_all("div", {"class": "group"})
        if not message_groups:
            return None

        last_group = message_groups[-1]
        # Find the assistant's message
        assistant_msg = last_group.find("div", {"class": "markdown"})
        if not assistant_msg:
            return None

        # Extract text content
        reply_text = assistant_msg.get_text(strip=True)
        return reply_text if reply_text else None

    except Exception as e:
        print(f"Error extracting latest reply: {e}")
        return None


def extract_code_blocks(html_content: str) -> List[Dict[str, Any]]:
    """
    Extract code blocks from ChatGPT's HTML content.

    Args:
        html_content: The HTML content from ChatGPT's response

    Returns:
        List of dictionaries containing code block information:
        {
            'language': str,  # Programming language
            'code': str,      # Code content
            'start_line': int # Starting line number
        }
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        code_blocks = []

        # Find all code blocks
        for pre in soup.find_all("pre"):
            code = pre.find("code")
            if not code:
                continue

            # Extract language from class
            language = None
            if code.get("class"):
                for cls in code["class"]:
                    if cls.startswith("language-"):
                        language = cls[9:]  # Remove 'language-' prefix
                        break

            # Extract code content
            code_text = code.get_text(strip=True)
            if not code_text:
                continue

            # Try to find line numbers
            start_line = 1
            line_match = re.search(r"^(\d+):", code_text)
            if line_match:
                start_line = int(line_match.group(1))
                code_text = re.sub(r"^\d+:", "", code_text)

            code_blocks.append(
                {"language": language, "code": code_text, "start_line": start_line}
            )

        return code_blocks

    except Exception as e:
        print(f"Error extracting code blocks: {e}")
        return []


def extract_web_element_text(element: WebElement) -> Optional[str]:
    """
    Extract text content from a Selenium WebElement.

    Args:
        element: The WebElement to extract text from

    Returns:
        The extracted text if successful, None otherwise
    """
    try:
        return element.text.strip()
    except Exception as e:
        print(f"Error extracting element text: {e}")
        return None


def clean_html_text(html_content: str) -> str:
    """
    Clean HTML content by removing unnecessary whitespace and formatting.

    Args:
        html_content: The HTML content to clean

    Returns:
        Cleaned text content
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text and clean it
        text = soup.get_text()
        # Break into lines and remove leading/trailing space
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Remove blank lines
        text = "\n".join(chunk for chunk in chunks if chunk)

        return text

    except Exception as e:
        print(f"Error cleaning HTML text: {e}")
        return html_content
