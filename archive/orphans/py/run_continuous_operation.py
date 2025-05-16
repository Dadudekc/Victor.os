import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from continuous_operation import ContinuousOperationHandler
from monitor_continuous_operation import ContinuousOperationMonitor
from run_validations import ValidationRunner
from validate_tasks import TaskValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContinuousOperationSystem:
    def __init__(self, queue_dir: Path):
        self.queue_dir = queue_dir
        self.handler = ContinuousOperationHandler(queue_dir)
        self.monitor = ContinuousOperationMonitor(queue_dir)
        self.validator = TaskValidator(queue_dir)
        self.runner = ValidationRunner(queue_dir)
        self.cycle_count = 0
        self.min_cycles = 25

    def run(self):
        """Run the continuous operation system."""
        logger.info("Starting continuous operation system")
        
        while True:
            try:
                # Check operation health
                if not self.monitor.check_operation_health():
                    logger.error("Operation health check failed")
                    self._handle_health_failure()
                    continue
                
                # Process any pending prompts
                self._process_pending_prompts()
                
                # Run validations
                self._run_validations()
                
                # Increment cycle count
                self.cycle_count += 1
                if self.cycle_count % 5 == 0:
                    logger.info(f"Cycle milestone reached: {self.cycle_count}")
                
                # Check if we've met minimum cycles
                if self.cycle_count >= self.min_cycles:
                    logger.info("Minimum cycles met")
                
                # Sleep briefly to prevent CPU overload
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in operation cycle: {e}")
                self._handle_operation_error(e)
                time.sleep(1)

    def _process_pending_prompts(self):
        """Process any pending prompts in the queue."""
        prompts_file = self.queue_dir / "agent_prompts.jsonl"
        if not prompts_file.exists():
            return
        
        with open(prompts_file) as f:
            for line in f:
                try:
                    prompt = json.loads(line)
                    self.handler.process_prompt(
                        prompt["agent_id"],
                        prompt["prompt"]
                    )
                except Exception as e:
                    logger.error(f"Error processing prompt: {e}")

    def _run_validations(self):
        """Run all validations."""
        try:
            self.runner.run_validations()
        except Exception as e:
            logger.error(f"Error running validations: {e}")
            self._handle_validation_error(e)

    def _handle_health_failure(self):
        """Handle operation health failure."""
        logger.error("Operation health failure detected")
        self.cycle_count = 0  # Reset cycle count
        
        # Log the failure
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "health_failure",
            "cycle_count": self.cycle_count
        }
        
        log_file = self.queue_dir / "health_failures.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def _handle_operation_error(self, error: Exception):
        """Handle operation errors."""
        logger.error(f"Operation error: {error}")
        self.cycle_count = 0  # Reset cycle count
        
        # Log the error
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "operation_error",
            "error": str(error),
            "cycle_count": self.cycle_count
        }
        
        log_file = self.queue_dir / "operation_errors.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def _handle_validation_error(self, error: Exception):
        """Handle validation errors."""
        logger.error(f"Validation error: {error}")
        self.cycle_count = 0  # Reset cycle count
        
        # Log the error
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "validation_error",
            "error": str(error),
            "cycle_count": self.cycle_count
        }
        
        log_file = self.queue_dir / "validation_errors.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

def run_continuous_operation(queue_dir: Path):
    """Run the continuous operation system."""
    system = ContinuousOperationSystem(queue_dir)
    system.run()

if __name__ == "__main__":
    queue_dir = Path(__file__).parent
    run_continuous_operation(queue_dir) 