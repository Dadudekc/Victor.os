# src/tools/validation/validate_gui_coords.py
import argparse
import json
import logging
import math
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# from dreamos.core.config import AppConfig # Removed F401
# from dreamos.core.errors import CoordinateError # Removed F401

# Try importing GUI libraries, warn if unavailable
try:
    import pyautogui
    import pygetwindow
    import pyperclip

    GUI_AVAILABLE = True
except ImportError:
    pyautogui = None
    pyperclip = None
    pygetwindow = None
    GUI_AVAILABLE = False
    logging.warning(
        "PyAutoGUI or PyGetWindow not found. GUI validation checks disabled."
    )

# EDIT START: Remove dummy OrchestratorBot fallback, require real import
try:
    from dreamos.core.bots.orchestrator_bot import OrchestratorBot
except ImportError as e:
    raise ImportError(
        "OrchestratorBot must be available for GUI validation. Please check your PYTHONPATH and dependencies."  # noqa: E501
    ) from e
# EDIT END

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Configuration ---
# EDIT START: Remove hardcoded paths, will be derived from AppConfig
# PROJECT_ROOT = Path(__file__).resolve().parents[3]
# DEFAULT_COORDS_PATH = PROJECT_ROOT / "runtime" / "config" / "cursor_agent_coords.json"
# DEFAULT_OUTPUT_PATH = (
#     PROJECT_ROOT / "runtime" / "validation" / "gui_coord_validation_results.json"
# )
# EDIT END

TEST_PROMPT = "Ping from Dream.OS Validator"
RESPONSE_WAIT_SECONDS = 5  # Time to wait after injection before trying to copy response
ACTION_DELAY = 0.5  # Small delay between pyautogui actions

# EDIT: Instantiate OrchestratorBot (assuming no critical config needed for basic actions)  # noqa: E501
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
                f"Target window '{window_title}' found but not active. Attempting to activate."  # noqa: E501
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
            f"[{agent_id}] Bypassing window activation check due to --force-unsafe-clicks flag."  # noqa: E501
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
            f"Missing '{element}' coordinates for agent '{agent_id}'. Cannot retrieve response."  # noqa: E501
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
            f"[{agent_id}] Bypassing window activation check due to --force-unsafe-clicks flag."  # noqa: E501
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


# EDIT START: Add structure validation functions (renamed for clarity)
def _validate_coord_structure(coords_data: Dict[str, Any], results: Dict[str, Any]):
    """Validates the basic structure (dict with x, y) and types (int) of coordinates."""
    for name, data in coords_data.items():
        if not isinstance(data, dict) or "x" not in data or "y" not in data:
            results["errors"][name] = (
                f"Invalid structure, missing 'x' or 'y'. Data: {data}"
            )
            continue
        x, y = data["x"], data["y"]
        if not isinstance(x, int) or not isinstance(y, int):
            results["errors"][name] = (
                f"Invalid types, 'x' or 'y' not integers. Got: ({type(x)}, {type(y)})"
            )
            continue
        # Check if coordinates are within screen bounds (optional but recommended)
        try:
            screen_width, screen_height = pyautogui.size()
            if not (0 <= x < screen_width and 0 <= y < screen_height):
                results["warnings"].append(
                    f"Coordinate '{name}' ({x},{y}) is outside screen bounds ({screen_width}x{screen_height})."  # noqa: E501
                )
        except Exception as e:
            # Handle cases where screen size cannot be obtained (headless env?)
            results["warnings"].append(
                f"Could not verify screen bounds for coordinate '{name}': {e}"
            )


def _check_coord_proximity(
    coords_data: Dict[str, Any], results: Dict[str, Any], min_distance: float
):
    """Checks if any coordinate pairs are too close together."""
    coords_list = [
        (name, data["x"], data["y"])
        for name, data in coords_data.items()
        if isinstance(data, dict) and "x" in data and "y" in data
    ]
    for i in range(len(coords_list)):
        name1, x1, y1 = coords_list[i]
        for j in range(i + 1, len(coords_list)):
            name2, x2, y2 = coords_list[j]
            distance = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
            if distance < min_distance:
                results["warnings"].append(
                    f"Coordinates '{name1}' ({x1},{y1}) and '{name2}' ({x2},{y2}) are too close: {distance:.2f}px (min: {min_distance}px)."
                )


def _check_accessibility(coords_data: Dict[str, Any], results: Dict[str, Any]):
    # This requires integration with accessibility tools or more advanced UI inspection
    logger.info(  # noqa: F821
        "Accessibility checks require manual verification or specific OS tools."
    )
    results["info"].append(
        "Accessibility check skipped (requires manual verification)."
    )
    # Example placeholder for future:
    # for name, data in coords_data.items():
    #     x, y = data['x'], data['y']
    #     try:
    #         element = accessibility_tool.get_element_at(x, y)
    #         if not element or not element.is_clickable():
    #             results["warnings"].append(f"Element at '{name}' ({x},{y}) might not be accessible/clickable.")  # noqa: E501
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
                f"Duplicate coordinate value ({coord_tuple[0]},{coord_tuple[1]}) found for '{name}' and '{seen_coords[coord_tuple]}'."  # noqa: E501
            )
        else:
            seen_coords[coord_tuple] = name


def validate_gui_coordinates(coords_file: Path, min_distance: float) -> Dict[str, Any]:
    """Performs static validation on GUI coordinate data."""
    results = {"errors": {}, "warnings": [], "info": []}

    coords_data = load_coords(coords_file)
    if coords_data is None:
        results["errors"]["loading"] = f"Failed to load or parse {coords_file}."
        return results

    _validate_coord_structure(coords_data, results)
    _check_coord_proximity(coords_data, results, min_distance)
    _check_for_duplicates(coords_data, results)
    _check_accessibility(coords_data, results)  # Basic placeholder

    return results


def main():
    # EDIT START: Load AppConfig and use its paths
    # config = load_app_config() # Assumes standard loading works here
    # default_coords_path = config.paths.runtime / "config" / "cursor_agent_coords.json"
    # default_output_path = config.paths.runtime / "validation" / "gui_coord_validation_results.json"
    # EDIT END

    parser = argparse.ArgumentParser(
        description="Validate GUI coordinates for Dream.OS agents."
    )
    parser.add_argument(
        "--coords-file",
        type=Path,
        # EDIT START: Use config path as default
        # default=default_coords_path,
        # EDIT END
        help="Path to the JSON file containing GUI coordinates.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        # EDIT START: Use config path as default
        # default=default_output_path,
        # EDIT END
        help="Path to save the validation results JSON file.",
    )
    parser.add_argument(
        "--window-title",
        type=str,
        # EDIT: Use config if available, otherwise keep default
        # default=getattr(getattr(config, 'integrations', None), 'cursor', {}).get('window_title', "Cursor"),
        help="Title of the target application window (e.g., 'Cursor').",
    )
    parser.add_argument(
        "--test-injection",
        action="store_true",
        help="Perform a live test by injecting a prompt and trying to copy the response.",
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        default="Agent-1",  # Keep a default for testing
        help="Agent ID whose coordinates should be used for live injection test.",
    )
    parser.add_argument(
        "--force-unsafe-clicks",
        action="store_true",
        help="Bypass window activation checks before performing clicks (use with caution).",
    )
    parser.add_argument(
        "--min-distance",
        type=float,
        default=10.0,
        help="Minimum allowed pixel distance between distinct coordinate points.",
    )

    args = parser.parse_args()

    # --- Static Validation ---
    logging.info(f"Starting static validation of {args.coords_file}...")
    validation_results = validate_gui_coordinates(args.coords_file, args.min_distance)
    save_results(args.output_file, validation_results)

    has_errors = bool(validation_results["errors"])
    has_warnings = bool(validation_results["warnings"])

    if has_errors:
        logging.error("Static validation FAILED with errors.")
    elif has_warnings:
        logging.warning("Static validation PASSED with warnings.")
    else:
        logging.info("Static validation PASSED.")

    # --- Live Injection Test (Optional) ---
    if args.test_injection:
        if has_errors:
            logging.warning(
                "Skipping live injection test due to static validation errors."
            )
            return

        logging.info(
            f"Starting live injection test for agent '{args.agent_id}' in window '{args.window_title}'..."
        )
        all_coords = load_coords(args.coords_file)
        agent_coords = all_coords.get(args.agent_id)

        if not agent_coords:
            logging.error(
                f"Coordinates for agent '{args.agent_id}' not found in {args.coords_file}. Cannot run live test."
            )
            return

        if inject_test_prompt(
            args.agent_id, agent_coords, args.window_title, args.force_unsafe_clicks
        ):
            logging.info(
                f"Waiting {RESPONSE_WAIT_SECONDS} seconds for response generation..."
            )
            time.sleep(RESPONSE_WAIT_SECONDS)
            response = retrieve_response(
                args.agent_id, agent_coords, args.window_title, args.force_unsafe_clicks
            )
            if response:
                logging.info(
                    f"Live injection test PASSED. Retrieved: '{response[:50]}...'"
                )
            else:
                logging.error(
                    "Live injection test FAILED. Could not retrieve response."
                )
        else:
            logging.error("Live injection test FAILED during prompt injection.")


if __name__ == "__main__":
    main()
