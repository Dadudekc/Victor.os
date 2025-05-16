#!/usr/bin/env python3
"""
Task Disperser for Dream.OS
Allocates parsed tasks to agent inboxes based on ownership and intent.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskDisperser:
    def __init__(self, parsed_tasks_path: str):
        self.parsed_tasks_path = Path(parsed_tasks_path)
        self.tasks_data = None
        self.agent_inboxes = {}

    def load_tasks(self) -> bool:
        """Load parsed tasks from JSON file."""
        try:
            with open(self.parsed_tasks_path, "r") as f:
                self.tasks_data = json.load(f)
            return True
        except Exception as e:
            logger.error(f"Error loading tasks: {str(e)}")
            return False

    def get_agent_inbox_path(self, agent_id: str) -> Path:
        """Get the path to an agent's inbox."""
        return Path(f"runtime/inboxes/{agent_id}/inbox.json")

    def load_agent_inbox(self, agent_id: str) -> Dict[str, Any]:
        """Load an agent's inbox or create if it doesn't exist."""
        inbox_path = self.get_agent_inbox_path(agent_id)

        if inbox_path.exists():
            try:
                with open(inbox_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading inbox for {agent_id}: {str(e)}")
                return {"tasks": []}
        else:
            # Create inbox directory and file
            inbox_path.parent.mkdir(parents=True, exist_ok=True)
            inbox_data = {"agent_id": agent_id, "tasks": []}
            with open(inbox_path, "w") as f:
                json.dump(inbox_data, f, indent=2)
            return inbox_data

    def disperse_tasks(self) -> bool:
        """Disperse tasks to agent inboxes."""
        if not self.tasks_data:
            logger.error("No tasks data loaded")
            return False

        # Group tasks by owner
        tasks_by_owner = {}
        for task in self.tasks_data["tasks"]:
            owner = task["owner"]
            if owner not in tasks_by_owner:
                tasks_by_owner[owner] = []
            tasks_by_owner[owner].append(task)

        # Update each agent's inbox
        for owner, tasks in tasks_by_owner.items():
            inbox_data = self.load_agent_inbox(owner)

            # Add new tasks
            for task in tasks:
                if not any(t["id"] == task["id"] for t in inbox_data["tasks"]):
                    inbox_data["tasks"].append(task)

            # Save updated inbox
            inbox_path = self.get_agent_inbox_path(owner)
            try:
                with open(inbox_path, "w") as f:
                    json.dump(inbox_data, f, indent=2)
                logger.info(f"Updated inbox for {owner} with {len(tasks)} tasks")
            except Exception as e:
                logger.error(f"Error saving inbox for {owner}: {str(e)}")
                return False

        return True

    def create_agent_identity_config(self) -> bool:
        """Create agent identity configuration file."""
        identity_config = {
            "agents": {
                "Agent-1": {
                    "role": "⚙️ Engineer",
                    "purpose": "System engineering and optimization",
                },
                "Agent-2": {
                    "role": "🛡️ Escalation Watch",
                    "purpose": "Safety and oversight",
                },
                "Agent-3": {
                    "role": "📦 Task Router",
                    "purpose": "Task distribution and coordination",
                },
                "Agent-4": {
                    "role": "🔬 Validator",
                    "purpose": "Quality assurance and validation",
                },
                "Agent-5": {
                    "role": "🎯 Captain",
                    "purpose": "Strategic direction and leadership",
                },
                "Agent-6": {
                    "role": "🧠 Reflection",
                    "purpose": "System reflection and improvement",
                },
                "Agent-7": {
                    "role": "📡 Bridge Ops",
                    "purpose": "Communication and integration",
                },
                "Agent-8": {
                    "role": "🕊️ Lorekeeper",
                    "purpose": "Documentation and knowledge management",
                },
            }
        }

        config_path = Path("runtime/config/agent_identity.json")
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_path, "w") as f:
                json.dump(identity_config, f, indent=2)
            logger.info("Created agent identity configuration")
            return True
        except Exception as e:
            logger.error(f"Error creating agent identity config: {str(e)}")
            return False


def main():
    if len(sys.argv) != 2:
        print("Usage: python disperse_tasks.py <parsed_tasks_json_path>")
        sys.exit(1)

    tasks_path = sys.argv[1]
    disperser = TaskDisperser(tasks_path)

    if disperser.load_tasks():
        if disperser.disperse_tasks():
            if disperser.create_agent_identity_config():
                logger.info("Task dispersal completed successfully")
            else:
                logger.error("Failed to create agent identity config")
        else:
            logger.error("Failed to disperse tasks")
    else:
        logger.error("Failed to load tasks")
        sys.exit(1)


if __name__ == "__main__":
    main()
