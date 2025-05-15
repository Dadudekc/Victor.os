import pyautogui
import json
import time
import os

COORDS_FILE_PATH = os.path.join("runtime", "config", "cursor_agent_coords.json")
AGENT_IDS = [f"Agent-{i}" for i in range(1, 9)]

def load_coords():
    """Loads existing coordinates from the JSON file or returns a new structure."""
    if os.path.exists(COORDS_FILE_PATH):
        try:
            with open(COORDS_FILE_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {COORDS_FILE_PATH} contains invalid JSON. Starting fresh.")
            return {agent_id: {} for agent_id in AGENT_IDS}
    return {agent_id: {} for agent_id in AGENT_IDS}

def save_coords(coords_data):
    """Saves the updated coordinates data to the JSON file."""
    try:
        os.makedirs(os.path.dirname(COORDS_FILE_PATH), exist_ok=True)
        with open(COORDS_FILE_PATH, "w") as f:
            json.dump(coords_data, f, indent=4)
        print(f"Successfully saved coordinates to {COORDS_FILE_PATH}")
    except IOError as e:
        print(f"Error saving coordinates: {e}")

def main():
    """Main function to guide user through coordinate calibration."""
    print("Starting Agent GUI Initial Coordinate Calibration...")
    print("You will be prompted for each of the 8 agents.")
    print("Please ensure the agent's GUI window is visible and in its initial state (no messages sent yet).")
    print("IMPORTANT: PyAutoGUI's FailSafe can be triggered by moving the mouse to a screen corner.")
    
    coords_data = load_coords()

    for agent_id in AGENT_IDS:
        print(f"\n--- Calibrating for {agent_id} ---")
        input(f"1. Ensure {agent_id}'s GUI is ready and its input box is clear. Press Enter to continue...")
        
        print("2. You have 5 seconds to move your mouse cursor to the CENTER of {agent_id}'s input box.")
        print("   The script will capture the coordinates after the countdown.")

        for i in range(5, 0, -1):
            print(f"   Capturing in {i}...", end="\r", flush=True)
            time.sleep(1)
        print("   Capturing now!                       ")

        try:
            pos = pyautogui.position()
            coords_data[agent_id]["input_box_initial"] = {"x": pos.x, "y": pos.y}
            print(f"   Captured coordinates for {agent_id} input_box_initial: ({pos.x}, {pos.y})")
            
            # Save after each successful capture
            save_coords(coords_data) 
            
        except Exception as e:
            print(f"   Error capturing coordinates for {agent_id}: {e}")
            print("   Skipping this agent. You may need to re-run the script or manually edit the JSON.")
            continue # Continue to the next agent

    print("\nCalibration process complete!")
    print(f"All captured coordinates have been saved to {COORDS_FILE_PATH}")

if __name__ == "__main__":
    try:
        pyautogui.FAILSAFE = True # Enable failsafe
        main()
    except ImportError:
        print("Error: PyAutoGUI library is not installed. Please install it (pip install pyautogui) and try again.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}") 