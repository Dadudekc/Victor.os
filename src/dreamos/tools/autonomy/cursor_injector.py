"""
Cursor Injector for Dream.OS Agents

This script injects prompts into Cursor and copies agent responses.
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
logger = logging.getLogger("cursor_injector")

# Constants
PROMPT = "RESUME AUTONOMY"
COORDS_PATH = Path("runtime/config/cursor_agent_coords.json")
AGENTS = [f"Agent-{i}" for i in range(1, 9)]
PASTE_DELAY = 0.5
COPY_DELAY = 0.5

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

def route_response_to_chatgpt(response: str) -> None:
    """Route the agent's response to the chat bridge (placeholder)."""
    logger.info(f"Routing response: {response[:50]}...")

def main(dry_run: bool = False) -> int:
    """Main execution loop."""
    console.print("[bold cyan]🚀 Starting Cursor Injector[/bold cyan]")
    if dry_run:
        console.print("[bold yellow]⚠️ Dry-run mode: No clicks or clipboard operations[/bold yellow]")

    coords = load_coordinates()
    if not coords:
        return 1

    for agent_id in AGENTS:
        if agent_id not in coords:
            logger.error(f"❌ Missing coordinates for {agent_id}")
            continue

        input_box = coords[agent_id]["input_box"]
        copy_button = coords[agent_id]["copy_button"]

        # Paste prompt
        if not dry_run:
            pyautogui.click(input_box["x"], input_box["y"])
            time.sleep(PASTE_DELAY)
            pyautogui.typewrite(PROMPT)
            time.sleep(PASTE_DELAY)
            pyautogui.press("enter")
        logger.info(f"✅ Sent to {agent_id} → {PROMPT}")

        # Click copy button
        if not dry_run:
            pyautogui.click(copy_button["x"], copy_button["y"])
            time.sleep(COPY_DELAY)
        logger.info(f"✅ Clicked copy button for {agent_id}")

        # Read clipboard
        if not dry_run:
            response = pyperclip.paste()
            route_response_to_chatgpt(response)
        else:
            logger.info(f"[DRY-RUN] Would route clipboard content for {agent_id}")

    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cursor Injector for Dream.OS Agents")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without clicking or clipboard operations")
    args = parser.parse_args()
    sys.exit(main(dry_run=args.dry_run)) 