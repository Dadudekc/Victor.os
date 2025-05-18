import json
import logging
import random
import time
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

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
CONTEXT_BOUNDARIES_FILE = Path("runtime/context_boundaries.json")


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
        """Load agent-specific coordinates from file"""
        try:
            if not self.coords_file.exists():
                self.log.warning(f"Coordinates file not found: {self.coords_file}")
                return None

            with open(self.coords_file, "r", encoding="utf-8") as f:
                all_coords = json.load(f)
                return all_coords  # Return entire config for all agents
        except Exception as e:
            self.log.error(f"Error loading coordinates: {e}")
            return None

    def _get_specific_agent_coords(self, element_key: str) -> Optional[Tuple[int, int]]:
        """Get coordinates for a specific element for this agent"""
        if not self.all_coords:
            return None

        agent_coords = self.all_coords.get(self.agent_id, {})
        if not agent_coords:
            self.log.warning(f"No coordinates found for {self.agent_id}")
            return None

        coords = agent_coords.get(element_key)
        if not coords:
            self.log.warning(
                f"No '{element_key}' coordinates found for {self.agent_id}"
            )
            return None

        try:
            x, y = coords
            return int(x), int(y)
        except (ValueError, TypeError) as e:
            self.log.error(f"Invalid coordinates format for {element_key}: {e}")
            return None

    def _random_pause(self) -> None:
        """Perform a random pause to simulate human behavior"""
        pause_time = random.uniform(self.min_pause, self.max_pause)
        time.sleep(pause_time)

    def _add_random_offset(self, x: int, y: int) -> Tuple[int, int]:
        """Add a small random offset to coordinates to simulate human behavior"""
        offset_x = random.randint(-self.random_offset, self.random_offset)
        offset_y = random.randint(-self.random_offset, self.random_offset)
        return x + offset_x, y + offset_y

    def _verify_window_focus(self) -> bool:
        """Verify that the correct window has focus"""
        if not self.focus_check_available:
            self.log.warning("Window focus check requested but pygetwindow not available")
            return True  # Assume focus is correct

        try:
            active_window = pygetwindow.getActiveWindow()
            if not active_window:
                self.log.warning("No active window detected")
                return False
                
            # Check if window title contains our target (partial match)
            if self.window_title.lower() not in active_window.title.lower():
                self.log.warning(
                    f"Wrong window has focus. Expected: {self.window_title}, Got: {active_window.title}"
                )
                return False
                
            return True
        except Exception as e:
            self.log.error(f"Error checking window focus: {e}")
            return False  # Assume focus is incorrect on error

    def inject(self, text: str, target_coords: Tuple[int, int]) -> bool:
        """
        Inject text into an input field at the specified coordinates.
        
        Args:
            text: The text to inject
            target_coords: The (x, y) coordinates to click before injecting
            
        Returns:
            bool: True if injection was successful, False otherwise
        """
        try:
            # Check for context boundary markers in the prompt
            text = self._check_and_add_context_markers(text)
            
            # Verify window focus if enabled
            if self.focus_verify_enabled and not self._verify_window_focus():
                self.log.error("Window focus verification failed")
                return False

            # Move to target position with random offset
            x, y = self._add_random_offset(*target_coords)
            pyautogui.moveTo(x, y, duration=0.3)
            self._random_pause()
            
            # Click to focus
            pyautogui.click()
            self._random_pause()
            
            # Use paste if enabled and available
            if self.use_paste_enabled and self.paste_available:
                # 1. Store original clipboard content
                try:
                    original_clipboard = pyperclip.paste()
                except:
                    original_clipboard = ""
                
                # 2. Copy our text to clipboard
                pyperclip.copy(text)
                self._random_pause()
                
                # 3. Paste
                pyautogui.hotkey('ctrl', 'v')
                self._random_pause()
                
                # 4. Restore original clipboard content
                pyperclip.copy(original_clipboard)
            else:
                # Fallback to typewrite
                pyautogui.typewrite(text, interval=0.01)
                
            return True
        except Exception as e:
            self.log.error(f"Error injecting text: {e}")
            return False

    async def inject_text(self, text: str, is_initial_prompt: bool = False) -> bool:
        """Async wrapper for inject method.
        
        Args:
            text: The text to inject into the agent's input field.
            is_initial_prompt: If True, uses 'input_box_initial' coordinates, otherwise uses 'input_box'.
            
        Returns:
            bool: True if injection was successful, False otherwise.
        """
        element_key_suffix = "input_box_initial" if is_initial_prompt else "input_box"
        target_input_coords = self._get_specific_agent_coords(element_key_suffix)

        if not target_input_coords:
            self.log.error(
                f"Cannot inject text: Input coordinates not loaded/found for {self.agent_id} using key '{element_key_suffix}'."
            )
            return False

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.inject, text, target_input_coords)

    async def inject_text_hybrid(
        self, 
        text: str, 
        is_initial_prompt: bool = False,
        retries: int = 1
    ) -> bool:
        """Inject text using a hybrid approach with retries.
        
        Args:
            text: The text to inject
            is_initial_prompt: Whether this is an initial prompt
            retries: Number of times to retry if injection fails
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check for context boundary markers in the prompt
        text = self._check_and_add_context_markers(text)
        
        element_key_suffix = "input_box_initial" if is_initial_prompt else "input_box"
        target_input_coords = self._get_specific_agent_coords(element_key_suffix)
        
        if not target_input_coords:
            self.log.error(
                f"Cannot inject text via hybrid method: Input coordinates not found for {self.agent_id} using key '{element_key_suffix}'."
            )
            return False
            
        attempt = 0
        while attempt <= retries:
            attempt += 1
            
            try:
                # Verify window focus if enabled
                if self.focus_verify_enabled and not self._verify_window_focus():
                    self.log.warning(f"Window focus verification failed on attempt {attempt}")
                    if attempt <= retries:
                        await asyncio.sleep(1)
                        continue
                    else:
                        return False
                
                # Move to target position with random offset
                x, y = self._add_random_offset(*target_input_coords)
                pyautogui.moveTo(x, y, duration=0.3)
                await asyncio.sleep(0.1)
                
                # Click to focus
                pyautogui.click()
                await asyncio.sleep(0.2)
                
                # Clear any existing text with Ctrl+A, Delete
                pyautogui.hotkey('ctrl', 'a')
                await asyncio.sleep(0.1)
                pyautogui.press('delete')
                await asyncio.sleep(0.1)
                
                # Use paste if available
                if PYPERCLIP_AVAILABLE:
                    # Store original clipboard
                    try:
                        original_clipboard = pyperclip.paste()
                    except:
                        original_clipboard = ""
                    
                    # Copy text to clipboard
                    pyperclip.copy(text)
                    await asyncio.sleep(0.1)
                    
                    # Paste with keyboard shortcut
                    pyautogui.hotkey('ctrl', 'v')
                    await asyncio.sleep(0.2)
                    
                    # Restore original clipboard
                    pyperclip.copy(original_clipboard)
                else:
                    # Fall back to typewrite (slower but more reliable for shorter text)
                    max_segment_length = 1000  # Maximum length for each segment
                    
                    # Split text into manageable segments
                    segments = [text[i:i+max_segment_length] for i in range(0, len(text), max_segment_length)]
                    
                    for segment in segments:
                        pyautogui.typewrite(segment, interval=0.01)
                        await asyncio.sleep(0.5)  # Pause between segments
                
                self.log.info(f"Successfully injected text (~{len(text)} chars) on attempt {attempt}")
                return True
                
            except Exception as e:
                self.log.error(f"Error during hybrid text injection (attempt {attempt}/{retries}): {e}")
                if attempt <= retries:
                    await asyncio.sleep(1)
                else:
                    return False
        
        return False

    async def send_submission_keys(self, key_combo: List[str]) -> bool:
        """Send key combination to submit prompt.
        
        Args:
            key_combo: List of keys to press together (e.g. ['ctrl', 'enter'])
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Verify window focus
            if self.focus_verify_enabled and not self._verify_window_focus():
                self.log.error("Window focus verification failed when trying to submit")
                return False
                
            # Send key combination
            pyautogui.hotkey(*key_combo)
            return True
            
        except Exception as e:
            self.log.error(f"Error sending submission keys {key_combo}: {e}")
            return False

    def _check_and_add_context_markers(self, text: str) -> str:
        """
        Check if there are context boundaries and add appropriate markers to the prompt
        
        Args:
            text: The original prompt text
            
        Returns:
            str: The modified prompt text with context boundary information if available
        """
        try:
            if not CONTEXT_BOUNDARIES_FILE.exists():
                return text
                
            with open(CONTEXT_BOUNDARIES_FILE, "r") as f:
                boundaries = json.load(f)
                
            current_phase = boundaries.get("current_phase")
            if not current_phase:
                return text
                
            # Find most recent boundary for this agent
            agent_boundaries = [
                b for b in boundaries.get("boundaries", [])
                if b.get("agent_id") == self.agent_id
            ]
            
            if not agent_boundaries:
                return text
                
            # Get latest boundary
            latest_boundary = sorted(
                agent_boundaries,
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )[0]
            
            # Add context marker to prompt
            marker = f"""
--- CONTEXT BOUNDARY INFORMATION ---
PLANNING PHASE: {latest_boundary.get('phase')}
BOUNDARY ID: {latest_boundary.get('boundary_id')}
REASON: {latest_boundary.get('reason')}
---

"""
            # Add marker at the beginning of the prompt
            return marker + text
            
        except Exception as e:
            self.log.error(f"Error adding context markers: {e}")
            return text
            
        
    def reset(self) -> None:
        """Reset any internal state"""
        pass


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

    # Attempt to get coordinates for the test
    test_input_coords = injector._get_specific_agent_coords("input_box_initial")

    if test_input_coords: # Check if we got the specific coordinates
        log.info( # Use log not self.log since we're in __main__
            f"Injector created for {test_agent_id} with input_coords: {test_input_coords}"
        )

        # Make sure a window that might match "Agent-1" and "Cursor" is open and visible
        # For a real test, you'd have the agent GUI running.
        log.info(
            "Please ensure a GUI window for Agent-1 (or a window with 'Cursor' in title) is open and visible."
        )
        log.info("Test will attempt to focus and inject in 5 seconds...")
        time.sleep(5)

        test_prompt = "Hello from CursorInjector test! This is a test prompt."
        # Pass the resolved coordinates to the inject method
        success = injector.inject(test_prompt, test_input_coords)
        if success:
            log.info(f"Successfully injected prompt for {test_agent_id}.")
        else:
            log.error(f"Failed to inject prompt for {test_agent_id}.")
            injector.take_screenshot_on_error(f"test_inject_fail_{test_agent_id}")

        log.info("Test injection complete. Check the target GUI.")
    else:
        log.error(
            f"Could not initialize injector properly for {test_agent_id} due to missing 'input_box_initial' coordinates. Test aborted."
        )
        log.info(
            f"Ensure '{test_agent_id}.input_box_initial' key exists in {coords_file_path}"
        )

    log.info("Script finished. To test other agents, modify 'test_agent_id'.")
