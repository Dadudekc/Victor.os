#!/usr/bin/env python
"""
Direct Inbox Prompt Tool for Dream.OS

This script directly sends a prompt to agents via GUI automation
telling them to check their inbox and implement the loop protocol.

Usage:
    python direct_inbox_prompt.py
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import pyautogui
    import pygetwindow as gw
except ImportError:
    print("Required packages not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui", "pygetwindow"])
    import pyautogui
    import pygetwindow as gw

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("direct_inbox_prompt")

# Constants
AGENT_COUNT = 8
COORDS_PATH = Path("runtime/config/cursor_agent_coords.json")
WINDOW_TITLE = "Cursor"
PASTE_DELAY = 1.0  # seconds between operations

# The direct prompt to send to agents
DIRECT_PROMPT = """CHECK YOUR INBOX NOW at runtime/agent_comms/agent_mailboxes/Agent-{AGENT_ID}/inbox/ and implement the inbox checking loop protocol."""

def get_window_bounds():
    """Get the bounds of the Cursor window."""
    try:
        win = gw.getWindowsWithTitle(WINDOW_TITLE)
        if not win:
            logger.error(f"No window found with title: {WINDOW_TITLE}")
            return None
        window = win[0]
        return (window.left, window.top, window.width, window.height)
    except Exception as e:
        logger.error(f"Error getting window bounds: {e}")
        return None

def load_coordinates():
    """Load agent coordinates from config file."""
    try:
        if not COORDS_PATH.exists():
            logger.error(f"Coordinates file not found: {COORDS_PATH}")
            return None
            
        coords = json.loads(COORDS_PATH.read_text())
        logger.info(f"Loaded coordinates for {len(coords)} agents")
        return coords
    except json.JSONDecodeError:
        logger.error("Invalid JSON in coordinates file")
        return None
    except Exception as e:
        logger.error(f"Error loading coordinates: {e}")
        return None

def focus_cursor_window():
    """Focus the Cursor window."""
    try:
        win = gw.getWindowsWithTitle(WINDOW_TITLE)
        if not win:
            logger.error(f"No window found with title: {WINDOW_TITLE}")
            return False
        win[0].activate()
        time.sleep(0.5)
        logger.info("Cursor window focused")
        return True
    except Exception as e:
        logger.error(f"Error focusing window: {e}")
        return False

def send_prompt_to_agent(agent_id, coords):
    """Send the inbox checking prompt to an agent."""
    if agent_id not in coords:
        logger.error(f"No coordinates found for {agent_id}")
        return False
    
    # Create personalized prompt with agent ID
    prompt_text = DIRECT_PROMPT.replace("{AGENT_ID}", str(agent_id.split('-')[1]))
    
    try:
        # Get agent coordinates
        box = coords[agent_id]["input_box"]
        x, y = box["x"], box["y"]
        
        # Get window bounds
        window_bounds = get_window_bounds()
        if not window_bounds:
            return False
            
        left, top, width, height = window_bounds
        
        # Click on the input box
        pyautogui.click(left + x, top + y)
        time.sleep(0.25)
        
        # Type the prompt
        pyautogui.write(prompt_text)
        time.sleep(0.1)
        pyautogui.press("enter")
        
        logger.info(f"✓ Sent inbox prompt to {agent_id}")
        return True
    except Exception as e:
        logger.error(f"Error sending prompt to {agent_id}: {e}")
        return False

def setup_coordinates():
    """Set up coordinates for each agent."""
    logger.info("Starting coordinate setup...")
    
    # Get window bounds
    window_bounds = get_window_bounds()
    if not window_bounds:
        return None
        
    left, top, width, height = window_bounds
    logger.info(f"Cursor window bounds: left={left}, top={top}, width={width}, height={height}")
    
    # Prompt user to click each agent's input box
    coords = {}
    for i in range(1, AGENT_COUNT + 1):
        agent_id = f"Agent-{i}"
        logger.info(f"Please click the input box for {agent_id}...")
        
        # Wait for user to position mouse
        input(f"Position mouse over {agent_id}'s input box and press Enter...")
        
        # Get current mouse position
        x, y = pyautogui.position()
        
        # Store coordinates relative to window
        coords[agent_id] = {
            "input_box": {
                "x": x - left,  # Make relative to window
                "y": y - top
            }
        }
        logger.info(f"Recorded coordinates for {agent_id}: ({x-left}, {y-top})")
    
    # Save coordinates
    COORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    COORDS_PATH.write_text(json.dumps(coords, indent=4))
    logger.info(f"✅ Saved coordinates to {COORDS_PATH}")
    
    return coords

def main():
    """Main execution function."""
    logger.info("Starting direct inbox prompt injection...")
    
    # Focus Cursor window
    if not focus_cursor_window():
        logger.error("Failed to focus Cursor window")
        return 1
    
    # Load coordinates
    coords = load_coordinates()
    if not coords:
        logger.warning("No valid coordinates found. Setting up now...")
        coords = setup_coordinates()
        if not coords:
            logger.error("Failed to set up coordinates")
            return 1
    
    # Send prompts to each agent
    success_count = 0
    for i in range(1, AGENT_COUNT + 1):
        agent_id = f"Agent-{i}"
        logger.info(f"Sending inbox prompt to {agent_id}...")
        
        if send_prompt_to_agent(agent_id, coords):
            success_count += 1
        
        # Wait before next agent
        time.sleep(PASTE_DELAY)
    
    logger.info(f"Successfully sent inbox prompts to {success_count}/{AGENT_COUNT} agents")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 