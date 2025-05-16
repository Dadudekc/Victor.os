# src/dreamos/cli/calibrate_gui_coords.py
import argparse
import json
import os
import time
from pathlib import Path

import pyautogui

# Assuming PROJECT_ROOT is defined appropriately elsewhere or determined dynamically
# For simplicity, let's try to find it relative to this script
# TODO (Masterpiece Review - Captain-Agent-8): PROJECT_ROOT calculation here is fragile.
#      If integrated into the main click app, use PathsConfig from the loaded AppConfig.
#      If kept standalone, this calculation is a necessary evil but less robust.
try:
    PROJECT_ROOT = Path(__file__).resolve().parents[3]  # Adjust depth as needed
except NameError:
    # Fallback if __file__ is not defined (e.g., interactive execution)
    PROJECT_ROOT = Path(".").resolve()

# TODO (Masterpiece Review - Captain-Agent-8): Coordinate file paths should be sourced
#      from AppConfig (e.g., GuiAutomationConfig or PathsConfig) for consistency,
#      rather than being hardcoded here, especially if integrated into the main CLI.
COORDS_FILE = PROJECT_ROOT / "runtime" / "config" / "cursor_agent_coords.json"
COPY_COORDS_FILE = PROJECT_ROOT / "runtime" / "config" / "cursor_agent_copy_coords.json"
SESSION_START_COORDS_FILE = (
    PROJECT_ROOT / "runtime" / "config" / "cursor_agent_session_start_coords.json"
)


def load_coords(file_path: Path) -> dict:
    """Loads coordinates from a JSON file."""
    if not file_path.exists():
        print(f"Error: Coordinate file not found: {file_path}")
        return None
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return None
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None


def save_coords(file_path: Path, data: dict):
    """Saves coordinates to a JSON file atomically."""
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    try:
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, file_path)
        print(f"Successfully saved updated coordinates to {file_path}")
    except Exception as e:
        print(f"Error saving coordinates to {file_path}: {e}")
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except OSError:
                pass  # Ignore error during cleanup


def calibrate_coordinates(coords_data: dict, file_name: str):
    """Interactively calibrates coordinates."""
    if not coords_data:
        return None

    updated_coords = coords_data.copy()
    print(f"\n--- Calibrating {file_name} ---")
    print("For each key, move your mouse to the target location and wait.")
    print("Press Ctrl+C to skip remaining keys in this file.")

    try:
        for key, value in coords_data.items():
            print(f"\nCalibrating '{key}'... Current value: {value}")
            print("Position your mouse over the target location NOW.")
            print("Capturing in 3...", end="", flush=True)
            time.sleep(1)
            print(" 2...", end="", flush=True)
            time.sleep(1)
            print(" 1...", end="", flush=True)
            time.sleep(1)

            try:
                current_pos = pyautogui.position()
                print(f" Captured: {current_pos}")
            except Exception as e:
                print(f"\nError capturing position: {e}. Skipping key '{key}'.")
                continue

            confirm = input(
                f"Update '{key}' to {current_pos}? (y/n/s=skip file): "
            ).lower()
            if confirm == "y":
                updated_coords[key] = [current_pos.x, current_pos.y]
                print(f"'{key}' updated.")
            elif confirm == "s":
                print(f"Skipping calibration for the rest of {file_name}.")
                return None  # Indicate skip
            else:
                print(f"Keeping original value for '{key}'.")

    except KeyboardInterrupt:
        print(
            "\nCalibration interrupted by user. " "Proceeding with changes made so far."
        )

    return updated_coords


def main():
    # TODO (Masterpiece Review - Captain-Agent-8): This uses argparse, while main.py uses click.
    #      Consolidate CLI framework usage (likely migrating this to be a click command
    #      within the main cli app defined in main.py).
    parser = argparse.ArgumentParser(description="GUI Coordinate Calibration Utility")
    parser.add_argument(
        "--session-start-only",
        action="store_true",
        help="Only calibrate session start coordinates (skip standard and copy).",
    )
    args = parser.parse_args()

    print("Starting GUI Coordinate Calibration Utility")
    print(f"Looking for coordinate files relative to: {PROJECT_ROOT}")
    print(f"Coords file: {COORDS_FILE}")
    print(f"Copy coords file: {COPY_COORDS_FILE}")
    print(
        f"Session start coords file: {SESSION_START_COORDS_FILE}"
    )  # For Cursor session automation

    if not args.session_start_only:
        # --- Calibrate standard coordinates ---
        coords = load_coords(COORDS_FILE)
        if coords:
            updated_coords = calibrate_coordinates(coords, COORDS_FILE.name)
            if updated_coords is not None:
                if updated_coords != coords:  # Only save if changed
                    save_confirm = input(
                        f"\nSave updated coordinates to " f"{COORDS_FILE.name}? (y/n): "
                    ).lower()
                    if save_confirm == "y":
                        save_coords(COORDS_FILE, updated_coords)
                    else:
                        print("Changes to standard coordinates discarded.")
                else:
                    print("No changes made to standard coordinates.")
            else:
                print(f"Calibration skipped for {COORDS_FILE.name}.")

        # --- Calibrate copy coordinates ---
        copy_coords = load_coords(COPY_COORDS_FILE)
        if copy_coords:
            updated_copy_coords = calibrate_coordinates(
                copy_coords, COPY_COORDS_FILE.name
            )
            if updated_copy_coords is not None:
                if updated_copy_coords != copy_coords:  # Only save if changed
                    save_copy_confirm = input(
                        f"\nSave updated copy coordinates to "
                        f"{COPY_COORDS_FILE.name}? (y/n): "
                    ).lower()
                    if save_copy_confirm == "y":
                        save_coords(COPY_COORDS_FILE, updated_copy_coords)
                    else:
                        print("Changes to copy coordinates discarded.")
                else:
                    print("No changes made to copy coordinates.")
            else:
                print(f"Calibration skipped for {COPY_COORDS_FILE.name}.")

    # --- Calibrate session start coordinates (for Cursor automation) ---
    session_start_coords = load_coords(SESSION_START_COORDS_FILE)
    if session_start_coords:
        updated_session_start_coords = calibrate_coordinates(
            session_start_coords, SESSION_START_COORDS_FILE.name
        )
        if updated_session_start_coords is not None:
            if (
                updated_session_start_coords != session_start_coords
            ):  # Only save if changed
                save_session_start_confirm = input(
                    f"\nSave updated session start coordinates to "
                    f"{SESSION_START_COORDS_FILE.name}? (y/n): "
                ).lower()
                if save_session_start_confirm == "y":
                    save_coords(
                        SESSION_START_COORDS_FILE,
                        updated_session_start_coords,
                    )
                else:
                    print("Changes to session start coordinates discarded.")
            else:
                print("No changes made to session start coordinates.")
        else:
            print(f"Calibration skipped for {SESSION_START_COORDS_FILE.name}.")

    print("\nCalibration utility finished.")


if __name__ == "__main__":
    # Basic check if pyautogui is available
    try:
        pyautogui.size()  # Check if display is available
    except Exception as e:
        print(f"Error initializing PyAutoGUI (likely no display available): {e}")
        print("This script requires a GUI environment to run.")
        exit(1)
    main()
