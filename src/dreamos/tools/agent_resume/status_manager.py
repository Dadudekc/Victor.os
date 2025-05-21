"""
Status Manager Module

Handles agent status tracking and updates.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
import json

logger = logging.getLogger('status_manager')

class StatusManager:
    def __init__(self, status_dir: Path):
        self.status_dir = status_dir
        self.status_dir.mkdir(parents=True, exist_ok=True)
        
    def update_status(self, agent_id: str, status: str, additional_data: dict = None) -> None:
        """Update agent's status file."""
        try:
            status_file = self.status_dir / agent_id / "status.json"
            status_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing status or create new
            if status_file.exists():
                with open(status_file, 'r') as f:
                    status_data = json.load(f)
            else:
                status_data = {
                    "agent_id": agent_id,
                    "status": "inactive",
                    "last_update": None
                }
            
            # Update status
            status_data["status"] = status
            status_data["last_update"] = datetime.now(timezone.utc).isoformat()
            
            # Add any additional data
            if additional_data:
                status_data.update(additional_data)
            
            # Write updated status
            with open(status_file, 'w') as f:
                json.dump(status_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to update status for {agent_id}: {e}")
            
    def get_status(self, agent_id: str) -> dict:
        """Get current status for an agent."""
        try:
            status_file = self.status_dir / agent_id / "status.json"
            if status_file.exists():
                with open(status_file, 'r') as f:
                    return json.load(f)
            return {"status": "unknown"}
        except Exception as e:
            logger.error(f"Failed to get status for {agent_id}: {e}")
            return {"status": "error"} 