"""
Dream.OS Agent Startup System

Integrates pyautogui with the onboarding system to:
1. Send startup messages to each agent
2. Initialize their mailboxes
3. Trigger the onboarding protocol
"""

import json
import logging
import time
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
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("agent_startup")
console = Console()

# Paths
COORDS_PATH = Path("runtime/config/cursor_agent_coords.json")
ONBOARDING_PATH = Path("runtime/onboarding")
MAILBOX_PATH = Path("runtime/agent_comms/agent_mailboxes")

# Timings
INITIAL_DELAY = 1.5  # Time to wait after initial click
PASTE_DELAY = 0.5    # Time to wait after paste
AGENT_DELAY = 8      # Delay between agents

def load_coordinates() -> Optional[Dict]:
    """Load agent coordinates from config file."""
    try:
        if not COORDS_PATH.exists():
            logger.error(f"❌ Coordinates file not found: {COORDS_PATH}")
            return None
        coords = json.loads(COORDS_PATH.read_text())
        logger.info(f"✅ Loaded coordinates for {len(coords)} agents")
        return coords
    except Exception as e:
        logger.error(f"❌ Error loading coordinates: {e}")
        return None

def initialize_mailbox(agent_id: str) -> bool:
    """Initialize an agent's mailbox structure."""
    try:
        agent_mailbox = MAILBOX_PATH / f"agent-{agent_id}"
        for dir_name in ["inbox", "outbox", "processed", "state"]:
            (agent_mailbox / dir_name).mkdir(parents=True, exist_ok=True)
        
        # Initialize status.json
        status = {
            "agent_id": agent_id,
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "initializing",
            "mailbox_version": "1.0.0"
        }
        (agent_mailbox / "status.json").write_text(json.dumps(status, indent=2))
        
        # Initialize empty devlog
        devlog = f"""# Agent {agent_id} Devlog

## Initialization
* **Timestamp:** {status['last_updated']}
* **Status:** INITIALIZING
* **Task ID:** INIT-{agent_id}-{int(time.time())}
* **Summary:** Agent mailbox initialized
* **Actions Taken:**
    * **Created** mailbox structure
    * **Initialized** status tracking
* **Next Step:** Await onboarding protocol
* **Tags:** #initialization #onboarding #priority_high
"""
        (agent_mailbox / "devlog.md").write_text(devlog)
        
        logger.info(f"✅ Initialized mailbox for {agent_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error initializing mailbox for {agent_id}: {e}")
        return False

def send_startup_message(agent_id: str, coords: Dict) -> bool:
    """Send startup message to an agent."""
    agent = coords.get(agent_id, {})
    if not agent:
        logger.error(f"❌ No coordinates found for {agent_id}")
        return False

    try:
        # Click input box
        pyautogui.click(agent["input_box"]["x"], agent["input_box"]["y"])
        time.sleep(INITIAL_DELAY)

        # Compose startup message
        startup_msg = (
            f"{agent_id}: Welcome to Dream.OS! Your mailbox has been initialized. "
            f"Please check your inbox for the onboarding protocol (use /check_mailbox)."
        )

        # Send message
        pyperclip.copy(startup_msg)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(PASTE_DELAY)
        pyautogui.press("enter")

        logger.info(f"✅ Sent startup message to {agent_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error sending startup message to {agent_id}: {e}")
        return False

def start_agents() -> bool:
    """Start all agents with onboarding protocol."""
    coords = load_coordinates()
    if not coords:
        return False

    success = True
    for agent_id in coords.keys():
        console.print(f"\n[cyan]Starting {agent_id}...")
        
        # Initialize mailbox
        if not initialize_mailbox(agent_id):
            success = False
            continue
            
        # Send startup message
        if not send_startup_message(agent_id, coords):
            success = False
            continue
            
        # Wait before next agent
        time.sleep(AGENT_DELAY)

    if success:
        console.print("\n[green]✅ All agents started successfully!")
    else:
        console.print("\n[yellow]⚠️ Some agents failed to start properly")
    
    return success

if __name__ == "__main__":
    start_agents() 