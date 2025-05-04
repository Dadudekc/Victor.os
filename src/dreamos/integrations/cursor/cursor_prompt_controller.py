import logging
import time
import warnings  # EDIT START: Import warnings module

# EDIT START: Import OrchestratorBot here to fix E402
from dreamos.core.bots.orchestrator_bot import OrchestratorBot

# import pyautogui # F401 Unused Import
# import pyperclip  # F401 Unused Import

# EDIT START: Add module level deprecation warning
warnings.warn(
    "The CursorPromptController module (using pyautogui) is deprecated due to its "
    "inherent fragility. Use the event-based mechanism via "
    "integrations.cursor.utils.publish_cursor_inject_event and AgentBus instead.",
    DeprecationWarning,
    stacklevel=2,
)
# EDIT END

# Configure logging
logger = logging.getLogger("CursorPromptController")
if not logger.hasHandlers():
    # Avoid double logging if root logger is configured
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

# --- Constants (Potentially move to config) ---
# These might need adjustment based on screen resolution, OS, and Cursor layout
CURSOR_WINDOW_TITLE = "Cursor"  # Default title, might need adjustment
# Coordinates are highly unreliable - use image recognition or activation sequences instead
# INPUT_FIELD_COORDS = (500, 950) # Example - VERY UNRELIABLE

# Time delays for UI actions (seconds)
ACTIVATE_DELAY = 0.5
TYPE_INTERVAL = 0.01  # Faster typing
PASTE_DELAY = 0.2
ENTER_DELAY = 0.1
SUBMIT_WAIT_DELAY = 1.0  # Wait after submitting


class CursorPromptController:
    # EDIT START: Add class level deprecation warning
    """DEPRECATED: Uses fragile pyautogui to send prompts. Use AgentBus events instead.

    Uses pyautogui to send prompts to the Cursor chat interface.
    WARNING: This approach is highly unreliable and prone to breaking with UI changes,
             timing issues, or focus stealing. It should only be used as a last resort
             if the AgentBus event mechanism is unavailable.
    """
    # EDIT END

    def __init__(self):
        # EDIT START: Add init level deprecation warning
        warnings.warn(
            "CursorPromptController is deprecated. Prefer integrations.cursor.utils.publish_cursor_inject_event.",
            DeprecationWarning,
            stacklevel=2,
        )
        # EDIT END
        # Note: Consider integrating CursorWindowController here for activation if this
        # class were to be maintained, but deprecation is strongly recommended.
        self.bot = OrchestratorBot(config=None, agent_id="CursorPromptController")

    def _activate_cursor_window(self):
        """Attempts to find and activate the Cursor window."""
        # EDIT START: Use OrchestratorBot for window activation
        return self.bot.activate_window(CURSOR_WINDOW_TITLE)
        # EDIT END

    def _focus_chat_input(self):
        """Attempts to focus the chat input field. Highly dependent on layout/hotkeys."""
        logger.info("Attempting to focus Cursor chat input...")
        # EDIT START: Use OrchestratorBot for hotkey
        try:
            self.bot.hotkey("ctrl", "l")
            time.sleep(PASTE_DELAY)
            logger.info("Sent Ctrl+L hotkey to focus chat input.")
            return True
        except Exception as e:
            logger.error(f"Failed to send focus hotkey: {e}")
            logger.warning(
                "Focusing chat input failed. " "Pasting might go to wrong location."
            )
            return False
        # EDIT END

    def send_prompt_to_chat(self, prompt: str) -> bool:
        """DEPRECATED: Activates Cursor, focuses chat (best effort), pastes, and submits prompt."""
        warnings.warn(
            "send_prompt_to_chat is deprecated. Prefer "
            "integrations.cursor.utils.publish_cursor_inject_event.",
            DeprecationWarning,
            stacklevel=2,
        )
        logger.warning(
            "Executing deprecated send_prompt_to_chat via OrchestratorBot. "
            "This is unreliable."
        )
        logger.info(f"Attempting to send prompt to Cursor chat: '{prompt[:100]}...'")

        if not self._activate_cursor_window():
            return False

        self._focus_chat_input()

        # EDIT START: Use OrchestratorBot for clipboard and typing
        try:
            self.bot.copy_to_clipboard(prompt)
            time.sleep(PASTE_DELAY)
            self.bot.hotkey("ctrl", "v")
            logger.info("Pasted prompt using Ctrl+V.")
            time.sleep(PASTE_DELAY)
        except Exception as e:
            logger.error(
                f"Failed to paste prompt using OrchestratorBot clipboard: {e}",
                exc_info=True,
            )
            logger.info("Falling back to typing prompt...")
            try:
                self.bot.typewrite(prompt, interval=TYPE_INTERVAL)
                logger.info("Finished typing prompt.")
            except Exception as type_e:
                logger.error(f"Fallback typing also failed: {type_e}")
                return False
        # EDIT END

        # Submit the prompt
        try:
            self.bot.press("enter")
            logger.info("Pressed Enter to submit prompt.")
            time.sleep(SUBMIT_WAIT_DELAY)
            return True
        except Exception as e:
            logger.error(f"Failed to press Enter: {e}")
            return False


# Example Usage Block
if __name__ == "__main__":
    # EDIT START: Add warning to example usage
    print("### WARNING: Running DEPRECATED CursorPromptController example! ###")
    print("This uses fragile UI automation (pyautogui) and is not recommended.")
    print("Prefer using the AgentBus event mechanism for interaction.")
    # EDIT END
    print("Running CursorPromptController example...")

    # --- IMPORTANT SAFETY NOTICE ---
    # This script will take control of your mouse and keyboard.
    # Ensure the Cursor window is visible and potentially active before running.
    # Be prepared to manually stop the script (e.g., Ctrl+C in terminal) if needed.
    # PyAutoGUI has a failsafe (move mouse to corner), but be cautious.
    # --- --- --- --- --- --- --- ---

    controller = CursorPromptController()

    test_prompt = (
        "Hello Cursor! This is an automated test prompt from "
        "CursorPromptController. Please write a short python function to add two numbers."
    )

    print(f"Will attempt to send the following prompt in 5 seconds:")
    print(f"---\n{test_prompt}\n---")
    print("SWITCH TO CURSOR NOW if needed. Press Ctrl+C to abort.")

    try:
        time.sleep(5)
        print("Attempting to send prompt...")
        success = controller.send_prompt_to_chat(test_prompt)
        if success:
            print("Prompt sent successfully (check Cursor!).")
        else:
            print("Failed to send prompt.")

    except KeyboardInterrupt:
        print("\nOperation aborted by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {{e}}")
        logger.error("Error in example usage block", exc_info=True)

    print("CursorPromptController example finished.")
