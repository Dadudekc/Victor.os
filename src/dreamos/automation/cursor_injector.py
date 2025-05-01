# src/dreamos/automation/cursor_injector.py
import json
import logging
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pyautogui

# Import the shared utilities
from ..utils.gui_utils import (
    get_specific_coordinate,
    is_window_focused,
    load_coordinates,
    trigger_recalibration,
)
from ..utils.path_utils import (  # Assuming find_project_root is in path_utils
    find_project_root,
)

# Attempt to import GUI helpers
try:
    import pyperclip

    PYPERCLIPBOARD_AVAILABLE = True
except ImportError:
    PYPERCLIPBOARD_AVAILABLE = False
    logging.warning("pyperclip not found. Pasting disabled, will use typing (slower).")

try:
    import pygetwindow

    PYGETWINDOW_AVAILABLE = True
except ImportError:
    PYGETWINDOW_AVAILABLE = False
    logging.warning(
        "pygetwindow not found. Window focus check for verification is disabled."
    )

logger = logging.getLogger(__name__)

# Default configuration
# Use the project root finder if available
try:
    PROJECT_ROOT = find_project_root(__file__)
except ImportError:
    logger.warning(
        "Could not import find_project_root, using relative path calculation."
    )
    PROJECT_ROOT = Path(__file__).resolve().parents[2]  # automation -> dreamos -> src

# Standardized coordinate path and generic name
DEFAULT_COORDS_PATH = PROJECT_ROOT / "runtime" / "config" / "cursor_agent_coords.json"
# RECALIBRATION_SCRIPT_PATH = ( # Definition moved to gui_utils
#     PROJECT_ROOT / "src" / "tools" / "calibration" / "recalibrate_coords.py"
# )
# Example: Target window title - this should ideally come from config
TARGET_WINDOW_TITLE = "Agent Chat Window"  # Placeholder - NEEDS CONFIGURATION
DEFAULT_QUEUE_PATH = PROJECT_ROOT / "runtime" / "cursor_queue"
DEFAULT_PROCESSED_PATH = PROJECT_ROOT / "runtime" / "cursor_processed"
MIN_PAUSE = 0.10  # Minimum pause between pyautogui actions
MAX_PAUSE = 0.25  # Maximum pause
RECALIBRATION_RETRIES = 1  # How many times to attempt recalibration on failure

# --- Configuration Loading ---

# Removed local load_coordinates, using shared util from dreamos.utils.gui_automation

# --- Queue Management ---


def get_next_prompt(
    agent_id: str, queue_base: Path = DEFAULT_QUEUE_PATH
) -> Optional[Tuple[str, Path]]:
    """Gets the text and path of the next prompt file for an agent."""
    agent_queue_dir = queue_base / agent_id
    if not agent_queue_dir.is_dir():
        # logger.debug(f"Queue directory not found for {agent_id}: {agent_queue_dir}")
        return None

    try:
        # Get the oldest file based on name (e.g., timestamp prefix)
        prompt_files = sorted([f for f in agent_queue_dir.iterdir() if f.is_file()])
        if not prompt_files:
            return None

        next_prompt_file = prompt_files[0]
        prompt_text = next_prompt_file.read_text(encoding="utf-8")
        return prompt_text, next_prompt_file
    except Exception as e:
        logger.error(f"Error reading prompt queue for {agent_id}: {e}", exc_info=True)
        return None


def mark_prompt_processed(
    prompt_file_path: Path, processed_base: Path = DEFAULT_PROCESSED_PATH
):
    """Moves a processed prompt file to the processed directory."""
    try:
        agent_id = prompt_file_path.parent.name
        processed_dir = processed_base / agent_id
        processed_dir.mkdir(parents=True, exist_ok=True)
        target_path = processed_dir / prompt_file_path.name
        prompt_file_path.rename(target_path)
        logger.debug(f"Moved {prompt_file_path.name} to {target_path}")
    except Exception as e:
        logger.error(
            f"Error moving processed prompt {prompt_file_path}: {e}", exc_info=True
        )


# --- GUI Interaction Helpers ---
# Removed local is_window_focused and trigger_recalibration, using shared utils


# --- Core Injection Logic ---
def inject_prompt(
    agent_id: str,
    prompt_text: str,
    full_coordinates: Dict[str, Any],
    coords_file_path: Path,  # Still needed to pass to trigger_recalibration if it doesn't use default
    element_key: str = "input_box",
    use_paste: bool = True,
    random_offset: int = 3,
) -> bool:
    """Injects a single prompt, with verification and recalibration attempt."""

    identifier = f"{agent_id}.{element_key}"
    recalibration_attempts = 0

    # Make a mutable copy for potential reloading within the loop
    current_full_coordinates = full_coordinates.copy()

    while recalibration_attempts <= RECALIBRATION_RETRIES:
        target_coords = get_specific_coordinate(identifier, current_full_coordinates)
        if not target_coords:
            logger.error(f"Could not find coordinates for identifier '{identifier}'.")
            if recalibration_attempts < RECALIBRATION_RETRIES:
                logger.info(
                    f"Coordinates missing for {identifier}, attempting recalibration..."
                )
                # Use shared trigger_recalibration, pass the specific coords file path
                if trigger_recalibration(identifier, coords_file_path):
                    reloaded_coords = load_coordinates(coords_file_path)
                    if not reloaded_coords:
                        logger.error(
                            "Failed to reload coordinates after recalibration."
                        )
                        return False
                    current_full_coordinates = (
                        reloaded_coords  # Update local copy for retry
                    )
                    recalibration_attempts += 1
                    continue
                else:
                    logger.error(
                        f"Recalibration failed for missing coordinates {identifier}."
                    )
                    return False
            else:
                logger.error(
                    f"Coordinates still missing for {identifier} after recalibration attempt."
                )
                return False

        target_x, target_y = target_coords
        # Apply optional random offset
        if random_offset > 0:
            offset_x = random.randint(-random_offset, random_offset)
            offset_y = random.randint(-random_offset, random_offset)
            target_x += offset_x
            target_y += offset_y

        logger.info(
            f"Injecting prompt for {identifier} at ({target_x}, {target_y}) (Attempt {recalibration_attempts + 1})..."
        )

        try:
            # 1. Move mouse to target
            pyautogui.moveTo(target_x, target_y, duration=random.uniform(0.1, 0.3))
            time.sleep(random.uniform(MIN_PAUSE, MAX_PAUSE))

            # 2. Click to focus
            pyautogui.click(x=target_x, y=target_y)
            time.sleep(random.uniform(MIN_PAUSE, MAX_PAUSE))

            # --- Verification Step ---
            # Use shared is_window_focused
            if not is_window_focused(TARGET_WINDOW_TITLE):
                logger.warning(
                    f"Click verification failed for {identifier} (window focus check)."
                )
                if recalibration_attempts < RECALIBRATION_RETRIES:
                    logger.info(f"Attempting recalibration for {identifier}...")
                    # Use shared trigger_recalibration
                    if trigger_recalibration(identifier, coords_file_path):
                        reloaded_coords = load_coordinates(coords_file_path)
                        if not reloaded_coords:
                            logger.error(
                                "Failed to reload coordinates after recalibration."
                            )
                            return False
                        current_full_coordinates = reloaded_coords  # Update local copy
                        recalibration_attempts += 1
                        logger.info(
                            f"Recalibration successful. Retrying injection for {identifier}."
                        )
                        continue
                    else:
                        logger.error(
                            f"Recalibration failed for {identifier} after focus check failure."
                        )
                        return False
                else:
                    logger.error(
                        f"Click verification failed for {identifier} after {RECALIBRATION_RETRIES+1} attempts."
                    )
                    return False
            # --- Verification Passed ---
            logger.debug(f"Click verified for {identifier}. Proceeding with injection.")

            # 3. Clear field (Simulate Ctrl+A, Delete)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(random.uniform(MIN_PAUSE / 2, MAX_PAUSE / 2))
            pyautogui.press("delete")
            time.sleep(random.uniform(MIN_PAUSE, MAX_PAUSE))

            # 4. Insert prompt (Paste or Type)
            if use_paste and PYPERCLIPBOARD_AVAILABLE:
                try:
                    pyperclip.copy(prompt_text)
                    time.sleep(
                        random.uniform(MIN_PAUSE / 2, MAX_PAUSE / 2)
                    )  # Small pause for clipboard
                    pyautogui.hotkey("ctrl", "v")
                    logger.debug(f"Pasted prompt for {identifier}.")
                except Exception as paste_err:
                    logger.warning(
                        f"Pasting failed for {identifier}, falling back to typing: {paste_err}"
                    )
                    pyautogui.write(
                        prompt_text, interval=random.uniform(0.01, 0.03)
                    )  # Type slowly
            else:
                logger.debug(f"Typing prompt for {identifier}...")
                pyautogui.write(
                    prompt_text, interval=random.uniform(0.01, 0.03)
                )  # Type slowly

            time.sleep(random.uniform(MIN_PAUSE, MAX_PAUSE))

            # 5. Press Enter
            pyautogui.press("enter")
            logger.info(f"Prompt submitted for {identifier}.")
            time.sleep(random.uniform(MIN_PAUSE, MAX_PAUSE))  # Small pause after enter

            return True  # Successful injection

        except Exception as e:
            logger.error(
                f"PyAutoGUI error during injection attempt {recalibration_attempts + 1} for {identifier}: {e}",
                exc_info=True,
            )
            # General errors fail immediately without triggering recalibration
            return False

    # Loop finished without success
    logger.error(
        f"Injection for {identifier} failed after {recalibration_attempts} recalibration attempts."
    )
    return False


# --- Main Loop ---


def run_injection_loop(
    agent_ids: Optional[list[str]] = None,
    coords_path: Path = DEFAULT_COORDS_PATH,
    queue_path: Path = DEFAULT_QUEUE_PATH,
    processed_path: Path = DEFAULT_PROCESSED_PATH,
    cycle_pause: float = 1.0,
):
    """Continuously checks agent queues and injects prompts."""
    # Load the full coordinate structure once using shared util
    full_coordinates = load_coordinates(coords_path)
    if not full_coordinates:
        logger.critical("Failed to load agent coordinates. Exiting injection loop.")
        return

    # Determine which agents to monitor
    agents_to_monitor = agent_ids or list(
        full_coordinates.keys()
    )  # Use keys from loaded coords if agent_ids is None
    logger.info(f"Monitoring agents: {', '.join(agents_to_monitor)}")

    logger.info("Starting Cursor prompt injection loop...")
    while True:
        prompts_processed_this_cycle = 0
        # Create a copy or handle dict modification carefully if reloading modifies it
        current_coords_for_cycle = full_coordinates.copy()
        for agent_id in agents_to_monitor:
            if agent_id not in current_coords_for_cycle:
                continue

            prompt_info = get_next_prompt(agent_id, queue_path)
            if prompt_info:
                prompt_text, prompt_file = prompt_info
                logger.info(f"Found prompt for {agent_id}: {prompt_file.name}")
                # Pass the current coordinate dict AND the path to the coords file
                # If inject_prompt modifies the dict via reloading, it won't affect other agents in this cycle
                success = inject_prompt(
                    agent_id,
                    prompt_text,
                    current_coords_for_cycle,
                    coords_path,
                    element_key="input_box",
                )
                if success:
                    mark_prompt_processed(prompt_file, processed_path)
                    prompts_processed_this_cycle += 1
                else:
                    logger.error(
                        f"Failed to inject prompt for {agent_id}. File remains in queue: {prompt_file.name}"
                    )
                    # Consider what happens if coords were reloaded but still failed.
                    # Update the main dict if needed for subsequent cycles?
                    # For now, we assume failure means stop for this prompt.

        # If coordinates were potentially updated by recalibration, reload for the next cycle
        # This assumes inject_prompt doesn't return the modified dict currently
        # A cleaner way might be for trigger_recalibration to update a shared state or return status.
        # Simple approach: reload if >0 prompts were processed (as failure might have occurred)
        if (
            prompts_processed_this_cycle > 0
        ):  # A bit broad, but ensures potential updates are caught
            reloaded_coords_main = load_coordinates(coords_path)
            if reloaded_coords_main:
                full_coordinates = reloaded_coords_main
                logger.debug("Reloaded coordinates for next main loop cycle.")
            else:
                logger.error(
                    "Failed to reload coordinates in main loop after processing prompts!"
                )
                # Decide how to handle this - continue with old coords? Exit?

        # Pause logic
        if prompts_processed_this_cycle == 0:
            logger.debug(
                f"No prompts found in queues this cycle. Pausing for {cycle_pause}s."
            )
            time.sleep(cycle_pause)
        else:
            logger.info(f"Processed {prompts_processed_this_cycle} prompts this cycle.")
            time.sleep(max(0.1, cycle_pause / 5))


if __name__ == "__main__":
    # Example of running the loop directly
    # Configure logging
    log_format = "%(asctime)s - %(levelname)-8s - %(name)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format)

    # Ensure queue/processed directories exist for testing
    test_agents = ["agent_01", "agent_02"]
    for aid in test_agents:
        (DEFAULT_QUEUE_PATH / aid).mkdir(parents=True, exist_ok=True)
        # Create dummy prompt file for agent_01
        if aid == "agent_01":
            (DEFAULT_QUEUE_PATH / aid / "001_test_prompt.txt").write_text(
                "This is a test prompt for agent_01 from main.", encoding="utf-8"
            )

    print(
        "Starting example injection loop (runs indefinitely)... Press Ctrl+C to stop."
    )
    # Assumes config/cursor_agent_coords.json exists with coords for agent_01, agent_02
    try:
        run_injection_loop(agent_ids=test_agents)
    except KeyboardInterrupt:
        print("\nInjection loop stopped by user.")
