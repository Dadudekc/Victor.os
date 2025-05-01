# src/dreamos/utils/gui_utils.py
"""Utilities for GUI Automation and related coordinate handling."""

import json  # Added json
import logging
import subprocess  # Added subprocess
import sys  # Added sys
from pathlib import Path  # Added Path
from typing import Any, Dict, Optional, Tuple

# Import core error and potentially PROJECT_ROOT if needed here
from ..core.errors import (  # Assuming CoordinateError is defined in core.errors
    CoordinateError,
    ToolError,
)

# from ..core.config import PROJECT_ROOT # If needed for default paths

logger = logging.getLogger(__name__)

# --- Coordinate Utilities ---


def get_specific_coordinate(
    identifier: str, full_coords: Optional[Dict[str, Any]]
) -> Optional[Tuple[int, int]]:
    """Extracts specific (x, y) coordinates for an identifier (e.g., 'agent_01.input_box')."""
    if not full_coords:
        logger.debug(f"Full coordinates data is None, cannot get '{identifier}'.")
        return None

    parts = identifier.split(".")  # e.g., ['agent_01', 'input_box']
    if len(parts) != 2:
        logger.warning(
            f"Invalid coordinate identifier format: '{identifier}'. Expected 'agent_id.element_key'."
        )
        return None

    agent_id, element_key = parts

    agent_coords = full_coords.get(agent_id)
    if not agent_coords or not isinstance(agent_coords, dict):
        logger.debug(
            f"No coordinate data found for agent '{agent_id}' in the provided structure."
        )
        return None

    coords = agent_coords.get(element_key)
    if not coords:
        logger.debug(
            f"No coordinates found for element '{element_key}' within agent '{agent_id}'."
        )
        return None

    # Expecting coords to be [x, y] list or (x, y) tuple or {'x': val, 'y': val} dict
    if (
        isinstance(coords, (list, tuple))
        and len(coords) == 2
        and all(isinstance(c, int) for c in coords)
    ):
        logger.debug(
            f"Found list/tuple coordinates for '{identifier}': {tuple(coords)}"
        )
        return tuple(coords)
    elif (
        isinstance(coords, dict)
        and "x" in coords
        and "y" in coords
        and isinstance(coords["x"], int)
        and isinstance(coords["y"], int)
    ):
        logger.debug(
            f"Found dict coordinates for '{identifier}': {(coords['x'], coords['y'])}"
        )
        return (coords["x"], coords["y"])
    else:
        logger.warning(
            f"Invalid coordinate format for '{identifier}': {coords}. Expected [x, y] or {{ 'x': x, 'y': y }}."
        )
        return None


# --- Add other missing GUI utils here ---


def load_coordinates(coords_file_path: Path | str) -> Optional[Dict[str, Any]]:
    """Safely loads and parses the JSON coordinate file."""
    path = Path(coords_file_path)
    if not path.exists() or not path.is_file():
        logger.error(f"Coordinate file not found or is not a file: {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                logger.warning(f"Coordinate file is empty: {path}")
                return {}
            data = json.loads(content)
            if not isinstance(data, dict):
                logger.error(
                    f"Coordinate file does not contain a valid JSON dictionary: {path}"
                )
                return None
            logger.info(f"Successfully loaded coordinates from: {path}")
            return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from coordinate file {path}: {e}")
        return None
    except IOError as e:
        logger.error(f"Failed to read coordinate file {path}: {e}")
        return None
    except Exception as e:
        logger.error(
            f"An unexpected error occurred loading coordinates from {path}: {e}",
            exc_info=True,
        )
        return None


# --- Window Utilities ---

try:
    import pygetwindow

    PYGETWINDOW_AVAILABLE = True
except ImportError:
    pygetwindow = None
    PYGETWINDOW_AVAILABLE = False
    logger.warning(
        "pygetwindow not found. Window focus check may be unreliable or disabled."
    )


def is_window_focused(target_title_substring: str) -> bool:
    """Checks if the currently active window's title contains the target substring.

    Uses pygetwindow for cross-platform compatibility, but might be less reliable
    than OS-specific APIs, especially for exact matching or complex scenarios.

    Args:
        target_title_substring: A case-insensitive substring to look for in the active window title.

    Returns:
        True if pygetwindow is available, an active window is found, and its title contains the substring.
        False otherwise.
    """
    if not PYGETWINDOW_AVAILABLE or pygetwindow is None:
        logger.warning("is_window_focused check skipped: pygetwindow not available.")
        return False  # Cannot verify without the library

    try:
        active_window = pygetwindow.getActiveWindow()
        if active_window and active_window.title:
            logger.debug(f"Active window found: '{active_window.title}'")
            # Case-insensitive comparison
            if target_title_substring.lower() in active_window.title.lower():
                logger.debug(
                    f"Active window title contains target substring '{target_title_substring}'. Focus presumed correct."
                )
                return True
            else:
                logger.debug(
                    f"Active window title does not contain target substring '{target_title_substring}'."
                )
                return False
        elif active_window:
            logger.warning("Active window found but has no title.")
            return False  # Can't verify without a title
        else:
            logger.warning("Could not get active window.")
            return False
    except pygetwindow.PyGetWindowException as e:
        # Errors can occur if no window is active (e.g., full screen game, RDP session)
        logger.error(f"Error getting active window using pygetwindow: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking window focus: {e}", exc_info=True)
        return False


# --- Recalibration Utility ---

# Define path relative to this file (utils/gui_utils.py -> utils -> core -> dreamos -> src -> tools)
# Or rely on PROJECT_ROOT if imported from config
try:
    from ...core.config import PROJECT_ROOT  # Use config value
except ImportError:
    logger.error(
        "Cannot import PROJECT_ROOT from dreamos.core.config. Recalibration script path may be incorrect."
    )
    PROJECT_ROOT = (
        Path(__file__).resolve().parents[2]
    )  # Fallback: utils -> core -> dreamos -> src

RECALIBRATION_SCRIPT_PATH = (
    PROJECT_ROOT / "src" / "tools" / "calibration" / "recalibrate_coords.py"
)


def trigger_recalibration(identifier: str, coords_file_path: Path | str) -> bool:
    """Triggers the external recalibration script for a specific coordinate identifier.

    Args:
        identifier: The identifier that failed verification (e.g., 'agent_01.copy_button').
        coords_file_path: The path to the coordinate file that needs updating.

    Returns:
        True if the script executed successfully (return code 0), False otherwise.
    """
    if not RECALIBRATION_SCRIPT_PATH.exists():
        logger.error(
            f"Recalibration script not found at: {RECALIBRATION_SCRIPT_PATH}. Cannot recalibrate."
        )
        return False

    python_exe = sys.executable  # Use the same python that's running this
    command = [
        python_exe,
        str(RECALIBRATION_SCRIPT_PATH),
        "--identifier",
        identifier,
        "--coords-file",
        str(coords_file_path),
        # Add any other necessary args for the script
    ]

    logger.info(
        f"Triggering recalibration script for '{identifier}' with command: {' '.join(command)}"
    )

    try:
        # Execute the script, wait for completion, capture output
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception on non-zero exit code
            cwd=PROJECT_ROOT,  # Run from project root for consistent relative paths in script
        )

        if process.returncode == 0:
            logger.info(
                f"Recalibration script for '{identifier}' completed successfully."
            )
            logger.debug(f"Recalibration stdout:\n{process.stdout}")
            if process.stderr:
                logger.warning(f"Recalibration stderr:\n{process.stderr}")
            return True
        else:
            logger.error(
                f"Recalibration script for '{identifier}' failed with return code {process.returncode}."
            )
            logger.error(f"Recalibration stdout:\n{process.stdout}")
            logger.error(f"Recalibration stderr:\n{process.stderr}")
            return False

    except FileNotFoundError as e:
        # Error finding python executable or script itself
        logger.error(
            f"Error executing recalibration script: {e}. Check Python path and script path.",
            exc_info=True,
        )
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error running recalibration script for '{identifier}': {e}",
            exc_info=True,
        )
        return False


# def trigger_recalibration(...)
