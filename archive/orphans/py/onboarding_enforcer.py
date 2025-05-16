"""
Dream.OS Onboarding Enforcer

Enforces onboarding for all agents by:
1. Copying any pending response from the copy button
2. If a response exists, save to THEA's outbox and trigger resume prompt
3. If not, send onboarding protocol message
4. Waits between agents to reduce overload
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pyautogui
import pyperclip
from rich.console import Console
from rich.logging import RichHandler

# Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("onboarding_enforcer")
console = Console()

# Paths
COORDS_PATH = Path("runtime/config/cursor_agent_coords.json")
MAILBOX_PATH = Path("runtime/agent_comms/agent_mailboxes")
THEA_OUTBOX = Path("runtime/agent_comms/agent_mailboxes/commander-THEA/outbox")
ONBOARDING_PATH = Path("runtime/governance/onboarding")
PROTOCOLS_PATH = Path("runtime/governance/protocols")
PROJECT_PLAN = Path("specs/PROJECT_PLAN.md")

# Timings
COPY_WAIT = 1.5  # Time to wait after clicking copy
PASTE_WAIT = 1.0  # Time to wait after paste before reading
AGENT_DELAY = 8  # Delay between agents
MESSAGE_DELAY = 1.5  # Time to allow UI input buffer to settle


def load_coordinates() -> Optional[Dict]:
    try:
        if not COORDS_PATH.exists():
            logger.error(f"❌ Missing coordinates: {COORDS_PATH}")
            return None
        return json.loads(COORDS_PATH.read_text())
    except Exception as e:
        logger.error(f"❌ Failed to load coordinates: {e}")
        return None


def save_to_thea_outbox(
    agent_id: str, response: str, tag: str = "pending_onboarding"
) -> None:
    try:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_path = THEA_OUTBOX / f"{agent_id}_{tag}_{timestamp}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_id": agent_id,
                    "tag": tag,
                    "response": response,
                },
                indent=2,
            )
        )
        logger.info(f"📦 Saved response from {agent_id} to THEA's outbox")
    except Exception as e:
        logger.error(f"❌ Failed to save to THEA outbox: {e}")


def create_onboarding_prompt(agent_id: str) -> str:
    return f"""# 🧠 ONBOARDING PROTOCOL ACTIVE ({agent_id})

Welcome to Dream.OS. Review your responsibilities:

📘 Review these docs:
- {ONBOARDING_PATH}
- {PROTOCOLS_PATH}
- {PROJECT_PLAN}

🎯 Responsibilities:
- Maintain continuous operation
- Log every action to your devlog
- Validate all improvements
- Do not stop unless protocol allows

✅ Begin task execution and stay in loop.

# END OF PROMPT"""


def send_prompt(agent_id: str, coords: Dict, msg: str, dry_run: bool) -> None:
    if agent_id not in coords:
        logger.warning(f"⚠️ Missing coords for {agent_id}")
        return
    try:
        input_box = coords[agent_id]["input_box"]
        if not dry_run:
            pyautogui.click(input_box["x"], input_box["y"])
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "enter")  # Clear input
            time.sleep(MESSAGE_DELAY)
            pyperclip.copy(msg)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(PASTE_WAIT)
            pyautogui.press("enter")
            logger.info(f"📤 Sent prompt to {agent_id}")
        else:
            logger.info(f"[DRY-RUN] Would send to {agent_id}: {msg[:60]}...")
    except Exception as e:
        logger.error(f"❌ Failed to send to {agent_id}: {e}")


def copy_response(agent_id: str, coords: Dict, dry_run: bool) -> Optional[str]:
    try:
        copy_button = coords[agent_id]["copy_button"]
        if not dry_run:
            pyautogui.click(copy_button["x"], copy_button["y"])
            time.sleep(COPY_WAIT)
            return pyperclip.paste().strip()
        else:
            logger.info(f"[DRY-RUN] Would copy response from {agent_id}")
            return f"[Simulated response from {agent_id}]"
    except Exception as e:
        logger.error(f"❌ Failed to copy from {agent_id}: {e}")
        return None


def enforce_onboarding(agent_ids: List[str], dry_run: bool = False) -> int:
    coords = load_coordinates()
    if not coords:
        return 1
    targets = agent_ids or list(coords.keys())
    logger.info(f"🚀 Enforcing onboarding for {len(targets)} agents")

    for agent_id in targets:
        console.rule(f"[bold cyan]🔁 {agent_id} Onboarding Cycle")
        response = copy_response(agent_id, coords, dry_run)
        if response:
            save_to_thea_outbox(agent_id, response)
            send_prompt(
                agent_id,
                coords,
                "Resume autonomy — self-prompt loop triggered.",
                dry_run,
            )
        else:
            onboarding_msg = create_onboarding_prompt(agent_id)
            send_prompt(agent_id, coords, onboarding_msg, dry_run)
        logger.info(f"⏳ Waiting {AGENT_DELAY}s before next agent...\n")
        time.sleep(AGENT_DELAY)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dream.OS Onboarding Enforcer")
    parser.add_argument(
        "--agents",
        nargs="*",
        help="Agent IDs (e.g., Agent-1 Agent-2). Defaults to all agents.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate without clicking/pasting"
    )
    args = parser.parse_args()
    sys.exit(enforce_onboarding(args.agents, dry_run=args.dry_run))
