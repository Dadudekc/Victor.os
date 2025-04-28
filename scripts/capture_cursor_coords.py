#!/usr/bin/env python3
# scripts/capture_cursor_coords.py

import pyautogui
import time
import json
from pathlib import Path
import sys

# --- Configuration ---
AGENT_IDS = [f"agent_{i:02d}" for i in range(1, 9)] # agent_01 to agent_08
OUTPUT_FILE = Path("config/cursor_agent_coords.json")
CAPTURE_DELAY_SECONDS = 5 # Time user has to position the mouse

def capture_coordinates():
    """Interactive script to capture screen coordinates for agent input fields."""
    print("--- Cursor Agent Coordinate Capture --- ")
    print(f"You will be prompted to position your mouse for {len(AGENT_IDS)} agents.")
    print(f"For each agent, move your mouse to the CENTER of their chat input field.")
    print(f"You will have {CAPTURE_DELAY_SECONDS} seconds for each agent after the prompt.")
    print("-----------------------------------------")

    all_coordinates = {}

    try:
        for agent_id in AGENT_IDS:
            print(f"\n>>> Prepare for Agent: {agent_id} <<<")
            print(f"Move mouse to the CENTER of {agent_id}'s chat input field...")

            # Countdown
            for i in range(CAPTURE_DELAY_SECONDS, 0, -1):
                print(f"Capturing in {i}...", end='\r')
                time.sleep(1)
            print("Capturing now!      ") # Extra spaces to overwrite countdown

            # Capture coordinates
            current_pos = pyautogui.position()
            coords = {"x": current_pos.x, "y": current_pos.y}
            all_coordinates[agent_id] = coords

            print(f"--> Captured for {agent_id}: X={coords['x']}, Y={coords['y']}")
            time.sleep(0.5) # Small pause before next agent

    except pyautogui.FailSafeException:
        print("\nERROR: PyAutoGUI fail-safe triggered (mouse moved to top-left corner). Aborting.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nUser interrupted capture. Aborting.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

    # Save the coordinates
    print("\n--- Capture Complete --- ")
    print(f"Saving coordinates for {len(all_coordinates)} agents to: {OUTPUT_FILE}")

    try:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_coordinates, f, indent=4)
        print(f"✅ Coordinates successfully saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"\nERROR: Failed to save coordinates file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    capture_coordinates() 