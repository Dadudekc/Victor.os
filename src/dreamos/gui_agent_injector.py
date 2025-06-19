"""
Stub for GUI agent prompt injection.
This will be expanded into a more robust injector module.
"""
import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pyautogui

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    pyperclip = None
    PYPERCLIP_AVAILABLE = False

try:
    import pygetwindow
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    pygetwindow = None
    PYGETWINDOW_AVAILABLE = False

logger = logging.getLogger(__name__)

# --- Constants from the original CursorInjector ---
DEFAULT_COORDS_FILE = Path("runtime/config/cursor_agent_coords.json")
DEFAULT_WINDOW_TITLE = "Cursor"

# --- CursorInjector class definition (copied from src/dreamos/utils/gui/injector.py) ---
class CursorInjector:
    """Handles direct GUI interactions to inject prompts into an agent's input field."""

    def __init__(
        self,
        agent_id: str,
        coords_file: Path = DEFAULT_COORDS_FILE,
        window_title: Optional[str] = None,  # Agent-specific title if needed
        min_pause: float = 0.05,
        max_pause: float = 0.15,
        random_offset: int = 2,
        focus_verify: bool = True,
        use_paste: bool = True,
    ):
        self.agent_id = agent_id
        self.coords_file = (
            Path(coords_file) if isinstance(coords_file, str) else coords_file
        )
        self.window_title = (
            window_title if window_title else f"{DEFAULT_WINDOW_TITLE}"
        ) 
        self.min_pause = min_pause
        self.max_pause = max_pause
        self.random_offset = random_offset
        self.focus_verify_enabled = focus_verify
        self.use_paste_enabled = use_paste
        self.paste_available = PYPERCLIP_AVAILABLE
        self.focus_check_available = PYGETWINDOW_AVAILABLE
        self.log = logging.getLogger(self.__class__.__name__ + f".{agent_id}") # Made logger more specific
        self.all_coords: Optional[Dict[str, Any]] = self._load_agent_coordinates()

        if not self.all_coords:
            self.log.error(
                f"Failed to load coordinates for any agent from {self.coords_file}"
            )

    def _load_agent_coordinates(self) -> Optional[Dict[str, Any]]:
        """Loads the full coordinate structure from the JSON file."""
        try:
            if self.coords_file.exists():
                with open(self.coords_file, "r") as f:
                    data = json.load(f)
                    self.log.info(
                        f"Successfully loaded coordinates from {self.coords_file}"
                    )
                    return data
            else:
                self.log.error(f"Coordinates file not found: {self.coords_file}")
                return None
        except json.JSONDecodeError:
            self.log.exception(f"Error decoding JSON from {self.coords_file}")
            return None
        except Exception as e:
            self.log.exception(f"Unexpected error loading coordinates: {e}")
            return None

    def _get_specific_agent_coords(
        self, element_key_suffix: str
    ) -> Optional[Tuple[int, int]]:
        """Extracts coordinates for the agent's specified element."""
        if not self.all_coords:
            self.log.error("Cannot get specific agent coords: all_coords not loaded.")
            return None
        agent_coord_key = f"{self.agent_id}.{element_key_suffix}"
        coords = self.all_coords.get(agent_coord_key)
        if coords is None and self.agent_id in self.all_coords:
            agent_data = self.all_coords[self.agent_id]
            coords = agent_data.get(element_key_suffix)
        if isinstance(coords, list) and len(coords) == 2:
            return tuple(coords) # type: ignore
        elif (
            isinstance(coords, dict) and "x" in coords and "y" in coords
        ):  
            return (coords["x"], coords["y"])
        else:
            self.log.warning(
                f"Coordinates for key '{self.agent_id}.{element_key_suffix}' are not in the expected list [x, y] or dict {{x:val, y:val}} "
                f"in {self.coords_file}. Found: {coords}"
            )
            return None

    def _pause(self, duration: Optional[float] = None) -> None:
        time.sleep(
            duration
            if duration is not None
            else random.uniform(self.min_pause, self.max_pause)
        )

    def focus_window(self) -> bool:
        """Focus the agent's window."""
        if not self.focus_check_available or not pygetwindow:
            self.log.warning("pygetwindow not available, cannot focus window by title.")
            return False # Or True if we want to attempt injection anyway
        try:
            # Attempt to find a window title that matches self.window_title, which might be specific like "Cursor - Agent-1"
            # If self.window_title is just "Cursor", it will find the first one.
            target_windows = pygetwindow.getWindowsWithTitle(self.window_title)
            if not target_windows:
                self.log.error(f"Could not find window with title '{self.window_title}' for {self.agent_id}")
                # Fallback: try to find any window containing the base DEFAULT_WINDOW_TITLE if specific title failed
                if self.window_title != DEFAULT_WINDOW_TITLE:
                    self.log.info(f"Falling back to search for general window title '{DEFAULT_WINDOW_TITLE}'")
                    target_windows = pygetwindow.getWindowsWithTitle(DEFAULT_WINDOW_TITLE)
                    if not target_windows:
                        self.log.error(f"Fallback window search for '{DEFAULT_WINDOW_TITLE}' also failed.")
                        return False
                else:
                    return False
            
            win = target_windows[0] # Take the first match
            if win.isMinimized:
                win.restore()
            win.activate()
            self._pause(0.2) # Allow time for focus
            return win.isActive # Verify if activation was successful
        except Exception as e:
            self.log.error(f"Error focusing window for {self.agent_id} (title: '{self.window_title}'): {e}", exc_info=True)
            return False

    def _type_or_paste(self, text: str) -> None:
        """Internal helper to type or paste text."""
        if self.use_paste_enabled and self.paste_available and pyperclip:
            try:
                current_clipboard = pyperclip.paste()
                pyperclip.copy(text)
                self._pause(0.05)
                pyautogui.hotkey("ctrl", "v")
                self._pause(0.05)
                if isinstance(current_clipboard, str):
                    pyperclip.copy(current_clipboard)
                self.log.debug(f"Pasted text for {self.agent_id} via clipboard.")
                return
            except Exception as e:
                self.log.warning(
                    f"Clipboard paste failed for {self.agent_id} ({e}). Falling back to typing."
                )
        for char in text:
            pyautogui.typewrite(char)
            time.sleep(random.uniform(0.01, 0.03))
        self.log.debug(f"Typed text for {self.agent_id} using pyautogui.typewrite.")

    def _clear_input_field(self, x: int, y: int) -> None:
        """Clicks the field, selects all, and deletes."""
        pyautogui.click(x, y)
        self._pause()
        pyautogui.hotkey("ctrl", "a")
        self._pause()
        pyautogui.press("delete")
        self._pause()
        self.log.debug(f"Cleared input field for {self.agent_id} at ({x},{y}).")

    # Synchronous inject method, kept for potential direct use or reference
    def inject(self, prompt: str, current_input_coords: Optional[Tuple[int, int]]) -> bool:
        """Focuses the agent's window and injects the prompt into its input field."""
        self.log.info(
            f"Attempting to inject prompt for {self.agent_id}: '{prompt[:50]}...'"
        )
        if not current_input_coords:
            self.log.error(
                f"Cannot inject prompt: Input coordinates not provided or not loaded/found for {self.agent_id}."
            )
            return False
        if self.focus_verify_enabled and not self.focus_window(): # focus_verify_enabled check
            self.log.warning(
                f"Failed to focus window for {self.agent_id}. Injection may fail or go to wrong window."
            )
        x, y = current_input_coords
        tx = x + random.randint(-self.random_offset, self.random_offset)
        ty = y + random.randint(-self.random_offset, self.random_offset)
        try:
            pyautogui.moveTo(tx, ty, duration=random.uniform(0.1, 0.3))
            self._pause(0.1)
            self._clear_input_field(tx, ty)
            self._type_or_paste(prompt)
            self._pause()
            pyautogui.press('enter')
            self.log.debug(f"Pressed Enter for {self.agent_id} after injection.")
            self.log.info(f"Successfully injected prompt for {self.agent_id}.")
            return True
        except Exception as e:
            self.log.error(
                f"Error during prompt injection for {self.agent_id}: {e}", exc_info=True
            )
            self.take_screenshot_on_error(f"inject_fail_{self.agent_id}")
            return False

    async def inject_text(self, text: str, is_initial_prompt: bool = False) -> bool:
        """Async wrapper to inject text. Handles initial prompt specially if needed."""
        self.log.info(f"Async inject_text called for {self.agent_id}. Initial: {is_initial_prompt}")
        # Determine which coordinates to use
        coord_key = "input_box_initial" if is_initial_prompt else "input_box_followup"
        # Fallback to initial if followup not defined
        input_coords = self._get_specific_agent_coords(coord_key)
        if not input_coords and not is_initial_prompt:
            self.log.warning(f"Follow-up input coordinates '{coord_key}' not found for {self.agent_id}. Falling back to initial input box.")
            input_coords = self._get_specific_agent_coords("input_box_initial")
        
        if not input_coords:
            self.log.error(f"Input coordinates ('{coord_key}' or fallback) not found for {self.agent_id}. Cannot inject.")
            self.take_screenshot_on_error(f"no_coords_fail_{self.agent_id}")
            return False

        # The actual GUI interaction (inject) is synchronous
        # We run it in an executor to make this method awaitable and non-blocking
        loop = asyncio.get_event_loop()
        try:
            success = await loop.run_in_executor(
                None,  # Uses the default ThreadPoolExecutor
                self.inject, # The synchronous method to call
                text, # Argument for self.inject
                input_coords # Argument for self.inject
            )
            return success
        except Exception as e:
            self.log.error(f"Exception in run_in_executor for inject: {e}", exc_info=True)
            self.take_screenshot_on_error(f"executor_fail_{self.agent_id}")
            return False

    def take_screenshot_on_error(self, filename_prefix: str = "error_screenshot"):
        """Takes a screenshot and saves it to a debug directory."""
        try:
            screenshot_dir = Path("runtime/debug_screenshots") # Consider making this configurable
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            path = screenshot_dir / f"{filename_prefix}_{timestamp}.png"
            pyautogui.screenshot(str(path))
            self.log.info(f"Error screenshot saved to {path}")
        except Exception as e:
            self.log.error(f"Failed to take error screenshot: {e}", exc_info=True)

# --- Updated inject_prompt function ---
async def inject_prompt(agent_id: str, text: str, initial: bool = False) -> bool:
    """
    Injects a prompt into the specified agent's GUI using CursorInjector.
    Args:
        agent_id: The ID of the target agent (e.g., "Agent-1").
        text: The prompt text to inject.
        initial: Whether this is the initial prompt for the agent.
    Returns:
        True if injection was successful, False otherwise.
    """
    if not text:
        logger.warning(f"No prompt text provided for {agent_id}. Skipping injection.")
        return False

    try:
        # CursorInjector is now defined in this file.
        # TODO: Decide if coords_file or window_title should be passed from a central config
        # For now, it uses defaults or agent_id to derive them.
        logger.info(f"Attempting to inject prompt into {agent_id} (initial: {initial}): '{text[:100]}...'")
        injector = CursorInjector(agent_id=agent_id) 
        
        success = await injector.inject_text(text, is_initial_prompt=initial)
        
        if success:
            logger.info(f"Successfully injected prompt into {agent_id}.")
            return True
        else:
            logger.error(f"Failed to inject prompt into {agent_id} via CursorInjector.")
            return False
    except Exception as e:
        logger.error(f"Error during prompt injection for {agent_id}: {e}", exc_info=True)
        return False

# Example of how this might be called (for illustration):
# async def example_usage():
#     if await inject_prompt("Agent-1", "Hello, this is your first task.", initial=True):
#         print("Prompt sent!")
#     else:
#         print("Failed to send prompt.") 