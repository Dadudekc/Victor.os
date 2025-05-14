"""Agent monitoring and supervision utilities for Dream.OS. (Reconstructed)"""

import yaml
import time # Added for potential timestamping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set # Added Set for potential use in AgentMonitor

def get_windows_safe_timestamp() -> str:
    """Get ISO timestamp safe for Windows filenames. (Copied from previous context)"""
    return datetime.utcnow().isoformat().replace(":", "_")

class AgentMonitor:
    """Monitors agent activity and status. (Reconstructed Skeleton)"""
    def __init__(self, agent_id: str, log_dir: Union[str, Path] = "runtime/agent_logs"):
        self.agent_id = agent_id
        self.log_dir = Path(log_dir) / agent_id
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.active_tasks: Set[str] = set()
        self._last_heartbeat: Optional[float] = None
        print(f"AgentMonitor for {agent_id} initialized. Logging to {self.log_dir}")

    def log_action(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log an agent action."""
        log_entry = {
            "timestamp": get_windows_safe_timestamp(),
            "agent_id": self.agent_id,
            "action": action,
            "details": details or {}
        }
        log_file = self.log_dir / f"actions_{datetime.utcnow().strftime('%Y-%m-%d')}.log.yaml"
        with open(log_file, 'a') as f:
            yaml.dump([log_entry], f) # Store as a list item for easier YAML stream reading

    def start_task(self, task_id: str) -> None:
        """Mark a task as started."""
        self.active_tasks.add(task_id)
        self.log_action("task_started", {"task_id": task_id, "active_count": len(self.active_tasks)})

    def complete_task(self, task_id: str) -> None:
        """Mark a task as completed."""
        if task_id in self.active_tasks:
            self.active_tasks.remove(task_id)
        self.log_action("task_completed", {"task_id": task_id, "active_count": len(self.active_tasks)})

    def heartbeat(self) -> None:
        """Record a heartbeat for the agent."""
        self._last_heartbeat = time.time()
        self.log_action("heartbeat", {"timestamp": self._last_heartbeat})

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "agent_id": self.agent_id,
            "active_tasks": list(self.active_tasks),
            "last_heartbeat": self._last_heartbeat,
            "log_directory": str(self.log_dir)
        }

class CommandSupervisor:
    """Supervises and executes agent commands. (Reconstructed Skeleton)"""
    def __init__(self, command_dir: Union[str, Path] = "runtime/commands"):
        self.command_dir = Path(command_dir)
        self.command_dir.mkdir(parents=True, exist_ok=True)
        print(f"CommandSupervisor initialized. Command directory: {self.command_dir}")

    def queue_command(self, agent_id: str, command: Dict[str, Any]) -> str:
        """Queue a command for an agent."""
        command_id = f"cmd_{agent_id}_{get_windows_safe_timestamp()}"
        command_file = self.command_dir / f"{command_id}.yaml"
        command_data = {
            "command_id": command_id,
            "agent_id": agent_id,
            "command_details": command,
            "status": "PENDING",
            "queued_at": datetime.utcnow().isoformat()
        }
        with open(command_file, 'w') as f:
            yaml.dump(command_data, f)
        print(f"Command {command_id} queued for agent {agent_id}: {command_file}")
        return command_id

    def get_command_status(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a queued command."""
        command_file = self.command_dir / f"{command_id}.yaml"
        if command_file.exists():
            with open(command_file, 'r') as f:
                return yaml.safe_load(f)
        return None

    def update_command_status(self, command_id: str, status: str, result: Optional[Any] = None) -> bool:
        """Update the status of a command."""
        command_file = self.command_dir / f"{command_id}.yaml"
        if command_file.exists():
            data = self.get_command_status(command_id)
            if data:
                data["status"] = status
                data["updated_at"] = datetime.utcnow().isoformat()
                if result is not None:
                    data["result"] = result
                with open(command_file, 'w') as f:
                    yaml.dump(data, f)
                return True
        return False

# Note: This is a reconstructed file. Review and restoration from backup/VCS is preferred. 