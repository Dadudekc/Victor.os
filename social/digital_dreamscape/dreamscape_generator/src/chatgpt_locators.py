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

    # Add other locators as needed
    # --- Model Selection Locators (Guesses) ---
    MODEL_SELECTOR_BUTTON = (By.XPATH, "//button[contains(., 'GPT-')]") # Button showing current model
    MODEL_MENU_ITEM = (By.XPATH, "//div[@role='menuitemradio']//div[contains(text(), '{model_name}')]") # Template for model option
    # -----------------------------------------

    # Maybe add locators for Send button if needed, regenerate, stop etc.

    # --- Chat History Locators (Guesses) ---
    HISTORY_SIDEBAR = (By.XPATH, "//nav[contains(@aria-label, 'Chat history')]") # The nav element
    HISTORY_LINK_ITEM = (By.XPATH, ".//a[contains(@href, '/c/')]") # Links within the sidebar
    HISTORY_TITLE_TEXT = (By.XPATH, ".//div[contains(@class, 'overflow-hidden')]") # Div containing title text, relative to link
    # --- Guessed scroll container (might be inside the nav) ---
    HISTORY_SCROLL_CONTAINER = (By.XPATH, "//nav[contains(@aria-label, 'Chat history')]/div[contains(@class, 'flex-col')]") # Guessing a div with flex-col often scrolls
    # ---------------------------------------

    # Add more locators as needed for specific scraper functionality... 