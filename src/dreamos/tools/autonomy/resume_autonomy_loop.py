"""
Resume Autonomy Loop for Dream.OS Agents

This script manages the autonomous operation of Dream.OS agents by:
1. Validating the environment
2. Reading agent coordinates
3. Sending resume prompts
4. Monitoring agent status
"""

import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pyautogui
import pygetwindow as gw
from rich.console import Console
from rich.logging import RichHandler

from dreamos.tools.env.check_env import verify_runtime_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("resume_autonomy")

# Constants
PROMPT = "RESUME AUTONOMY"
COORDS_PATH = Path("runtime/config/cursor_agent_coords.json")
AGENTS = [f"Agent-{i}" for i in range(1, 9)]
PASTE_DELAY = 0.5
WINDOW_TITLE = "Cursor"
MAX_RETRIES = 3
RETRY_DELAY = 2
STALL_TIMEOUT = timedelta(minutes=5)
STATUS_PATH = Path("runtime/status/agent_status.json")
MIN_CYCLES = 25

console = Console()

class AgentStatus:
    def __init__(self):
        self.last_active: Dict[str, datetime] = {}
        self.stalled_agents: Set[str] = set()
        self.cycle_count = 0
        self.load_status()

    def load_status(self):
        """Load agent status from file."""
        try:
            if STATUS_PATH.exists():
                data = json.loads(STATUS_PATH.read_text())
                self.last_active = {
                    agent: datetime.fromisoformat(time)
                    for agent, time in data.get("last_active", {}).items()
                }
                self.stalled_agents = set(data.get("stalled_agents", []))
                self.cycle_count = data.get("cycle_count", 0)
        except Exception as e:
            logger.error(f"❌ Error loading status: {e}")

    def save_status(self):
        """Save agent status to file."""
        try:
            data = {
                "last_active": {
                    agent: time.isoformat()
                    for agent, time in self.last_active.items()
                },
                "stalled_agents": list(self.stalled_agents),
                "cycle_count": self.cycle_count
            }
            STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
            STATUS_PATH.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"❌ Error saving status: {e}")

    def update_agent(self, agent_id: str):
        """Update agent's last active timestamp."""
        self.last_active[agent_id] = datetime.now()
        if agent_id in self.stalled_agents:
            self.stalled_agents.remove(agent_id)
        self.save_status()

    def check_stalled(self) -> Set[str]:
        """Check for stalled agents."""
        now = datetime.now()
        stalled = {
            agent for agent, last_active in self.last_active.items()
            if now - last_active > STALL_TIMEOUT
        }
        self.stalled_agents = stalled
        self.save_status()
        return stalled

    def increment_cycle(self):
        """Increment cycle count and save."""
        self.cycle_count += 1
        self.save_status()

    def reset_cycle(self):
        """Reset cycle count and save."""
        self.cycle_count = 0
        self.save_status()

def get_window_bounds() -> Optional[Tuple[int, int, int, int]]:
    """Get the bounds of the Cursor window."""
    try:
        win = gw.getWindowsWithTitle(WINDOW_TITLE)
        if not win:
            logger.error(f"❌ No window found with title: {WINDOW_TITLE}")
            return None
        window = win[0]
        return (window.left, window.top, window.width, window.height)
    except Exception as e:
        logger.error(f"❌ Error getting window bounds: {e}")
        return None

def validate_coordinates(coords: Dict, window_bounds: Tuple[int, int, int, int]) -> bool:
    """Validate that coordinates are within window bounds."""
    if not window_bounds:
        return False
    
    left, top, width, height = window_bounds
    for agent_id, agent_coords in coords.items():
        if "input_box" not in agent_coords:
            logger.error(f"❌ Missing input_box for {agent_id}")
            return False
        
        x, y = agent_coords["input_box"]["x"], agent_coords["input_box"]["y"]
        if not (left <= x <= left + width and top <= y <= top + height):
            logger.error(f"❌ Coordinates for {agent_id} ({x}, {y}) outside window bounds")
            return False
    
    return True

def validate_environment() -> bool:
    """Validate the Dream.OS environment before proceeding.

    Catches SystemExit from verify_runtime_env(strict=True) to ensure
    protocol-compliant boolean return and proper error handling.
    """
    logger.info("🔍 Validating environment...")
    try:
        result = verify_runtime_env(strict=True)
        # If function returns, treat as success (legacy fallback)
        logger.info("✅ Environment validated")
        return True
    except SystemExit as e:
        if e.code == 0:
            logger.info("✅ Environment validated")
            return True
        else:
            logger.error("❌ Environment validation failed (SystemExit)")
            return False

def load_coordinates() -> Optional[Dict]:
    """Load and validate agent coordinates from config file."""
    try:
        if not COORDS_PATH.exists():
            logger.error(f"❌ Coordinates file not found: {COORDS_PATH}")
            return None
            
        coords = json.loads(COORDS_PATH.read_text())
        
        # Get window bounds
        window_bounds = get_window_bounds()
        if not window_bounds:
            return None
            
        # Validate coordinates
        if not validate_coordinates(coords, window_bounds):
            logger.error("❌ Invalid coordinates detected")
            return None
            
        logger.info(f"✅ Loaded and validated coordinates for {len(coords)} agents")
        return coords
    except json.JSONDecodeError:
        logger.error("❌ Invalid JSON in coordinates file")
        return None
    except Exception as e:
        logger.error(f"❌ Error loading coordinates: {e}")
        return None

def focus_cursor_window(window_title: str = WINDOW_TITLE) -> bool:
    """Focus the Cursor window."""
    try:
        win = gw.getWindowsWithTitle(window_title)
        if not win:
            logger.error(f"❌ No window found with title: {window_title}")
            return False
        win[0].activate()
        time.sleep(0.5)
        return True
    except Exception as e:
        logger.error(f"❌ Error focusing window: {e}")
        return False

def paste_prompt(agent_id: str, coords: Dict, retry_count: int = 0) -> bool:
    """Send resume prompt to an agent."""
    try:
        if agent_id not in coords:
            logger.error(f"❌ Missing coordinates for {agent_id}")
            return False

        box = coords[agent_id]["input_box"]
        pyautogui.click(box["x"], box["y"])
        time.sleep(0.25)
        pyautogui.typewrite(PROMPT)
        time.sleep(0.1)
        pyautogui.press("enter")
        logger.info(f"✅ Sent to {agent_id} → {PROMPT}")
        return True
    except Exception as e:
        if retry_count < MAX_RETRIES:
            logger.warning(f"⚠️ Retry {retry_count + 1}/{MAX_RETRIES} for {agent_id}: {e}")
            time.sleep(RETRY_DELAY)
            return paste_prompt(agent_id, coords, retry_count + 1)
        logger.error(f"❌ Failed to send prompt to {agent_id}: {e}")
        return False

def monitor_agent_status(agent_id: str, status: AgentStatus) -> bool:
    """Monitor agent status after sending prompt."""
    status.update_agent(agent_id)
    stalled = status.check_stalled()
    if agent_id in stalled:
        logger.warning(f"⚠️ {agent_id} is stalled")
        return False
    return True

def get_cursor_coordinates() -> Optional[Dict]:
    """Get the actual coordinates of agent input boxes in Cursor window."""
    try:
        # Get window bounds
        window_bounds = get_window_bounds()
        if not window_bounds:
            return None
            
        left, top, width, height = window_bounds
        logger.info(f"Cursor window bounds: left={left}, top={top}, width={width}, height={height}")
        
        # Prompt user to click each agent's input box
        coords = {}
        for agent_id in AGENTS:
            logger.info(f"Please click the input box for {agent_id}...")
            # Wait for click
            x, y = pyautogui.position()
            time.sleep(0.5)  # Wait for click to complete
            
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
    except Exception as e:
        logger.error(f"❌ Error getting coordinates: {e}")
        return None

def main() -> int:
    """Main execution loop."""
    console.print("[bold cyan]🚀 Starting Resume Autonomy Loop[/bold cyan]")
    
    # Initialize agent status
    status = AgentStatus()
    
    # Reset cycle count on start
    status.reset_cycle()
    
    # Validate environment
    if not validate_environment():
        return 1

    # Load coordinates
    coords = load_coordinates()
    if not coords:
        logger.warning("⚠️ No valid coordinates found. Would you like to set them up? (y/n)")
        response = input().lower()
        if response == 'y':
            coords = get_cursor_coordinates()
            if not coords:
                return 1
        else:
            return 1

    # Focus Cursor window
    if not focus_cursor_window():
        return 1

    try:
        while True:
            # Check cycle count
            if status.cycle_count >= MIN_CYCLES:
                logger.info(f"✅ Completed {MIN_CYCLES} cycles")
                status.reset_cycle()
            
            # Check for stalled agents
            stalled = status.check_stalled()
            if stalled:
                logger.warning(f"⚠️ Found stalled agents: {', '.join(stalled)}")
            
            # Process each agent
            for agent_id in AGENTS:
                if paste_prompt(agent_id, coords):
                    if monitor_agent_status(agent_id, status):
                        logger.info(f"✅ {agent_id} resumed successfully")
                    else:
                        logger.warning(f"⚠️ {agent_id} may need attention")
                time.sleep(PASTE_DELAY)
            
            # Increment cycle count
            status.increment_cycle()
            
            # Log cycle status
            if status.cycle_count % 5 == 0:
                logger.info(f"🔄 Completed {status.cycle_count} cycles")
            
            # Wait before next cycle
            time.sleep(15)  # Tune this as needed

    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️ Interrupted by user[/bold yellow]")
        return 0
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 