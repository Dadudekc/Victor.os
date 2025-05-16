import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class ContinuousOperationHandler:
    def __init__(self, queue_dir: Path):
        self.queue_dir = queue_dir
        self.prompts_file = queue_dir / "agent_prompts.jsonl"
        self.cycle_count = 0
        self.last_cycle_time = datetime.now(timezone.utc)
        self.min_cycles = 25
        self.cycle_timeout = 60  # seconds

    def check_cycle_health(self) -> bool:
        """Check if the current cycle is healthy and continuous."""
        current_time = datetime.now(timezone.utc)
        time_diff = (current_time - self.last_cycle_time).total_seconds()
        
        if time_diff > self.cycle_timeout:
            self.reset_cycle_count()
            return False
        
        return True

    def reset_cycle_count(self):
        """Reset the cycle count when a stop is detected."""
        self.cycle_count = 0
        self.last_cycle_time = datetime.now(timezone.utc)
        self.log_cycle_reset("Cycle timeout detected")

    def increment_cycle(self):
        """Increment the cycle count and update the last cycle time."""
        self.cycle_count += 1
        self.last_cycle_time = datetime.now(timezone.utc)
        
        if self.cycle_count % 5 == 0:
            self.log_cycle_milestone()

    def log_cycle_reset(self, reason: str):
        """Log when the cycle count is reset."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "cycle_reset",
            "reason": reason,
            "cycle_count": self.cycle_count
        }
        self._append_to_log(log_entry)

    def log_cycle_milestone(self):
        """Log cycle milestones."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "cycle_milestone",
            "cycle_count": self.cycle_count
        }
        self._append_to_log(log_entry)

    def _append_to_log(self, entry: Dict):
        """Append an entry to the operation log."""
        log_file = self.queue_dir / "operation_log.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def process_prompt(self, agent_id: str, prompt: str) -> bool:
        """Process a prompt and ensure continuous operation."""
        if not self.check_cycle_health():
            return False

        # Record the prompt
        prompt_entry = {
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": prompt
        }
        
        with open(self.prompts_file, "a") as f:
            f.write(json.dumps(prompt_entry) + "\n")

        # Increment cycle and check health
        self.increment_cycle()
        return self.cycle_count >= self.min_cycles

    def get_operation_status(self) -> Dict:
        """Get the current operation status."""
        return {
            "cycle_count": self.cycle_count,
            "last_cycle_time": self.last_cycle_time.isoformat(),
            "is_healthy": self.check_cycle_health(),
            "min_cycles_met": self.cycle_count >= self.min_cycles
        }

def ensure_continuous_operation(queue_dir: Path) -> ContinuousOperationHandler:
    """Create and return a continuous operation handler."""
    handler = ContinuousOperationHandler(queue_dir)
    return handler 