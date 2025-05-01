# src/dreamos/core/health_checks/cursor_window_check.py
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

try:
    import pyautogui

    PYAUTOGUI_AVAILABLE = True
except ImportError:
    pyautogui = None
    PYAUTOGUI_AVAILABLE = False
    logging.error(
        "pyautogui not found. Cursor window reachability check cannot verify screen bounds."
    )

logger = logging.getLogger(__name__)

# TODO: Make EXPECTED_AGENT_IDS configurable or dynamically retrieved.
EXPECTED_AGENT_IDS = [f"agent_{i:03d}" for i in range(1, 9)]  # agent_001 to agent_008

# {{ EDIT START: Define constants for return structure }}
CheckStatus = Literal["PASS", "WARN", "FAIL", "ERROR"]
CHECK_NAME = "cursor_window_reachability"
# {{ EDIT END }}

# TODO: Make DEFAULT_COORDS_PATH configurable via AppConfig.
CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
DEFAULT_COORDS_PATH = CONFIG_DIR / "cursor_agent_copy_coords.json"


def _load_coordinates(coords_path: Path) -> Optional[Dict[str, Dict[str, int]]]:
    """Loads coordinates from the JSON file."""
    if not coords_path.exists():
        logger.error(f"Coordinate file not found: {coords_path}")
        return None
    try:
        with open(coords_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.error(f"Coordinate file content is not a dictionary: {coords_path}")
            return None
        return data
    except json.JSONDecodeError:
        logger.error(
            f"Failed to decode JSON from coordinate file: {coords_path}", exc_info=True
        )
        return None
    except Exception as e:
        logger.error(
            f"Failed to load coordinate file {coords_path}: {e}", exc_info=True
        )
        return None


def check_cursor_window_reachability(
    coords_path: Path = DEFAULT_COORDS_PATH,
) -> Dict[str, Any]:
    """Checks if configured cursor coordinates for expected agents are valid and within screen bounds."""
    logger.info(f"Running {CHECK_NAME} check using: {coords_path}")
    details: Dict[str, Any] = {"per_agent": {}, "config_path": str(coords_path)}
    overall_status: CheckStatus = "PASS"  # Start optimistic

    coords_data = _load_coordinates(coords_path)

    screen_width, screen_height = (None, None)
    if pyautogui is not None:
        try:
            screen_width, screen_height = pyautogui.size()
            logger.info(f"Detected screen size: {screen_width}x{screen_height}")
        except Exception as e:
            logger.error(f"Failed to get screen size using pyautogui: {e}")

    if coords_data is None:
        logger.error(
            f"{CHECK_NAME}: Cannot perform check: Failed to load coordinate data."
        )
        details["error"] = "Coordinate file load failed."
        # Mark all agents as failed in details
        for agent_id in EXPECTED_AGENT_IDS:
            details["per_agent"][agent_id] = {
                "reachable": False,
                "reason": details["error"],
            }
        return {"check_name": CHECK_NAME, "status": "ERROR", "details": details}

    any_unreachable = False
    for agent_id in EXPECTED_AGENT_IDS:
        agent_result = {"reachable": False, "reason": "Not configured", "coords": None}
        agent_coords = coords_data.get(agent_id)

        if agent_coords:
            x = agent_coords.get("x")
            y = agent_coords.get("y")
            agent_result["coords"] = {"x": x, "y": y}  # Store original coords

            if isinstance(x, int) and isinstance(y, int):
                if pyautogui is not None and screen_width is not None:
                    if 0 <= x < screen_width and 0 <= y < screen_height:
                        agent_result["reachable"] = True
                        agent_result["reason"] = (
                            "Coordinates valid and within screen bounds."
                        )
                    else:
                        agent_result["reason"] = (
                            f"Coordinates ({x},{y}) outside screen bounds ({screen_width}x{screen_height})."
                        )
                        any_unreachable = True
                else:
                    agent_result["reachable"] = (
                        True  # Assume reachable if bounds check failed
                    )
                    agent_result["reason"] = (
                        "Coordinates syntactically valid (Screen bounds check unavailable/failed)."
                    )
                    # Consider making this a WARN instead of PASS?
                    if overall_status == "PASS":
                        overall_status = "WARN"
            else:
                agent_result["reason"] = (
                    f"Invalid coordinates format (x={x}, y={y}). Expected integers."
                )
                any_unreachable = True
        else:
            any_unreachable = True  # Missing agent is unreachable

        details["per_agent"][agent_id] = agent_result
        # Logging individual results is good, keep it
        if agent_result["reachable"]:
            logger.debug(
                f"{CHECK_NAME} PASSED for {agent_id}: {agent_result['reason']}"
            )
        else:
            logger.warning(
                f"{CHECK_NAME} FAILED for {agent_id}: {agent_result['reason']}"
            )

    if any_unreachable:
        # If any agent is unreachable, the check overall is FAIL
        if overall_status != "ERROR":  # Don't override ERROR
            overall_status = "FAIL"

    logger.info(f"{CHECK_NAME} check complete. Overall status: {overall_status}")
    return {"check_name": CHECK_NAME, "status": overall_status, "details": details}


if __name__ == "__main__":
    print("Running Cursor Window Reachability Check...")
    # Ensure config directory exists for dummy file creation
    DEFAULT_COORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Create dummy coord file if needed
    if not DEFAULT_COORDS_PATH.exists():
        dummy_coords = {
            f"agent_{i:03d}": {"x": 10 * i, "y": 20 * i} for i in range(1, 9)
        }
        # Add one invalid entry and one out of bounds (assuming screen > 100x100)
        dummy_coords["agent_003"]["y"] = "invalid"
        if pyautogui is not None:
            sw, sh = pyautogui.size()
            dummy_coords["agent_004"] = {"x": sw + 100, "y": sh + 100}
        else:
            dummy_coords["agent_004"] = {"x": 99999, "y": 99999}  # Likely out of bounds

        try:
            with open(DEFAULT_COORDS_PATH, "w") as f:
                json.dump(dummy_coords, f, indent=2)
            print(f"Created dummy coordinates file: {DEFAULT_COORDS_PATH}")
        except Exception as e:
            print(f"Error creating dummy coordinates file: {e}")

    check_results = check_cursor_window_reachability()
    print("\n--- Check Results ---")
    import pprint

    pprint.pprint(check_results)
    print("-------------------")
