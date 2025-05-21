import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import time

class RecoverySystem:
    def __init__(self, agent_id: str, workspace_root: str):
        self.agent_id = agent_id
        self.workspace_root = Path(workspace_root)
        self.state_path = self.workspace_root / "runtime" / "agent_comms" / "agent_mailboxes" / agent_id / "state.json"
        self.recovery_path = self.workspace_root / "runtime" / "agent_comms" / "agent_mailboxes" / agent_id / "recovery.json"
        self.last_good_state = None
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
        
    def save_good_state(self, state: Dict):
        """Save a known good state for recovery."""
        self.last_good_state = state.copy()
        try:
            with open(self.recovery_path, "w") as f:
                json.dump({
                    "last_good_state": state,
                    "timestamp": datetime.utcnow().isoformat()
                }, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving good state: {e}")
            
    def load_last_good_state(self) -> Optional[Dict]:
        """Load the last known good state."""
        if self.recovery_path.exists():
            try:
                with open(self.recovery_path, "r") as f:
                    data = json.load(f)
                    return data.get("last_good_state")
            except Exception as e:
                logging.error(f"Error loading last good state: {e}")
        return None
        
    def attempt_recovery(self, current_state: Dict, stopping_condition: str) -> bool:
        """Attempt to recover from a stopping condition."""
        if self.recovery_attempts >= self.max_recovery_attempts:
            logging.error("Max recovery attempts reached")
            return False
            
        self.recovery_attempts += 1
        
        # Try different recovery strategies
        recovery_strategies = [
            self._attempt_state_restore,
            self._attempt_partial_recovery,
            self._attempt_cleanup_recovery
        ]
        
        for strategy in recovery_strategies:
            try:
                if strategy(current_state, stopping_condition):
                    self._log_recovery_attempt(stopping_condition, True, f"Strategy {strategy.__name__} succeeded")
                    return True
            except Exception as e:
                logging.error(f"Recovery strategy {strategy.__name__} failed: {e}")
                continue
                
        self._log_recovery_attempt(stopping_condition, False, "All recovery strategies failed")
        return False
        
    def _attempt_state_restore(self, current_state: Dict, stopping_condition: str) -> bool:
        """Attempt to restore from last good state."""
        last_good_state = self.load_last_good_state()
        if not last_good_state:
            return False
            
        try:
            # Validate state before restoration
            if not self._validate_state(last_good_state):
                return False
                
            # Restore state
            with open(self.state_path, "w") as f:
                json.dump(last_good_state, f, indent=2)
                
            return True
            
        except Exception as e:
            logging.error(f"State restore failed: {e}")
            return False
            
    def _attempt_partial_recovery(self, current_state: Dict, stopping_condition: str) -> bool:
        """Attempt partial recovery by merging good state with current state."""
        last_good_state = self.load_last_good_state()
        if not last_good_state:
            return False
            
        try:
            # Merge states, keeping critical data from current state
            merged_state = last_good_state.copy()
            merged_state.update({
                "last_action": current_state.get("last_action"),
                "next_action": current_state.get("next_action"),
                "recovery_attempts": self.recovery_attempts
            })
            
            # Validate merged state
            if not self._validate_state(merged_state):
                return False
                
            # Save merged state
            with open(self.state_path, "w") as f:
                json.dump(merged_state, f, indent=2)
                
            return True
            
        except Exception as e:
            logging.error(f"Partial recovery failed: {e}")
            return False
            
    def _attempt_cleanup_recovery(self, current_state: Dict, stopping_condition: str) -> bool:
        """Attempt recovery by cleaning up and reinitializing state."""
        try:
            # Create clean state
            clean_state = {
                "cycle_count": 0,
                "last_action": None,
                "next_action": None,
                "recovery_attempts": self.recovery_attempts,
                "last_stop_time": datetime.utcnow().isoformat(),
                "autonomy_score": 0
            }
            
            # Validate clean state
            if not self._validate_state(clean_state):
                return False
                
            # Save clean state
            with open(self.state_path, "w") as f:
                json.dump(clean_state, f, indent=2)
                
            return True
            
        except Exception as e:
            logging.error(f"Cleanup recovery failed: {e}")
            return False
            
    def _validate_state(self, state: Dict) -> bool:
        """Validate state structure and required fields."""
        if not isinstance(state, dict):
            return False
            
        required_fields = [
            "cycle_count",
            "last_action",
            "next_action",
            "recovery_attempts",
            "last_stop_time",
            "autonomy_score"
        ]
        
        return all(field in state for field in required_fields)
        
    def _log_recovery_attempt(self, stopping_condition: str, success: bool, error: str = None):
        """Log recovery attempt details."""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "stopping_condition": stopping_condition,
                "success": success,
                "attempt_number": self.recovery_attempts
            }
            
            if error:
                log_entry["error"] = error
                
            # Append to recovery log
            log_path = self.workspace_root / "runtime" / "logs" / "recovery.log"
            with open(log_path, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logging.error(f"Error logging recovery attempt: {e}")
            
    def reset_recovery_attempts(self):
        """Reset recovery attempt counter."""
        self.recovery_attempts = 0
        
    def get_recovery_status(self) -> Dict:
        """Get current recovery system status."""
        return {
            "recovery_attempts": self.recovery_attempts,
            "max_attempts": self.max_recovery_attempts,
            "has_last_good_state": self.last_good_state is not None,
            "last_recovery_time": self._get_last_recovery_time()
        }
        
    def _get_last_recovery_time(self) -> Optional[str]:
        """Get timestamp of last recovery attempt."""
        log_path = self.workspace_root / "runtime" / "logs" / "recovery.log"
        if not log_path.exists():
            return None
            
        try:
            with open(log_path, "r") as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1])
                    return last_entry.get("timestamp")
        except Exception as e:
            logging.error(f"Error reading last recovery time: {e}")
            
        return None 