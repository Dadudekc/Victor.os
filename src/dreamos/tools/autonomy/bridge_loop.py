"""
Dream.OS Agent Bridge Loop

This script automates the agent resume loop by:
1. Pasting the resume prompt into each agent's input box
2. Clicking the copy button to extract the agent's response
3. Reading from clipboard and routing the response to the chat bridge
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import pyautogui
import pyperclip
from rich.console import Console
from rich.logging import RichHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("bridge_loop")

# Constants
PROMPT = "Please analyze the current state of the Dream.OS system and provide a detailed status report."
COORDS_PATH = Path("runtime/config/cursor_agent_coords.json")
TARGET_AGENT = "Agent-3"  # Only target Agent-3
PASTE_DELAY = 2  # seconds to wait after pasting
COPY_DELAY = 1   # seconds to wait after clicking copy

console = Console()

def load_coordinates() -> Optional[Dict]:
    """Load agent coordinates from config file."""
    try:
        if not COORDS_PATH.exists():
            logger.error(f"❌ Coordinates file not found: {COORDS_PATH}")
            return None
        coords = json.loads(COORDS_PATH.read_text())
        logger.info(f"✅ Loaded coordinates for {len(coords)} agents")
        return coords
    except json.JSONDecodeError:
        logger.error("❌ Invalid JSON in coordinates file")
        return None
    except Exception as e:
        logger.error(f"❌ Error loading coordinates: {e}")
        return None

def route_response_to_chatgpt(agent_id: str, response: str) -> None:
    """Route the agent's response to ChatGPT bridge."""
    # TODO: Implement actual routing logic
    logger.info(f"[DRY-RUN] Would route response from {agent_id} to ChatGPT bridge")
    logger.debug(f"Response content: {response[:100]}...")

def main(dry_run: bool = False) -> int:
    """Main bridge loop execution."""
    console.print("[bold cyan]🚀 Starting Dream.OS Agent Bridge Loop[/bold cyan]")
    if dry_run:
        console.print("[bold yellow]⚠️ Dry-run mode: No clicks or clipboard operations[/bold yellow]")

    coords = load_coordinates()
    if not coords:
        return 1

    if TARGET_AGENT not in coords:
        logger.error(f"❌ Missing coordinates for {TARGET_AGENT}")
        return 1

    input_box = coords[TARGET_AGENT]["input_box"]
    copy_button = coords[TARGET_AGENT]["copy_button"]

    try:
        # Paste prompt
        if not dry_run:
            pyautogui.click(input_box["x"], input_box["y"])
            pyperclip.copy(PROMPT)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(PASTE_DELAY)
            pyautogui.press('enter')  # Press Enter to send the prompt
            logger.info(f"✅ Sent to {TARGET_AGENT} → {PROMPT}")
            time.sleep(PASTE_DELAY)  # Wait for response
        else:
            logger.info(f"[DRY-RUN] Would send to {TARGET_AGENT} → {PROMPT}")

        # Click copy button
        if not dry_run:
            pyautogui.click(copy_button["x"], copy_button["y"])
            logger.info(f"✅ Clicked copy button for {TARGET_AGENT}")
            time.sleep(COPY_DELAY)
        else:
            logger.info(f"[DRY-RUN] Would click copy button for {TARGET_AGENT}")

        # Get response from clipboard
        if not dry_run:
            response = pyperclip.paste()
            if response:
                route_response_to_chatgpt(TARGET_AGENT, response)
            else:
                logger.warning(f"⚠️ No response captured for {TARGET_AGENT}")
        else:
            logger.info(f"[DRY-RUN] Would route clipboard content for {TARGET_AGENT}")

    except Exception as e:
        logger.error(f"❌ Error processing {TARGET_AGENT}: {e}")
        return 1

    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dream.OS Agent Bridge Loop")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without performing them")
    args = parser.parse_args()
    sys.exit(main(dry_run=args.dry_run)) 