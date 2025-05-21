#!/usr/bin/env python3
"""
Cursor Window Coordinate Finder

This tool helps map the exact positions of Cursor windows for the overnight runner.
It will:
1. Show your current mouse position
2. Let you click to capture coordinates
3. Save them to the coordinates file

Usage:
1. Run this script
2. Move your mouse to the input box of each Cursor window
3. Press 'i' to capture input box coordinates
4. Move to the copy button (if present) and press 'c' to capture copy button coordinates
5. Press 'q' to quit and save
"""

import json
import keyboard
import pyautogui
import time
from pathlib import Path

# Get project root and config path
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
COORDS_FILE = PROJECT_ROOT / "runtime/config/cursor_agent_coords.json"

# Initialize coordinates dictionary
coords = {}
current_agent = None

def load_existing_coords():
    """Load existing coordinates if file exists"""
    if COORDS_FILE.exists():
        with open(COORDS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_coords():
    """Save coordinates to file"""
    COORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(COORDS_FILE, 'w') as f:
        json.dump(coords, f, indent=4)
    print(f"\nCoordinates saved to {COORDS_FILE}")

def capture_input_box():
    """Capture input box coordinates for current agent"""
    if not current_agent:
        print("Please select an agent first (1-8)")
        return
    
    x, y = pyautogui.position()
    if current_agent not in coords:
        coords[current_agent] = {}
    
    coords[current_agent]["input_box"] = {"x": x, "y": y}
    coords[current_agent]["input_box_initial"] = {"x": x, "y": y}
    print(f"Captured input box coordinates for {current_agent}: ({x}, {y})")

def capture_copy_button():
    """Capture copy button coordinates for current agent"""
    if not current_agent:
        print("Please select an agent first (1-8)")
        return
    
    x, y = pyautogui.position()
    if current_agent not in coords:
        coords[current_agent] = {}
    
    coords[current_agent]["copy_button"] = {"x": x, "y": y}
    print(f"Captured copy button coordinates for {current_agent}: ({x}, {y})")

def select_agent(agent_num):
    """Select an agent to map"""
    global current_agent
    current_agent = f"Agent-{agent_num}"
    print(f"\nSelected {current_agent}")
    print("Move mouse to input box and press 'i'")
    print("Move mouse to copy button and press 'c'")
    print("Press 'q' to quit and save")

def main():
    global coords
    coords = load_existing_coords()
    
    print("Cursor Window Coordinate Finder")
    print("==============================")
    print("1. Select an agent (1-8)")
    print("2. Move mouse to input box and press 'i'")
    print("3. Move mouse to copy button and press 'c'")
    print("4. Press 'q' to quit and save")
    print("\nCurrent mouse position will be shown below:")
    
    # Register hotkeys
    for i in range(1, 9):
        keyboard.add_hotkey(str(i), lambda x=i: select_agent(x))
    keyboard.add_hotkey('i', capture_input_box)
    keyboard.add_hotkey('c', capture_copy_button)
    keyboard.add_hotkey('q', lambda: (save_coords(), exit()))
    
    try:
        while True:
            x, y = pyautogui.position()
            print(f"\rMouse position: ({x}, {y})", end='')
            time.sleep(0.1)
    except KeyboardInterrupt:
        save_coords()

if __name__ == "__main__":
    main() 