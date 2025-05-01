import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Import the shared utility
from ..utils.gui_utils import (
    get_specific_coordinate,
    load_coordinates,
    trigger_recalibration,
)
from ..utils.path_utils import (  # Assuming find_project_root is in path_utils
    find_project_root,
)

try:
    import pyautogui
    import pyperclip

    PYAUTOGUI_AVAILABLE = True
except ImportError:
    logging.error(
        "pyautogui or pyperclip not found. Response retrieval cannot function."
    )
    logging.error("Please install them: pip install pyautogui pyperclip")
    pyautogui = None
    pyperclip = None
    PYAUTOGUI_AVAILABLE = False

# --- Configuration ---
# Use the project root finder if available
try:
    PROJECT_ROOT = find_project_root(__file__)
except ImportError:
    # Adjust fallback path calculation relative to this file's location
    # response_retriever.py -> automation -> dreamos -> src -> PROJECT_ROOT
    logger.warning(
        "Could not import find_project_root, using relative path calculation."
    )
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Standardized coordinate path
DEFAULT_COORDS_FILE = PROJECT_ROOT / "runtime" / "config" / "cursor_agent_coords.json"
# RECALIBRATION_SCRIPT_PATH = PROJECT_ROOT / "src" / "tools" / "calibration" / "recalibrate_coords.py" # Definition moved to gui_utils
CLICK_DELAY_SECONDS = 0.2  # Increased slightly for clipboard
RECALIBRATION_RETRIES = 1  # Added
# --- Configuration End ---

logger = logging.getLogger(__name__)

# --- Recalibration Helper ---
# Removed local trigger_recalibration, using shared util

# --- Coordinate Loading Helper ---
# Removed local load_coordinates, using shared util


class ResponseRetriever:
    """Handles retrieving agent responses by clicking 'Copy' and reading the clipboard."""

    def __init__(self, coords_file: Path = DEFAULT_COORDS_FILE):
        self.coords_file = coords_file
        # Load the entire structure using shared util
        self.full_coordinates: Optional[Dict[str, Any]] = load_coordinates(
            self.coords_file
        )

    def retrieve_agent_response(
        self, agent_id: str, element_key: str = "copy_button"
    ) -> Optional[str]:
        """Clicks the specified element, verifies via clipboard, recalibrates on failure."""
        if not PYAUTOGUI_AVAILABLE:
            logger.error(
                "Dependencies (pyautogui/pyperclip) not met. Cannot retrieve response."
            )
            return None

        identifier = f"{agent_id}.{element_key}"
        recalibration_attempts = 0

        # Make a mutable copy for potential reloading within the loop
        current_full_coordinates = (
            self.full_coordinates.copy() if self.full_coordinates else None
        )

        while recalibration_attempts <= RECALIBRATION_RETRIES:
            if current_full_coordinates is None:
                logger.error(
                    f"Initial coordinate load failed or coordinates became None. Cannot proceed."
                )
                return None

            coords = get_specific_coordinate(identifier, current_full_coordinates)

            if not coords:
                logger.error(f"No coordinates found for identifier: {identifier}")
                if recalibration_attempts < RECALIBRATION_RETRIES:
                    logger.info(
                        f"Coordinates missing for {identifier}, attempting recalibration..."
                    )
                    # Use shared trigger_recalibration
                    if trigger_recalibration(identifier, self.coords_file):
                        reloaded_coords = load_coordinates(
                            self.coords_file
                        )  # Use shared loader
                        if reloaded_coords is None:
                            logger.error(
                                "Failed to reload coordinates after recalibration."
                            )
                            return None
                        current_full_coordinates = reloaded_coords  # Update local copy
                        recalibration_attempts += 1
                        continue
                    else:
                        logger.error(
                            f"Recalibration failed for missing coordinates {identifier}."
                        )
                        return None
                else:
                    logger.error(
                        f"Coordinates still missing for {identifier} after recalibration attempt."
                    )
                    return None

            x, y = coords
            original_pos = None
            try:
                logger.debug(
                    f"Retrieving response for {identifier}: Clicking at ({x}, {y}) (Attempt {recalibration_attempts + 1})"
                )
                # Clear clipboard before clicking
                clipboard_before = pyperclip.paste()
                # Ensure it's clear, sometimes copy needs a non-empty starting point?
                pyperclip.copy(f"_clear_{time.time()}_")
                time.sleep(0.05)

                # Store original mouse position
                original_pos = pyautogui.position()

                # Perform the click
                pyautogui.moveTo(x, y, duration=0.1)
                pyautogui.click()
                time.sleep(CLICK_DELAY_SECONDS)

                # Restore original mouse position immediately after click
                if original_pos:
                    pyautogui.moveTo(original_pos.x, original_pos.y, duration=0.1)

                # --- Verification Step ---
                clipboard_after = pyperclip.paste()
                # Improved check: ensure it changed AND is not the placeholder
                if (
                    clipboard_after != f"_clear_{time.time()}_"
                    and clipboard_after != clipboard_before
                    and clipboard_after is not None
                ):
                    logger.info(
                        f"Successfully retrieved response for {identifier} (length: {len(clipboard_after)})"
                    )
                    return clipboard_after  # Success
                else:
                    logger.warning(
                        f"Click verification failed for {identifier} (clipboard content invalid). Before='{clipboard_before}', After='{clipboard_after}'"
                    )
                    if recalibration_attempts < RECALIBRATION_RETRIES:
                        logger.info(f"Attempting recalibration for {identifier}...")
                        # Use shared trigger_recalibration
                        if trigger_recalibration(identifier, self.coords_file):
                            reloaded_coords = load_coordinates(
                                self.coords_file
                            )  # Use shared loader
                            if reloaded_coords is None:
                                logger.error(
                                    "Failed to reload coordinates after recalibration."
                                )
                                return None
                            current_full_coordinates = (
                                reloaded_coords  # Update local copy
                            )
                            recalibration_attempts += 1
                            logger.info(
                                f"Recalibration successful. Retrying retrieval for {identifier}."
                            )
                            continue
                        else:
                            logger.error(
                                f"Recalibration failed for {identifier} after clipboard check failure."
                            )
                            return None
                    else:
                        logger.error(
                            f"Clipboard check failed for {identifier} after {RECALIBRATION_RETRIES+1} attempts."
                        )
                        return None
            except Exception as e:
                logger.error(
                    f"Error during response retrieval attempt {recalibration_attempts + 1} for {identifier}: {e}",
                    exc_info=True,
                )
                # Restore mouse on general error too
                if original_pos:
                    try:
                        pyautogui.moveTo(original_pos.x, original_pos.y, duration=0.1)
                    except Exception as move_err:
                        logger.error(
                            f"Failed to restore mouse position after error: {move_err}"
                        )
                return None  # Fail on general pyautogui errors

        # Loop finished without success
        logger.error(
            f"Retrieval for {identifier} failed after {recalibration_attempts} recalibration attempts."
        )
        return None


# Optional: Provide a simple function interface
def get_response(agent_id: str, element_key: str = "copy_button") -> Optional[str]:
    """Helper function to get response using a default ResponseRetriever instance."""
    # Note: Creates a new instance each time. Consider singleton or passing instance.
    retriever = ResponseRetriever()
    # Check if coordinates loaded successfully in the instance
    if retriever.full_coordinates is None:
        logger.error(
            "Failed to initialize ResponseRetriever due to coordinate loading error."
        )
        return None
    return retriever.retrieve_agent_response(agent_id, element_key)


# Example Usage (for testing)
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    if not PYAUTOGUI_AVAILABLE:
        exit(1)

    test_agent_id = "agent_03"  # Agent to test
    print(f"--- Testing Response Retrieval for {test_agent_id} ---")

    # Ensure you have the Cursor window for agent_03 visible and with some text + Copy button
    print("Please ensure the Cursor window for the agent is ready.")
    print("Test will start in 5 seconds...")
    time.sleep(5)

    retrieved_text = get_response(test_agent_id)

    if retrieved_text is not None:
        print("--- Retrieval Result ---")
        print(f"Retrieved Text (first 100 chars):\n{retrieved_text[:100]}...")
    else:
        print("--- Retrieval Failed ---")
        print("Check logs for details.")

    print("--- Test Complete ---")
