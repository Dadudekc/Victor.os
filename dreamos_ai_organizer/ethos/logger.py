"""
Logger Module for Dream.OS Ethos

This module handles logging of emotional context, intent, and system behavior
for the purpose of maintaining and improving ethos compliance.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import threading
from queue import Queue
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmpathyLogger:
    """Handles logging of emotional context and intent."""
    
    def __init__(self):
        self.log_path = Path(__file__).parent.parent / "logs"
        self.log_path.mkdir(exist_ok=True)
        
        # Set up log files
        self.empathy_log = self.log_path / "empathy.log"
        self.action_log = self.log_path / "actions.log"
        self.validation_log = self.log_path / "validation.log"
        
        # Set up async logging
        self.log_queue = Queue()
        self.log_thread = threading.Thread(target=self._process_log_queue, daemon=True)
        self.log_thread.start()
    
    def log_intent(self, intent_type: str, data: Dict[str, Any]):
        """Log an intent with emotional context."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "intent_type": intent_type,
            "data": data
        }
        self.log_queue.put(("empathy", log_entry))
    
    def log_action(self, action: Dict[str, Any], context: Dict[str, Any]):
        """Log an action with its context."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "context": context
        }
        self.log_queue.put(("action", log_entry))
    
    def log_validation(self, validation_result: Dict[str, Any]):
        """Log a validation result."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "validation": validation_result
        }
        self.log_queue.put(("validation", log_entry))
    
    def _process_log_queue(self):
        """Process the log queue asynchronously."""
        while True:
            try:
                log_type, log_entry = self.log_queue.get()
                
                if log_type == "empathy":
                    self._write_log(self.empathy_log, log_entry)
                elif log_type == "action":
                    self._write_log(self.action_log, log_entry)
                elif log_type == "validation":
                    self._write_log(self.validation_log, log_entry)
                
                self.log_queue.task_done()
            except Exception as e:
                logger.error(f"Error processing log entry: {e}")
            
            time.sleep(0.1)  # Prevent CPU spinning
    
    def _write_log(self, log_file: Path, entry: Dict[str, Any]):
        """Write a log entry to the specified file."""
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Error writing to log file {log_file}: {e}")
    
    def get_recent_logs(self, log_type: str, minutes: int = 60) -> list[Dict[str, Any]]:
        """Get recent logs of the specified type."""
        log_file = getattr(self, f"{log_type}_log")
        if not log_file.exists():
            return []
        
        cutoff_time = datetime.now().timestamp() - (minutes * 60)
        recent_logs = []
        
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(entry["timestamp"]).timestamp()
                        if entry_time >= cutoff_time:
                            recent_logs.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error reading log file {log_file}: {e}")
        
        return recent_logs
    
    def analyze_emotional_trends(self, minutes: int = 60) -> Dict[str, Any]:
        """Analyze emotional trends from recent logs."""
        recent_logs = self.get_recent_logs("empathy", minutes)
        
        # Count intent types
        intent_counts = {}
        for log in recent_logs:
            intent_type = log["intent_type"]
            intent_counts[intent_type] = intent_counts.get(intent_type, 0) + 1
        
        # Analyze emotional context
        emotional_contexts = []
        for log in recent_logs:
            if "emotional_context" in log["data"]:
                emotional_contexts.append(log["data"]["emotional_context"])
        
        return {
            "intent_distribution": intent_counts,
            "emotional_contexts": emotional_contexts,
            "total_logs": len(recent_logs)
        }
    
    def get_action_statistics(self, minutes: int = 60) -> Dict[str, Any]:
        """Get statistics about recent actions."""
        recent_logs = self.get_recent_logs("action", minutes)
        
        # Count action types
        action_counts = {}
        for log in recent_logs:
            action_type = log["action"].get("type", "unknown")
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
        
        return {
            "action_distribution": action_counts,
            "total_actions": len(recent_logs)
        }
    
    def get_validation_statistics(self, minutes: int = 60) -> Dict[str, Any]:
        """Get statistics about recent validations."""
        recent_logs = self.get_recent_logs("validation", minutes)
        
        # Count validation results
        validation_results = {
            "compliant": 0,
            "non_compliant": 0,
            "warnings": 0
        }
        
        for log in recent_logs:
            validation = log["validation"]
            if validation.get("is_valid", False):
                validation_results["compliant"] += 1
            else:
                validation_results["non_compliant"] += 1
            
            validation_results["warnings"] += len(validation.get("warnings", []))
        
        return {
            "validation_results": validation_results,
            "total_validations": len(recent_logs)
        } 