"""
Main module for PyAutoGUI-based GUI automation tasks.

This module will contain functions and classes related to controlling
and interacting with the graphical user interface.
"""

import logging
import os  # Added for screenshot path handling
import time

import pyautogui

# Configure logging
# Use a more robust logging setup, perhaps configured elsewhere
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger(__name__) # Use module-specific logger

# PyAutoGUI Configuration (Optional, but good practice)
pyautogui.PAUSE = 0.25 # Slightly faster default pause
pyautogui.FAILSAFE = True # Enable failsafe (move mouse to top-left corner to stop)

class GuiActionError(Exception):
    """Custom exception for GUI action failures."""
    pass

# --- Configuration ---
# Consider loading configuration from external files (e.g., JSON, YAML)
# or environment variables instead of hardcoding.
# Example:
# config = load_config('config/automation_config.yaml')

# --- Core Automation Functions ---

def example_gui_task():
    """
    An example function demonstrating basic PyAutoGUI usage with error handling.
    """
    try:
        logger.info("Starting example GUI task...")
        # Placeholder: Add actual PyAutoGUI commands here
        # e.g., pyautogui.click(100, 100)
        # pyautogui.write('Hello world!', interval=0.1)
        screen_width, screen_height = pyautogui.size()
        logger.info(f"Screen resolution: {screen_width}x{screen_height}")

        # Example click with error handling
        try:
            pyautogui.click(x=screen_width // 2, y=screen_height // 2, duration=0.5)
            logger.info("Clicked center of the screen.")
        except Exception as click_err:
            logger.error(f"Failed to perform click: {click_err}")
            # Handle specific exceptions as needed, e.g., pyautogui.FailSafeException

        logger.info("Example GUI task finished.")
        return True

    except pyautogui.FailSafeException:
        logger.error("Fail-safe triggered! Mouse moved to a corner.")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during the GUI task: {e}")
        return False

# --- Swarm Bridge Integration (Placeholder) ---
# This section will be developed further as part of DEV-003.
# It might involve:
# - Listening for triggers/commands from other agents/systems.
# - Reporting status/results back.
# - Using shared queues or APIs for communication.

def listen_for_automation_triggers():
    """Placeholder for the mechanism that waits for automation commands.""""
    logger.info("Automation listener started (placeholder)...")
    # Example: loop waiting for messages from a queue or API endpoint
    pass

def report_automation_status(task_id, status, result=None):
    """Placeholder for reporting task status back to the swarm/coordinator.""""
    logger.info(f"Reporting status for {task_id}: {status}, Result: {result}")
    # Example: send message to a queue or update a database/API
    pass

def execute_gui_action(action_name: str, target: any = None, text: str = None, **kwargs):
    """
    Executes a specific GUI automation action using pyautogui via the automation bridge.

    Args:
        action_name (str): The name of the action to perform. Supported actions:
                           'click', 'type', 'move', 'locate', 'screenshot'.
        target (any, optional): The primary target for the action.
                                - For 'click', 'move': Can be coordinates (x, y tuple) or None (uses current position).
                                - For 'locate': The path to the image file to locate.
                                - For 'screenshot': Optional path to save the screenshot. If None, uses a default name/location.
                                - Not used for 'type'. Defaults to None.
        text (str, optional): The text to type for the 'type' action. Defaults to None.
        kwargs (dict): Additional keyword arguments passed directly to the underlying
                       pyautogui function (e.g., button='right', duration=0.5, interval=0.1, confidence=0.8).

    Returns:
        any: The result of the action, specific to the action type.
             - For 'locate': A Box object (left, top, width, height) if found, else None.
             - For 'screenshot': The path to the saved screenshot file.
             - For other actions: True on success, False on failure.

    Raises:
        GuiActionError: If the action fails due to PyAutoGUI issues (e.g., image not found, failsafe)
                        or if the action name is unsupported.
        ValueError: If required arguments are missing or invalid for the specified action.
    """
    action_name = action_name.lower()
    logger.info(f"Received GUI action request: '{action_name}' | Target: {target} | Text: {text} | Kwargs: {kwargs}")

    try:
        if action_name == 'click':
            if target is not None and not (isinstance(target, (tuple, list)) and len(target) == 2):
                raise ValueError(f"Invalid target for 'click': Expected (x, y) tuple or None, got {target}")
            logger.debug(f"Performing click at {target if target else 'current position'} with options {kwargs}")
            pyautogui.click(target, **kwargs)
            return True

        elif action_name == 'type':
            if text is None or not isinstance(text, str):
                raise ValueError(f"Invalid or missing 'text' argument for 'type' action: Expected a string, got {type(text)}")
            # Ensure text is escaped for logging if it contains problematic characters, or truncate safely
            log_text = text.replace('\n', '\\n').replace('\r', '\\r')[:50]
            logger.debug(f"Typing text: '{log_text}...' with options {kwargs}")
            pyautogui.typewrite(text, **kwargs)
            return True

        elif action_name == 'move':
            if target is None or not (isinstance(target, (tuple, list)) and len(target) == 2):
                 raise ValueError(f"Invalid or missing 'target' for 'move': Expected (x, y) tuple, got {target}")
            logger.debug(f"Moving mouse to {target} with options {kwargs}")
            pyautogui.moveTo(target[0], target[1], **kwargs)
            return True

        elif action_name == 'locate':
            if target is None or not isinstance(target, str):
                 raise ValueError(f"Invalid or missing 'target' for 'locate': Expected image file path (string), got {type(target)}")
            logger.debug(f"Locating image '{target}' on screen with options {kwargs}")
            # Ensure confidence is passed if provided, otherwise use pyautogui default
            location = pyautogui.locateOnScreen(target, **kwargs)
            if location:
                logger.info(f"Image '{target}' found at {location}")
                return location
            else:
                logger.warning(f"Image '{target}' not found on screen.")
                return None # Explicitly return None if not found

        elif action_name == 'screenshot':
            # Determine save path
            save_path = target if isinstance(target, str) else f"screenshot_{int(time.time())}.png"
            # Ensure directory exists if path contains directories
            save_dir = os.path.dirname(save_path)
            if save_dir and not os.path.exists(save_dir):
                try:
                    os.makedirs(save_dir)
                    logger.info(f"Created directory for screenshot: {save_dir}")
                except OSError as e:
                     logger.error(f"Failed to create directory {save_dir} for screenshot: {e}")
                     raise GuiActionError(f"Failed to create directory for screenshot: {e}")

            logger.debug(f"Taking screenshot and saving to '{save_path}' with options {kwargs}")
            screenshot_img = pyautogui.screenshot(**kwargs) # Pass region etc. via kwargs
            screenshot_img.save(save_path)
            logger.info(f"Screenshot saved to: {save_path}")
            return save_path

        else:
            # Log unsupported actions
            logger.error(f"Unsupported GUI action name: '{action_name}'")
            raise GuiActionError(f"Unsupported GUI action: {action_name}")

    except pyautogui.FailSafeException:
        # Log failsafe errors specifically
        logger.critical("PyAutoGUI FAILSAFE triggered by moving mouse to a corner.")
        raise GuiActionError("Failsafe triggered")
    except (pyautogui.ImageNotFoundException, FileNotFoundError) as img_err:
        # Log image-related errors
        logger.error(f"Error during 'locate' or 'screenshot' for target '{target}': {img_err}")
        raise GuiActionError(f"Image-related error for target '{target}': {img_err}") from img_err
    except Exception as e:
        # Catch-all for other pyautogui or logic errors, log and raise custom error
        logger.exception(f"An unexpected error occurred executing GUI action '{action_name}': {e}")
        raise GuiActionError(f"Failed to execute action '{action_name}': {e}") from e

# Example Usage (Updated for new structure)
if __name__ == '__main__':
    try:
        logger.info("GUI Automation Test Sequence Starting...")
        time.sleep(2)

        # Example 1: Move mouse
        logger.info("Moving mouse to (100, 100)")
        execute_gui_action('move', target=(100, 100), duration=0.5)
        time.sleep(1)

        # Example 2: Click at current location (Right Click)
        # logger.info("Right-clicking at current location")
        # execute_gui_action('click', button='right') # Uncomment carefully!
        # time.sleep(1)

        # Example 3: Type text (ensure a text field is active first!)
        # logger.info("Typing 'Hello from the bridge!'")
        # execute_gui_action('type', text='Hello from the bridge!', interval=0.05)
        # time.sleep(1)

        # Example 4: Locate an image (replace with a real path)
        # image_path = 'path/to/your/image.png'
        # logger.info(f"Attempting to locate '{image_path}'")
        # location = execute_gui_action('locate', target=image_path, confidence=0.8)
        # if location:
        #     logger.info(f"Image found at: {location}")
        #     center = pyautogui.center(location)
        #     execute_gui_action('move', target=center, duration=0.5)
        # else:
        #     logger.warning("Image not found.")
        # time.sleep(1)

        # Example 5: Take a screenshot
        logger.info("Taking a screenshot (default name)")
        screenshot_file = execute_gui_action('screenshot')
        logger.info(f"Screenshot taken: {screenshot_file}")
        time.sleep(1)
        # Example 5b: Take screenshot with specific name/region
        # logger.info("Taking screenshot of region (10, 10, 100, 100)")
        # screenshot_file_region = execute_gui_action('screenshot', target='region_screenshot.png', region=(10, 10, 100, 100))
        # logger.info(f"Region screenshot taken: {screenshot_file_region}")
        # time.sleep(1)


        # Example 6: Unsupported action
        # logger.info("Testing unsupported action 'fly'")
        # execute_gui_action('fly')

        logger.info("GUI Automation Test Sequence Completed.")

    except GuiActionError as e:
        logger.error(f"GUI Action Error during test: {e}")
    except ValueError as e:
        logger.error(f"Value Error during test: {e}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during test: {e}")
