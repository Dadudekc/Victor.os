from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, Any, Optional

class AgentAutonomyManager:
    """Core logic for managing agent autonomy, drift detection, and status updates."""
    
    def __init__(self, inbox_base: Path, bridge_file: Optional[Path] = None):
        self.inbox_base = inbox_base
        self.bridge_file = bridge_file or Path("runtime/bridge/queue/agent_prompts.jsonl")
        self.drift_threshold = timedelta(minutes=5)
        
    def detect_drift(self, agent_id: str) -> bool:
        """Check if an agent has drifted based on its last heartbeat.
        
        Args:
            agent_id: The ID of the agent to check
            
        Returns:
            bool: True if agent has drifted, False otherwise
        """
        status = self._load_agent_status(agent_id)
        if not status:
            return False
            
        last_heartbeat = datetime.fromisoformat(status["last_heartbeat"])
        return datetime.utcnow() - last_heartbeat > self.drift_threshold
        
    def should_resume_agent(self, agent_id: str) -> bool:
        """Check if agent should be resumed."""
        status_path = self.inbox_base / agent_id / "status.json"
        if not status_path.exists():
            return True
        status = self._load_agent_status(agent_id)
        return not status.get("loop_active", False)
        
    def mark_agent_resumed(self, agent_id: str) -> None:
        """Mark an agent as resumed and update its status.
        
        Args:
            agent_id: The ID of the agent to mark as resumed
        """
        status = self._load_agent_status(agent_id) or {
            "agent_id": agent_id,
            "current_task": "idle",
            "loop_active": True,
            "compliance_score": 100
        }
        
        status.update({
            "loop_active": True,
            "compliance_score": 100,
            "last_heartbeat": datetime.utcnow().isoformat()
        })
        
        self._save_agent_status(agent_id, status)
        
    def update_agent_status(
        self,
        agent_id: str,
        current_task: Optional[str] = None,
        compliance_score: Optional[int] = None
    ) -> None:
        """Update an agent's status with new information.
        
        Args:
            agent_id: The ID of the agent to update
            current_task: Optional new current task
            compliance_score: Optional new compliance score
        """
        status = self._load_agent_status(agent_id) or {
            "agent_id": agent_id,
            "current_task": "idle",
            "loop_active": True,
            "compliance_score": 100
        }
        
        if current_task is not None:
            status["current_task"] = current_task
        if compliance_score is not None:
            status["compliance_score"] = compliance_score
            
        status["last_heartbeat"] = datetime.utcnow().isoformat()
        self._save_agent_status(agent_id, status)
        
    def enqueue_resume_prompt(self, agent_id: str, reason: str = "Drift detected") -> None:
        """Enqueue a resume prompt for an agent.
        
        Args:
            agent_id: The ID of the agent to resume
            reason: The reason for resuming the agent
        """
        self.bridge_file.parent.mkdir(parents=True, exist_ok=True)
        
        prompt = {
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "prompt": "resume autonomy",
            "reason": reason
        }
        
        with open(self.bridge_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(prompt) + "\n")
            
    def _load_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Load an agent's status from its status file.
        
        Args:
            agent_id: The ID of the agent to load status for
            
        Returns:
            Optional[Dict[str, Any]]: The agent's status or None if not found
        """
        status_path = self.inbox_base / agent_id / "status.json"
        if not status_path.exists():
            return None
            
        try:
            return json.loads(status_path.read_text())
        except (json.JSONDecodeError, IOError):
            return None
            
    def _save_agent_status(self, agent_id: str, status: Dict[str, Any]) -> None:
        """Save an agent's status to its status file.
        
        Args:
            agent_id: The ID of the agent to save status for
            status: The status to save
        """
        status_path = self.inbox_base / agent_id / "status.json"
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(json.dumps(status)) 