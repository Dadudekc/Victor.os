"""
Locators for elements on the chat.openai.com website.
"""
from selenium.webdriver.common.by import By

class ChatGPTLocators:
    # --- Login / Authentication ---
    LOGIN_BUTTON = (By.XPATH, "//button[contains(text(), 'Log in')]")
    EMAIL_INPUT = (By.ID, "username") # Or appropriate ID/name
    PASSWORD_INPUT = (By.ID, "password") # Or appropriate ID/name
    CONTINUE_BUTTON = (By.XPATH, "//button[contains(text(), 'Continue')]") # Might need adjustment
    
    # --- Main Chat Interface ---
    CHAT_HISTORY_NAV = (By.CSS_SELECTOR, 'nav[aria-label="Chat history"]') # Used for login check
    TEXT_INPUT_AREA = (By.ID, "prompt-textarea") 
    SEND_BUTTON = (By.CSS_SELECTOR, '[data-testid="send-button"]') # Often has a test ID
    REGENERATE_BUTTON = (By.XPATH, "//button[contains(text(), 'Regenerate')]") # Or similar text
    
    # --- Chat Messages ---
    # These selectors might need adjustment based on the exact structure
    CHAT_CONTAINER = (By.CSS_SELECTOR, 'div.markdown') # Example, likely needs refinement
    MESSAGE_TURN_SELECTOR = (By.CSS_SELECTOR, 'div[data-testid^="conversation-turn-"]') # Example selector for a message block
    USER_MESSAGE_SELECTOR = (By.CSS_SELECTOR, 'div[data-message-author-role="user"]') # Example
    ASSISTANT_MESSAGE_SELECTOR = (By.CSS_SELECTOR, 'div[data-message-author-role="assistant"] .markdown') # Example to get assistant text

    # --- Other elements ---
    STOP_GENERATING_BUTTON = (By.XPATH, "//button[contains(text(), 'Stop generating')]") # Example

    # Add more locators as needed for specific scraper functionality... 