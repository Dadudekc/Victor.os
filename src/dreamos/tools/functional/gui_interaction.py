import logging
import platform
import time

import pyautogui
import pyperclip

# EDIT START: Remove dummy OrchestratorBot fallback, require real import
try:
    from dreamos.core.bots.orchestrator_bot import OrchestratorBot
except ImportError as e:
    raise ImportError(
        "OrchestratorBot must be available for GUI interaction. "
        "Please check your PYTHONPATH and dependencies."
    ) from e
# EDIT END

# Basic configuration
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s"
)
logger = logging.getLogger("GuiInteraction")

# Platform-specific settings (adjust delays/hotkeys if needed)
OS_PLATFORM = platform.system()
STANDARD_DELAY = 0.5  # Delay between actions
TYPING_INTERVAL = 0.05  # Delay between keystrokes
WINDOW_ACTIVATION_DELAY = 1.5  # Time to wait for window activation
RESPONSE_WAIT_TIMEOUT = 30  # Max seconds to wait for Cursor response
RESPONSE_CHECK_INTERVAL = 1  # Seconds between response checks

# EDIT: Instantiate OrchestratorBot
try:
    bot = OrchestratorBot(config=None, agent_id="GuiInteractionTool")
except Exception as e:
    logging.error(
        f"Failed to initialize OrchestratorBot: {e}. " "GUI actions will fail."
    )
    bot = OrchestratorBot()  # Use dummy if init fails

# --- Core Interaction Function ---


def find_and_activate_cursor_window(
    title_substring="Cursor", retries=3, delay=WINDOW_ACTIVATION_DELAY
):
    """Attempts to find and activate the Cursor window."""
    logger.info(
        f"Attempting to find and activate window containing '{title_substring}'"
    )
    for attempt in range(retries):
        try:
            # Get all windows with the title substring
            windows = pyautogui.getWindowsWithTitle(title_substring)
            if not windows:
                logger.warning(
                    f"Attempt {attempt + 1}/{retries}: No window found with title "
                    f"containing '{title_substring}'. Retrying after {delay}s..."
                )
                time.sleep(delay)
                continue

            # Attempt to activate the first found window
            cursor_window = windows[0]
            logger.info(f"Found window: {cursor_window.title}")

            # Activation differs slightly by OS
            if OS_PLATFORM == "Windows":
                if cursor_window.isMinimized:
                    cursor_window.restore()
                cursor_window.activate()
            elif OS_PLATFORM == "Darwin":  # macOS
                # macOS activation might need AppleScript or different handling
                # For now, using activate() which might bring it to front
                cursor_window.activate()
            else:  # Linux
                cursor_window.activate()  # May depend on window manager

            time.sleep(delay)  # Wait for window to become active

            if cursor_window.isActive:
                logger.info("Cursor window successfully activated.")
                return cursor_window
            else:
                logger.warning(
                    f"Attempt {attempt + 1}/{retries}: Failed to activate window "
                    f"'{cursor_window.title}'. Window might be obscured or unresponsive."  # noqa: E501
                )
                time.sleep(delay)

        except Exception as e:
            logger.error(
                f"Attempt {attempt + 1}/{retries}: Error finding/activating "
                f"Cursor window: {e}"
            )
            time.sleep(delay)

    logger.error(f"Failed to activate Cursor window after {retries} attempts.")
    return None


def type_prompt_and_send(prompt: str):
    """Types the prompt into the active window and presses Enter."""
    logger.info("Typing prompt...")
    try:
        # Assume input field is focused after activation, or add click logic if needed
        # pyautogui.click(x=100, y=200) # Example: Click coordinates if needed
        time.sleep(STANDARD_DELAY)
        bot.typewrite(prompt, interval=TYPING_INTERVAL)
        time.sleep(STANDARD_DELAY)
        bot.press("enter")
        logger.info("Prompt entered and sent.")
        return True
    except Exception as e:
        logger.error(f"Error typing or sending prompt via OrchestratorBot: {e}")
        return False


def copy_cursor_response() -> str | None:
    """Attempts to select all and copy text from the active window."""
    logger.info("Attempting to copy response...")
    try:
        time.sleep(STANDARD_DELAY * 2)  # Give UI time to settle
        # Use standard select-all and copy hotkeys
        if OS_PLATFORM == "Darwin":  # macOS
            bot.hotkey("command", "a")
            time.sleep(STANDARD_DELAY)
            bot.hotkey("command", "c")
        else:  # Windows/Linux
            bot.hotkey("ctrl", "a")
            time.sleep(STANDARD_DELAY)
            bot.hotkey("ctrl", "c")

        time.sleep(STANDARD_DELAY)  # Wait for clipboard operation
        response = pyperclip.paste()

        if response:
            logger.info(f"Successfully copied response (length: {len(response)}).")
            return response
        else:
            logger.warning("Copy operation resulted in empty clipboard.")
            return None
    except Exception as e:
        logger.error(f"Error selecting/copying response: {e}")
        return None


def interact_with_cursor(prompt: str) -> str | None:
    """
    Main function to orchestrate interaction with the Cursor application.

    1. Finds and activates the Cursor window.
    2. Types the given prompt into the chat input.
    3. Presses Enter to send the prompt.
    4. Waits for a response (simple delay-based for now).
    5. Attempts to copy the response text.
    6. Returns the copied text or None on failure.
    """
    logger.info(f"--- Starting Cursor Interaction for prompt: '{prompt[:50]}...'")

    # 1. Activate Window
    cursor_window = find_and_activate_cursor_window()
    if not cursor_window:
        return None  # Failed to activate window

    # 2. Type Prompt and Send
    if not type_prompt_and_send(prompt):
        return None  # Failed to type/send

    # 3. Wait for Response (Simplistic approach - replace with better check if possible)
    # TODO: Implement a more robust check for response completion if possible
    #       (e.g., image recognition of 'thinking' indicator, OCR of response area)
    logger.info(
        f"Waiting approximately {RESPONSE_WAIT_TIMEOUT}s for Cursor to "
        "generate response..."
    )
    time.sleep(RESPONSE_WAIT_TIMEOUT)  # Simple wait - unreliable

    # 4. Copy Response
    response_text = copy_cursor_response()

    if response_text:
        logger.info("--- Cursor Interaction Completed Successfully ---")
    else:
        logger.error("--- Cursor Interaction Failed (Could not copy response) ---")

    return response_text


# --- Example Usage ---
if __name__ == "__main__":
    test_prompt = "Explain the theory of relativity in simple terms."
    logger.info(f"Running test interaction with prompt: {test_prompt}")

    # Give user time to switch focus away from terminal if running manually
    print("Switch focus away from this terminal in 5 seconds...")
    time.sleep(5)

    response = interact_with_cursor(test_prompt)

    if response:
        print("\n--- Response Received ---")
        print(response)
        print("-------------------------")
    else:
        print("\n--- Failed to get response from Cursor ---")

    logger.info("Test interaction finished.")
