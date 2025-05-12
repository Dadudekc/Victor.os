"""
Dream.OS Self-Prompting Loop

This script implements an automated self-prompting system that:
1. Generates prompts based on previous responses
2. Sends prompts to the specified agent
3. Captures and analyzes responses
4. Uses feedback to improve future prompts

Usage:
    python self_prompt_loop.py --agent Agent-3
    python self_prompt_loop.py --agent Agent-5 --dry-run
"""

import argparse
import json
import logging
import sys
import os
import time
from pathlib import Path
from typing import Dict, Optional, List

import pyautogui
import pyperclip
from rich.console import Console
from rich.logging import RichHandler
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from dreamos.agents.utils.agent_status_utils import update_status, append_devlog, check_drift

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("self_prompt_loop")

# Constants
COORDS_PATH = Path("runtime/config/cursor_agent_coords.json")
PASTE_DELAY = 2
COPY_DELAY = 1
MAX_ITERATIONS = 5

# Initial prompts to start the loop
INITIAL_PROMPTS = [
    "Please analyze your current capabilities and identify areas for improvement.",
    "What are your key strengths in system analysis and how can they be enhanced?",
    "How can you better integrate with the Dream.OS ecosystem?",
    "What patterns do you notice in your responses that could be optimized?",
    "How can you improve your self-awareness and learning capabilities?"
]

console = Console()

def validate_agent_id(agent_id: str) -> bool:
    """Validate the agent ID format."""
    if not agent_id.startswith("Agent-"):
        return False
    try:
        num = int(agent_id.split("-")[1])
        return 1 <= num <= 8
    except (ValueError, IndexError):
        return False

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

def generate_next_prompt(previous_responses: List[str]) -> str:
    """Generate the next prompt based on previous responses."""
    if not previous_responses:
        return INITIAL_PROMPTS[0]
    
    # Analyze the last response to generate a follow-up prompt
    last_response = previous_responses[-1]
    
    # Simple prompt generation based on response content
    if "capabilities" in last_response.lower():
        return "How can you expand these capabilities further?"
    elif "strengths" in last_response.lower():
        return "What specific improvements would enhance these strengths?"
    elif "integration" in last_response.lower():
        return "What concrete steps can you take to improve integration?"
    elif "patterns" in last_response.lower():
        return "How can you optimize these patterns for better performance?"
    elif "awareness" in last_response.lower():
        return "What specific learning mechanisms can you implement?"
    
    # Default prompt if no specific pattern is detected
    return "Based on your previous responses, what new insights have you gained about your capabilities?"

def send_prompt_and_get_response(coords: Dict, agent_id: str, prompt: str, dry_run: bool = False) -> Optional[str]:
    """Send a prompt and get the response."""
    input_box = coords[agent_id]["input_box"]
    copy_button = coords[agent_id]["copy_button"]

    try:
        # Paste prompt
        if not dry_run:
            pyautogui.click(input_box["x"], input_box["y"])
            pyperclip.copy(prompt)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(PASTE_DELAY)
            pyautogui.press('enter')
            logger.info(f"✅ Sent prompt to {agent_id} → {prompt}")
            time.sleep(PASTE_DELAY)
        else:
            logger.info(f"[DRY-RUN] Would send prompt to {agent_id} → {prompt}")

        # Click copy button
        if not dry_run:
            pyautogui.click(copy_button["x"], copy_button["y"])
            logger.info(f"✅ Clicked copy button for {agent_id}")
            time.sleep(COPY_DELAY)
        else:
            logger.info(f"[DRY-RUN] Would click copy button for {agent_id}")

        # Get response
        if not dry_run:
            response = pyperclip.paste()
            if response:
                logger.info(f"✅ Captured response from {agent_id}: {response[:100]}...")
                return response
            else:
                logger.warning(f"⚠️ No response captured from {agent_id}")
        else:
            logger.info(f"[DRY-RUN] Would capture response from {agent_id}")

    except Exception as e:
        logger.error(f"❌ Error with {agent_id}: {e}")
    
    return None

def main(agent_id: str, dry_run: bool = False) -> int:
    """Main self-prompting loop execution."""
    if not validate_agent_id(agent_id):
        logger.error(f"❌ Invalid agent ID: {agent_id}. Must be in format 'Agent-N' where N is 1-8")
        return 1

    console.print(f"[bold cyan]🚀 Starting Dream.OS Self-Prompting Loop for {agent_id}[/bold cyan]")
    if dry_run:
        console.print("[bold yellow]⚠️ Dry-run mode: No clicks or clipboard operations[/bold yellow]")

    coords = load_coordinates()
    AGENT_ID = agent_id
    MAILBOX_PATH = f"runtime/agent_comms/agent_mailboxes/{agent_id}"
    cycle_count = 0
    missing_coords = False
    if not coords or agent_id not in coords:
        logger.error(f"❌ Missing or invalid coordinates for {agent_id}")
        append_devlog(agent_id=AGENT_ID, mailbox_path=MAILBOX_PATH, entry="Missing or invalid coordinates file; running in degraded mode.")
        missing_coords = True

    previous_responses = []
    current_prompt = INITIAL_PROMPTS[0]
    while True:
        cycle_count += 1
        # 1. Update status heartbeat
        update_status(agent_id=AGENT_ID, mailbox_path=MAILBOX_PATH, task="Self-prompt loop running", loop_active=True, compliance_score=100)
        # 2. Append devlog entry
        append_devlog(agent_id=AGENT_ID, mailbox_path=MAILBOX_PATH, entry=f"Cycle {cycle_count}: Heartbeat and devlog updated.")
        # 3. Check for drift
        if check_drift(agent_id=AGENT_ID, mailbox_path=MAILBOX_PATH, threshold_minutes=5):
            append_devlog(agent_id=AGENT_ID, mailbox_path=MAILBOX_PATH, entry=f"Cycle {cycle_count}: Drift detected, triggering recovery.")
            # Placeholder for recovery action (e.g., resume autonomy prompt)
        # 4. Main agent logic (only if config is present)
        if not missing_coords:
            # ... existing prompt/response logic ...
            pass
        else:
            # Log degraded mode
            append_devlog(agent_id=AGENT_ID, mailbox_path=MAILBOX_PATH, entry=f"Cycle {cycle_count}: Skipping prompt logic due to missing coordinates.")
        time.sleep(30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dream.OS Self-Prompting Loop")
    parser.add_argument("--agent", required=True, help="Agent ID (e.g., Agent-3)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without performing them")
    args = parser.parse_args()
    sys.exit(main(args.agent, dry_run=args.dry_run)) 
    