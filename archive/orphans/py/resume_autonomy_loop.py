"""
Resume Autonomy Loop for Dream.OS Agents

This script manages the autonomous operation of Dream.OS agents by:
1. Validating the environment
2. Reading agent configurations
3. Sending resume prompts
4. Monitoring agent status
"""

import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Set

from rich.console import Console
from rich.logging import RichHandler

from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.tools.agent_bootstrap_runner.config import AgentConfig
from dreamos.tools.agent_bootstrap_runner.ui_interaction import AgentUIInteractor
from dreamos.tools.env.check_env import verify_runtime_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("resume_autonomy")

# Constants
PROMPT = "RESUME AUTONOMY"
AGENTS = [f"Agent-{i}" for i in range(1, 9)]
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
                    agent: time.isoformat() for agent, time in self.last_active.items()
                },
                "stalled_agents": list(self.stalled_agents),
                "cycle_count": self.cycle_count,
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
            agent
            for agent, last_active in self.last_active.items()
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


def validate_environment() -> bool:
    """Validate the Dream.OS environment before proceeding."""
    logger.info("🔍 Validating environment...")
    try:
        verify_runtime_env(strict=True)
        logger.info("✅ Environment validated")
        return True
    except SystemExit as e:
        if e.code == 0:
            logger.info("✅ Environment validated")
            return True
        else:
            logger.error("❌ Environment validation failed (SystemExit)")
            return False


async def resume_agent(agent_id: str, status: AgentStatus) -> bool:
    """Resume operation for a single agent."""
    try:
        config = AgentConfig(agent_id=agent_id)
        ui_interactor = AgentUIInteractor(logger, config)
        bus = AgentBus()

        if not ui_interactor.initialize():
            logger.error(f"❌ Failed to initialize UI interactor for {agent_id}")
            return False

        # Inject resume prompt
        if not await ui_interactor.inject_prompt(bus, PROMPT):
            logger.error(f"❌ Failed to inject prompt for {agent_id}")
            return False

        # Update status
        status.update_agent(agent_id)
        logger.info(f"✅ Successfully resumed {agent_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Error resuming {agent_id}: {e}")
        return False


async def monitor_agent_status(agent_id: str, status: AgentStatus) -> bool:
    """Monitor an agent's status and resume if stalled."""
    if agent_id in status.check_stalled():
        logger.warning(f"⚠️ {agent_id} appears stalled - attempting resume")
        return await resume_agent(agent_id, status)
    return True


async def main() -> int:
    """Main execution loop."""
    console.print("[bold cyan]🚀 Starting Resume Autonomy Loop[/bold cyan]")

    if not validate_environment():
        return 1

    status = AgentStatus()

    while True:
        try:
            # Check and resume any stalled agents
            for agent_id in AGENTS:
                await monitor_agent_status(agent_id, status)

            # Increment cycle count
            status.increment_cycle()

            # Sleep before next cycle
            time.sleep(30)  # 30-second cycle time

        except KeyboardInterrupt:
            console.print("\n[bold yellow]⚠️ Shutdown requested[/bold yellow]")
            break
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}")
            return 1

    return 0


if __name__ == "__main__":
    import asyncio

    sys.exit(asyncio.run(main()))
