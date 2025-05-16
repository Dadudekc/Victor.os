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
        self.devlog_dir = self.workspace_root / "runtime/logs"
        self.devlog_path = self.devlog_dir / "devlog.txt"
        
        # Ensure devlog directory exists
        self.devlog_dir.mkdir(parents=True, exist_ok=True)

    def get_devlog_path(self, agent_id: str) -> Path:
        """Get the path to the agent's devlog file."""
        return self.devlog_path

    def write_devlog_entry(self, agent_id: str, entry: Dict[str, Any]) -> None:
        """Write an entry to the devlog file."""
        try:
            # Format timestamp
            timestamp = datetime.now().isoformat()
            
            # Format message based on entry type
            if entry.get("type") == "task_progress":
                message = f"Agent-{agent_id}: Task {entry['task_id']}: {entry['status']} - {entry['details']}"
            elif entry.get("type") == "error":
                message = f"Agent-{agent_id}: Error: {entry['message']}"
                if entry.get("details"):
                    message += f" - {json.dumps(entry['details'])}"
            elif entry.get("type") == "autonomy":
                message = f"Agent-{agent_id}: Autonomy Decision: {entry['decision']} - {entry['reasoning']}"
            else:
                message = f"Agent-{agent_id}: {entry.get('message', 'Unknown entry type')}"
            
            # Write to devlog
            with open(self.devlog_path, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
                
        except Exception as e:
            logger.error(f"Error writing to devlog: {e}")

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

    def get_recent_entries(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent entries from the devlog."""
        try:
            entries = []
            with open(self.devlog_path, 'r') as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if len(entries) >= limit:
                        break
                    if f"Agent-{agent_id}:" in line:
                        # Parse timestamp and message
                        timestamp_str = line[1:line.find("]")]
                        message = line[line.find("]") + 2:].strip()
                        entries.append({
                            "timestamp": timestamp_str,
                            "message": message
                        })
            return entries
        except Exception as e:
            logger.error(f"Error reading devlog: {e}")
            return [] 