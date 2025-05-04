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


# {{ EDIT START: Add THEA Response Copy Utility }}
def copy_thea_reply(
    anchor_image_path: str,
    click_offset: Tuple[int, int],
    confidence: float = 0.9,
    retries: int = 2,
    delay_between_actions: float = 0.1,
) -> Optional[str]:
    """
    Attempts to copy the latest THEA reply text from Cursor UI.

    Locates an anchor image (e.g., THEA's avatar) near the last response,
    clicks nearby using an offset, selects all, copies,
    and returns clipboard content.

    Args:
        anchor_image_path: Path to the anchor image (e.g., THEA's avatar).
        click_offset: (x, y) offset from anchor center to click inside the message.
        confidence: Confidence level for locating the anchor image.
        retries: Number of times to retry the copy sequence if validation fails.
        delay_between_actions: Pause duration between pyautogui actions.

    Returns:
        The copied text content, or None if unsuccessful.
    """
    if (
        not PYAUTOGUI_AVAILABLE
        or not pyautogui
        or not PYPERCLIP_AVAILABLE
        or not pyperclip
    ):
        logger.error(
            "copy_thea_reply cannot run: pyautogui or pyperclip not available."
        )
        return None

    clipboard_placeholder = f"_dreamos_clear_{time.time()}_"
    original_clipboard = None

    for attempt in range(retries + 1):
        logger.info(
            f"Attempting to copy THEA reply (Attempt {attempt + 1}/{retries + 1})..."
        )
        try:
            # 1. Locate Anchor
            logger.debug(f"Locating anchor image: {anchor_image_path}")
            anchor_pos = pyautogui.locateCenterOnScreen(
                anchor_image_path, confidence=confidence, grayscale=True
            )
            if not anchor_pos:
                logger.warning(
                    f"Anchor image '{Path(anchor_image_path).name}' not found on screen."
                )
                if attempt < retries:
                    time.sleep(0.5 * (attempt + 1))  # Simple backoff
                    continue
                else:
                    return None  # Failed after retries
            logger.debug(f"Anchor found at: {anchor_pos}")

            # 2. Calculate Click Position
            click_x = anchor_pos.x + click_offset[0]
            click_y = anchor_pos.y + click_offset[1]
            logger.debug(f"Calculated click position: ({click_x}, {click_y})")

            # 3. Prepare Clipboard (Clear)
            try:
                original_clipboard = (
                    pyperclip.paste()
                )  # Store original to restore later if needed
                pyperclip.copy(clipboard_placeholder)
                time.sleep(delay_between_actions / 2)
                if pyperclip.paste() != clipboard_placeholder:
                    logger.warning("Clipboard clear verification failed.")
                    # Continue anyway, maybe copy will overwrite
            except Exception as clip_err:
                logger.error(f"Failed to prepare clipboard: {clip_err}")
                # Don't retry if clipboard interaction fails fundamentally
                return None

            # 4. Click to Focus
            pyautogui.click(click_x, click_y, duration=delay_between_actions / 2)
            time.sleep(delay_between_actions)

            # 5. Select All
            pyautogui.hotkey(
                "ctrl", "a"
            )  # Assuming Windows/Linux, adjust for Mac ('command', 'a') if needed
            time.sleep(delay_between_actions)

            # 6. Copy
            pyautogui.hotkey(
                "ctrl", "c"
            )  # Assuming Windows/Linux, adjust for Mac ('command', 'c') if needed
            time.sleep(delay_between_actions * 2)  # Give clipboard time to update

            # 7. Retrieve & Validate
            copied_text = pyperclip.paste()

            if copied_text != clipboard_placeholder and copied_text.strip():
                logger.info(f"Successfully copied text (length: {len(copied_text)}).")
                return copied_text
            else:
                logger.warning(
                    f"Validation failed: Clipboard content empty or unchanged (attempt {attempt + 1})."
                )
                # Continue to next retry attempt

        except pyautogui.FailSafeException:
            logger.error("PyAutoGUI fail-safe triggered (mouse moved to corner?).")
            return None  # Fail safe means stop
        except Exception as e:
            logger.exception(
                f"Error during THEA reply copy sequence (attempt {attempt + 1}): {e}"
            )
            # Fall through to retry logic

        # If loop continues (validation failed or general error), wait before next attempt
        if attempt < retries:
            wait_time = 0.5 * (attempt + 1)  # Simple backoff
            logger.info(f"Waiting {wait_time:.1f}s before retry...")
            time.sleep(wait_time)

    # If loop finishes without returning, all retries failed
    logger.error("Failed to copy THEA reply after all retries.")
    # Optionally restore original clipboard content?
    # if original_clipboard is not None:
    #     pyperclip.copy(original_clipboard)
    return None


# {{ EDIT END }}
