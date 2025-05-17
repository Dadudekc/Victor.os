import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class AutonomyEngine:
    """Manages agent autonomy and devlog writing."""
    
    def __init__(self, workspace_root):
        from pathlib import Path
        self.workspace_root = Path(workspace_root)
        self.devlog_root_dir = self.workspace_root / "runtime/devlog/agents"
        
        self.devlog_root_dir.mkdir(parents=True, exist_ok=True)

    def get_devlog_path(self, agent_id: str) -> Path:
        """Get the path to the specific agent's devlog file."""
        self.devlog_root_dir.mkdir(parents=True, exist_ok=True)
        return self.devlog_root_dir / f"{agent_id}_cycle_events.log"

    def write_devlog_entry(self, agent_id: str, entry: Dict[str, Any]) -> None:
        """Write an entry to the agent-specific devlog file."""
        log_file_path = self.get_devlog_path(agent_id)
        try:
            timestamp = datetime.now().isoformat()
            
            if entry.get("type") == "task_progress":
                message = f"Task {entry['task_id']}: {entry['status']} - {entry['details']}"
            elif entry.get("type") == "error":
                message = f"Error: {entry['message']}"
                if entry.get("details"):
                    message += f" - {json.dumps(entry['details'])}"
            elif entry.get("type") == "autonomy":
                message = f"Autonomy Decision: {entry['decision']} - {entry['reasoning']}"
            elif entry.get("type") == "generic_event":
                message = f"Event: {entry.get('event_name', 'Unknown Event')} - Details: {json.dumps(entry.get('details', {}))}"
            else:
                message = f"{entry.get('message', 'Unknown entry type')}"
            
            with open(log_file_path, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
                
        except Exception as e:
            logger.error(f"Error writing to devlog for {agent_id} at {log_file_path}: {e}")

    def log_task_progress(self, agent_id: str, task_id: str, status: str, details: str) -> None:
        """Log task progress to devlog."""
        entry = {
            "type": "task_progress",
            "task_id": task_id,
            "status": status,
            "details": details
        }
        self.write_devlog_entry(agent_id, entry)

    def log_error(self, agent_id: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log an error to devlog."""
        entry = {
            "type": "error",
            "message": message,
            "details": details
        }
        self.write_devlog_entry(agent_id, entry)

    def log_autonomy_decision(self, agent_id: str, decision: str, reasoning: str) -> None:
        """Log an autonomy decision to devlog."""
        entry = {
            "type": "autonomy",
            "decision": decision,
            "reasoning": reasoning
        }
        self.write_devlog_entry(agent_id, entry)

    def log_generic_event(self, agent_id: str, event_name: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log a generic event to devlog."""
        entry = {
            "type": "generic_event",
            "event_name": event_name,
            "details": details or {}
        }
        self.write_devlog_entry(agent_id, entry)

    def get_recent_entries(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent entries from the agent-specific devlog."""
        log_file_path = self.get_devlog_path(agent_id)
        if not log_file_path.exists():
            return []
        try:
            entries = []
            with open(log_file_path, 'r') as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if len(entries) >= limit:
                        break
                    timestamp_str = line[1:line.find("]")]
                    message_content = line[line.find("]") + 2:].strip()
                    entries.append({
                        "timestamp": timestamp_str,
                        "message": message_content
                    })
            return entries
        except Exception as e:
            logger.error(f"Error reading devlog for {agent_id} from {log_file_path}: {e}")
            return []