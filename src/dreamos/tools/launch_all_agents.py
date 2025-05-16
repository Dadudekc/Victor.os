"""
Launch all Cursor-based agents (Agent-1 to Agent-8) in parallel
Each agent runs its own inbox loop using the universal agent bootstrap runner
"""

import argparse
import asyncio
import json
import logging
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Constants
AGENTS = [f"Agent-{n}" for n in range(1, 9)]  # 1-8 inclusive, EXCLUDING 0
RUNNER = "src/dreamos/tools/agent_bootstrap_runner/__main__.py"
LOG_DIR = Path("runtime/parallel_logs")
STATE_FILE = LOG_DIR / "launcher_state.json"
WATCHDOG_INTERVAL = 30  # seconds
MAX_RESTARTS = 3  # Maximum number of auto-restarts per agent
SHUTDOWN_TIMEOUT = 10  # seconds


class AgentProcess:
    """Represents a running agent process with metadata"""

    def __init__(self, agent_id: str, process: subprocess.Popen, log_file: Path):
        self.agent_id = agent_id
        self.process = process
        self.log_file = log_file
        self.start_time = datetime.now()
        self.restart_count = 0
        self.last_restart = None

    def is_alive(self) -> bool:
        """Check if the agent process is still running"""
        return self.process.poll() is None

    def terminate(self, timeout: int = SHUTDOWN_TIMEOUT) -> bool:
        """
        Gracefully terminate the agent process

        Args:
            timeout: Seconds to wait for graceful termination

        Returns:
            bool: True if terminated successfully
        """
        if not self.is_alive():
            return True

        # Try graceful shutdown first
        self.process.terminate()
        try:
            self.process.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            # Force kill if graceful shutdown fails
            self.process.kill()
            self.process.wait()
            return True

    def restart(self) -> bool:
        """
        Restart the agent process

        Returns:
            bool: True if restart was successful
        """
        if self.restart_count >= MAX_RESTARTS:
            logger.error(f"{self.agent_id} exceeded maximum restarts ({MAX_RESTARTS})")
            return False

        self.terminate()

        # Reopen log file in append mode
        log = open(self.log_file, "a")

        # Start new process
        try:
            self.process = subprocess.Popen(
                [sys.executable, RUNNER, "--agent", self.agent_id, "--no-delay"],
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            self.restart_count += 1
            self.last_restart = datetime.now()
            logger.info(
                f"Restarted {self.agent_id} (attempt {self.restart_count}/{MAX_RESTARTS})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to restart {self.agent_id}: {e}")
            return False


class AgentLauncher:
    """Manages launching and monitoring of multiple agent processes"""

    def __init__(self, agents: Optional[List[str]] = None):
        """
        Initialize the launcher

        Args:
            agents: List of agent IDs to launch, or None for all agents
        """
        self.agents = agents or AGENTS
        self.processes: Dict[str, AgentProcess] = {}
        self.running = False
        self._setup_logging()

    def _setup_logging(self):
        """Set up logging directory and files"""
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Create launcher log file
        launcher_log = LOG_DIR / "launcher.log"
        file_handler = logging.FileHandler(launcher_log)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(file_handler)

    def _save_state(self):
        """Save launcher state to file"""
        state = {
            agent_id: {
                "pid": proc.process.pid,
                "start_time": proc.start_time.isoformat(),
                "restart_count": proc.restart_count,
                "last_restart": (
                    proc.last_restart.isoformat() if proc.last_restart else None
                ),
                "log_file": str(proc.log_file),
            }
            for agent_id, proc in self.processes.items()
        }

        with STATE_FILE.open("w") as f:
            json.dump(state, f, indent=2)

    def launch_agents(self) -> bool:
        """
        Launch all configured agents

        Returns:
            bool: True if all agents launched successfully
        """
        success = True
        for agent_id in self.agents:
            log_file = LOG_DIR / f"{agent_id}.out"
            try:
                with open(log_file, "w") as log:
                    logger.info(f"🛰️ Launching {agent_id}...")
                    process = subprocess.Popen(
                        [sys.executable, RUNNER, "--agent", agent_id, "--no-delay"],
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                    self.processes[agent_id] = AgentProcess(agent_id, process, log_file)
            except Exception as e:
                logger.error(f"Failed to launch {agent_id}: {e}")
                success = False

        self._save_state()
        return success

    async def monitor_agents(self):
        """Monitor agent processes and restart if needed"""
        self.running = True
        logger.info("\n🧭 All agents launched. Monitoring status...\n")

        while self.running:
            for agent_id, proc in list(self.processes.items()):
                if not proc.is_alive():
                    exit_code = proc.process.returncode
                    logger.warning(f"⚠️  {agent_id} exited with code {exit_code}")

                    if proc.restart_count < MAX_RESTARTS:
                        if proc.restart():
                            self._save_state()
                    else:
                        logger.error(f"❌ {agent_id} exceeded maximum restarts")

            await asyncio.sleep(WATCHDOG_INTERVAL)

    def shutdown(self):
        """Gracefully shutdown all agent processes"""
        logger.info("🛑 Stopping all agents...")
        self.running = False

        for agent_id, proc in self.processes.items():
            logger.info(f"Stopping {agent_id}...")
            if proc.terminate():
                logger.info(f"Stopped {agent_id}")
            else:
                logger.error(f"Failed to stop {agent_id}")

        self._save_state()


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Launch Dream.OS agents in parallel")
    parser.add_argument(
        "--agents",
        nargs="+",
        help="Specific agents to launch (e.g., 'Agent-1 Agent-2')",
    )
    parser.add_argument("--once", action="store_true", help="Run agents once and exit")
    return parser.parse_args()


async def main():
    """Main entry point"""
    args = parse_args()

    # Set up signal handlers
    def signal_handler(sig, frame):
        logger.info("\nReceived shutdown signal...")
        launcher.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and start launcher
    launcher = AgentLauncher(agents=args.agents)
    if not launcher.launch_agents():
        logger.error("Failed to launch all agents")
        sys.exit(1)

    if args.once:
        logger.info("Running in --once mode, waiting for completion...")
        # Wait for all processes to complete
        for proc in launcher.processes.values():
            proc.process.wait()
    else:
        # Start monitoring
        await launcher.monitor_agents()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nShutdown requested...")
        sys.exit(0)
