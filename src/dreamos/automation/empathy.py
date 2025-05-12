"""
DreamOS Empathy Logger
Manages agent empathy logs and emotional state tracking.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class EmpathyLogger:
    def __init__(self, state_dir: str = "runtime/state"):
        self.state_dir = state_dir
        self.log_file = os.path.join(state_dir, "empathy_log.json")
        self._load_state()

    def _load_state(self) -> None:
        """Load the current empathy state."""
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = self._initialize_state()
            self._save_state()

    def _save_state(self) -> None:
        """Save the current empathy state."""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def _initialize_state(self) -> Dict:
        """Initialize a new empathy state."""
        return {
            "episode": 5,
            "last_updated": datetime.utcnow().isoformat(),
            "agents": {
                "JARVIS": self._create_agent_empathy(),
                "ORCHESTRATOR": self._create_agent_empathy(),
                "VALIDATOR": self._create_agent_empathy()
            },
            "system_metrics": {
                "total_entries": 0,
                "last_entry": datetime.utcnow().isoformat()
            }
        }

    def _create_agent_empathy(self) -> Dict:
        """Create initial empathy state for an agent."""
        return {
            "emotional_state": {
                "confidence": 0.85,
                "engagement": 1.0,
                "satisfaction": 1.0
            },
            "interaction_history": [],
            "empathy_patterns": {
                "positive": 0,
                "neutral": 0,
                "negative": 0
            }
        }

    def log_interaction(self, agent: str, interaction_type: str, details: Dict) -> bool:
        """Log an agent interaction."""
        if agent not in self.state["agents"]:
            return False

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": interaction_type,
            "details": details
        }

        self.state["agents"][agent]["interaction_history"].append(entry)
        self.state["system_metrics"]["total_entries"] += 1
        self.state["system_metrics"]["last_entry"] = entry["timestamp"]

        self._save_state()
        return True

    def update_emotional_state(self, agent: str, state_updates: Dict) -> bool:
        """Update an agent's emotional state."""
        if agent not in self.state["agents"]:
            return False

        self.state["agents"][agent]["emotional_state"].update(state_updates)
        self._save_state()
        return True

    def get_agent_empathy(self, agent: str) -> Optional[Dict]:
        """Get the current empathy state of an agent."""
        if agent not in self.state["agents"]:
            return None
        return self.state["agents"][agent]

    def get_system_metrics(self) -> Dict:
        """Get the current system metrics."""
        return self.state["system_metrics"] 