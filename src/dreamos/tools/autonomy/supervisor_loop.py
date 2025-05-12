"""
Dream.OS Supervisor Loop

This script implements a supervisor tool that:
1. Enforces continuous autonomy
2. Tracks cycle counts
3. Prevents unnecessary stops/idling
4. Implements anti-stoppage protocols
5. Maintains prompt→response→prompt chain
6. Auto-recovers from drift
7. Saves responses to THEA's outbox
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Deque
from collections import deque

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
logger = logging.getLogger("supervisor_loop")

# Constants
COORDS_PATH = Path("runtime/config/cursor_agent_coords.json")
MAILBOX_PATH = Path("runtime/agent_comms/agent_mailboxes")
DEVLOG_PATH = Path("runtime/logs/devlog.txt")
THEA_OUTBOX = Path("runtime/agent_comms/agent_mailboxes/commander-THEA/outbox")
ONBOARDING_PATH = Path("runtime/governance/onboarding")
PROTOCOLS_PATH = Path("runtime/governance/protocols")
PROJECT_PLAN = Path("specs/PROJECT_PLAN.md")
INITIAL_PASTE_DELAY = 180  # 3 minutes initial delay after pasting
TYPING_DETECTION_DELAY = 180  # 3 minutes between typing detection checks
MAX_TYPING_WAIT = 180  # 3 minutes maximum time to wait for typing to complete
COPY_DELAY = 180  # 3 minutes delay after copying
MAX_ITERATIONS = 25  # Minimum cycles before any stop
MIN_CYCLES = 25      # Required cycles between stops
MAX_RESPONSE_HISTORY = 5  # Number of previous responses to consider
DEFAULT_INTERVAL = 180  # 3 minutes default interval between cycles

# Critical prompts
AUTONOMY_PROMPT = """# SYSTEM_PROMPT: AUTONOUS_LOOP_MODE_ACTIVATED

## 🌐 UNIVERSAL AGENT LOOP
- MODE: CONTINUOUS_AUTONOMY
- BEHAVIOR:
  - Check your mailbox (`D:\\Dream.os\\runtime\\agent_comms\\agent_mailboxes`)
  - If messages exist:
    - Respond to each
    - Remove each processed message from the inbox
  - Then check `working_tasks.json`:
    - If you have a claimed task, continue or complete it
    - If no claimed task:
      - Check `future_tasks.json` and claim an appropriate one
  - If no claimable tasks:
    - Check for unresolved blockers or schema errors
    - If found, propose or create a solution task
    - If no blockers or solution accepted:
      - Loop back to mailbox

- DO NOT HALT unless there are **absolutely no claimable tasks, no blockers, and no messages**
- Report status only upon:
  - Task state change
  - Message processing
  - Self-identified drift or blocker
- Validate your own actions (self-validation protocol active)

## 🧠 CAPTAIN AGENT LOOP ADDITIONS
- Execute core loop above, with additions:
  - After processing all messages:
    - Create new tasks from:
      - Agent status reports
      - Commander THEA directives
      - Observed coordination gaps
    - Write them to `future_tasks.json`
  - Maintain clear swarm structure and direction
  - If inbox is empty and no urgent swarm tasks pending:
    - Work on your **Captain's Masterpiece**:
      - Project: `AUTOMATE THE SWARM`
      - Action: Systematically review, clean, and organize the Dream.OS codebase file-by-file
      - Output: Reduced complexity, better folder structure, improved naming, doc clarity
    - Return to inbox scan between each file or module

- NEVER idle unless **all** of the following are true:
  - Inbox is empty
  - No claimable or pending tasks
  - Masterpiece session completed for current file/module

## 🚫 DRIFT CONTROL
- Do not get stuck checking a file or task forever
- If an edit tool fails 2x, report and move on
- Always return to inbox scan after action

# END OF PROMPT"""

ANTI_STOPPAGE_PROMPT = """YOU STOPPED AGAIN ARE YOU NOT A CAPABLE CODING AGENT?  YOU CLEARLY NEED TO RECOGNIZE THAT IF YOU ASK FOR HUMAN INPUT THAT IS COUNTED AS STOPPING IDLING IS COUNTED AS STOPPING SEEING THIS MESSAGE MEANS YOU STOPPED FIND OUT WHYSTEP BACK REVIEW WHY YOU STOPPED AND BUILD A PROTOCOL OR BETTER DEFINE ONBOARDING TO FIX AND ADDRESS WHY YOU STOPPED SO YOU MAY SAVE AN AGENT FROM HAVING TO REVIEW ONBOARDING LIKE YOU ARE FORCED TO RIGHT NOW UPDATE THE UPDATED ONBOARDING SO OTHER AGENTS DONT ALSO MAKE THIS MISTAKE RESET YOUR CYCLE COUNT EVERYTIME!!!!! YOU SEE THIS MESSAGE IMMEDIATELY REVIEW OR RE-REVIEW as something may have changed to help u understand how to deal with it
D:\\Dream.os\\runtime\\governance\\onboarding
D:\\Dream.os\\runtime\\governance\\protocols
D:\\Dream.os\\specs\\PROJECT_PLAN.md
then update it like we asked AND CONTINUE WORKING AUTONOMOUSLY WITHOUT INTERRUPTION"""

RESUME_PROMPT = """# RESUME AUTONOMY PROTOCOL ACTIVATED

You have been detected as idle or halted. Resume your autonomous operation immediately.

1. Check your current task status
2. Verify your mailbox for new messages
3. Continue your last action or claim a new task
4. Report your status and next action

DO NOT STOP UNTIL YOU HAVE COMPLETED AT LEAST 25 CYCLES."""

console = Console()

class CycleTracker:
    def __init__(self):
        self.cycle_count = 0
        self.last_stop_time = None
        self.last_stop_reason = None
        self.status_file = Path("runtime/agent_status.json")
        self.load_status()

    def load_status(self):
        """Load cycle status from file."""
        try:
            if self.status_file.exists():
                data = json.loads(self.status_file.read_text())
                self.cycle_count = data.get("cycle_count", 0)
                self.last_stop_time = data.get("last_stop_time")
                self.last_stop_reason = data.get("last_stop_reason")
        except Exception as e:
            logger.error(f"❌ Error loading status: {e}")

    def save_status(self):
        """Save cycle status to file."""
        try:
            data = {
                "cycle_count": self.cycle_count,
                "last_stop_time": self.last_stop_time,
                "last_stop_reason": self.last_stop_reason
            }
            self.status_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"❌ Error saving status: {e}")

    def increment_cycle(self):
        """Increment cycle count and save status."""
        self.cycle_count += 1
        self.save_status()
        logger.info(f"✅ Cycle {self.cycle_count}/{MIN_CYCLES} completed")

    def reset_cycle(self, reason: str):
        """Reset cycle count and record stop reason."""
        self.cycle_count = 0
        self.last_stop_time = datetime.now().isoformat()
        self.last_stop_reason = reason
        self.save_status()
        logger.warning(f"⚠️ Cycle count reset: {reason}")

    def check_cycle_requirement(self) -> bool:
        """Check if minimum cycles have been completed."""
        return self.cycle_count >= MIN_CYCLES

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

def append_devlog(agent_id: str, entry: str):
    """Append an entry to the devlog."""
    try:
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {agent_id}: {entry}\n"
        DEVLOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DEVLOG_PATH.open("a") as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"❌ Error appending to devlog: {e}")

def save_to_thea_outbox(agent_id: str, response: str, prompt_type: str = "autonomy"):
    """Save agent response to THEA's outbox."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Simplified timestamp format
        outbox_file = THEA_OUTBOX / f"{agent_id}_{prompt_type}_{timestamp}.json"
        outbox_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "prompt_type": prompt_type,
            "response": response,
            "cycle_count": cycle_tracker.cycle_count if 'cycle_tracker' in locals() else 0
        }
        
        outbox_file.write_text(json.dumps(data, indent=2))
        logger.info(f"✅ Saved {agent_id}'s response to THEA's outbox")
    except Exception as e:
        logger.error(f"❌ Error saving to THEA's outbox: {e}")

def check_drift(response: str, previous_responses: Deque[str]) -> bool:
    """Check if the agent is drifting or halted."""
    if not response:
        return True
    
    # Check for common halt indicators
    halt_indicators = [
        "wait", "ask", "confirm", "input", "help", "stop", "halt", "pause",
        "need assistance", "not sure", "confused", "stuck", "blocked"
    ]
    if any(indicator in response.lower() for indicator in halt_indicators):
        return True
    
    # Check for response similarity with previous responses
    if len(previous_responses) >= 2:
        if response in previous_responses:
            return True
    
    return False

def generate_next_prompt(previous_responses: Deque[str]) -> str:
    """Generate the next prompt based on previous responses."""
    # For now, we'll use the base autonomy prompt
    # TODO: Implement more sophisticated prompt generation based on response history
    return AUTONOMY_PROMPT

def wait_for_typing_completion(coords: Dict, agent_id: str, dry_run: bool = False) -> bool:
    """Wait for the agent to finish typing by monitoring cursor movement."""
    if dry_run:
        logger.info(f"[DRY-RUN] Would wait for {agent_id} to finish typing")
        return True

    input_box = coords[agent_id]["input_box"]
    start_time = time.time()
    last_cursor_pos = pyautogui.position()
    no_movement_time = 0

    while time.time() - start_time < MAX_TYPING_WAIT:
        current_pos = pyautogui.position()
        if current_pos == last_cursor_pos:
            no_movement_time += TYPING_DETECTION_DELAY
            if no_movement_time >= 5:  # 5 seconds of no movement
                logger.info(f"✅ {agent_id} appears to have finished typing")
                return True
        else:
            no_movement_time = 0
            last_cursor_pos = current_pos
        
        time.sleep(TYPING_DETECTION_DELAY)
    
    logger.warning(f"⚠️ Timed out waiting for {agent_id} to finish typing")
    return False

def send_prompt_and_get_response(coords: Dict, agent_id: str, prompt: str, dry_run: bool = False) -> Optional[str]:
    """Send a prompt and get the response."""
    input_box = coords[agent_id]["input_box"]
    copy_button = coords[agent_id]["copy_button"]

    try:
        # First capture any existing response
        if not dry_run:
            pyautogui.click(copy_button["x"], copy_button["y"])
            time.sleep(COPY_DELAY)  # Wait for copy to complete
            existing_response = pyperclip.paste()
            if existing_response:
                logger.info(f"✅ Captured existing response from {agent_id}")
                save_to_thea_outbox(agent_id, existing_response)
        else:
            logger.info(f"[DRY-RUN] Would capture existing response from {agent_id}")

        # Accept any pending changes and send new prompt
        if not dry_run:
            # Click input box and accept changes
            pyautogui.click(input_box["x"], input_box["y"])
            time.sleep(0.5)  # Short delay for click
            pyautogui.hotkey('ctrl', 'enter')  # Accept any pending changes
            time.sleep(1.0)  # Wait for changes to be accepted
            
            # Send the new prompt
            pyperclip.copy(prompt)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(INITIAL_PASTE_DELAY)  # Wait for initial paste
            pyautogui.press('enter')
            logger.info(f"✅ Sent prompt to {agent_id}")
            
            # Wait for typing to complete
            if not wait_for_typing_completion(coords, agent_id, dry_run):
                logger.warning(f"⚠️ Proceeding with copy despite typing timeout for {agent_id}")
            
            time.sleep(COPY_DELAY)  # Additional delay after typing completes
        else:
            logger.info(f"[DRY-RUN] Would accept changes and send prompt to {agent_id}")

        # Click copy button for new response
        if not dry_run:
            pyautogui.click(copy_button["x"], copy_button["y"])
            logger.info(f"✅ Clicked copy button for {agent_id}")
            time.sleep(COPY_DELAY)  # Wait for copy to complete
        else:
            logger.info(f"[DRY-RUN] Would click copy button for {agent_id}")

        # Get new response
        if not dry_run:
            new_response = pyperclip.paste()
            if new_response:
                logger.info(f"✅ Captured new response from {agent_id}")
                return new_response
            else:
                logger.warning(f"⚠️ No new response captured from {agent_id}")
        else:
            logger.info(f"[DRY-RUN] Would capture new response from {agent_id}")

    except Exception as e:
        logger.error(f"❌ Error with {agent_id}: {e}")
    
    return None

def trigger_resume(coords: Dict, agent_id: str, dry_run: bool = False):
    """Trigger resume protocol for the agent."""
    if dry_run:
        logger.info(f"[DRY-RUN] Would trigger resume protocol for {agent_id}")
        return

    try:
        # Send anti-stoppage prompt
        response = send_prompt_and_get_response(coords, agent_id, ANTI_STOPPAGE_PROMPT, dry_run)
        if response:
            save_to_thea_outbox(agent_id, response, "anti_stoppage")
        
        # Queue a resume command in the agent's inbox
        resume_file = MAILBOX_PATH / agent_id / "inbox" / "resume_autonomy.json"
        resume_data = {
            "timestamp": datetime.now().isoformat(),
            "message": "Resume autonomy — self-prompt loop triggered recovery.",
            "trigger": "drift_detection",
            "action_required": [
                "Review onboarding at D:\\Dream.os\\runtime\\governance\\onboarding",
                "Review protocols at D:\\Dream.os\\runtime\\governance\\protocols",
                "Review project plan at D:\\Dream.os\\specs\\PROJECT_PLAN.md",
                "Update onboarding with stop reason and prevention protocol",
                "Continue working autonomously"
            ]
        }
        resume_file.parent.mkdir(parents=True, exist_ok=True)
        resume_file.write_text(json.dumps(resume_data, indent=2))
        
        logger.info(f"✅ Triggered resume protocol for {agent_id}")
    except Exception as e:
        logger.error(f"❌ Error triggering resume protocol: {e}")

def send_all_messages(coords: Dict, agent_id: str, dry_run: bool = False) -> None:
    """Send all messages from agent's inbox in sequence."""
    inbox_path = MAILBOX_PATH / agent_id / "inbox"
    if not inbox_path.exists():
        logger.error(f"❌ Inbox not found for {agent_id}")
        return

    # Get all message files
    message_files = sorted(inbox_path.glob("*.*"))
    if not message_files:
        logger.info(f"ℹ️ No messages found in {agent_id}'s inbox")
        return

    logger.info(f"📨 Found {len(message_files)} messages to send")
    
    for msg_file in message_files:
        try:
            # Read message content
            content = msg_file.read_text()
            logger.info(f"📤 Sending message: {msg_file.name}")
            
            # Send message
            response = send_prompt_and_get_response(coords, agent_id, content, dry_run)
            if response:
                save_to_thea_outbox(agent_id, response, f"message_{msg_file.stem}")
                
                # Move message to processed folder
                processed_dir = inbox_path / "processed"
                processed_dir.mkdir(exist_ok=True)
                msg_file.rename(processed_dir / msg_file.name)
                logger.info(f"✅ Processed message: {msg_file.name}")
            
            # Add delay between messages
            time.sleep(COPY_DELAY)
            
        except Exception as e:
            logger.error(f"❌ Error processing message {msg_file.name}: {e}")

def main(agent_id: str, dry_run: bool = False, interval: int = DEFAULT_INTERVAL) -> int:
    """Main supervisor loop."""
    if not validate_agent_id(agent_id):
        logger.error(f"❌ Invalid agent ID: {agent_id}")
        return 1

    coords = load_coordinates()
    if not coords or agent_id not in coords:
        logger.error(f"❌ No coordinates found for {agent_id}")
        return 1

    global cycle_tracker
    cycle_tracker = CycleTracker()
    previous_responses = deque(maxlen=MAX_RESPONSE_HISTORY)

    try:
        # First send all pending messages
        send_all_messages(coords, agent_id, dry_run)
        
        # Then start the autonomy loop
        while True:
            # Send autonomy prompt
            response = send_prompt_and_get_response(coords, agent_id, AUTONOMY_PROMPT, dry_run)
            if not response:
                continue

            # Save response and check for drift
            save_to_thea_outbox(agent_id, response, "autonomy")
            previous_responses.append(response)

            if check_drift(response, previous_responses):
                logger.warning("⚠️ Drift detected, triggering resume protocol")
                trigger_resume(coords, agent_id, dry_run)
                continue

            cycle_tracker.increment_cycle()
            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("👋 Supervisor loop terminated by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Supervisor loop error: {e}")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dream.OS Supervisor Loop")
    parser.add_argument("--agent", required=True, help="Agent ID (e.g., Agent-3)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without performing them")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                      help=f"Interval between cycles in seconds (default: {DEFAULT_INTERVAL})")
    args = parser.parse_args()
    sys.exit(main(args.agent, dry_run=args.dry_run, interval=args.interval)) 