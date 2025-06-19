import logging
import os
from pathlib import Path
from typing import List

from dreamos.skills.lifecycle.stable_loop import StableAutonomousLoop

logging.basicConfig(level=logging.INFO)

class SimpleAgent(StableAutonomousLoop):
    """Minimal agent using StableAutonomousLoop."""

    def __init__(self, agent_id: str, workspace: Path):
        super().__init__(name=f"agent-{agent_id}-loop")
        self.agent_id = agent_id
        self.workspace = workspace
        self.log_file = workspace / f"agent-{agent_id}.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _process_operations(self):
        self.register_action("echo")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"cycle {self.cycle_count}\n")

    def _persist_state(self):
        state_file = self.workspace / "state.json"
        state_file.write_text(str(self.state))

    def _recover_from_error(self, error: Exception) -> bool:
        logging.error("Recovering from error: %s", error)
        return True


def launch_swarm(num_agents: int = 3):
    base = Path("logs")
    agents: List[SimpleAgent] = []
    for i in range(num_agents):
        agent = SimpleAgent(agent_id=str(i + 1), workspace=base)
        agents.append(agent)

    for agent in agents:
        agent.run()


if __name__ == "__main__":
    launch_swarm()
