"""
dreamos.utils.gui.retriever
----------------------------------
High-reliability GUI clipboard retriever for Dream.OS agents.
• Waits for completion image
• Clicks copy button with retry & adaptive sleeps
• Validates clipboard via placeholder
• Saves debug screenshots on failure
"""

import asyncio, json, logging, os, random, time
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

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_COORDS_FILE = Path("runtime/config/cursor_agent_coords.json")
GENERATING_IMAGE    = Path("runtime/config/assets/gui_images/generating.png")
COMPLETE_IMAGE      = Path("runtime/config/assets/gui_images/complete.png")

CLICK_DELAY         = 0.25   # seconds between move+click
POST_CLICK_WAIT     = 1.0    # seconds to allow clipboard to update
IMAGE_TIMEOUT       = 300    # seconds to wait for COMPLETE_IMAGE
IMAGE_CONF          = 0.80   # pyautogui confidence
COPY_RETRIES        = 3      # attempts if clipboard unchanged
SCREENSHOT_DIR      = Path("runtime/debug_screenshots")

# ── Helper ────────────────────────────────────────────────────────────────────
def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

# ── Main class ────────────────────────────────────────────────────────────────
class ResponseRetriever:
    """Handles retrieving responses, typically from the clipboard after an agent action."""

    def __init__(self, agent_id: str, coords_file: Path = DEFAULT_COORDS_FILE):
        self.agent_id = agent_id
        self.coords_file = Path(coords_file)
        self.log = logging.getLogger(f"Retriever.{agent_id}")
        self.post_click_wait = POST_CLICK_WAIT

        self.all_coords = self._load_coords()
        self.copy_button_coords = self._get_coords("copy_button")
        if not self.copy_button_coords:
            self.log.error("Copy button coords missing for %s", agent_id)

        if not PYPERCLIP_AVAILABLE:
            self.log.warning("Pyperclip is not available. Clipboard operations will not work.")

    # --------------------------------------------------------------------- IO
    def _load_coords(self) -> Optional[Dict[str, Any]]:
        if not self.coords_file.exists():
            self.log.error("Coords file missing: %s", self.coords_file)
            return None
        try:
            return json.loads(self.coords_file.read_text(encoding="utf-8"))
        except Exception as e:
            self.log.exception("Failed to parse coords JSON: %s", e)
            return None

    def _get_coords(self, key: str) -> Optional[Tuple[int, int]]:
        if not self.all_coords:
            return None
        entry = self.all_coords.get(self.agent_id, {}).get(key)
        if isinstance(entry, dict) and "x" in entry and "y" in entry:
            return (entry["x"], entry["y"])
        return None

    # ----------------------------------------------------------------- Screen
    def _wait_for_image(self, img: Path) -> bool:
        self.log.info("Waiting for %s …", img.name)
        start = time.time()
        while time.time() - start < IMAGE_TIMEOUT:
            try:
                if pyautogui.locateOnScreen(str(img), confidence=IMAGE_CONF):
                    self.log.info("%s detected.", img.name)
                    return True
            except pyautogui.PyAutoGUIException as e:
                self.log.warning("Image search error: %s", e)
            time.sleep(1)
        self.log.warning("Timeout waiting for %s", img.name)
        return False

    def _debug_screenshot(self, label: str):
        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            path = SCREENSHOT_DIR / f"{label}_{self.agent_id}_{_now_ts()}.png"
            pyautogui.screenshot(str(path))
            self.log.info("Screenshot saved to: %s", path)
        except Exception as e:
            self.log.error("Failed screenshot: %s", e)

    # ------------------------------------------------------------- Clipboard
    def _prime_clipboard(self) -> str:
        placeholder = f"DREAMOS_PLACEHOLDER_{random.randint(1000,9999)}"
        if PYPERCLIP_AVAILABLE:
            pyperclip.copy(placeholder)
        return placeholder

    def _clipboard_text(self) -> str:
        return pyperclip.paste() if PYPERCLIP_AVAILABLE else ""

    # --------------------------------------------------------------- Actions
    def _click_copy(self):
        x, y = self.copy_button_coords
        pyautogui.moveTo(x, y, duration=0.15)
        pyautogui.click()
        time.sleep(CLICK_DELAY)

    # ----------------------------------------------------------------- Core
    def _do_copy_cycle(self) -> Optional[str]:
        placeholder = f"PLACEHOLDER_{random.randint(1000,9999)}"
        if PYPERCLIP_AVAILABLE:
            pyperclip.copy(placeholder)
        
        self._click_copy()
        time.sleep(self.post_click_wait)

        text = self._clipboard_text()
        if not text or text == placeholder:
            self.log.warning("Clipboard unchanged/empty.")
            return None
        return text

    # ---------------------------------------------------------------- Async
    async def get_response(self) -> Optional[str]:
        # // EDIT START: User directive to bypass actual GUI copy for now
        self.log.info(f"get_response called for {self.agent_id}. GUI copy cycle will be bypassed as per user directive.")

        # We can still wait for the completion image as a signal the agent might have processed the prompt.
        if not self.copy_button_coords: # Though copy_button_coords are not used for copy, its absence might indicate setup issues.
            self.log.warning(f"Bypassing response retrieval for {self.agent_id}: copy_button_coords not loaded. This might be okay if only injection is tested.")
            # return "[INFO] GUI Response Retrieval Bypassed: Missing copy_button_coords (setup issue?)"
            # No, let's proceed to image check if possible, as copy_button_coords is for the CLICK part.

        # 1. Wait for completion image (optional, but can be a useful signal)
        # If COMPLETE_IMAGE path is not valid or image not found, this will return None or log errors.
        # For a full bypass, we could skip this too, but let's keep it for now.
        found_completion_image = await asyncio.get_event_loop().run_in_executor(
            None, self._wait_for_image, COMPLETE_IMAGE
        )
        if not found_completion_image:
            self._debug_screenshot("no_complete_image_during_bypass") # Still useful to know if completion image wasn't seen
            self.log.warning(f"Completion image not detected for {self.agent_id} during bypass. Prompt may not have been fully processed.")
            # Return a specific message if completion image is vital even for bypass
            # return "[INFO] GUI Response Retrieval Bypassed: Completion image not found."
        else:
            self.log.info(f"Completion image detected for {self.agent_id} during bypass.")

        # Explicitly return the bypass message instead of attempting copy
        bypass_message = "[INFO] GUI Response Retrieval Bypassed by User Directive"
        self.log.info(f"Returning bypass message for {self.agent_id}: {bypass_message}")
        return bypass_message
        # // EDIT END: Original logic below is now bypassed

        # if not self.copy_button_coords:
        #     return None
        #
        # # 1. Wait for completion image
        # found = await asyncio.get_event_loop().run_in_executor(
        #     None, self._wait_for_image, COMPLETE_IMAGE
        # )
        # if not found:
        #     self._debug_screenshot("no_complete_image")
        #     return None
        #
        # await asyncio.sleep(self.post_click_wait)
        #
        # # 2. Attempt copy with retries
        # for attempt in range(1, COPY_RETRIES + 1):
        #     text = await asyncio.get_event_loop().run_in_executor(None, self._do_copy_cycle)
        #     if text:
        #         self.log.info("Response retrieved (%d chars).", len(text))
        #         return text
        #     self.log.info("Retrying copy (%d/%d)…", attempt, COPY_RETRIES)
        #     await asyncio.sleep(1)
        #
        # self.log.error("Failed to retrieve clipboard after %d retries.", COPY_RETRIES)
        # self._debug_screenshot("copy_fail")
        # return None

    def get_response_from_clipboard(self, timeout: int = 5, interval: float = 0.5) -> Optional[str]:
        """
        Attempts to get text from the clipboard.
        Optionally retries for a certain timeout if the clipboard is initially empty or unchanged.
        """
        if not PYPERCLIP_AVAILABLE:
            self.log.error("Cannot get response from clipboard: Pyperclip is not available.")
            return None

        start_time = time.time()
        previous_content = pyperclip.paste()
        self.log.debug(f"Initial clipboard content: '{previous_content[:100]}...'")

        while time.time() - start_time < timeout:
            current_content = pyperclip.paste()
            if current_content != previous_content and current_content:
                self.log.info(f"Retrieved new content from clipboard: '{current_content[:100]}...'")
                return current_content
            time.sleep(interval)
            self.log.debug(f"Checking clipboard again... (current: '{current_content[:100]}...')")
        
        self.log.warning(f"Timeout reached. No new content retrieved from clipboard after {timeout}s.")
        # Return current content even if it's same as initial, in case it was the target but set before check started
        # Or if it was empty and remained empty.
        return current_content 

    def simulate_copy_to_clipboard(self, text_to_copy: str) -> bool:
        """
        Simulates an agent copying text to the clipboard. For testing purposes.
        """
        if not PYPERCLIP_AVAILABLE:
            self.log.error("Cannot simulate copy to clipboard: Pyperclip is not available.")
            return False
        try:
            pyperclip.copy(text_to_copy)
            self.log.info(f"Simulated: Copied to clipboard: '{text_to_copy[:100]}...'")
            return True
        except Exception as e:
            self.log.error(f"Error simulating copy to clipboard: {e}", exc_info=True)
            return False

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

    if PYPERCLIP_AVAILABLE:
        log.info("--- Testing Clipboard Retrieval ---")
        
        original_clipboard = pyperclip.paste()
        log.info(f"Current clipboard content: '{original_clipboard}'")
        log.info("Please change your clipboard content manually within the next 7 seconds to test retrieval.")
        
        retrieved_response = retriever.get_response_from_clipboard(timeout=7, interval=1)
        if retrieved_response and retrieved_response != original_clipboard:
            log.info(f"SUCCESS: Retrieved response: '{retrieved_response}'")
        elif retrieved_response == original_clipboard:
            log.warning("Clipboard content did not change, or was already the target content.")
        else:
            log.error("FAILED: No response retrieved or clipboard was empty.")

        log.info("--- Testing Simulated Clipboard Copy ---")
        mock_agent_response = "This is a simulated response from an agent."
        retriever.simulate_copy_to_clipboard(mock_agent_response)
        
        # Verify by reading it back
        time.sleep(0.1) # Give clipboard a moment
        pasted_content = pyperclip.paste()
        if pasted_content == mock_agent_response:
            log.info(f"SUCCESS: Verified simulated content in clipboard: '{pasted_content}'")
        else:
            log.error(f"FAILED: Simulated content not found in clipboard. Found: '{pasted_content}'")
        
        # Restore original clipboard content if possible
        if isinstance(original_clipboard, str):
            pyperclip.copy(original_clipboard)
            log.info("Restored original clipboard content.")
    else:
        log.error("Pyperclip is not available, cannot run ResponseRetriever tests.")

    log.info("ResponseRetriever test finished.")
