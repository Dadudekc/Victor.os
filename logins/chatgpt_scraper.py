"""
D:\\Dream.os\\logins\\chatgpt_scraper.py

ChatGPT Web Scraper for Dream.OS - Extracts conversation content and handles ChatGPT interactions.
Integrates with Dream.OS login system while providing robust session management and response handling.

Features:
- Reliable authentication handling with cookie persistence
- Dynamic element detection for UI changes
- Robust response waiting with stability detection
- Support for hybrid responses (text + JSON memory updates)
"""

import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import undetected_chromedriver as uc
from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
    NoSuchWindowException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Import local project modules
from setup_logging import setup_logging
from openai_login import get_openai_driver, login_openai, is_logged_in

# Configure logging
logger = setup_logging("chatgpt_scraper", log_dir=os.path.join(os.getcwd(), "logs", "chatgpt"))

# ---------------------------
# Configuration & Constants
# ---------------------------
CHATGPT_URL = "https://chat.openai.com/chat"
PROFILE_DIR = os.path.join(os.getcwd(), "chrome_profile", "openai") 
COOKIE_FILE = os.path.join(os.getcwd(), "cookies", "openai.pkl")
CONTENT_LOG_DIR = os.path.join(os.getcwd(), "chat_logs")

# Ensure directories exist
os.makedirs(CONTENT_LOG_DIR, exist_ok=True)

# Selectors for ChatGPT UI elements
CHAT_INPUT_SELECTORS = [
    'p[data-placeholder="Ask anything"]',  # New primary selector
    'textarea[data-id="chat-input"]',      # Older selector
    'textarea[placeholder="Send a message"]',
    'textarea[aria-label="Chat input"]',
]

SEND_BUTTON_SELECTORS = [
    'button[data-testid="send-button"]',     # Primary test ID
    'button[class*="send"]',                 # Class containing 'send'
    'button[aria-label*="Send"]',            # Aria label containing 'Send'
    "//button[.//span[text()='Send message']]", # XPath for specific text
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
        """Extract text and structured JSON data from a hybrid response."""
        logger.info("Parsing hybrid response for narrative text and MEMORY_UPDATE JSON")
        
        # Regex to capture JSON block between ```json and ```
        json_pattern = r"""```json(.*?)```"""
        match = re.search(json_pattern, raw_response, re.DOTALL)

        if match:
            json_content = match.group(1).strip()
            try:
                memory_update = json.loads(json_content)
                logger.info("Successfully parsed MEMORY_UPDATE JSON")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                memory_update = {}
        else:
            logger.info("No JSON block found in the response")
            memory_update = {}

        # Remove the JSON block from the raw response to extract pure narrative text
        text_part = re.sub(json_pattern, "", raw_response, flags=re.DOTALL).strip()

        return text_part, memory_update


# ---------------------------
# Core Response Handler Class
# ---------------------------
class ChatGPTScraper:
    """
    Main class for interacting with ChatGPT. Handles authentication, sending prompts, 
    receiving responses, and conversation management.
    """

    def __init__(
        self,
        driver: Optional[uc.Chrome] = None,
        timeout: int = 180,
        stable_period: int = 10,
        poll_interval: int = 5,
    ) -> None:
        """
        Initialize the ChatGPT scraper with options for controlling response handling.
        
        Args:
            driver: Existing undetected_chromedriver instance, or None to create one
            timeout: Maximum seconds to wait for a complete response
            stable_period: Seconds without change to consider a response complete
            poll_interval: Seconds between response polling checks
        """
        logger.info("Initializing ChatGPT scraper")
        self.driver = driver
        self.timeout = timeout
        self.stable_period = stable_period
        self.poll_interval = poll_interval
        self._last_msg_count = 0
        
        # Message selectors
        self._message_elements_selector_primary = ".markdown.prose.w-full.break-words"
        self._message_elements_selector_fallback = "div[class*='markdown prose']"
        
        # Create hybrid response handler
        self.hybrid_handler = HybridResponseHandler()
        
        # Automatically initialize driver if not provided
        if self.driver is None:
            self.driver = get_openai_driver(profile_path=PROFILE_DIR, headless=False)
            
        logger.info("ChatGPT scraper initialized")

    # ---------------------------
    # Authentication Methods
    # ---------------------------
    def ensure_login_session(self) -> bool:
        """
        Ensures a valid login session exists for ChatGPT.
        Uses cookies if available, falls back to manual login if needed.
        
        Returns:
            bool: True if login successful, False otherwise
        """
        logger.info("Ensuring login session")
        
        if is_logged_in(self.driver):
            logger.info("Already logged into ChatGPT")
            return True
            
        return login_openai(self.driver)
        
    # ---------------------------
    # Helper Methods
    # ---------------------------
    def ensure_chat_page(self, chat_url: str = CHATGPT_URL) -> bool:
        """
        Ensures the browser is on the chat page.
        
        Args:
            chat_url: The URL of the ChatGPT interface
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Ensuring browser is on chat page: {chat_url}")
        
        current_url = self.driver.current_url
        if "chat.openai.com" not in current_url:
            try:
                logger.info(f"Navigating to chat page: {chat_url}")
                self.driver.get(chat_url)
                time.sleep(3)  # Allow page to load
            except Exception as e:
                logger.error(f"Error navigating to chat page: {e}")
                return False
                
        # Wait for chat interface to load
        try:
            WebDriverWait(self.driver, 15).until(
                lambda d: self._find_chat_input(d) is not None
            )
            logger.info("Chat page loaded successfully")
            return True
        except TimeoutException:
            logger.error("Timed out waiting for chat interface to load")
            return False
        except Exception as e:
            logger.error(f"Error verifying chat page: {e}")
            return False
    
    def _find_chat_input(self, driver) -> Optional[Any]:
        """
        Find the chat input field using multiple possible selectors.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            WebElement if found, None otherwise
        """
        for selector in CHAT_INPUT_SELECTORS:
            try:
                if selector.startswith("//"):
                    # XPath selector
                    element = driver.find_element(By.XPATH, selector)
                else:
                    # CSS selector
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                return element
            except Exception:
                continue
        return None
        
    def _find_send_button(self, driver) -> Optional[Any]:
        """
        Find the send button using multiple possible selectors.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            WebElement if found, None otherwise
        """
        for selector in SEND_BUTTON_SELECTORS:
            try:
                if selector.startswith("//"):
                    # XPath selector
                    element = driver.find_element(By.XPATH, selector)
                else:
                    # CSS selector
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                return element
            except Exception:
                continue
        return None

    # ---------------------------
    # Prompt & Response Methods
    # ---------------------------
    def send_prompt(self, prompt: str) -> bool:
        """
        Sends a prompt to ChatGPT.
        
        Args:
            prompt: The text to send to ChatGPT
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Sending prompt (length: {len(prompt)} chars)")
        
        # Check if window is still open
        try:
            # This will throw if window is closed
            current_url = self.driver.current_url
        except NoSuchWindowException:
            logger.error("Browser window is no longer available")
            return False
            
        # Make sure we're on the chat page
        if not self.ensure_chat_page():
            return False
            
        # Find and interact with the input field
        input_field = self._find_chat_input(self.driver)
        if not input_field:
            logger.error("Could not find chat input field")
            return False
            
        try:
            # Focus and clear the input field
            input_field.click()
            time.sleep(0.5)
            
            # Enter text (in chunks if necessary)
            chunk_size = 1000  # Send text in chunks to avoid issues with very long prompts
            for i in range(0, len(prompt), chunk_size):
                chunk = prompt[i:i + chunk_size]
                input_field.send_keys(chunk)
                time.sleep(0.3)
                
            logger.info("Text entered successfully")
            
            # Find and click send button or use Enter key
            send_button = self._find_send_button(self.driver)
            if send_button and send_button.is_enabled():
                send_button.click()
                logger.info("Clicked send button")
            else:
                # Fallback to Enter key
                input_field.send_keys(Keys.RETURN)
                logger.info("Used Enter key to send")
                
            # Wait a moment for the submission to start
            time.sleep(2)
            return True
            
        except ElementNotInteractableException:
            logger.error("Chat input is not interactable")
        except StaleElementReferenceException:
            logger.error("Element reference is stale")
        except Exception as e:
            logger.error(f"Error sending prompt: {e}")
            
        return False
        
    def fetch_response(self, timeout: int = None) -> str:
        """
        Fetch the most recent response from ChatGPT.
        
        Args:
            timeout: Maximum time to wait for any response, None to use instance default
            
        Returns:
            str: The raw response text
        """
        if timeout is None:
            timeout = self.timeout
            
        logger.info(f"Fetching response (timeout: {timeout}s)")
        
        start_time = time.time()
        response = ""
        
        try:
            # Wait for any response to appear
            while time.time() - start_time < timeout:
                message_elements = self._get_message_elements()
                if message_elements and len(message_elements) > self._last_msg_count:
                    # New message detected
                    response = message_elements[-1].text
                    if response:
                        # Found a non-empty response
                        return response
                time.sleep(1)
                
            logger.warning(f"No response within timeout ({timeout}s)")
            return ""
            
        except Exception as e:
            logger.error(f"Error fetching response: {e}")
            return ""
    
    def wait_for_stable_response(self) -> str:
        """
        Wait for a complete, stable response from ChatGPT.
        'Stable' means the response text hasn't changed for self.stable_period seconds.
        
        Returns:
            str: The complete response text
        """
        logger.info(f"Waiting for stable response (timeout: {self.timeout}s, stability period: {self.stable_period}s)")
        
        start_time = time.time()
        last_stable_time = start_time
        previous_response = ""
        current_response = ""
        
        # Check if "Continue generating" or similar buttons are present and handle them
        def check_continue_buttons():
            try:
                # Look for "Continue generating" button
                continue_buttons = self.driver.find_elements(
                    By.XPATH, 
                    "//button[contains(., 'Continue') or contains(., 'continue')]"
                )
                for button in continue_buttons:
                    if button.is_displayed():
                        logger.info("Clicking 'Continue generating' button")
                        button.click()
                        time.sleep(2)
                        return True
                return False
            except Exception as e:
                logger.debug(f"Error checking continue buttons: {e}")
                return False
        
        while time.time() - start_time < self.timeout:
            # Handle "Continue generating" buttons if present
            if check_continue_buttons():
                # Reset stability timer if we clicked a button
                last_stable_time = time.time()
                
            # Check if response is still being generated
            try:
                # Look for standard loading indicators
                loading_indicators = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    "div.result-streaming, div[class*='thinking'], *[class*='loading']"
                )
                is_loading = any(ind.is_displayed() for ind in loading_indicators if ind)
                
                if is_loading:
                    logger.debug("Response still generating...")
                    last_stable_time = time.time()  # Reset stability timer
            except Exception:
                pass  # Ignore errors checking loading state
                
            # Get current response
            message_elements = self._get_message_elements()
            if message_elements and len(message_elements) > 0:
                current_response = message_elements[-1].text
                
                # Check if response is changing
                if current_response != previous_response:
                    logger.debug(f"Response updated (length: {len(current_response)} chars)")
                    previous_response = current_response
                    last_stable_time = time.time()  # Reset stability timer
                    
            # Check if response has been stable for the required period
            time_since_last_change = time.time() - last_stable_time
            if current_response and time_since_last_change >= self.stable_period:
                logger.info(f"Response stable for {self.stable_period}s - complete!")
                return current_response
                
            # Wait before next check
            time.sleep(self.poll_interval)
            
        # Timeout reached
        logger.warning(f"Timeout reached without stable response. Returning current response (length: {len(current_response)} chars)")
        return current_response

    @staticmethod
    def clean_response(response: str) -> str:
        """
        Clean up a response by removing any special markers or artifacts.
        
        Args:
            response: Raw response text
            
        Returns:
            str: Cleaned response text
        """
        # Remove any "ChatGPT <date>" headers that sometimes appear
        cleaned = re.sub(r"^ChatGPT\s+\d+.*?\n", "", response)
        return cleaned.strip()
        
    def handle_hybrid_response(self, raw_response: str) -> Tuple[str, Dict]:
        """
        Process a hybrid response that might contain both text and structured data.
        
        Args:
            raw_response: The raw response from ChatGPT
            
        Returns:
            Tuple[str, Dict]: Cleaned text response and any extracted structured data
        """
        text_part, memory_update = self.hybrid_handler.parse_hybrid_response(raw_response)
        return self.clean_response(text_part), memory_update
    
    def execute_prompt_cycle(self, prompt: str) -> str:
        """
        Execute a complete prompt cycle: ensure login, send prompt, wait for response.
        
        Args:
            prompt: The prompt to send to ChatGPT
            
        Returns:
            str: The complete response text
        """
        logger.info("Starting prompt execution cycle")
        
        # Ensure we have a valid login session
        if not self.ensure_login_session():
            logger.error("Failed to establish login session")
            return ""
            
        # Send the prompt
        if not self.send_prompt(prompt):
            logger.error("Failed to send prompt")
            return ""
            
        # Wait for stable response
        response = self.wait_for_stable_response()
        cleaned_response = self.clean_response(response)
        
        logger.info(f"Prompt cycle complete: received {len(cleaned_response)} chars")
        return cleaned_response
    
    # ---------------------------
    # Conversation Management Methods
    # ---------------------------
    def _get_message_elements(self) -> List[Any]:
        """
        Get all message elements from the current conversation.
        
        Returns:
            List of WebElements representing all messages
        """
        elements = []
        try:
            # Try primary selector first
            elements = self.driver.find_elements(
                By.CSS_SELECTOR, self._message_elements_selector_primary
            )
            
            # Fall back to secondary selector if needed
            if not elements:
                elements = self.driver.find_elements(
                    By.CSS_SELECTOR, self._message_elements_selector_fallback
                )
                
            return elements
        except Exception as e:
            logger.error(f"Error getting message elements: {e}")
            return []
    
    def get_conversation_content(self) -> List[Dict[str, str]]:
        """
        Extract the full conversation as a list of message objects.
        
        Returns:
            List of dicts with 'role' and 'content' keys
        """
        logger.info("Retrieving conversation content")
        
        try:
            # Get all message elements
            elements = self._get_message_elements()
            if not elements:
                logger.warning("No message elements found")
                return []
                
            # Determine which messages are from user vs assistant
            messages = []
            
            # Find role indicators (e.g., "user", "assistant" labels or their container elements)
            user_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "img[alt*='User'], div[class*='user']"
            )
            assistant_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "img[alt*='ChatGPT'], img[alt*='Assistant'], div[class*='assistant']"
            )
            
            # Simple alternating pattern fallback if role detection fails
            if len(user_elements) < 1 or len(assistant_elements) < 1:
                logger.info("Using alternating pattern for message roles")
                for i, elem in enumerate(elements):
                    role = "user" if i % 2 == 0 else "assistant"
                    messages.append({
                        "role": role,
                        "content": elem.text
                    })
            else:
                logger.info("Using role indicators for message attribution")
                # More complex detection based on page structure - implementation details will
                # depend on exact DOM structure which we'd need to analyze
                
                # This is a placeholder implementation
                for i, elem in enumerate(elements):
                    # Simplified approach - alternate but with smarter detection
                    role = "user" if i % 2 == 0 else "assistant"
                    messages.append({
                        "role": role,
                        "content": elem.text
                    })
            
            logger.info(f"Retrieved {len(messages)} messages from conversation")
            return messages
            
        except Exception as e:
            logger.error(f"Error extracting conversation: {e}")
            return []
            
    def save_conversation(self, conversation_id: str = None) -> str:
        """
        Save the current conversation to a file.
        
        Args:
            conversation_id: Optional ID for the conversation, uses timestamp if None
            
        Returns:
            str: Path to the saved file
        """
        if conversation_id is None:
            conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        messages = self.get_conversation_content()
        if not messages:
            logger.warning("No messages to save")
            return ""
            
        # Create conversation data structure
        conversation_data = {
            "id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "messages": messages
        }
        
        # Save to file
        file_path = os.path.join(CONTENT_LOG_DIR, f"conversation_{conversation_id}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved conversation to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            return ""
    
    # ---------------------------
    # Resource Management
    # ---------------------------
    def shutdown(self) -> None:
        """
        Clean up resources (close browser, etc.)
        """
        logger.info("Shutting down ChatGPT scraper")
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")


# ---------------------------
# Utility Functions
# ---------------------------
def execute_single_prompt(prompt: str) -> str:
    """
    Utility function to execute a single prompt and return the response.
    Handles setup and cleanup.
    
    Args:
        prompt: The prompt to send to ChatGPT
        
    Returns:
        str: The response text
    """
    scraper = ChatGPTScraper()
    try:
        return scraper.execute_prompt_cycle(prompt)
    finally:
        scraper.shutdown()

def execute_conversation(prompts: List[str]) -> List[Dict[str, str]]:
    """
    Execute a sequence of prompts as a conversation and return the full history.
    
    Args:
        prompts: List of prompts to send in sequence
        
    Returns:
        List of message objects with role and content
    """
    scraper = ChatGPTScraper()
    try:
        for prompt in prompts:
            scraper.execute_prompt_cycle(prompt)
            time.sleep(2)  # Brief pause between prompts
            
        return scraper.get_conversation_content()
    finally:
        scraper.shutdown()


# ---------------------------
# Main Function
# ---------------------------
if __name__ == "__main__":
    # Demo usage
    prompt = input("Enter your prompt to ChatGPT (or 'demo' for test): ")
    
    if prompt.lower() == "demo":
        prompt = "What are the 3 most effective ways to implement defensive programming in Python? Provide code examples."
        
    print(f"\nSending prompt: {prompt}\n")
    response = execute_single_prompt(prompt)
    
    print("\n" + "-"*80)
    print("RESPONSE:")
    print("-"*80)
    print(response)
    print("-"*80)
