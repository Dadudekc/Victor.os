# src/dreamos/utils/gui_utils.py
"""Utilities for GUI Automation and related coordinate handling."""

import json  # Added json
import logging
import subprocess  # Added subprocess
import sys  # Added sys
import time
from pathlib import Path  # Added Path
from typing import Any, Dict, Optional, Tuple

# Import core error and potentially PROJECT_ROOT if needed here
# from ..core.config import PROJECT_ROOT # If needed for default paths
# --- EDIT START: Import AppConfig ---
from dreamos.core.config import AppConfig, load_config

# --- EDIT END ---

logger = logging.getLogger(__name__)

# --- Coordinate Utilities ---


def get_specific_coordinate(
    identifier: str, full_coords: Optional[Dict[str, Any]]
) -> Optional[Tuple[int, int]]:
    """Extracts specific (x, y) coordinates for an identifier (e.g., 'agent_01.input_box')."""  # noqa: E501
    if not full_coords:
        logger.debug(f"Full coordinates data is None, cannot get '{identifier}'.")
        return None

    parts = identifier.split(".")  # e.g., ['agent_01', 'input_box']
    if len(parts) != 2:
        logger.warning(
            f"Invalid coordinate identifier format: '{identifier}'. Expected 'agent_id.element_key'."  # noqa: E501
        )
        return None

    agent_id, element_key = parts

    agent_coords = full_coords.get(agent_id)
    if not agent_coords or not isinstance(agent_coords, dict):
        logger.debug(
            f"No coordinate data found for agent '{agent_id}' in the provided structure."  # noqa: E501
        )
        return None

    coords = agent_coords.get(element_key)
    if not coords:
        logger.debug(
            f"No coordinates found for element '{element_key}' within agent '{agent_id}'."  # noqa: E501
        )
        return None

    # Expecting coords to be [x, y] list or (x, y) tuple or {'x': val, 'y': val} dict
    if (
        isinstance(coords, (list, tuple))
        and len(coords) == 2
        and all(isinstance(c, int) for c in coords)
    ):
        logger.debug(
            f"Found list/tuple coordinates for '{identifier}': {tuple(coords)}"
        )
        return tuple(coords)
    elif (
        isinstance(coords, dict)
        and "x" in coords
        and "y" in coords
        and isinstance(coords["x"], int)
        and isinstance(coords["y"], int)
    ):
        logger.debug(
            f"Found dict coordinates for '{identifier}': {(coords['x'], coords['y'])}"
        )
        return (coords["x"], coords["y"])
    else:
        logger.warning(
            f"Invalid coordinate format for '{identifier}': {coords}. Expected [x, y] or {{ 'x': x, 'y': y }}."  # noqa: E501
        )
        return None


# --- Add other missing GUI utils here ---

# {{ EDIT START: Add placeholder functions for missing utils }}


def copy_text_from_cursor(*args, **kwargs) -> Optional[str]:
    """**Placeholder:** Copies text from the Cursor window (Not Implemented)."""
    logger.warning(
        "Placeholder function 'copy_text_from_cursor' called. Not implemented."
    )
    return None


def close_browser(*args, **kwargs):
    """**Placeholder:** Closes the browser used by web agents (Not Implemented)."""
    logger.warning("Placeholder function 'close_browser' called. Not implemented.")
    pass


def launch_browser(*args, **kwargs):
    """**Placeholder:** Launches a browser for web agents (Not Implemented)."""
    logger.warning("Placeholder function 'launch_browser' called. Not implemented.")
    pass


def inject_text_via_mouse(*args, **kwargs):
    """**Placeholder:** Injects text at current mouse position (Not Implemented)."""
    logger.warning(
        "Placeholder function 'inject_text_via_mouse' called. Not implemented."
    )
    pass


def perform_mouse_action(*args, **kwargs):
    """**Placeholder:** Performs a generic mouse action (Not Implemented)."""
    logger.warning(
        "Placeholder function 'perform_mouse_action' called. Not implemented."
    )
    pass


def navigate_to_page(*args, **kwargs):
    """**Placeholder:** Navigates browser to a specific page (Not Implemented)."""
    logger.warning("Placeholder function 'navigate_to_page' called. Not implemented.")
    pass


def wait_for_login(*args, **kwargs):
    """**Placeholder:** Waits for a login process to complete (Not Implemented)."""
    logger.warning("Placeholder function 'wait_for_login' called. Not implemented.")
    pass


# {{ EDIT END }}


def load_coordinates(coords_file_path: Path | str) -> Optional[Dict[str, Any]]:
    """Safely loads and parses the JSON coordinate file."""
    path = Path(coords_file_path)
    if not path.exists() or not path.is_file():
        logger.error(f"Coordinate file not found or is not a file: {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                logger.warning(f"Coordinate file is empty: {path}")
                return {}
            data = json.loads(content)
            if not isinstance(data, dict):
                logger.error(
                    f"Coordinate file does not contain a valid JSON dictionary: {path}"
                )
                return None
            logger.info(f"Successfully loaded coordinates from: {path}")
            return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from coordinate file {path}: {e}")
        return None
    except IOError as e:
        logger.error(f"Failed to read coordinate file {path}: {e}")
        return None
    except Exception as e:
        logger.error(
            f"An unexpected error occurred loading coordinates from {path}: {e}",
            exc_info=True,
        )
        return None


# --- Window Utilities ---

try:
    import pygetwindow

    PYGETWINDOW_AVAILABLE = True
except ImportError:
    pygetwindow = None
    PYGETWINDOW_AVAILABLE = False
    logger.warning(
        "pygetwindow not found. Window focus check may be unreliable or disabled."
    )

# Attempt PyAutoGUI import here as well for wait_for_element
try:
    import pyautogui

    PYAUTOGUI_AVAILABLE = True  # Assume it's available if import succeeds
except ImportError:
    pyautogui = None
    # Keep PYAUTOGUI_AVAILABLE based on earlier check potentially?
    # For simplicity, if it fails here, assume not available for wait_for_element
    PYAUTOGUI_AVAILABLE = False
    logger.warning("pyautogui not found for wait_for_element. Visual waits disabled.")

try:
    import pyperclip

    PYPERCLIP_AVAILABLE = True
except ImportError:
    pyperclip = None
    PYPERCLIP_AVAILABLE = False


def is_window_focused(target_title_substring: str) -> bool:
    """Checks if the currently active window's title contains the target substring.

    Uses pygetwindow for cross-platform compatibility, but might be less reliable
    than OS-specific APIs, especially for exact matching or complex scenarios.

    Args:
        target_title_substring: A case-insensitive substring to look for in the active window title.

    Returns:
        True if pygetwindow is available, an active window is found, and its title contains the substring.
        False otherwise.
    """  # noqa: E501
    if not PYGETWINDOW_AVAILABLE or pygetwindow is None:
        logger.warning("is_window_focused check skipped: pygetwindow not available.")
        return False  # Cannot verify without the library

    try:
        active_window = pygetwindow.getActiveWindow()
        if active_window and active_window.title:
            logger.debug(f"Active window found: '{active_window.title}'")
            # Case-insensitive comparison
            if target_title_substring.lower() in active_window.title.lower():
                logger.debug(
                    f"Active window title contains target substring '{target_title_substring}'. Focus presumed correct."  # noqa: E501
                )
                return True
            else:
                logger.debug(
                    f"Active window title does not contain target substring '{target_title_substring}'."  # noqa: E501
                )
                return False
        elif active_window:
            logger.warning("Active window found but has no title.")
            return False  # Can't verify without a title
        else:
            logger.warning("Could not get active window.")
            return False
    except pygetwindow.PyGetWindowException as e:
        # Errors can occur if no window is active (e.g., full screen game, RDP session)
        logger.error(f"Error getting active window using pygetwindow: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking window focus: {e}", exc_info=True)
        return False


# --- Recalibration Utility ---

# EDIT START: Remove local PROJECT_ROOT calculation
# # Define path relative to this file (utils/gui_utils.py -> utils -> core -> dreamos -> src -> tools)  # noqa: E501
# # Replicate PROJECT_ROOT definition locally to avoid problematic cross-module import
# GUI_UTILS_DIR = Path(__file__).resolve().parent
# PROJECT_ROOT = GUI_UTILS_DIR.parents[2] # utils -> core -> dreamos -> src
#
# RECALIBRATION_SCRIPT_PATH = (
#     PROJECT_ROOT / "src" / "tools" / "calibration" / "recalibrate_coords.py"
# )
# EDIT END


# EDIT START: Update function signature
def trigger_recalibration(
    identifier: str, coords_file_path: Path | str, project_root: Path
) -> bool:
    # EDIT END
    """Triggers the external recalibration script for a specific coordinate identifier.

    Args:
        identifier: The identifier that failed verification (e.g., 'agent_01.copy_button').
        coords_file_path: The path to the coordinate file that needs updating.
        project_root: The root path of the project.

    Returns:
        True if the script executed successfully (return code 0), False otherwise.
    """  # noqa: E501
    # EDIT START: Define script path using project_root argument
    recalibration_script_path = (
        project_root / "src" / "tools" / "calibration" / "recalibrate_coords.py"
    )
    # EDIT END

    if not recalibration_script_path.exists():
        logger.error(
            f"Recalibration script not found at: {recalibration_script_path}. Cannot recalibrate."  # noqa: E501
        )
        return False

    python_exe = sys.executable  # Use the same python that's running this
    command = [
        python_exe,
        str(recalibration_script_path),
        "--identifier",
        identifier,
        "--coords-file",
        str(coords_file_path),
        # Add any other necessary args for the script
    ]

    logger.info(
        f"Triggering recalibration script for '{identifier}' with command: {' '.join(command)}"  # noqa: E501
    )

    try:
        # Execute the script, wait for completion, capture output
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception on non-zero exit code
            # EDIT START: Use project_root argument for cwd
            cwd=project_root,
            # EDIT END
        )

        if process.returncode == 0:
            logger.info(
                f"Recalibration script for '{identifier}' completed successfully."
            )
            logger.debug(f"Recalibration stdout:\n{process.stdout}")
            if process.stderr:
                logger.warning(f"Recalibration stderr:\n{process.stderr}")
            return True
        else:
            logger.error(
                f"Recalibration script for '{identifier}' failed with return code {process.returncode}."  # noqa: E501
            )
            logger.error(f"Recalibration stdout:\n{process.stdout}")
            logger.error(f"Recalibration stderr:\n{process.stderr}")
            return False

    except FileNotFoundError as e:
        # Error finding python executable or script itself
        logger.error(
            f"Error executing recalibration script: {e}. Check Python path and script path.",  # noqa: E501
            exc_info=True,
        )
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error running recalibration script for '{identifier}': {e}",
            exc_info=True,
        )
        return False


# def trigger_recalibration(...)


# EDIT START: Add wait_for_element utility (Correct Implementation)
def wait_for_element(
    image_path: Path | str,
    timeout: float = 10.0,
    poll_interval: float = 0.5,
    confidence: float = 0.8,
    grayscale: bool = True,
) -> Optional[Tuple[int, int]]:
    """Waits for a visual element (image) to appear on screen.

    Polls using pyautogui.locateCenterOnScreen until the element is found
    or the timeout is reached.

    Args:
        image_path: Path to the reference image file.
        timeout: Maximum time to wait in seconds.
        poll_interval: Time between checks in seconds.
        confidence: Confidence level for image matching (0.0 to 1.0).
        grayscale: Use grayscale matching for robustness.

    Returns:
        Tuple (x, y) of the center coordinates if found, None otherwise.
    """
    if not PYAUTOGUI_AVAILABLE or pyautogui is None:
        logger.error("wait_for_element cannot run: pyautogui not available.")
        return None

    start_time = time.time()
    img_path_str = str(image_path)
    img_filename = Path(img_path_str).name
    logger.debug(f"Waiting up to {timeout:.1f}s for element: {img_filename}")

    while time.time() - start_time < timeout:
        try:
            # Ensure pyautogui has screen access (can fail in some environments)
            center = pyautogui.locateCenterOnScreen(
                img_path_str, confidence=confidence, grayscale=grayscale
            )
            if center:
                logger.info(
                    f"Element {img_filename} found at ({center.x}, {center.y}) after {time.time() - start_time:.2f}s."  # noqa: E501
                )
                # Return as plain tuple
                return (center.x, center.y)
            # else: # No need to log 'not found yet' every poll interval, too verbose
            #     logger.debug(f"Element {img_filename} not found yet, polling...")
        except pyautogui.ImageNotFoundException:
            # This is expected if the image isn't there yet
            logger.debug(
                f"Element {img_filename} not found (ImageNotFoundException), polling..."
            )
        except Exception as e:
            # Log other errors, but continue polling unless it's fatal
            logger.error(
                f"Unexpected error during locateCenterOnScreen for {img_filename}: {e}",
                # exc_info=True, # Maybe too verbose for polling loop
            )
            # Consider adding specific error handling if needed (e.g., permissions)

        # Wait before next poll
        time.sleep(poll_interval)

    logger.warning(
        f"Timeout waiting for element {img_filename} after {timeout:.1f} seconds."
    )
    return None


# EDIT END


# --- EDIT START: Define default config keys ---
DEFAULT_THEA_COPY_CONFIG = {
    "anchor_image_path": "assets/thea_reply_anchor.png",
    "click_offset_x": 50,
    "click_offset_y": 50,
    "confidence": 0.9,
    "retries": 2,
    "delay_between_actions": 0.1,
}
# --- EDIT END ---


def copy_thea_reply(
    # --- EDIT START: Remove direct args, add optional config ---
    # anchor_image_path: str,
    # click_offset: Tuple[int, int],
    # confidence: float = 0.9,
    # retries: int = 2,
    # delay_between_actions: float = 0.1,
    config: Optional[AppConfig] = None,
    # --- EDIT END ---
) -> Optional[str]:
    """Locates the THEA reply anchor image, clicks relative to it, selects all,
    copies the text to the clipboard, and returns it.

    Uses pyautogui for visual search and control, and pyperclip for clipboard access.
    Loads parameters from AppConfig if provided, otherwise uses defaults.
    Handles platform-specific hotkeys.
    """
    # --- EDIT START: Load config and parameters ---
    if not config:
        try:
            config = load_config()
            logger.debug("Loaded AppConfig internally for copy_thea_reply.")
        except Exception as e:
            logger.error(
                f"Failed to load AppConfig for copy_thea_reply: {e}. Using defaults.",
                exc_info=True,
            )
            config = None  # Ensure config is None if loading fails

    # Get parameters from config or use defaults
    thea_config = (
        getattr(config.gui_automation, "thea_copy", {})
        if config and hasattr(config, "gui_automation")
        else {}
    )

    anchor_image_path_str = thea_config.get(
        "anchor_image_path", DEFAULT_THEA_COPY_CONFIG["anchor_image_path"]
    )
    click_offset_x = thea_config.get(
        "click_offset_x", DEFAULT_THEA_COPY_CONFIG["click_offset_x"]
    )
    click_offset_y = thea_config.get(
        "click_offset_y", DEFAULT_THEA_COPY_CONFIG["click_offset_y"]
    )
    confidence = thea_config.get("confidence", DEFAULT_THEA_COPY_CONFIG["confidence"])
    retries = thea_config.get("retries", DEFAULT_THEA_COPY_CONFIG["retries"])
    delay_between_actions = thea_config.get(
        "delay_between_actions", DEFAULT_THEA_COPY_CONFIG["delay_between_actions"]
    )

    # Resolve relative anchor image path against project root if config was loaded
    if config and config.paths and config.paths.project_root:
        anchor_image_path = config.paths.project_root / anchor_image_path_str
    else:
        # Fallback if config or project_root couldn't be loaded
        logger.warning(
            "Cannot resolve project root. Assuming anchor image path is absolute or relative to CWD."
        )
        anchor_image_path = Path(anchor_image_path_str)

    click_offset = (click_offset_x, click_offset_y)

    logger.info(f"Attempting to copy THEA reply using anchor: {anchor_image_path}")
    # --- EDIT END ---

    if not PYAUTOGUI_AVAILABLE or pyautogui is None:
        logger.error("copy_thea_reply failed: pyautogui is not available.")
        return None
    if not PYPERCLIP_AVAILABLE or pyperclip is None:
        logger.error("copy_thea_reply failed: pyperclip is not available.")
        return None

    initial_clipboard = pyperclip.paste()  # Store initial clipboard content
    found_text = None

    for attempt in range(retries + 1):
        try:
            logger.debug(f"Attempt {attempt + 1}/{retries + 1}: Locating anchor...")
            center = pyautogui.locateCenterOnScreen(
                str(anchor_image_path),
                confidence=confidence,
                grayscale=True,  # Greyscale often helps
            )

            if center is None:
                logger.warning("Anchor image not found on screen.")
                if attempt < retries:
                    time.sleep(0.5)  # Wait before retrying
                    continue
                else:
                    logger.error("Anchor image not found after all retries.")
                    return None

            target_x = center.x + click_offset[0]
            target_y = center.y + click_offset[1]

            logger.debug(
                f"Anchor found at {center}. Clicking at offset ({target_x}, {target_y})."
            )
            pyautogui.moveTo(target_x, target_y, duration=0.1)
            time.sleep(delay_between_actions)  # Small delay before click
            pyautogui.click()
            time.sleep(delay_between_actions)  # Small delay after click

            # --- EDIT START: Platform-specific hotkeys ---
            logger.debug(
                f"Executing select-all and copy hotkeys for platform: {sys.platform}"
            )
            if sys.platform == "darwin":  # macOS
                pyautogui.hotkey("command", "a")
                time.sleep(delay_between_actions)
                pyautogui.hotkey("command", "c")
            else:  # Windows, Linux, etc.
                pyautogui.hotkey("ctrl", "a")
                time.sleep(delay_between_actions)
                pyautogui.hotkey("ctrl", "c")
            # --- EDIT END ---

            time.sleep(0.2)  # Allow clipboard time to update

            copied_text = pyperclip.paste()

            if copied_text != initial_clipboard and copied_text:
                logger.info("Successfully copied new content from THEA reply area.")
                found_text = copied_text
                break  # Success
            else:
                logger.warning(
                    "Copy action did not yield new clipboard content. Retrying if possible."
                )
                # Clear clipboard to help detect changes on next attempt?
                # pyperclip.copy("")
                # time.sleep(0.1)
                if attempt >= retries:
                    logger.error("Failed to copy new content after all retries.")
                    return None  # Failed after retries

        except pyautogui.FailSafeException:
            logger.error(
                "PyAutoGUI fail-safe triggered (mouse moved to corner). Aborting."
            )
            return None
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during THEA copy attempt {attempt + 1}: {e}",
                exc_info=True,
            )
            if attempt >= retries:
                logger.error(
                    "Aborting THEA copy after encountering errors in final attempt."
                )
                return None  # Failed after retries

        # Wait before next attempt if not the last one
        if attempt < retries:
            logger.debug(f"Waiting before retry attempt {attempt + 2}...")
            time.sleep(0.5)

    return found_text


# Example of using the clipboard safely
def get_clipboard_content_safe() -> Optional[str]:
    if not PYPERCLIP_AVAILABLE:
        logger.error("Cannot get clipboard content: Pyperclip not available.")
        return None
    try:
        content = safe_paste_from_clipboard()
        return content
    except RuntimeError as e:
        logger.error(f"Failed to get clipboard content after retries: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting clipboard content: {e}")
        return None


def copy_text_from_agent(copy_coords: tuple[int, int], delay: float = 0.5) -> str:
    """Click the copy area and capture clipboard content from the agent window."""
    try:
        logger.debug(f"Clicking copy coordinates: {copy_coords}")
        pyautogui.click(copy_coords)
        time.sleep(delay)  # Wait after click
        pyautogui.hotkey("ctrl", "a")  # Select all
        time.sleep(0.1)  # Short delay between hotkeys
        pyautogui.hotkey("ctrl", "c")  # Copy
        time.sleep(0.2)  # Allow clipboard to update
        response = pyperclip.paste().strip()
        logger.debug(f"Clipboard content retrieved: {len(response)} chars")
        return response
    except Exception as e:
        logger.error(f"Error during agent text copy via GUI: {e}", exc_info=True)
        # Depending on pyautogui setup, errors like FailSafeException might occur
        # Returning empty string indicates failure to copy
        return ""
