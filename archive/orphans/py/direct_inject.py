#!/usr/bin/env python
"""
Direct Prompt Injection Tool for Dream.OS

This script directly injects prompts to agents by:
1. Reading the prepared onboarding prompts
2. Finding the Cursor window
3. Clicking on each agent's input box using stored coordinates
4. Pasting the prompt content

Usage:
    python direct_inject.py
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
logger = logging.getLogger("direct_injector")

# Constants
AGENT_COUNT = 8
MAILBOX_BASE = Path("runtime/agent_comms/agent_mailboxes")
COORDS_PATH = Path("runtime/config/cursor_agent_coords.json")
WINDOW_TITLE = "Cursor"
PASTE_DELAY = 1.0  # seconds between operations
RESUME_PROMPT = "RESUME AUTONOMY"  # Simple prompt if no onboarding prompt exists

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

def get_latest_prompt(agent_id):
    """Get the latest onboarding prompt for an agent."""
    inbox_dir = MAILBOX_BASE / agent_id / "inbox"
    
    # Find all onboarding prompt files
    prompt_files = list(inbox_dir.glob("onboarding_prompt_*.md"))
    
    if not prompt_files:
        # Check for the base onboarding prompt
        base_prompt = inbox_dir / "onboarding_prompt.md"
        if base_prompt.exists():
            return base_prompt.read_text(encoding="utf-8")
        else:
            logger.warning(f"No onboarding prompt found for {agent_id}")
            return RESUME_PROMPT
    
    # Sort by timestamp (newest first)
    latest_prompt = max(prompt_files, key=lambda p: p.stat().st_mtime)
    return latest_prompt.read_text(encoding="utf-8")

def send_prompt_to_agent(agent_id, coords, prompt_text=None):
    """Send a prompt to an agent."""
    if agent_id not in coords:
        logger.error(f"No coordinates found for {agent_id}")
        return False
    
    # Get the prompt text
    if prompt_text is None:
        prompt_text = get_latest_prompt(agent_id)
    
    # Use a simplified prompt if it's too long
    if len(prompt_text) > 500:  # Arbitrary limit to avoid pasting huge texts
        logger.info(f"Prompt for {agent_id} is too long, using simplified version")
        prompt_text = f"{RESUME_PROMPT}\n\nCheck your inbox for the full onboarding prompt."
    
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
        
        logger.info(f"✓ Sent prompt to {agent_id}")
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
    logger.info("Starting direct prompt injection...")
    
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
        logger.info(f"Sending prompt to {agent_id}...")
        
        if send_prompt_to_agent(agent_id, coords):
            success_count += 1
        
        # Wait before next agent
        time.sleep(PASTE_DELAY)
    
    logger.info(f"Successfully sent prompts to {success_count}/{AGENT_COUNT} agents")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 