"""GUI utilities for interacting with Cursor IDE."""

import logging
import time
from typing import Optional, Tuple, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Import GUI automation libraries with availability checks
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    pyautogui = None
    PYAUTOGUI_AVAILABLE = False
    logger.warning("pyautogui not found; GUI automation features will be disabled.")

try:
    import pygetwindow as gw
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    gw = None
    PYGETWINDOW_AVAILABLE = False
    logger.warning("pygetwindow not found; window focus checks will be disabled.")

DEFAULT_WINDOW_TITLE = "Cursor"

def get_cursor_windows() -> List[Any]:
    """Get all Cursor IDE windows.
    
    Returns:
        List[Any]: List of window objects matching Cursor IDE.
    """
    if not PYGETWINDOW_AVAILABLE or gw is None:
        logger.warning("Window detection skipped: pygetwindow not available")
        return []
        
    try:
        # Get all windows with "Cursor" in the title
        cursor_windows = gw.getWindowsWithTitle("Cursor")
        return cursor_windows
    except Exception as e:
        logger.error(f"Error detecting Cursor windows: {e}")
        return []

def get_cursor_window_handle(window_title: str = DEFAULT_WINDOW_TITLE) -> Optional[int]:
    """Get the window handle for the Cursor IDE.
    
    Args:
        window_title (str): The window title to match. Defaults to "Cursor".
        
    Returns:
        Optional[int]: Window handle if found, None otherwise.
    """
    if not PYGETWINDOW_AVAILABLE or gw is None:
        logger.warning("Window handle detection skipped: pygetwindow not available")
        return None
        
    try:
        # Get matching windows
        cursor_windows = gw.getWindowsWithTitle(window_title)
        if cursor_windows:
            # Return the handle of the first matching window
            return cursor_windows[0]._hWnd
        return None
    except Exception as e:
        logger.error(f"Error getting window handle: {e}")
        return None

def get_cursor_window_rect(window_title: str = DEFAULT_WINDOW_TITLE) -> Optional[Tuple[int, int, int, int]]:
    """Get the window rectangle for the Cursor IDE.
    
    Args:
        window_title (str): The window title to match. Defaults to "Cursor".
        
    Returns:
        Optional[Tuple[int, int, int, int]]: (left, top, right, bottom) if found, None otherwise.
    """
    if not PYGETWINDOW_AVAILABLE or gw is None:
        logger.warning("Window rectangle detection skipped: pygetwindow not available")
        return None
        
    try:
        # Get matching windows
        cursor_windows = gw.getWindowsWithTitle(window_title)
        if cursor_windows:
            window = cursor_windows[0]
            return (window.left, window.top, window.right, window.bottom)
        return None
    except Exception as e:
        logger.error(f"Error getting window rectangle: {e}")
        return None

def is_cursor_window_active(window_title: str = DEFAULT_WINDOW_TITLE) -> bool:
    """Check if the Cursor IDE window is active.
    
    Args:
        window_title (str): The window title to match. Defaults to "Cursor".
        
    Returns:
        bool: True if active, False otherwise.
    """
    if not PYGETWINDOW_AVAILABLE or gw is None:
        logger.warning("Window active check skipped: pygetwindow not available")
        return False
        
    try:
        active_window = gw.getActiveWindow()
        if active_window and window_title.lower() in active_window.title.lower():
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking window active state: {e}")
        return False

def wait_for_cursor_window(window_title: str = DEFAULT_WINDOW_TITLE, timeout: float = 5.0) -> bool:
    """Wait for the Cursor IDE window to become active.
    
    Args:
        window_title (str): The window title to match. Defaults to "Cursor".
        timeout (float): Maximum time to wait in seconds.
        
    Returns:
        bool: True if window became active, False if timed out.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_cursor_window_active(window_title):
            return True
        time.sleep(0.1)
    return False

def focus_cursor_window(window_title: str = DEFAULT_WINDOW_TITLE) -> bool:
    """Focus the Cursor IDE window.
    
    Args:
        window_title (str): The window title to match. Defaults to "Cursor".
        
    Returns:
        bool: True if successfully focused, False otherwise.
    """
    if not PYGETWINDOW_AVAILABLE or gw is None:
        logger.warning("Window focus skipped: pygetwindow not available")
        return False
        
    try:
        cursor_windows = gw.getWindowsWithTitle(window_title)
        if cursor_windows:
            window = cursor_windows[0]
            if window.isMinimized:
                window.restore()
            window.activate()
            return True
        return False
    except Exception as e:
        logger.error(f"Error focusing window: {e}")
        return False

def wait_for_element(image_path: str, timeout: int = 10, confidence: float = 0.9) -> Optional[Tuple[int, int, int, int]]:
    """Waits for a specified image to appear on the screen.
    
    Args:
        image_path (str): Path to the image file to locate.
        timeout (int): Maximum time to wait in seconds.
        confidence (float): Confidence level for image matching (0.0 to 1.0).
        
    Returns:
        Optional[Tuple[int, int, int, int]]: Bounding box (left, top, width, height) if found, None otherwise.
    """
    if not PYAUTOGUI_AVAILABLE or pyautogui is None:
        logger.warning("Image detection skipped: pyautogui not available")
        return None

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                return location
        except pyautogui.PyAutoGUIException as e:
            # This can happen if the platform is not supported or screen access is denied
            logger.error(f"PyAutoGUI error during locateOnScreen: {e}")
            return None # Stop trying if pyautogui itself errors out
        time.sleep(0.5)
    logger.debug(f"Element with image '{image_path}' not found within {timeout}s timeout.")
    return None 