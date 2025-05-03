# src/tools/validation/validate_gui_coords.py
import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import math

try:
    import pyautogui
    import pyperclip
except ImportError:
    print(
        "ERROR: pyautogui and pyperclip are required. Install with `pip install pyautogui pyperclip`"
    )
    exit(1)

# EDIT START: Remove dummy OrchestratorBot fallback, require real import
try:
    from dreamos.core.bots.orchestrator_bot import OrchestratorBot
except ImportError as e:
    raise ImportError(
        "OrchestratorBot must be available for GUI validation. Please check your PYTHONPATH and dependencies."
    ) from e
# EDIT END

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Configuration ---
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_COORDS_PATH = PROJECT_ROOT / "runtime" / "config" / "cursor_agent_coords.json"
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT / "runtime" / "validation" / "gui_coord_validation_results.json"
)

TEST_PROMPT = "Ping from Dream.OS Validator"
RESPONSE_WAIT_SECONDS = 5  # Time to wait after injection before trying to copy response
ACTION_DELAY = 0.5  # Small delay between pyautogui actions

# EDIT: Instantiate OrchestratorBot (assuming no critical config needed for basic actions)
# For a real scenario, config might be needed and passed via args or loaded
try:
    bot = OrchestratorBot(
        config=None, agent_id="ValidatorTool"
    )  # Pass None config for now
except Exception as e:
    logging.error(f"Failed to initialize OrchestratorBot: {e}. GUI actions will fail.")
    bot = OrchestratorBot()  # Use dummy if init fails


def load_coords(filepath: Path) -> Optional[Dict[str, Any]]:
    """Loads coordinates from the JSON file."""
    if not filepath.exists():
        logging.error(f"Coordinates file not found: {filepath}")
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {filepath}.")
        return None
    except Exception as e:
        logging.error(f"Error reading {filepath}: {e}")
        return None


def find_and_activate_window(window_title: str):
    """Finds and attempts to activate the target window."""
    try:
        target_windows = pyautogui.getWindowsWithTitle(window_title)
        if not target_windows:
            logging.error(f"Target window '{window_title}' not found.")
            return False
        window = target_windows[0]
        if not window.isActive:
            logging.warning(
                f"Target window '{window_title}' found but not active. Attempting to activate."
            )
            try:
                window.activate()
                time.sleep(0.7)  # Increase activation wait slightly
                if not window.isActive:
                    logging.error(f"Failed to activate target window '{window_title}'.")
                    return False
            except Exception as act_err:
                logging.error(
                    f"Error activating target window '{window_title}': {act_err}"
                )
                return False
        logging.debug(f"Target window '{window_title}' is active.")
        return True
    except Exception as win_err:
        logging.error(f"Window check failed for '{window_title}': {win_err}")
        return False


def inject_test_prompt(
    agent_id: str, coords: Dict[str, int], window_title: str, force_unsafe_clicks: bool
) -> bool:
    """Injects the test prompt into the input box."""
    element = "input_box"
    if element not in coords:
        logging.error(
            f"Missing '{element}' coordinates for agent '{agent_id}'. Cannot inject."
        )
        return False

    x, y = coords[element]["x"], coords[element]["y"]
    logging.info(f"[{agent_id}] Injecting test prompt at ({x}, {y})...")

    if not force_unsafe_clicks:
        if not find_and_activate_window(window_title):
            return False
    else:
        logging.warning(
            f"[{agent_id}] Bypassing window activation check due to --force-unsafe-clicks flag."
        )

    try:
        # EDIT: Replace pyautogui calls with OrchestratorBot calls
        # Note: Assuming OrchestratorBot handles necessary waits/delays
        bot.move_to(x=x, y=y, duration=0.2)
        # time.sleep(ACTION_DELAY) # Delay likely handled by bot or not needed
        bot.click()
        # time.sleep(ACTION_DELAY * 2) # Delay likely handled by bot or not needed
        bot.hotkey("ctrl", "a")
        # time.sleep(ACTION_DELAY / 2) # Delay likely handled by bot or not needed
        bot.press("delete")
        # time.sleep(ACTION_DELAY) # Delay likely handled by bot or not needed
        pyperclip.copy(TEST_PROMPT)  # Keep pyperclip for now
        # time.sleep(ACTION_DELAY / 2) # Delay likely handled by bot or not needed
        bot.hotkey("ctrl", "v")
        # time.sleep(ACTION_DELAY) # Delay likely handled by bot or not needed
        bot.press("enter")
        logging.info(f"[{agent_id}] Test prompt injected.")
        return True
    except Exception as e:
        # Catch specific bot exceptions if defined, otherwise general Exception
        logging.error(f"[{agent_id}] Error during injection via OrchestratorBot: {e}")
        return False


def retrieve_response(
    agent_id: str, coords: Dict[str, int], window_title: str, force_unsafe_clicks: bool
) -> Optional[str]:
    """Clicks the copy button and retrieves clipboard content."""
    element = "copy_button"
    if element not in coords:
        logging.error(
            f"Missing '{element}' coordinates for agent '{agent_id}'. Cannot retrieve response."
        )
        return None

    x, y = coords[element]["x"], coords[element]["y"]
    logging.info(
        f"[{agent_id}] Attempting to copy response via button at ({x}, {y})..."
    )

    if not force_unsafe_clicks:
        if not find_and_activate_window(window_title):
            return None
    else:
        logging.warning(
            f"[{agent_id}] Bypassing window activation check due to --force-unsafe-clicks flag."
        )

    original_clipboard = ""
    try:
        original_clipboard = (
            pyperclip.paste()
        )  # Store original to restore later if needed
        pyperclip.copy("")  # Clear clipboard
        # time.sleep(ACTION_DELAY / 2) # Delay likely handled by bot or not needed

        # EDIT: Replace pyautogui calls with OrchestratorBot calls
        bot.move_to(x=x, y=y, duration=0.2)
        # time.sleep(ACTION_DELAY) # Delay likely handled by bot or not needed
        bot.click()
        time.sleep(
            RESPONSE_WAIT_SECONDS
        )  # EDIT: Keep explicit wait for response generation / clipboard update

        response = pyperclip.paste()  # Keep pyperclip for now
        if response:
            logging.info(
                f"[{agent_id}] Successfully retrieved response from clipboard."
            )
        else:
            logging.warning(
                f"[{agent_id}] Clipboard was empty after clicking copy button."
            )
        return response

    except Exception as e:
        # Catch specific bot exceptions if defined, otherwise general Exception
        logging.error(
            f"[{agent_id}] Error during response retrieval via OrchestratorBot: {e}"
        )
        return None
    finally:
        # Attempt to restore original clipboard content (best effort)
        try:
            if original_clipboard:
                pyperclip.copy(original_clipboard)
        except Exception:
            pass


def save_results(filepath: Path, results: Dict[str, Optional[str]]):
    """Saves the validation results to a JSON file."""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)
        logging.info(f"Validation results saved to {filepath}")
    except Exception as e:
        logging.error(f"Failed to save validation results: {e}")


def _validate_coordinates(coords_data: Dict[str, Any], results: Dict[str, Any]):
    for name, data in coords_data.items():
        if not isinstance(data, dict) or "x" not in data or "y" not in data:
            results["errors"][name] = f"Invalid structure, missing 'x' or 'y'. Data: {data}"
            continue
        x, y = data["x"], data["y"]
        if not isinstance(x, int) or not isinstance(y, int):
            results["errors"][name] = f"Invalid types, 'x' or 'y' not integers. Got: ({type(x)}, {type(y)})"
            continue
        # Check if coordinates are within screen bounds (optional but recommended)
        try:
            screen_width, screen_height = pyautogui.size()
            if not (0 <= x < screen_width and 0 <= y < screen_height):
                results["warnings"].append(
                    f"Coordinate '{name}' ({x},{y}) is outside screen bounds ({screen_width}x{screen_height})."
                )
        except Exception as e:
            # Handle cases where screen size cannot be obtained (headless env?)
            results["warnings"].append(
                f"Could not verify screen bounds for coordinate '{name}': {e}"
            )


def _check_coordinate_overlap(coords_data: Dict[str, Any], results: Dict[str, Any]):
    for name1, coord1 in coords_data.items():
        for name2, coord2 in coords_data.items():
            if name1 >= name2: # Avoid self-comparison and duplicates
                continue
            distance = math.sqrt((coord1["x"] - coord2["x"])**2 + (coord1["y"] - coord2["y"])**2)
            if distance < 10:
                results["warnings"].append(
                    f"Coordinates '{name1}' ({coord1['x']},{coord1['y']}) and '{name2}' ({coord2['x']},{coord2['y']}) are very close (distance: {distance:.2f} < 10). Potential overlap?"
                )


def _check_accessibility(coords_data: Dict[str, Any], results: Dict[str, Any]):
    # This requires integration with accessibility tools or more advanced UI inspection
    logger.info("Accessibility checks require manual verification or specific OS tools.")
    results["info"].append("Accessibility check skipped (requires manual verification).")
    # Example placeholder for future:
    # for name, data in coords_data.items():
    #     x, y = data['x'], data['y']
    #     try:
    #         element = accessibility_tool.get_element_at(x, y)
    #         if not element or not element.is_clickable():
    #             results["warnings"].append(f"Element at '{name}' ({x},{y}) might not be accessible/clickable.")
    #     except Exception as e:
    #         results["errors"][name] = f"Accessibility check failed: {e}"


def _check_for_duplicates(coords_data: Dict[str, Any], results: Dict[str, Any]):
    seen_coords: Dict[Tuple[int, int], str] = {}
    for name, data in coords_data.items():
        # Ensure data is valid before checking
        if name in results["errors"]:
             continue
        coord_tuple = (data["x"], data["y"])
        if coord_tuple in seen_coords:
            results["errors"].setdefault("duplicate_coordinates", []).append(
                f"Duplicate coordinate value ({coord_tuple[0]},{coord_tuple[1]}) found for '{name}' and '{seen_coords[coord_tuple]}'."
            )
        else:
            seen_coords[coord_tuple] = name


def validate_gui_coordinates(coords_file: str, min_distance: float) -> Dict[str, Any]:
    results = {
        "errors": {},
        "warnings": [],
        "info": []
    }

    coords_data = load_coords(Path(coords_file))
    if coords_data is None:
        results["errors"]["coordinates_file"] = "Failed to load coordinates file."
        return results

    _validate_coordinates(coords_data, results)
    _check_coordinate_overlap(coords_data, results)
    _check_for_duplicates(coords_data, results)
    _check_accessibility(coords_data, results) # Basic placeholder

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Validate GUI coordinates by injecting a test prompt and retrieving the response."
    )
    parser.add_argument(
        "agent_ids",
        help="Comma-separated list of agent IDs to validate (e.g., Agent-1,Agent-2).",
    )
    parser.add_argument(
        "target_window_title",
        help="Exact title of the target Cursor window(s). Used unless --force-unsafe-clicks is set.",
    )
    parser.add_argument(
        "--coords_file",
        default=str(DEFAULT_COORDS_PATH),
        help=f"Path to the coordinates JSON file (default: {DEFAULT_COORDS_PATH})",
    )
    parser.add_argument(
        "--output_file",
        default=str(DEFAULT_OUTPUT_PATH),
        help=f"Path to save the validation results JSON (default: {DEFAULT_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=RESPONSE_WAIT_SECONDS,
        help=f"Seconds to wait for response after injection (default: {RESPONSE_WAIT_SECONDS})",
    )
    parser.add_argument(
        "--force-unsafe-clicks",
        action="store_true",
        help="Bypass window title activation/check before clicking coordinates.",
    )
    parser.add_argument(
        "--min_distance",
        type=float,
        default=10,
        help="Minimum distance between coordinates to warn about potential overlap.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help=f"Path to save the validation results JSON file. Default: {DEFAULT_OUTPUT_PATH}",
    )

    args = parser.parse_args()

    agent_ids_list = [
        agent_id.strip() for agent_id in args.agent_ids.split(",") if agent_id.strip()
    ]
    if not agent_ids_list:
        print("ERROR: No valid agent IDs provided.")
        exit(1)

    coords_filepath = Path(args.coords_file)
    output_filepath = Path(args.output_file)
    window_title = args.target_window_title
    wait_seconds = args.wait
    force_unsafe = args.force_unsafe_clicks
    min_distance = args.min_distance

    print("\n=== Dream.OS GUI Coordinate Validation Tool ===")
    print(f"Validating Agents: {', '.join(agent_ids_list)}")
    if force_unsafe:
        print(
            "WARNING: Running with --force-unsafe-clicks. Window activation checks bypassed!"
        )
    else:
        print(f"Target Window Title: '{window_title}'")
    print(f"Using Coordinates: {coords_filepath}")
    print(f"Saving Results To: {output_filepath}")
    print(f"Waiting {wait_seconds}s for response after injection.")

    all_coords = load_coords(coords_filepath)
    if all_coords is None:
        print("Exiting due to coordinate loading error.")
        exit(1)

    validation_results = validate_gui_coordinates(coords_filepath, min_distance)

    # 4. Save Results
    save_results(output_filepath, validation_results)

    print("\n=== Validation Complete ===")


if __name__ == "__main__":
    main()
