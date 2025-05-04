# src/dreamos/core/health_checks/cursor_window_check.py
import json
import logging
from pathlib import Path
from typing import Any, Dict, Literal, Optional

# Import AppConfig for type hint and access
from ..config import AppConfig

try:
    import pyautogui

    PYAUTOGUI_AVAILABLE = True
except ImportError:
    pyautogui = None
    PYAUTOGUI_AVAILABLE = False
    logging.error(
        "pyautogui not found. Cursor window reachability check cannot verify screen bounds."  # noqa: E501
    )

logger = logging.getLogger(__name__)

# {{ EDIT START: Define constants for return structure }}
CheckStatus = Literal["PASS", "WARN", "FAIL", "ERROR"]
CHECK_NAME = "cursor_window_reachability"
# {{ EDIT END }}


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


class CursorWindowCheck:
    """Encapsulates the logic for the cursor window reachability check."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.coords_path = Path(config.health_checks.cursor_coords_path).resolve()
        self.expected_agent_ids = config.health_checks.expected_agent_ids
        logger.info(
            f"{CHECK_NAME} initialized. Coords path: {self.coords_path}, Expected Agents: {len(self.expected_agent_ids)}"
        )

    def run_check(self) -> Dict[str, Any]:
        """Checks if configured cursor coordinates for expected agents are valid and within screen bounds."""  # noqa: E501
        logger.info(f"Running {CHECK_NAME} check using: {self.coords_path}")
        details: Dict[str, Any] = {
            "per_agent": {},
            "config_path": str(self.coords_path),
        }
        overall_status: CheckStatus = "PASS"  # Start optimistic

        coords_data = _load_coordinates(self.coords_path)

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
            for agent_id in self.expected_agent_ids:
                details["per_agent"][agent_id] = {
                    "reachable": False,
                    "reason": details["error"],
                }
            return {"check_name": CHECK_NAME, "status": "ERROR", "details": details}

        any_unreachable = False
        for agent_id in self.expected_agent_ids:
            agent_result = {
                "reachable": False,
                "reason": "Not configured",
                "coords": None,
            }
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
                                f"Coordinates ({x},{y}) outside screen bounds ({screen_width}x{screen_height})."  # noqa: E501
                            )
                            any_unreachable = True
                    else:
                        agent_result["reachable"] = (
                            True  # Assume reachable if bounds check failed
                        )
                        agent_result["reason"] = (
                            "Coordinates syntactically valid (Screen bounds check unavailable/failed)."  # noqa: E501
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
            if agent_result["reachable"]:
                logger.debug(
                    f"{CHECK_NAME} PASSED for {agent_id}: {agent_result['reason']}"
                )
            else:
                logger.warning(
                    f"{CHECK_NAME} FAILED for {agent_id}: {agent_result['reason']}"
                )

        if any_unreachable:
            if overall_status != "ERROR":
                overall_status = "FAIL"

        logger.info(f"{CHECK_NAME} check complete. Overall status: {overall_status}")
        return {"check_name": CHECK_NAME, "status": overall_status, "details": details}


def check_cursor_window_reachability(config: AppConfig) -> Dict[str, Any]:
    """Runs the cursor window reachability check using configuration."""
    checker = CursorWindowCheck(config)
    return checker.run_check()


if __name__ == "__main__":
    # Load config to run standalone
    try:
        app_config = AppConfig.load()  # Assumes default config path works
    except Exception as e:
        print(f"Failed to load AppConfig: {e}. Cannot run check.")
        exit(1)

    print("Running Cursor Window Reachability Check...")
    # Use the coords path from config
    coords_file_path = Path(app_config.health_checks.cursor_coords_path).resolve()
    coords_file_path.parent.mkdir(parents=True, exist_ok=True)
    # Create dummy coord file if needed
    if not coords_file_path.exists():
        # Use expected agents from config
        dummy_coords = {
            agent_id: {"x": 10 * i, "y": 20 * i}
            for i, agent_id in enumerate(app_config.health_checks.expected_agent_ids)
        }
        # Add invalid/out of bounds entries if possible
        if len(app_config.health_checks.expected_agent_ids) >= 4:
            agent_3 = app_config.health_checks.expected_agent_ids[2]
            agent_4 = app_config.health_checks.expected_agent_ids[3]
            dummy_coords[agent_3]["y"] = "invalid"
            if pyautogui is not None:
                sw, sh = pyautogui.size()
                dummy_coords[agent_4] = {"x": sw + 100, "y": sh + 100}
            else:
                dummy_coords[agent_4] = {"x": 99999, "y": 99999}

        try:
            with open(coords_file_path, "w") as f:
                json.dump(dummy_coords, f, indent=2)
            print(f"Created dummy coordinates file: {coords_file_path}")
        except Exception as e:
            print(f"Error creating dummy coordinates file: {e}")

    # Run the check using the config
    check_results = check_cursor_window_reachability(config=app_config)
    print("\n--- Check Results ---")
    import pprint

    pprint.pprint(check_results)
    print("-------------------")
