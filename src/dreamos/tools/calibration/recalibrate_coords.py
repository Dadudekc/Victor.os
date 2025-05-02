#!/usr/bin/env python3
"""Tool to interactively recalibrate screen coordinates for a specific agent/key."""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import portalocker  # Import portalocker for file locking
import pyautogui

# EDIT START: Remove find_project_root import and calculate root directly
# # Assume project root is 3 levels up from src/tools/calibration
# # Use the utility if available, otherwise fallback
# try:
#     from dreamos.utils import find_project_root
#     PROJECT_ROOT = find_project_root(__file__)
# except ImportError:
#     logger.warning(
#         "Could not import find_project_root, using relative path calculation."
#     )
#     PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # Calculate directly
# EDIT END

# NOTE: Assumes a potentially nested structure like { "agent_id": { "element_key": [X, Y] } }
#       or a flat structure { "agent_id.element_key": [X, Y] }.
#       Let's target the NESTED structure for better organization.
DEFAULT_COORDS_FILE = (
    PROJECT_ROOT / "runtime" / "config" / "cursor_agent_coords.json"
)  # Generic name now
CAPTURE_DELAY_SECONDS = 5  # Time user has to position the mouse

# Configure logger
# Moved basicConfig into main block
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CoordRecalibrator")


def capture_single_coordinate(identifier: str) -> list[int]:
    """Captures a single screen coordinate interactively."""
    print(f"\n>>> Recalibrating: {identifier} <<<")
    print(f"Move mouse to the correct position for '{identifier}'...")

    try:
        # Countdown
        for i in range(CAPTURE_DELAY_SECONDS, 0, -1):
            print(f"Capturing in {i}...", end="\r")
            time.sleep(1)
        print("Capturing now!      ")  # Extra spaces to overwrite countdown

        # Capture coordinates
        current_pos = pyautogui.position()
        coords = [current_pos.x, current_pos.y]  # Use [X, Y] format

        print(f"--> Captured for {identifier}: X={coords[0]}, Y={coords[1]}")
        time.sleep(0.5)  # Small pause
        return coords

    except pyautogui.FailSafeException:
        logger.error(
            "PyAutoGUI fail-safe triggered (mouse moved to top-left corner). Aborting."
        )
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("User interrupted capture. Aborting.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during capture: {e}", exc_info=True)
        sys.exit(1)


def update_coords_file(
    coords_file: Path, identifier: str, new_coords: list[int]
) -> bool:
    """Updates the specified identifier in the coordinates JSON file. Handles nested keys with file locking."""
    logger.info(f"Attempting to update {identifier} in {coords_file}")

    # Ensure parent directory exists before attempting to lock/open
    try:
        coords_file.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(
            f"Failed to ensure directory exists for {coords_file}: {e}", exc_info=True
        )
        return False

    # Split identifier for potential nesting (e.g., "agent_01.input_box")
    keys = identifier.split(".")
    if not keys:
        logger.error(f"Invalid empty identifier provided.")
        return False

    try:
        # Use portalocker to handle locking during read-modify-write
        # Open in 'r+' mode initially, but portalocker manages the lock
        with portalocker.Lock(
            coords_file, mode="r+", encoding="utf-8", timeout=5, fail_when_locked=False
        ) as f:
            # Read existing data
            all_coordinates = {}
            try:
                # File might be empty if newly created by lock, or just opened
                f.seek(0)
                content = f.read()
                if content:
                    all_coordinates = json.loads(content)
                else:
                    logger.warning(
                        f"Coordinates file {coords_file} is empty or newly created."
                    )
                    all_coordinates = {}  # Start fresh
            except json.JSONDecodeError:
                logger.error(
                    f"Failed to decode JSON from {coords_file}. Cannot update."
                )
                return False
            # FileNotFoundError should be handled by portalocker or the initial check/mkdir

            # Navigate or create nested structure
            current_level = all_coordinates
            for i, key in enumerate(keys):
                if i == len(keys) - 1:  # Last key, assign the coordinates
                    current_level[key] = new_coords
                else:  # Navigate deeper
                    if key not in current_level:
                        logger.warning(
                            f"Creating missing key '{key}' in structure for identifier '{identifier}'"
                        )
                        current_level[key] = {}
                    elif not isinstance(current_level[key], dict):
                        logger.error(
                            f"Existing key '{key}' for identifier '{identifier}' is not a dictionary. Cannot update nested structure."
                        )
                        return False
                    current_level = current_level[key]

            # Write updated data back (within the lock)
            f.seek(0)  # Go to beginning to overwrite
            json.dump(all_coordinates, f, indent=4)
            f.truncate()  # Truncate to new size

        # Lock is automatically released here by portalocker context manager
        logger.info(
            f"Successfully updated {identifier} in {coords_file} to {new_coords}"
        )
        return True  # Indicate success

    except portalocker.LockException as e:
        logger.error(
            f"Failed to acquire lock for {coords_file} after timeout: {e}",
            exc_info=True,
        )
        return False
    except Exception as e:
        logger.error(
            f"Failed to update coordinates file {coords_file}: {e}", exc_info=True
        )
        return False  # Indicate general failure


def main():
    parser = argparse.ArgumentParser(
        description="Interactively recalibrate screen coordinates."
    )
    parser.add_argument(
        "identifier",
        help="The key identifier for the coordinate, potentially nested (e.g., 'agent_01.input_box', 'global.copy_button').",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_COORDS_FILE,
        help=f"Path to the coordinates JSON file. Defaults to: {DEFAULT_COORDS_FILE}",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")

    args = parser.parse_args()

    # Configure logging ONLY when run as a script
    log_format = (
        "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"  # Standard format
    )
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format=log_format)
    # Re-get logger potentially needed if basicConfig modified root handlers,
    # but getLogger should be sufficient if just setting level/format.
    logger = logging.getLogger("CoordRecalibrator")
    if args.debug:
        # Ensure module logger also gets debug level if basicConfig didn't propagate fully
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled.")

    # Capture the new coordinate
    new_coords = capture_single_coordinate(args.identifier)

    # Update the file
    success = update_coords_file(args.file, args.identifier, new_coords)

    if success:
        print(f"✅ Recalibration for '{args.identifier}' completed successfully.")
        sys.exit(0)
    else:
        print(f"❌ Recalibration for '{args.identifier}' failed. Check logs.")
        sys.exit(1)


if __name__ == "__main__":
    main()
