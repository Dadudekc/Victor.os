"""GUI utilities for interacting with Cursor IDE."""

import logging
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# EDIT START: Add PYAUTOGUI_AVAILABLE logic for pyautogui compatibility
try:
    import pyautogui

    PYAUTOGUI_AVAILABLE = True  # Expose for downstream checks (e.g., chatgpt_web_agent)
except ImportError:
    pyautogui = None
    PYAUTOGUI_AVAILABLE = False
    logger.warning("pyautogui not found; GUI automation features will be disabled.")
# EDIT END

# EDIT START: Add pygetwindow import and availability check
try:
    import pygetwindow

    PYGETWINDOW_AVAILABLE = True
except ImportError:
    pygetwindow = None
    PYGETWINDOW_AVAILABLE = False
    logger.warning("pygetwindow not found; window focus checks will be disabled.")
# EDIT END


def is_window_focused(target_title_substring: str) -> bool:
    """Check if a window with the given title substring is focused.

    Args:
        target_title_substring: Case-insensitive substring to match in window title

    Returns:
        bool: True if a matching window is focused, False otherwise
    """
    if not PYGETWINDOW_AVAILABLE or pygetwindow is None:
        logger.warning("Window focus check skipped: pygetwindow not available")
        return False

    try:
        active_window = pygetwindow.getActiveWindow()
        if active_window and active_window.title:
            return target_title_substring.lower() in active_window.title.lower()
        return False
    except Exception as e:
        logger.error(f"Error checking window focus: {e}")
        return False


def get_cursor_window_handle() -> Optional[int]:
    """Get the window handle for the Cursor IDE.

    Returns:
        Optional[int]: Window handle if found, None otherwise.
    """
    # TODO: Implement actual window handle detection
    logger.debug("Getting Cursor window handle")
    return None


def get_cursor_window_rect() -> Optional[Tuple[int, int, int, int]]:
    """Get the window rectangle for the Cursor IDE.

    Returns:
        Optional[Tuple[int, int, int, int]]: (left, top, right, bottom) if found, None otherwise.
    """
    # TODO: Implement actual window rectangle detection
    logger.debug("Getting Cursor window rectangle")
    return None


def is_cursor_window_active() -> bool:
    """Check if the Cursor IDE window is active.

    Returns:
        bool: True if active, False otherwise.
    """
    # TODO: Implement actual window active check
    logger.debug("Checking if Cursor window is active")
    return True


def wait_for_cursor_window(timeout: float = 5.0) -> bool:
    """Wait for the Cursor IDE window to become active.

    Args:
        timeout (float): Maximum time to wait in seconds.

    Returns:
        bool: True if window became active, False if timed out.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_cursor_window_active():
            return True
        time.sleep(0.1)
    return False
