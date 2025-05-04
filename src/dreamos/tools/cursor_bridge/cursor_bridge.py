# src/dreamos/tools/cursor_bridge/cursor_bridge.py
import logging
import platform
import time

import pyautogui
import pyperclip  # For reliable pasting
import pytesseract  # Requires pytesseract and Tesseract OCR engine

# Add imports for response reading
from PIL import Image  # Requires Pillow

logger = logging.getLogger(__name__)

# Configuration (Consider moving to config file or class)
CURSOR_WINDOW_TITLE_SUBSTRING = "Cursor"  # Adjust if needed
DEFAULT_TYPE_INTERVAL = 0.01  # Seconds between keystrokes
FOCUS_WAIT_TIME = 0.5  # Seconds to wait after focusing window
PASTE_WAIT_TIME = 0.1  # Seconds to wait after paste command

# Response reading config
RESPONSE_AREA_REGION = None  # (left, top, width, height) - MUST BE CONFIGURED
RESPONSE_POLL_INTERVAL = 0.5  # Seconds between checks
RESPONSE_STABILITY_THRESHOLD = 2.0  # Seconds of no change to declare stable
RESPONSE_TIMEOUT = 60.0  # Max seconds to wait for a response


class CursorBridgeError(Exception):
    """Base exception for bridge errors."""

    pass


class CursorInjectError(CursorBridgeError):
    """Custom exception for injection errors."""

    pass


class CursorExtractError(CursorBridgeError):
    """Custom exception for extraction errors."""

    pass


def find_and_focus_cursor_window(title_substring: str = CURSOR_WINDOW_TITLE_SUBSTRING):
    """Finds the Cursor window and attempts to focus it."""
    try:
        windows = pyautogui.getWindowsWithTitle(title_substring)
        if not windows:
            raise CursorInjectError(
                f"No window found with title containing '{title_substring}'"
            )

        # Assuming the first match is the correct one
        cursor_window = windows[0]
        logger.debug(f"Found Cursor window: {cursor_window.title}")

        # Different focus methods per OS might be needed for reliability
        os_type = platform.system()
        if os_type == "Windows":
            if cursor_window.isMinimized:
                cursor_window.restore()
            if not cursor_window.isActive:
                cursor_window.activate()
        elif os_type == "Darwin":  # macOS
            # macOS requires different handling, potentially AppleScript or other libs
            # For now, basic activate()
            if not cursor_window.isActive:
                cursor_window.activate()  # Might not be reliable on Mac
        else:  # Linux
            if not cursor_window.isActive:
                cursor_window.activate()

        time.sleep(FOCUS_WAIT_TIME)  # Give window time to activate

        # Verify focus (optional but recommended)
        active_window = pyautogui.getActiveWindow()
        if active_window is None or title_substring not in active_window.title:
            logger.warning(
                f"Attempted to focus Cursor window, but active window is now: {active_window.title if active_window else 'None'}"
            )
            # raise CursorInjectError("Failed to confirm focus on Cursor window.")

        return cursor_window

    except pyautogui.PyAutoGUIException as e:
        logger.error(
            f"PyAutoGUI error finding/focusing Cursor window: {e}", exc_info=True
        )
        raise CursorInjectError(f"PyAutoGUI error focusing window: {e}") from e
    except Exception as e:
        logger.error(
            f"Unexpected error finding/focusing Cursor window: {e}", exc_info=True
        )
        raise CursorInjectError(f"Unexpected error focusing window: {e}") from e


def inject_prompt_into_cursor(prompt: str):
    """Focuses Cursor, pastes the prompt, and presses Enter."""
    try:
        find_and_focus_cursor_window()

        # TODO: Need to locate the chat input field reliably
        # Option 1: Assume focus is correct and type/paste directly
        # Option 2: Use pyautogui.locateCenterOnScreen() with an image of the input field
        # Option 3: Use fixed coordinates (least reliable)

        # Using paste for potentially long prompts
        original_clipboard = pyperclip.paste()
        pyperclip.copy(prompt)
        time.sleep(PASTE_WAIT_TIME)  # Allow clipboard to update

        pyautogui.hotkey("ctrl", "v")  # Use hotkey for paste
        # pyautogui.typewrite(prompt, interval=DEFAULT_TYPE_INTERVAL) # Alternative: typing
        time.sleep(0.1)  # Brief pause after paste

        pyautogui.press("enter")
        logger.info("Prompt injected and Enter pressed.")

        # Restore clipboard
        pyperclip.copy(original_clipboard)

    except CursorInjectError:
        # Error already logged by find_and_focus
        raise  # Re-raise to signal failure
    except pyautogui.PyAutoGUIException as e:
        logger.error(f"PyAutoGUI error during prompt injection: {e}", exc_info=True)
        raise CursorInjectError(f"PyAutoGUI error injecting prompt: {e}") from e
    except Exception as e:
        # Catch potential clipboard errors too
        logger.error(f"Unexpected error during prompt injection: {e}", exc_info=True)
        raise CursorInjectError(f"Unexpected error injecting prompt: {e}") from e


# --- Core Functions (Extraction) --- #


def configure_response_area(region: tuple[int, int, int, int]):
    """Sets the global RESPONSE_AREA_REGION."""
    global RESPONSE_AREA_REGION
    if (
        isinstance(region, tuple)
        and len(region) == 4
        and all(isinstance(x, int) for x in region)
    ):
        RESPONSE_AREA_REGION = region
        logger.info(f"Response area configured: {RESPONSE_AREA_REGION}")
    else:
        raise ValueError(
            "Invalid region format. Must be tuple of 4 integers (left, top, width, height)."
        )


def capture_response_area(region: tuple[int, int, int, int]) -> Image.Image:
    """Captures a screenshot of the specified screen region."""
    if not region:
        raise CursorExtractError("Response area region is not configured.")
    try:
        screenshot = pyautogui.screenshot(region=region)
        logger.debug(f"Captured screenshot of region: {region}")
        return screenshot
    except pyautogui.PyAutoGUIException as e:
        logger.error(f"PyAutoGUI error capturing screenshot: {e}", exc_info=True)
        raise CursorExtractError(f"PyAutoGUI error capturing screen: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error capturing screenshot: {e}", exc_info=True)
        raise CursorExtractError(f"Unexpected error capturing screen: {e}") from e


def extract_text_from_image(image: Image.Image) -> str:
    """Extracts text from a PIL Image using Tesseract OCR."""
    try:
        # TODO: Add Tesseract configuration if needed (e.g., path, language, psm)
        # Example: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        text = pytesseract.image_to_string(image).strip()
        logger.debug(f"Extracted text length: {len(text)}")
        return text
    except pytesseract.TesseractNotFoundError:
        logger.critical(
            "Tesseract executable not found. Please install Tesseract OCR and ensure it's in the system PATH or configure the path in code."
        )
        raise CursorExtractError("Tesseract not found. Cannot perform OCR.")
    except Exception as e:
        logger.error(f"Error during OCR extraction: {e}", exc_info=True)
        # Return empty string on OCR error? Or raise?
        # raise CursorExtractError(f"OCR extraction failed: {e}") from e
        return ""  # Return empty on error for now


def monitor_and_extract_response(
    timeout_seconds: float = RESPONSE_TIMEOUT,
    stability_threshold: float = RESPONSE_STABILITY_THRESHOLD,
    poll_interval: float = RESPONSE_POLL_INTERVAL,
) -> str:
    """Monitors the response area for stable text and returns the final result."""
    if RESPONSE_AREA_REGION is None:
        raise CursorExtractError(
            "Response area region must be configured before extraction."
        )

    start_time = time.time()
    last_change_time = start_time
    last_text = ""
    aggregated_text = ""

    logger.info("Starting response monitoring...")

    while time.time() - start_time < timeout_seconds:
        try:
            screenshot = capture_response_area(RESPONSE_AREA_REGION)
            current_text = extract_text_from_image(screenshot)

            # Simple comparison (more advanced diffing could be used)
            if current_text != last_text:
                logger.debug(
                    f"Response text changed (Length: {len(current_text)}). Resetting stability timer."
                )
                aggregated_text = (
                    current_text  # Assume latest text is the full text for now
                )
                last_text = current_text
                last_change_time = time.time()
            else:
                # Text is stable, check if threshold met
                if time.time() - last_change_time >= stability_threshold:
                    logger.info(
                        f"Response stable for {stability_threshold}s. Extraction complete."
                    )
                    return aggregated_text

        except CursorBridgeError as e:
            logger.warning(f"Error during monitoring loop: {e}. Continuing...")
            # Decide if specific errors should break the loop

        time.sleep(poll_interval)

    # If loop finishes due to timeout
    logger.warning(f"Response monitoring timed out after {timeout_seconds}s.")
    # Return whatever text was aggregated last, even if potentially incomplete
    return aggregated_text


# --- Integrated Interaction Function (Example) --- #
def interact_with_cursor(prompt: str) -> str:
    """Injects prompt, monitors, and returns response."""
    try:
        inject_prompt_into_cursor(prompt)
        response = monitor_and_extract_response()
        return response
    except CursorBridgeError as e:
        logger.error(f"Cursor interaction failed: {e}")
        # Re-raise or return error message?
        raise


# Example Usage (for testing)
# if __name__ == '__main__':
#     logging.basicConfig(level=logging.DEBUG)
#     # IMPORTANT: Configure this manually based on your screen setup!
#     # Use a tool or pyautogui.displayMousePosition() to find coords.
#     # Example coords (replace with actual):
#     test_region = (100, 200, 800, 400) # (left, top, width, height)
#     try:
#         configure_response_area(test_region)
#     except ValueError as e:
#         print(f"Config Error: {e}")
#         exit()
#
#     test_prompt = "What is the capital of France?"
#     try:
#          print("Attempting to inject prompt and read response (ensure Cursor is open)...")
#          for i in range(3, 0, -1):
#               print(f"{i}...")
#               time.sleep(1)
#          response = interact_with_cursor(test_prompt)
#          print("\n--- Response Received ---")
#          print(response)
#          print("-------------------------")
#     except CursorBridgeError as e:
#          print(f"Interaction failed: {e}")
#     except Exception as e:
#          print(f"An unexpected error occurred: {e}")
