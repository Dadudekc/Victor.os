import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


class OperationStateManager:
    def __init__(self, state_file_path: str):
        self.state_file_path = state_file_path
        self.state = self._load_state()
        
    def _load_state(self) -> Dict[str, Any]:
        """Load the current state from file."""
        if not os.path.exists(self.state_file_path):
            return self._create_initial_state()
            
        try:
            with open(self.state_file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading state: {e}")
            return self._create_initial_state()
            
    def _create_initial_state(self) -> Dict[str, Any]:
        """Create initial state structure."""
        return {
            "agent_id": "Agent-1",
            "last_update": datetime.utcnow().isoformat() + "Z",
            "current_cycle": 0,
            "target_cycles": 25,
            "operation_state": "initialized",
            "last_known_good_state": {
                "cycle": 0,
                "state": "initialized",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            "recovery_context": {
                "last_error": None,
                "retry_count": 0,
                "max_retries": 3
            },
            "continuous_operation_metrics": {
                "total_cycles": 0,
                "successful_cycles": 0,
                "failed_cycles": 0,
                "recovery_attempts": 0,
                "last_violation": None
            }
        }
        
    def save_state(self) -> None:
        """Save current state to file."""
        try:
            with open(self.state_file_path, 'w') as f:
                json.dump(self.state, f, indent=4)
        except Exception as e:
            print(f"Error saving state: {e}")
            
    def update_cycle(self, success: bool = True) -> None:
        """Update cycle count and metrics."""
        self.state["current_cycle"] += 1
        self.state["last_update"] = datetime.utcnow().isoformat() + "Z"
        self.state["continuous_operation_metrics"]["total_cycles"] += 1
        
        if success:
            self.state["continuous_operation_metrics"]["successful_cycles"] += 1
            self.state["last_known_good_state"] = {
                "cycle": self.state["current_cycle"],
                "state": self.state["operation_state"],
                "timestamp": self.state["last_update"]
            }
        else:
            self.state["continuous_operation_metrics"]["failed_cycles"] += 1
            
        self.save_state()
        
    def record_violation(self, violation_type: str, details: str) -> None:
        """Record a protocol violation."""
        self.state["continuous_operation_metrics"]["last_violation"] = {
            "type": violation_type,
            "details": details,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        self.state["current_cycle"] = 0  # Reset cycle count on violation
        self.save_state()
        
    def update_operation_state(self, new_state: str) -> None:
        """Update the current operation state."""
        self.state["operation_state"] = new_state
        self.state["last_update"] = datetime.utcnow().isoformat() + "Z"
        self.save_state()
        
    def record_error(self, error: str) -> None:
        """Record an error in the recovery context."""
        self.state["recovery_context"]["last_error"] = error
        self.state["recovery_context"]["retry_count"] += 1
        self.state["continuous_operation_metrics"]["recovery_attempts"] += 1
        self.save_state()
        
    def reset_recovery_context(self) -> None:
        """Reset the recovery context after successful recovery."""
        self.state["recovery_context"] = {
            "last_error": None,
            "retry_count": 0,
            "max_retries": 3
        }
        self.save_state()
        
    def get_state(self) -> Dict[str, Any]:
        """Get the current state."""
        return self.state.copy()
        
    def should_continue(self) -> bool:
        """Check if operation should continue based on current state."""
        return (
            self.state["current_cycle"] < self.state["target_cycles"] and
            self.state["recovery_context"]["retry_count"] < self.state["recovery_context"]["max_retries"]
        ) 