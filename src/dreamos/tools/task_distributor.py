import yaml
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
import random
import time

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
            
    def assign_tasks_to_agent(self, agent_id: str, tasks: List[Dict[str, Any]]) -> bool:
        """Assign tasks to a specific agent."""
        try:
            if not tasks:
                logger.warning(f"No tasks available to assign to {agent_id}")
                return False
            
            # Create agent's task file
            agent_tasks_file = Path(f"runtime/agent_comms/agent_mailboxes/{agent_id}/tasks.yaml")
            agent_tasks_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Format tasks for the agent
            formatted_tasks = []
            for task in tasks:
                if isinstance(task, dict):
                    formatted_task = {
                        "id": task.get("id", ""),
                        "title": task.get("title", ""),
                        "description": task.get("description", ""),
                        "priority": task.get("priority", 0),
                        "status": "pending",
                        "assigned_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    formatted_tasks.append(formatted_task)
                else:
                    logger.warning(f"Skipping invalid task format for {agent_id}: {task}")
                    continue
            
            if not formatted_tasks:
                logger.warning(f"No valid tasks to assign to {agent_id}")
                return False
            
            # Save tasks to agent's task file
            with open(agent_tasks_file, 'w') as f:
                yaml.dump({"tasks": formatted_tasks}, f, default_flow_style=False)
            
            logger.info(f"Assigned {len(formatted_tasks)} tasks to {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign tasks to {agent_id}: {e}")
            return False

    def distribute_tasks(self):
        """Distribute tasks from episode files to agents."""
        try:
            # Get all episode files
            episode_files = list(Path("episodes").glob("episode-*.yaml"))
            if not episode_files:
                logger.warning("No episode files found")
                return
            
            # Load and combine tasks from all episode files
            all_tasks = []
            for episode_file in episode_files:
                try:
                    with open(episode_file, 'r') as f:
                        episode_data = yaml.safe_load(f)
                        if isinstance(episode_data, dict) and "tasks" in episode_data:
                            tasks = episode_data["tasks"]
                            if isinstance(tasks, list):
                                all_tasks.extend(tasks)
                            else:
                                logger.warning(f"Invalid tasks format in {episode_file}")
                except Exception as e:
                    logger.error(f"Failed to load tasks from {episode_file}: {e}")
                    continue
            
            if not all_tasks:
                logger.warning("No valid tasks found in episode files")
                return
            
            # Sort tasks by priority
            all_tasks.sort(key=lambda x: x.get("priority", 0), reverse=True)
            
            # Get available agents
            available_agents = list(self.registry.keys())
            if not available_agents:
                logger.warning("No agents available for task distribution")
                return
            
            # Distribute tasks evenly among agents
            tasks_per_agent = len(all_tasks) // len(available_agents)
            remaining_tasks = len(all_tasks) % len(available_agents)
            
            task_index = 0
            for agent_id in available_agents:
                # Calculate number of tasks for this agent
                agent_task_count = tasks_per_agent + (1 if remaining_tasks > 0 else 0)
                remaining_tasks -= 1
                
                # Get tasks for this agent
                agent_tasks = all_tasks[task_index:task_index + agent_task_count]
                task_index += agent_task_count
                
                # Assign tasks to agent
                if agent_tasks:
                    self.assign_tasks_to_agent(agent_id, agent_tasks)
            
            logger.info(f"Distributed {len(all_tasks)} tasks from {len(episode_files)} episode files")
            
        except Exception as e:
            logger.error(f"Error in task distribution: {e}")

def main():
    distributor = TaskDistributor()
    distributor.distribute_tasks()

if __name__ == "__main__":
    main() 