#!/usr/bin/env python3
"""Manages the Agent Points System ledger."""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import filelock
    FILELOCK_AVAILABLE = True
except ImportError:
    filelock = None
    FILELOCK_AVAILABLE = False

from ..core.config import AppConfig
from ..core.errors import ProjectBoardError, BoardLockError # Reuse PBM errors for now
from ..utils.common_utils import get_utc_iso_timestamp

logger = logging.getLogger(__name__)

DEFAULT_LEDGER_FILENAME = "agent_points.json"
DEFAULT_AUDIT_LOG_FILENAME = "agent_points_audit.log"
DEFAULT_LOCK_TIMEOUT = 10 # Shorter timeout? Or same as PBM?

# --- EDIT START: Define default point values ---
DEFAULT_POINT_VALUES = {
    "task_completion": 10,
    "task_completion_chore": 2,
    "task_failure": -5,
    "unblock_major": 20,
    "unblock_minor": 5,
    "uptime_period": 1,
    "idle_penalty_period": -2,
    "protocol_violation_minor": -1,
    "protocol_violation_major": -3,
    "improvement_award_small": 5,
    "improvement_award_medium": 15,
    "improvement_award_large": 30
}
# --- EDIT END ---

class AgentPointsManager:
    """
    Handles reading, writing, and updating agent points in the ledger file.
    Uses file locking for safe concurrent access.
    """

    def __init__(self, config: AppConfig, lock_timeout: int = DEFAULT_LOCK_TIMEOUT):
        self.config = config
        self.lock_timeout = lock_timeout

        # --- EDIT START: Correct governance_dir path construction ---
        # Assuming self.config.paths.runtime is a resolved Path object from AppConfig
        if hasattr(self.config.paths, 'runtime') and isinstance(self.config.paths.runtime, Path):
            self.governance_dir = (self.config.paths.runtime / "governance").resolve()
        else:
            # Fallback if paths.runtime is not as expected, though AppConfig should ensure it.
            logger.error("AppConfig.paths.runtime is not a valid Path object. Falling back for governance_dir.")
            self.governance_dir = (PROJECT_ROOT / "runtime" / "governance").resolve() # Needs PROJECT_ROOT if AppConfig fails
        # --- EDIT END ---

        self.ledger_path = self.governance_dir / DEFAULT_LEDGER_FILENAME
        self.lock_path = self.ledger_path.with_suffix(".lock")
        self.audit_log_path = self.governance_dir / DEFAULT_AUDIT_LOG_FILENAME
        self.governance_dir.mkdir(parents=True, exist_ok=True)

        # --- EDIT START: Load point values from AppConfig.agent_points_system ---
        self.point_values = DEFAULT_POINT_VALUES.copy() # Start with defaults
        
        if self.config.agent_points_system and isinstance(self.config.agent_points_system.point_values, dict):
            configured_values = self.config.agent_points_system.point_values
            if configured_values: # Check if the dictionary is not empty
                self.point_values.update(configured_values)
                logger.info(f"Loaded custom point values from AppConfig: {configured_values}")
            else:
                logger.info("AppConfig 'agent_points_system.point_values' is present but empty. Using default point values.")
        elif self.config.agent_points_system:
            logger.warning("AppConfig 'agent_points_system.point_values' is not a dictionary. Using default point values.")
        else:
            logger.info("AppConfig section 'agent_points_system' not found or 'point_values' not set. Using default point values.")
        
        logger.debug(f"Final point values in use: {self.point_values}")
        # --- EDIT END ---

        if not FILELOCK_AVAILABLE:
            logger.warning(
                "Filelock library not found. Agent points ledger operations will not be fully concurrency-safe."
            )
        logger.info(f"AgentPointsManager initialized. Ledger: {self.ledger_path}")

    def _get_lock(self) -> Optional[filelock.FileLock]:
        """Gets the file lock object for the ledger file."""
        if not FILELOCK_AVAILABLE:
            return None
        try:
            # Ensure lock directory exists
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            return filelock.FileLock(self.lock_path, timeout=self.lock_timeout)
        except Exception as e:
            logger.error(f"Failed to create FileLock object for {self.lock_path}: {e}", exc_info=True)
            raise ProjectBoardError(f"Failed to initialize lock for {self.lock_path}") from e

    def _read_ledger_file(self) -> dict:
        """Reads the ledger file, handling empty or corrupt files gracefully."""
        if not self.ledger_path.exists():
            logger.warning(f"Ledger file not found: {self.ledger_path}. Initializing default structure.")
            return {"_metadata": {"schema_version": "1.0"}, "points": {}}

        try:
            content = self.ledger_path.read_text(encoding="utf-8")
            if not content.strip():
                logger.warning(f"Ledger file is empty: {self.ledger_path}. Initializing default structure.")
                return {"_metadata": {"schema_version": "1.0"}, "points": {}}
            
            loaded_data = json.loads(content)
            if not isinstance(loaded_data, dict) or "points" not in loaded_data or not isinstance(loaded_data["points"], dict):
                logger.error(f"Invalid ledger file format in {self.ledger_path}. Expected dict with 'points' key. Reinitializing.")
                return {"_metadata": {"schema_version": "1.0"}, "points": {}}
            
            # Ensure metadata exists
            loaded_data.setdefault("_metadata", {}).setdefault("schema_version", "1.0")
            return loaded_data
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.ledger_path}: {e}. Reinitializing.")
            return {"_metadata": {"schema_version": "1.0"}, "points": {}}
        except IOError as e:
            logger.error(f"IOError reading ledger file {self.ledger_path}: {e}. Returning default structure.")
            return {"_metadata": {"schema_version": "1.0"}, "points": {}}
        except Exception as e:
            logger.exception(f"Unexpected error reading ledger file {self.ledger_path}: {e}. Returning default structure.")
            return {"_metadata": {"schema_version": "1.0"}, "points": {}}

    def _load_ledger(self) -> dict:
        """Loads the ledger data using file locking."""
        lock = self._get_lock()
        ledger_data = { } 
        lock_acquired_by_us = False
        try:
            if lock:
                lock.acquire()
                lock_acquired_by_us = True
            ledger_data = self._read_ledger_file()
        except filelock.Timeout as e:
            logger.error(f"Timeout acquiring lock for {self.ledger_path}: {e}")
            raise BoardLockError(f"Timeout acquiring lock for {self.ledger_path}") from e
        except Exception as e:
            logger.error(f"Error during locked read of {self.ledger_path}: {e}", exc_info=True)
            raise ProjectBoardError(f"Failed during locked read of {self.ledger_path}") from e
        finally:
            if lock_acquired_by_us and lock.is_locked:
                try:
                    lock.release()
                except Exception as e_rl:
                    logger.error(f"Failed to release ledger lock: {e_rl}", exc_info=True)
        return ledger_data

    def _atomic_write_ledger(self, ledger_data: dict):
        """Writes ledger data atomically using temp file and rename."""
        temp_file_path = self.ledger_path.with_suffix(f".tmp_{uuid.uuid4().hex}")
        try:
            with open(temp_file_path, "w", encoding="utf-8") as f:
                json.dump(ledger_data, f, indent=2)
            os.replace(temp_file_path, self.ledger_path)
        except Exception as e:
            logger.error(f"Failed atomic write to {self.ledger_path}: {e}", exc_info=True)
            if temp_file_path.exists():
                try: temp_file_path.unlink() # Clean up temp file
                except OSError: pass
            raise ProjectBoardError(f"Atomic write failure for {self.ledger_path}") from e

    def _save_ledger(self, ledger_data: dict):
        """Saves the ledger data using file locking and atomic write."""
        if not isinstance(ledger_data, dict):
            raise TypeError("Ledger data to save must be a dictionary.")

        # Update metadata timestamp before saving
        ledger_data.setdefault("_metadata", {})["last_updated_utc"] = get_utc_iso_timestamp()

        lock = self._get_lock()
        lock_acquired_by_us = False
        try:
            if lock:
                lock.acquire()
                lock_acquired_by_us = True
            self._atomic_write_ledger(ledger_data)
        except filelock.Timeout as e:
            logger.error(f"Timeout acquiring lock for saving {self.ledger_path}: {e}")
            raise BoardLockError(f"Timeout acquiring lock for saving {self.ledger_path}") from e
        except Exception as e:
            logger.error(f"Error during locked save of {self.ledger_path}: {e}", exc_info=True)
            raise ProjectBoardError(f"Failed during locked save of {self.ledger_path}") from e
        finally:
            if lock_acquired_by_us and lock.is_locked:
                try:
                    lock.release()
                except Exception as e_rl:
                    logger.error(f"Failed to release ledger lock after save: {e_rl}", exc_info=True)
                    
    def _log_audit_event(self, agent_id: str, points_change: int, new_total: int, reason: str, related_task_id: Optional[str]):
        """Logs a point change event to the audit log file."""
        try:
            log_entry = {
                "timestamp_utc": get_utc_iso_timestamp(),
                "agent_id": agent_id,
                "points_change": points_change,
                "new_total": new_total,
                "reason": reason,
                "related_task_id": related_task_id
            }
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                json.dump(log_entry, f)
                f.write("\n") # JSON Lines format
        except Exception as e:
            logger.error(f"Failed to write to agent points audit log {self.audit_log_path}: {e}", exc_info=True)

    # --- EDIT START: Add helper to get point value for a reason ---
    def get_points_for_reason(self, reason_key: str) -> int:
        """Gets the point value for a given reason key from the loaded configuration."""
        default_value = 0 
        points = self.point_values.get(reason_key, default_value)
        if points == default_value and reason_key not in self.point_values:
            # Only log warning if key truly missing, not just if value is 0
            logger.warning(f"Point value for reason '{reason_key}' not found in configuration. Defaulting to {default_value}.")
        return points
    # --- EDIT END ---

    # --- Public Methods ---

    def adjust_points(self, agent_id: str, points_change: int, reason: str, related_task_id: Optional[str] = None):
        """Adjusts points for a specific agent and logs the event."""
        if not isinstance(points_change, int):
            logger.error(f"Invalid points_change type: {type(points_change)}. Must be int.")
            return
            
        # This method needs to lock, load, modify, save, unlock
        lock = self._get_lock()
        lock_acquired_by_us = False
        try:
            if lock:
                lock.acquire()
                lock_acquired_by_us = True
                
            ledger_data = self._read_ledger_file()
            points_data = ledger_data.setdefault("points", {})
            
            current_points = points_data.get(agent_id, 0) # Default to 0 for new agents
            new_total = current_points + points_change
            points_data[agent_id] = new_total
            
            # Update metadata (already handled in _save_ledger, but good to have timestamp here too)
            ledger_data.setdefault("_metadata", {})["last_updated_utc"] = get_utc_iso_timestamp()
            
            self._atomic_write_ledger(ledger_data) # Save within lock
            
            # Log audit event AFTER successful save
            self._log_audit_event(agent_id, points_change, new_total, reason, related_task_id)
            
            logger.info(f"Adjusted points for {agent_id} by {points_change}. New total: {new_total}. Reason: {reason}")

        except filelock.Timeout as e:
            logger.error(f"Timeout acquiring lock for adjusting points ({agent_id}): {e}")
            raise BoardLockError(f"Timeout acquiring lock for adjusting points ({agent_id})") from e
        except Exception as e:
            logger.error(f"Error adjusting points for {agent_id}: {e}", exc_info=True)
            raise ProjectBoardError(f"Failed to adjust points for {agent_id}") from e
        finally:
            if lock_acquired_by_us and lock.is_locked:
                try:
                    lock.release()
                except Exception as e_rl:
                    logger.error(f"Failed to release ledger lock after adjust_points: {e_rl}", exc_info=True)

    def get_agent_score(self, agent_id: str) -> int:
        """Gets the current score for a specific agent."""
        ledger_data = self._load_ledger() # Handles locking internally
        return ledger_data.get("points", {}).get(agent_id, 0)

    def get_all_scores(self) -> Dict[str, int]:
        """Gets a dictionary of all agent scores."""
        ledger_data = self._load_ledger() # Handles locking internally
        return ledger_data.get("points", {}).copy() # Return a copy
        
    def determine_captain(self) -> Optional[str]:
        """Determines the current Captain based on the highest score."""
        scores = self.get_all_scores()
        if not scores:
            logger.warning("Cannot determine captain: No scores found in ledger.")
            return None
            
        # Find the agent ID(s) with the maximum score
        max_score = -sys.maxsize - 1 # Initialize with very small number
        captains = []
        for agent_id, score in scores.items():
            if score > max_score:
                max_score = score
                captains = [agent_id]
            elif score == max_score:
                captains.append(agent_id)
                
        if len(captains) == 1:
            captain_id = captains[0]
            logger.info(f"Determined Captain: {captain_id} with {max_score} points.")
            return captain_id
        elif len(captains) > 1:
            # Tie-breaking policy needed. Log warning and return None for now.
            logger.warning(f"Captaincy tie detected between agents: {captains} (Score: {max_score}). No single captain determined.")
            return None
        else: # Should not happen if scores is not empty
            logger.error("Error determining captain: Could not find maximum score.")
            return None

# Example Usage (Conceptual - Requires AppConfig)
# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO)
#     # Need a way to load AppConfig here for standalone testing
#     # config = AppConfig.load(...) 
#     # points_manager = AgentPointsManager(config)
#     # points_manager.adjust_points("Agent-1", 10, "task_completion", "TASK-XYZ")
#     # points_manager.adjust_points("Agent-2", -5, "failure", "TASK-ABC")
#     # print(points_manager.get_all_scores())
#     # print(f"Current Captain: {points_manager.determine_captain()}") 