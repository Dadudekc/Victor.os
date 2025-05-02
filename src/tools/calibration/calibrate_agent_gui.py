# src/tools/calibration/calibrate_agent_gui.py
import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

try:
    import pyautogui
except ImportError:
    print(
        "ERROR: pyautogui is required for this script. Please install it (`pip install pyautogui`)"
    )
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Configuration ---
# Assuming this script is in src/tools/calibration, project root is 3 levels up
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_COORDS_PATH = PROJECT_ROOT / "runtime" / "config" / "cursor_agent_coords.json"

# MODIFIED: Elements to calibrate
ELEMENTS_TO_CALIBRATE = [
    "input_box",  # Main text input area for prompts
    "copy_button",  # Button to copy the agent's response
]

# Delay before capturing coordinates (in seconds)
CAPTURE_DELAY = 3
# MODIFIED: Delay between agents
AGENT_SWITCH_DELAY = 10


def load_existing_coords(filepath: Path) -> Dict[str, Any]:
    """Loads existing coordinates from the JSON file."""
    if filepath.exists():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error(
                f"Error decoding JSON from {filepath}. Starting with empty coordinates."
            )
            return {}
        except Exception as e:
            logging.error(
                f"Error reading {filepath}: {e}. Starting with empty coordinates."
            )
            return {}
    else:
        logging.info(f"Coordinates file {filepath} not found. Creating a new one.")
        return {}


def save_coords(filepath: Path, coords_data: Dict[str, Any]):
    """Saves the coordinates dictionary to the JSON file."""
    try:
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(coords_data, f, indent=4)
        logging.info(f"Coordinates saved successfully to {filepath}")
    except Exception as e:
        logging.error(f"Failed to save coordinates to {filepath}: {e}")


def calibrate_element(element_name: str, agent_id: str) -> Dict[str, int]:
    """Guides user and captures coordinates for a single element."""
    print("\n" + "-" * 40)
    print(f"Calibration for Agent: '{agent_id}', Element: '{element_name}'")
    print("-" * 40)
    print(
        f"IMPORTANT: Please move your mouse cursor to the **CENTER** of the '{element_name}'."
    )
    print(f"Keep the mouse still for {CAPTURE_DELAY} seconds after positioning.")
    print(f"Capturing in...")

    for i in range(CAPTURE_DELAY, 0, -1):
        print(f"{i}...", end="", flush=True)
        time.sleep(1)
        print(" ", end="\r", flush=True)  # Clear the countdown number

    try:
        position = pyautogui.position()
        coords = {"x": position.x, "y": position.y}
        print(
            f"\nCaptured Coordinates for '{element_name}': ({coords['x']}, {coords['y']})"
        )
        return coords
    except Exception as e:
        logging.error(f"Failed to capture mouse position: {e}")
        print("ERROR: Could not capture mouse position. Please try again.")
        return None  # Indicate failure


def main():
    parser = argparse.ArgumentParser(
        description="Calibrate GUI coordinates for multiple Dream.OS agents."
    )
    # MODIFIED: Changed argument to accept a list
    parser.add_argument(
        "agent_ids",
        help="Comma-separated list of agent IDs to calibrate (e.g., Agent-1,Agent-2).",
    )
    parser.add_argument(
        "--coords_file",
        default=str(DEFAULT_COORDS_PATH),
        help=f"Path to the coordinates JSON file (default: {DEFAULT_COORDS_PATH})",
    )
    args = parser.parse_args()

    # MODIFIED: Split comma-separated IDs
    agent_ids_list = [
        agent_id.strip() for agent_id in args.agent_ids.split(",") if agent_id.strip()
    ]
    if not agent_ids_list:
        print("ERROR: No valid agent IDs provided.")
        exit(1)

    coords_filepath = Path(args.coords_file)

    print("\n=== Dream.OS Agent GUI Calibration Tool ===")
    print(f"Calibrating for Agent IDs: {', '.join(agent_ids_list)}")
    print(f"Saving coordinates to: {coords_filepath}")
    print("Please ensure the target Cursor windows are visible and ready.")

    all_coords = load_existing_coords(coords_filepath)

    # MODIFIED: Loop through agent IDs
    num_agents = len(agent_ids_list)
    for i, agent_id in enumerate(agent_ids_list):
        print("\n" + "=" * 50)
        print(f"Starting calibration for Agent: {agent_id} ({i+1}/{num_agents})")
        print("=" * 50)

        # Ensure agent_id entry exists
        if agent_id not in all_coords:
            all_coords[agent_id] = {}
        agent_coords = all_coords[agent_id]

        calibration_successful_for_agent = True
        for element in ELEMENTS_TO_CALIBRATE:
            captured = calibrate_element(element, agent_id)
            if captured:
                agent_coords[element] = captured
                # Save immediately after each successful capture
                save_coords(coords_filepath, all_coords)
            else:
                print(
                    f"ERROR: Skipping remaining elements for agent '{agent_id}' due to capture error for '{element}'."
                )
                calibration_successful_for_agent = False
                break  # Stop calibrating this agent if one element fails

        if calibration_successful_for_agent:
            print("\n" + "-" * 40)
            print(f"Calibration complete for Agent ID: {agent_id}")
            print("Current coordinates for this agent:")
            print(json.dumps({agent_id: agent_coords}, indent=4))
            print("-" * 40)

            # MODIFIED: Wait before starting next agent, if not the last one
            if i < num_agents - 1:
                print(
                    f"\nWaiting {AGENT_SWITCH_DELAY} seconds before calibrating next agent ({agent_ids_list[i+1]})..."
                )
                time.sleep(AGENT_SWITCH_DELAY)
        else:
            # Optional: Decide if you want to stop the whole script if one agent fails
            # print("\nStopping calibration process due to error.")
            # break
            pass  # Continue to next agent even if current one failed

    print("\n" + "=" * 50)
    print("Calibration process finished for all requested agents.")
    print("=" * 50)


if __name__ == "__main__":
    main()
