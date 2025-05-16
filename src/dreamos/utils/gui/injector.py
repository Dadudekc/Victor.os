import json
import logging
import random
import time
import asyncio
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

# Assuming project root is determinable or passed if necessary
# For simplicity, this version will assume a fixed relative path for coords
# or require it to be passed.
DEFAULT_COORDS_FILE = Path("runtime/config/cursor_agent_coords.json")
DEFAULT_WINDOW_TITLE = "Cursor"  # This might need to be agent-specific or configurable


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
        # Window title specific to the agent, e.g., "Cursor - Agent-1"
        # If not provided, could fall back to a general title or require one.
        self.window_title = (
            window_title if window_title else f"{DEFAULT_WINDOW_TITLE}"
        )  # Simplified for now

        self.min_pause = min_pause
        self.max_pause = max_pause
        self.random_offset = random_offset
        self.focus_verify_enabled = focus_verify
        self.use_paste_enabled = use_paste

        self.paste_available = PYPERCLIP_AVAILABLE
        self.focus_check_available = PYGETWINDOW_AVAILABLE

        self.log = logging.getLogger(self.__class__.__name__)
        self.all_coords: Optional[Dict[str, Any]] = self._load_agent_coordinates()

        if not self.all_coords:
            self.log.error(
                f"Failed to load coordinates for any agent from {self.coords_file}"
            )
            # Decide on error handling: raise error or operate in a degraded state?
            # For now, methods will check for self.input_coords availability

        self.input_coords = self._get_specific_agent_coords("input_box_initial")
        if not self.input_coords:
            self.log.warning(
                f"Could not find/load coordinates for '{self.agent_id}' input_box_initial."
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
        """Extracts coordinates for the agent's initial input box."""
        if not self.all_coords:
            self.log.error("Cannot get specific agent coords: all_coords not loaded.")
            return None

        # First try the flat format: "Agent-2.input_box_initial"
        agent_coord_key = f"{self.agent_id}.{element_key_suffix}"
        coords = self.all_coords.get(agent_coord_key)

        # If flat format not found, try nested format: all_coords["Agent-2"]["input_box_initial"]
        if coords is None and self.agent_id in self.all_coords:
            agent_data = self.all_coords[self.agent_id]
            coords = agent_data.get(element_key_suffix)

        # Handle different coordinate formats
        if isinstance(coords, list) and len(coords) == 2:
            return tuple(coords)  # type: ignore
        elif (
            isinstance(coords, dict) and "x" in coords and "y" in coords
        ):  # Support for dict format e.g. {"x": 1, "y": 2}
            return (coords["x"], coords["y"])
        else:
            self.log.warning(
                f"Coordinates for key '{self.agent_id}.{element_key_suffix}' are not in the expected list format [x, y] or dict {{'x': val, 'y': val}} "
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
        try:
            # Get window by title
            win = pygetwindow.getWindowsWithTitle("Cursor")[0]
            if not win:
                self.log.error(f"Could not find window for {self.agent_id}")
                return False

            # Try to activate window
            try:
                win.activate()
            except Exception as e:
                # Log but continue - some window managers may not support activate
                self.log.warning(f"Window activation failed for {self.agent_id}: {e}")
                # Try alternative method
                try:
                    win.minimize()
                    time.sleep(0.1)
                    win.restore()
                except Exception as e2:
                    self.log.warning(f"Alternative window focus failed for {self.agent_id}: {e2}")
                    return False

            # Wait for window to be active
            time.sleep(0.2)
            return True

        except Exception as e:
            self.log.error(f"Error focusing window for {self.agent_id} ('Cursor'): {e}")
            return False

    def _type_or_paste(self, text: str) -> None:
        """Internal helper to type or paste text."""
        if self.use_paste_enabled and self.paste_available and pyperclip:
            try:
                current_clipboard = pyperclip.paste()
                pyperclip.copy(text)
                self._pause(0.05)  # Small pause for clipboard to settle
                pyautogui.hotkey("ctrl", "v")
                self._pause(0.05)  # Pause after paste
                # Restore clipboard if it was simple text. Be careful with complex content.
                # For simplicity, only restore if it's likely plain text.
                # This is a common courtesy to the user but can be omitted if problematic.
                if isinstance(current_clipboard, str):
                    pyperclip.copy(current_clipboard)
                self.log.debug(f"Pasted text for {self.agent_id} via clipboard.")
                return
            except Exception as e:
                self.log.warning(
                    f"Clipboard paste failed for {self.agent_id} ({e}). Falling back to typing."
                )

        # Fallback to typing
        # Add small random delays between key presses to appear more human-like
        for char in text:
            pyautogui.typewrite(char)
            time.sleep(random.uniform(0.01, 0.03))  # Short random delay per character
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

    def inject(self, prompt: str) -> bool:
        """Focuses the agent's window and injects the prompt into its input field."""
        self.log.info(
            f"Attempting to inject prompt for {self.agent_id}: '{prompt[:50]}...'"
        )

        if not self.input_coords:
            self.log.error(
                f"Cannot inject prompt: Input coordinates not loaded/found for {self.agent_id}."
            )
            return False

        if not self.focus_window():
            self.log.warning(
                f"Failed to focus window for {self.agent_id}. Injection may fail or go to wrong window."
            )
            # Depending on strictness, might return False here
            # For now, we'll try to proceed

        x, y = self.input_coords
        # Add human-like jitter to click coordinates
        tx = x + random.randint(-self.random_offset, self.random_offset)
        ty = y + random.randint(-self.random_offset, self.random_offset)

        try:
            # Move to field, clear it, then type/paste
            pyautogui.moveTo(tx, ty, duration=random.uniform(0.1, 0.3))
            self._pause(0.1)  # Pause before click

            # Clear field before typing
            self._clear_input_field(tx, ty)

            self._type_or_paste(prompt)
            self._pause()  # Pause after typing/pasting

            # Optionally, press Enter if the GUI requires it (this is common)
            pyautogui.press('enter')
            self.log.debug(f"Pressed Enter for {self.agent_id} after injection.")
            # This should be configurable or part of the coordinate definition if 'enter_button' exists

            self.log.info(f"Successfully injected prompt for {self.agent_id}.")
            return True
        except Exception as e:
            self.log.error(
                f"Error during prompt injection for {self.agent_id}: {e}", exc_info=True
            )
            # Potentially take a screenshot on error if pyautogui.screenshot is available
            # self.take_screenshot_on_error(f"inject_fail_{self.agent_id}")
            return False

    async def inject_text(self, text: str) -> bool:
        """Async wrapper for inject method.
        
        Args:
            text: The text to inject into the agent's input field.
            
        Returns:
            bool: True if injection was successful, False otherwise.
        """
        # Run the synchronous inject method in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.inject, text)

    def take_screenshot_on_error(self, filename_prefix: str = "error_screenshot"):
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            # Ensure screenshots directory exists (e.g., runtime/debug_screenshots)
            # For now, saving to current dir or a predefined debug path
            screenshot_dir = Path("runtime/debug_screenshots")
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            filepath = screenshot_dir / f"{filename_prefix}_{timestamp}.png"
            pyautogui.screenshot(filepath)
            self.log.info(f"Screenshot saved to {filepath} on error.")
        except Exception as e:
            self.log.error(f"Failed to take screenshot: {e}")


if __name__ == "__main__":
    # Basic test and usage example
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    log = logging.getLogger(__name__)

    # --- Determine Project Root (if running as script) ---
    # This is a simplified way to get project root for the __main__ block.
    # In a real application, this might be handled differently.
    try:
        current_file_path = Path(__file__).resolve()
        # Assuming src/dreamos/utils/gui/injector.py
        # So, project root is 3 levels up from this file's directory.
        project_root_for_coords = current_file_path.parents[3]
    except NameError:  # __file__ is not defined (e.g. in interactive interpreter)
        project_root_for_coords = Path(".")  # Fallback to current directory

    coords_file_path = project_root_for_coords / DEFAULT_COORDS_FILE
    log.info(f"Using coordinate file: {coords_file_path}")

    if not coords_file_path.exists():
        log.error(
            f"CRITICAL: Coordinate file {coords_file_path} not found. Cannot run test."
        )
        # Create a dummy file for testing if it doesn't exist
        log.info(
            f"Attempting to create a dummy coordinate file for testing: {coords_file_path}"
        )
        try:
            coords_file_path.parent.mkdir(parents=True, exist_ok=True)
            dummy_coords = {
                "Agent-1.input_box_initial": [100, 100],
                "Agent-1.copy_button": [100, 150],
                "Agent-2.input_box_initial": [200, 100],
                "Agent-2.copy_button": [200, 150],
            }
            with open(coords_file_path, "w") as f:
                json.dump(dummy_coords, f, indent=4)
            log.info(
                f"Dummy coordinate file created at {coords_file_path}. Please calibrate for actual use."
            )
        except Exception as e:
            log.error(f"Failed to create dummy coordinate file: {e}")
            exit(1)

    # Test for a specific agent
    test_agent_id = "Agent-1"
    injector = CursorInjector(agent_id=test_agent_id, coords_file=coords_file_path)

    if injector.input_coords:
        log.info(
            f"Injector created for {test_agent_id} with input_coords: {injector.input_coords}"
        )

        # Make sure a window that might match "Agent-1" and "Cursor" is open and visible
        # For a real test, you'd have the agent GUI running.
        log.info(
            "Please ensure a GUI window for Agent-1 (or a window with 'Cursor' in title) is open and visible."
        )
        log.info("Test will attempt to focus and inject in 5 seconds...")
        time.sleep(5)

        test_prompt = "Hello from CursorInjector test! This is a test prompt."
        success = injector.inject(test_prompt)
        if success:
            log.info(f"Successfully injected prompt for {test_agent_id}.")
        else:
            log.error(f"Failed to inject prompt for {test_agent_id}.")
            injector.take_screenshot_on_error(f"test_inject_fail_{test_agent_id}")

        log.info("Test injection complete. Check the target GUI.")
    else:
        log.error(
            f"Could not initialize injector properly for {test_agent_id} due to missing coordinates. Test aborted."
        )
        log.info(
            f"Ensure '{test_agent_id}.input_box_initial' key exists in {coords_file_path}"
        )

    log.info("Script finished. To test other agents, modify 'test_agent_id'.")
