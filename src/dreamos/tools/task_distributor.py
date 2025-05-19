import yaml
import json
import logging
from pathlib import Path
from typing import Dict, List
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('task_distributor')

class TaskDistributor:
    def __init__(self):
        self.episodes_dir = Path("episodes")
        self.mailbox_dir = Path("runtime/agent_comms/agent_mailboxes")
        self.registry_file = Path("runtime/agent_registry.json")
        self.registry = self._load_registry()
        
    def _load_registry(self) -> dict:
        """Load agent registry."""
        try:
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return {}
            
    def _load_episode(self, episode_file: str) -> dict:
        """Load episode tasks from YAML."""
        try:
            with open(self.episodes_dir / episode_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load episode {episode_file}: {e}")
            return {}
            
    def _assign_tasks_to_agent(self, agent_id: str, tasks: List[dict]):
        """Assign tasks to an agent's inbox."""
        try:
            inbox_file = self.mailbox_dir / agent_id / "inbox.json"
            inbox_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing inbox or create new
            if inbox_file.exists():
                with open(inbox_file, 'r') as f:
                    inbox = json.load(f)
            else:
                inbox = {"tasks": []}
                
            # Add new tasks
            for task in tasks:
                task["assigned_to"] = agent_id
                task["status"] = "pending"
                inbox["tasks"].append(task)
                
            # Save updated inbox
            with open(inbox_file, 'w') as f:
                json.dump(inbox, f, indent=2)
                
            logger.info(f"Assigned {len(tasks)} tasks to {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to assign tasks to {agent_id}: {e}")
            
    def distribute_tasks(self, episode_file: str = "episode-launch-final-lock.yaml"):
        """Distribute tasks from an episode to agents."""
        try:
            # Load episode tasks
            episode = self._load_episode(episode_file)
            if not episode or "tasks" not in episode:
                logger.error(f"No tasks found in {episode_file}")
                return
                
            # Group tasks by priority
            tasks_by_priority = {
                "critical": [],
                "high": [],
                "medium": [],
                "low": []
            }
            
            for task in episode["tasks"]:
                priority = task.get("priority", "medium").lower()
                tasks_by_priority[priority].append(task)
                
            # Assign tasks to agents
            agents = list(self.registry.keys())
            if not agents:
                logger.error("No agents found in registry")
                return
                
            # Distribute critical tasks first
            for task in tasks_by_priority["critical"]:
                agent = random.choice(agents)
                self._assign_tasks_to_agent(agent, [task])
                
            # Distribute high priority tasks
            for task in tasks_by_priority["high"]:
                agent = random.choice(agents)
                self._assign_tasks_to_agent(agent, [task])
                
            # Distribute remaining tasks
            remaining_tasks = tasks_by_priority["medium"] + tasks_by_priority["low"]
            tasks_per_agent = len(remaining_tasks) // len(agents)
            extra_tasks = len(remaining_tasks) % len(agents)
            
            start_idx = 0
            for i, agent in enumerate(agents):
                # Calculate number of tasks for this agent
                num_tasks = tasks_per_agent + (1 if i < extra_tasks else 0)
                if num_tasks > 0:
                    agent_tasks = remaining_tasks[start_idx:start_idx + num_tasks]
                    self._assign_tasks_to_agent(agent, agent_tasks)
                    start_idx += num_tasks
                    
            logger.info(f"Distributed {len(episode['tasks'])} tasks from {episode_file}")
            
        except Exception as e:
            logger.error(f"Failed to distribute tasks: {e}")

def main():
    distributor = TaskDistributor()
    distributor.distribute_tasks()

if __name__ == "__main__":
    main() 