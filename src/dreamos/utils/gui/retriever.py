import logging
import json
import time
import random
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pyautogui

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    pyperclip = None
    PYPERCLIP_AVAILABLE = False

DEFAULT_COORDS_FILE = Path("runtime/config/cursor_agent_coords.json")
CLICK_DELAY_SECONDS = 0.2 # Standard delay after a click

class ResponseRetriever:
    """Handles retrieving agent responses by interacting with the GUI, typically by clicking a 'copy' button and reading the clipboard."""

    def __init__(
        self,
        agent_id: str, # Added agent_id for consistency, though copy button might be generic
        coords_file: Path = DEFAULT_COORDS_FILE,
        # element_key_for_copy: str = "copy_button" # Could be made configurable
    ):
        self.agent_id = agent_id
        self.coords_file = Path(coords_file) if isinstance(coords_file, str) else coords_file
        # self.element_key_for_copy = element_key_for_copy # e.g., Agent-1.copy_button
        self.log = logging.getLogger(self.__class__.__name__)
        self.all_coords: Optional[Dict[str, Any]] = self._load_agent_coordinates()

        if not self.all_coords:
            self.log.error(f"Failed to load coordinates from {self.coords_file} for {self.agent_id}")
        
        # While the user requested retrieve() to not take agent_id, the underlying coords are agent-specific.
        # So, we fetch the specific agent's copy button coords during init.
        self.copy_button_coords = self._get_specific_agent_coords("copy_button")
        if not self.copy_button_coords:
            self.log.warning(f"Could not find/load coordinates for '{self.agent_id}.copy_button'. Retrieval might fail.")

    def _load_agent_coordinates(self) -> Optional[Dict[str, Any]]:
        """Loads the full coordinate structure from the JSON file."""
        try:
            if self.coords_file.exists():
                with open(self.coords_file, 'r') as f:
                    data = json.load(f)
                    self.log.info(f"Successfully loaded coordinates from {self.coords_file} for {self.agent_id}")
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

    def _get_specific_agent_coords(self, element_key_suffix: str) -> Optional[Tuple[int, int]]:
        """Extracts coordinates for a specific element for the agent (e.g., 'copy_button')."""
        if not self.all_coords:
            self.log.error(f"Cannot get specific agent coords for '{element_key_suffix}': all_coords not loaded.")
            return None
        
        # First try the flat format: "Agent-2.copy_button"
        agent_coord_key = f"{self.agent_id}.{element_key_suffix}"
        coords = self.all_coords.get(agent_coord_key)
        
        # If flat format not found, try nested format: all_coords["Agent-2"]["copy_button"]
        if coords is None and self.agent_id in self.all_coords:
            agent_data = self.all_coords[self.agent_id]
            # Handle agent_data being a list (direct coordinates) or dict (with element keys)
            if isinstance(agent_data, dict):
                coords = agent_data.get(element_key_suffix)
            elif isinstance(agent_data, list) and len(agent_data) == 2:
                # If agent_data itself is a coordinate list, use it directly
                coords = agent_data
            else:
                self.log.warning(f"Agent data for '{self.agent_id}' is not in expected format. Found: {agent_data}")

        # Handle different coordinate formats
        if isinstance(coords, list) and len(coords) == 2:
            return tuple(coords) # type: ignore
        elif isinstance(coords, dict) and 'x' in coords and 'y' in coords:
            return (coords['x'], coords['y'])
        else:
            self.log.warning(
                f"Coordinates for key '{self.agent_id}.{element_key_suffix}' are not in the expected list [x,y] or dict format {{x:val, y:val}} "
                f"in {self.coords_file}. Found: {coords}"
            )
            return None

    def _pause(self, duration: Optional[float] = None) -> None:
        time.sleep(duration if duration is not None else random.uniform(0.1, 0.2))

    def retrieve(self) -> Optional[str]:
        """Clicks the agent's copy button (using pre-loaded coordinates) and returns clipboard content."""
        if not pyautogui or not PYPERCLIP_AVAILABLE or not pyperclip:
            self.log.error("pyautogui or pyperclip not available. Cannot retrieve response.")
            return None

        if not self.copy_button_coords:
            self.log.error(f"Cannot retrieve response for {self.agent_id}: copy button coordinates not found.")
            return None

        x, y = self.copy_button_coords
        self.log.debug(f"Attempting to retrieve response for {self.agent_id} by clicking copy button at ({x}, {y}).")

        original_pos = pyautogui.position()
        original_clipboard_content = pyperclip.paste()
        # Use a unique placeholder to ensure clipboard has changed
        placeholder = f"__retrieval_placeholder_{self.agent_id}_{time.time()}__"

        try:
            pyperclip.copy(placeholder) # Clear/set known state
            self._pause(0.05) # Ensure clipboard has time to update
            
            pyautogui.moveTo(x, y, duration=0.1)
            pyautogui.click()
            time.sleep(CLICK_DELAY_SECONDS) # Wait for the application to copy to clipboard

            # Restore mouse position immediately
            if original_pos:
                 pyautogui.moveTo(original_pos.x, original_pos.y, duration=0.1)

            retrieved_content = pyperclip.paste()

            if retrieved_content != placeholder and retrieved_content.strip():
                self.log.info(f"Successfully retrieved response for {self.agent_id} (length: {len(retrieved_content)}).")
                # Restore original clipboard if it was different from placeholder and not empty
                # This is a courtesy, but complex content might not restore perfectly.
                if original_clipboard_content != placeholder and isinstance(original_clipboard_content, str):
                    pyperclip.copy(original_clipboard_content)
                return retrieved_content
            else:
                self.log.warning(
                    f"Failed to retrieve valid response for {self.agent_id}. "
                    f"Clipboard content was same as placeholder or empty. Placeholder: '{placeholder}', Retrieved: '{retrieved_content}'"
                )
                # Restore original clipboard content on failure
                if isinstance(original_clipboard_content, str):
                     pyperclip.copy(original_clipboard_content)
                return None

        except Exception as e:
            self.log.error(f"Error during response retrieval for {self.agent_id}: {e}", exc_info=True)
            # Restore original clipboard content on exception
            if PYPERCLIP_AVAILABLE and pyperclip and isinstance(original_clipboard_content, str):
                 pyperclip.copy(original_clipboard_content)
            return None

if __name__ == '__main__':
    import random # Already imported but good for explicitness here
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log = logging.getLogger(__name__)

    try:
        current_file_path = Path(__file__).resolve()
        project_root_for_coords = current_file_path.parents[3] 
    except NameError: 
        project_root_for_coords = Path(".") 

    coords_file_path = project_root_for_coords / DEFAULT_COORDS_FILE
    log.info(f"Using coordinate file for retriever test: {coords_file_path}")

    if not coords_file_path.exists():
        log.error(f"CRITICAL: Coordinate file {coords_file_path} not found. Cannot run test.")
        log.info(f"Attempting to create a dummy coordinate file for testing: {coords_file_path}")
        try:
            coords_file_path.parent.mkdir(parents=True, exist_ok=True)
            dummy_coords = {
                "Agent-1.input_box_initial": [100, 100],
                "Agent-1.copy_button": [100, 150], # Crucial for this test
                "Agent-2.input_box_initial": [200, 100],
                "Agent-2.copy_button": [200, 150],
            }
            with open(coords_file_path, 'w') as f:
                json.dump(dummy_coords, f, indent=4)
            log.info(f"Dummy coordinate file created at {coords_file_path}. Please calibrate for actual use.")
        except Exception as e:
            log.error(f"Failed to create dummy coordinate file: {e}")
            exit(1)
    
    test_agent_id = "Agent-1"
    retriever = ResponseRetriever(agent_id=test_agent_id, coords_file=coords_file_path)

    if retriever.copy_button_coords:
        log.info(f"Retriever created for {test_agent_id} with copy_button_coords: {retriever.copy_button_coords}")
        log.info("Please ensure the GUI for Agent-1 is open, visible, and has some text that can be copied via its 'copy' button.")
        log.info("Also, ensure the mouse is not interfering with the copy operation spot.")
        log.info("Test will attempt to retrieve in 5 seconds...")
        time.sleep(5)

        # Simulate some content in clipboard to test restoration
        if PYPERCLIP_AVAILABLE and pyperclip:
            pyperclip.copy("Original clipboard content before test.")

        response = retriever.retrieve()

        if response:
            log.info(f"Successfully retrieved response for {test_agent_id}:\n---\n{response}\n---")
        else:
            log.error(f"Failed to retrieve response for {test_agent_id}.")
            # In a real scenario, injector might take a screenshot here too

        if PYPERCLIP_AVAILABLE and pyperclip:
            log.info(f"Clipboard content after test: {pyperclip.paste()}")
        log.info("Test retrieval complete.")
    else:
        log.error(f"Could not initialize retriever properly for {test_agent_id} due to missing copy_button coordinates.")
        log.info(f"Ensure '{test_agent_id}.copy_button' key exists in {coords_file_path}")

    log.info(f"Retriever script finished.") 