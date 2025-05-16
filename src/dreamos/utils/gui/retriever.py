import json
import logging
import random
import time
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import os

import pyautogui

try:
    import pyperclip

    PYPERCLIP_AVAILABLE = True
except ImportError:
    pyperclip = None
    PYPERCLIP_AVAILABLE = False

DEFAULT_COORDS_FILE = Path("runtime/config/cursor_agent_coords.json")
CLICK_DELAY_SECONDS = 0.2  # Standard delay after a click
GENERATING_IMAGE_PATH = Path("runtime/config/assets/gui_images/generating.png")
COMPLETE_IMAGE_PATH = Path("runtime/config/assets/gui_images/complete.png")
IMAGE_DETECTION_TIMEOUT_SECONDS = 300 # EDIT: Increased from 120 to 300 seconds (5 minutes)
IMAGE_DETECTION_CONFIDENCE = 0.8 # Confidence for pyautogui.locateOnScreen


class ResponseRetriever:
    """Handles retrieving agent responses by interacting with the GUI, typically by clicking a 'copy' button and reading the clipboard."""

    def __init__(
        self,
        agent_id: str,  # Added agent_id for consistency, though copy button might be generic
        coords_file: Path = DEFAULT_COORDS_FILE,
        # element_key_for_copy: str = "copy_button" # Could be made configurable
    ):
        self.agent_id = agent_id
        self.coords_file = (
            Path(coords_file) if isinstance(coords_file, str) else coords_file
        )
        # self.element_key_for_copy = element_key_for_copy # e.g., Agent-1.copy_button
        self.log = logging.getLogger(self.__class__.__name__)
        self.all_coords: Optional[Dict[str, Any]] = self._load_agent_coordinates()

        if not self.all_coords:
            self.log.error(
                f"Failed to load coordinates from {self.coords_file} for {self.agent_id}"
            )

        # While the user requested retrieve() to not take agent_id, the underlying coords are agent-specific.
        # So, we fetch the specific agent's copy button coords during init.
        self.copy_button_coords = self._get_specific_agent_coords("copy_button")
        if not self.copy_button_coords:
            self.log.warning(
                f"Could not find/load coordinates for '{self.agent_id}.copy_button'. Retrieval might fail."
            )

    def _load_agent_coordinates(self) -> Optional[Dict[str, Any]]:
        """Loads the full coordinate structure from the JSON file."""
        try:
            if self.coords_file.exists():
                with open(self.coords_file, "r") as f:
                    data = json.load(f)
                    self.log.info(
                        f"Successfully loaded coordinates from {self.coords_file} for {self.agent_id}"
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
        """Extracts coordinates for a specific element for the agent (e.g., 'copy_button')."""
        if not self.all_coords:
            self.log.error(
                f"Cannot get specific agent coords for '{element_key_suffix}': all_coords not loaded."
            )
            return None

        # Get agent data
        agent_data = self.all_coords.get(self.agent_id)
        if not agent_data:
            self.log.warning(f"No coordinates found for agent {self.agent_id}")
            return None

        # Get element coordinates
        element_data = agent_data.get(element_key_suffix)
        if not element_data:
            self.log.warning(f"No {element_key_suffix} coordinates found for agent {self.agent_id}")
            return None

        # Extract x,y coordinates
        if isinstance(element_data, dict) and "x" in element_data and "y" in element_data:
            return (element_data["x"], element_data["y"])
        else:
            self.log.warning(
                f"Coordinates for {self.agent_id}.{element_key_suffix} are not in the expected format {{x:val, y:val}}. Found: {element_data}"
            )
            return None

    def _pause(self, duration: Optional[float] = None) -> None:
        time.sleep(duration if duration is not None else random.uniform(0.1, 0.2))

    def retrieve(self) -> Optional[str]:
        """Clicks the agent's copy button (using pre-loaded coordinates) and returns clipboard content."""
        if not pyautogui or not PYPERCLIP_AVAILABLE or not pyperclip:
            self.log.error(
                "pyautogui or pyperclip not available. Cannot retrieve response."
            )
            return None

        if not self.copy_button_coords:
            self.log.error(
                f"Cannot retrieve response for {self.agent_id}: copy button coordinates not found."
            )
            return None

        x, y = self.copy_button_coords
        self.log.debug(
            f"Attempting to retrieve response for {self.agent_id} by clicking copy button at ({x}, {y})."
        )

        original_pos = pyautogui.position()
        original_clipboard_content = pyperclip.paste()
        # Use a unique placeholder to ensure clipboard has changed
        placeholder = f"__retrieval_placeholder_{self.agent_id}_{time.time()}__"

        try:
            pyperclip.copy(placeholder)  # Clear/set known state
            self._pause(0.05)  # Ensure clipboard has time to update

            pyautogui.moveTo(x, y, duration=0.1)
            pyautogui.click()
            # --- Take screenshot after clicking copy button ---
            try:
                screenshot_dir = Path("runtime/debug_screenshots")
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                screenshot_path = screenshot_dir / f"retriever_after_copy_{self.agent_id}_{int(time.time())}.png"
                pyautogui.screenshot(str(screenshot_path))
                self.log.info(f"Screenshot taken after copy click: {screenshot_path}")
            except Exception as e:
                self.log.warning(f"Failed to take screenshot after copy click: {e}")
            # --- End screenshot block ---
            time.sleep(
                CLICK_DELAY_SECONDS
            )  # Wait for the application to copy to clipboard

            # Restore mouse position immediately
            if original_pos:
                pyautogui.moveTo(original_pos.x, original_pos.y, duration=0.1)

            retrieved_content = pyperclip.paste()

            if retrieved_content != placeholder and retrieved_content.strip():
                self.log.info(
                    f"Successfully retrieved response for {self.agent_id} (length: {len(retrieved_content)})."
                )
                # Restore original clipboard if it was different from placeholder and not empty
                # This is a courtesy, but complex content might not restore perfectly.
                if original_clipboard_content != placeholder and isinstance(
                    original_clipboard_content, str
                ):
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
            self.log.error(
                f"Error during response retrieval for {self.agent_id}: {e}",
                exc_info=True,
            )
            # Restore original clipboard content on exception
            if (
                PYPERCLIP_AVAILABLE
                and pyperclip
                and isinstance(original_clipboard_content, str)
            ):
                pyperclip.copy(original_clipboard_content)
            return None

    def _wait_for_image(self, image_path: Path, timeout_seconds: int = IMAGE_DETECTION_TIMEOUT_SECONDS, confidence: float = IMAGE_DETECTION_CONFIDENCE) -> bool:
        """Waits for a specific image to appear on screen."""
        self.log.info(f"Waiting for image '{image_path}' to appear for up to {timeout_seconds} seconds...")
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            try:
                if pyautogui.locateOnScreen(str(image_path), confidence=confidence):
                    self.log.info(f"Image '{image_path}' detected.")
                    return True
            except pyautogui.PyAutoGUIException as e:
                self.log.warning(f"PyAutoGUIException while searching for image '{image_path}': {e}. Assuming image not found.", exc_info=True)
                # EDIT START: Add screenshot on PyAutoGUIException for debugging
                try:
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    screenshot_dir = Path("runtime/debug_screenshots")
                    screenshot_dir.mkdir(parents=True, exist_ok=True)
                    # Corrected filepath to avoid double .png if image_path.name already has it.
                    base, ext = os.path.splitext(image_path.name)
                    filepath = screenshot_dir / f"wait_for_image_fail_{timestamp}_{base}{ext}"
                    pyautogui.screenshot(str(filepath))
                    self.log.info(f"Debug screenshot saved to {filepath} on image search failure.")
                except Exception as se:
                    self.log.error(f"Failed to take debug screenshot: {se}")
                # EDIT END
            except Exception as e:
                # Catch any other unexpected errors during image search.
                self.log.error(f"Unexpected error while searching for image '{image_path}': {e}", exc_info=True)
            
            time.sleep(1) # Check once per second
        self.log.warning(f"Timeout: Image '{image_path}' not detected after {timeout_seconds} seconds.")
        return False

    async def get_response(
        self,
        retries: int = 3, # Retries for the copy action itself, after image is found
        retry_delay: int = 2,
        image_timeout_seconds: int = IMAGE_DETECTION_TIMEOUT_SECONDS # Allow override for specific calls
    ) -> Optional[str]:
        """Async wrapper for retrieve method with retries and delays, now waits for completion image."""
        try:
            # EDIT START: Wait for the "complete.png" image
            self.log.info(f"Waiting for response completion image for agent {self.agent_id}...")
            if not COMPLETE_IMAGE_PATH.exists():
                self.log.error(f"Completion image not found at {COMPLETE_IMAGE_PATH}. Cannot use image detection. Aborting retrieval for {self.agent_id}.")
                return None
                
            if not self._wait_for_image(COMPLETE_IMAGE_PATH, timeout_seconds=image_timeout_seconds):
                self.log.warning(f"Response completion image not detected for agent {self.agent_id}. Cannot retrieve response.")
                # Potentially take a screenshot here if debugging indicates it's useful
                # self.take_screenshot_on_error(f"no_complete_image_{self.agent_id}")
                return None
            
            self.log.info(f"Response completion image detected for {self.agent_id}. Proceeding to retrieve text.")
            # EDIT END
            
            # Try to retrieve response (original logic for click and copy)
            response = await asyncio.get_event_loop().run_in_executor(None, self.retrieve) # Run sync retrieve in executor
            if response:
                return response
                
            # If first attempt fails, retry with delays
            for attempt in range(retries):
                self.log.info(f"Copy-Retry attempt {attempt + 1}/{retries} for {self.agent_id} after completion image was found.")
                await asyncio.sleep(retry_delay * (attempt + 1)) # Exponential backoff for copy retries
                response = await asyncio.get_event_loop().run_in_executor(None, self.retrieve) # Run sync retrieve in executor
                if response:
                    return response
                    
            self.log.warning(f"Failed to retrieve response for {self.agent_id} after {retries} copy-retries (completion image was found).")
            return None
            
        except asyncio.CancelledError:
            self.log.info(f"Response retrieval cancelled for {self.agent_id}")
            return None
        except Exception as e:
            self.log.error(f"Error retrieving response for {self.agent_id}: {e}", exc_info=True)
            return None


if __name__ == "__main__":
    import random  # Already imported but good for explicitness here

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    log = logging.getLogger(__name__)

    try:
        current_file_path = Path(__file__).resolve()
        project_root_for_coords = current_file_path.parents[3]
    except NameError:
        project_root_for_coords = Path(".")

    coords_file_path = project_root_for_coords / DEFAULT_COORDS_FILE
    log.info(f"Using coordinate file for retriever test: {coords_file_path}")

    if not coords_file_path.exists():
        log.error(
            f"CRITICAL: Coordinate file {coords_file_path} not found. Cannot run test."
        )
        log.info(
            f"Attempting to create a dummy coordinate file for testing: {coords_file_path}"
        )
        try:
            coords_file_path.parent.mkdir(parents=True, exist_ok=True)
            dummy_coords = {
                "Agent-1.input_box_initial": [100, 100],
                "Agent-1.copy_button": [100, 150],  # Crucial for this test
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

    test_agent_id = "Agent-1"
    retriever = ResponseRetriever(agent_id=test_agent_id, coords_file=coords_file_path)

    if retriever.copy_button_coords:
        log.info(
            f"Retriever created for {test_agent_id} with copy_button_coords: {retriever.copy_button_coords}"
        )
        log.info(
            "Please ensure the GUI for Agent-1 is open, visible, and has some text that can be copied via its 'copy' button."
        )
        log.info(
            "Also, ensure the mouse is not interfering with the copy operation spot."
        )
        log.info("Test will attempt to retrieve in 5 seconds...")
        time.sleep(5)

        # Simulate some content in clipboard to test restoration
        if PYPERCLIP_AVAILABLE and pyperclip:
            pyperclip.copy("Original clipboard content before test.")

        response = retriever.retrieve()

        if response:
            log.info(
                f"Successfully retrieved response for {test_agent_id}:\n---\n{response}\n---"
            )
        else:
            log.error(f"Failed to retrieve response for {test_agent_id}.")
            # In a real scenario, injector might take a screenshot here too

        if PYPERCLIP_AVAILABLE and pyperclip:
            log.info(f"Clipboard content after test: {pyperclip.paste()}")
        log.info("Test retrieval complete.")
    else:
        log.error(
            f"Could not initialize retriever properly for {test_agent_id} due to missing copy_button coordinates."
        )
        log.info(
            f"Ensure '{test_agent_id}.copy_button' key exists in {coords_file_path}"
        )

    log.info("Retriever script finished.")
