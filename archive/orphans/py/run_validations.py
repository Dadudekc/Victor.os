import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from continuous_operation import ContinuousOperationHandler
from validate_tasks import TaskValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValidationRunner:
    def __init__(self, queue_dir: Path):
        self.queue_dir = queue_dir
        self.validator = TaskValidator(queue_dir)
        self.handler = ContinuousOperationHandler(queue_dir)
        self.cycle_count = 0
        self.min_cycles = 25

    def run_validations(self):
        """Run all validations and ensure continuous operation."""
        while True:
            try:
                # Run continuous operation validation
                self._run_validation("validate_continuous_operation.py")
                
                # Run any other validations
                validation_scripts = list(self.queue_dir.glob("validate_*.py"))
                for script in validation_scripts:
                    if script.name != "validate_continuous_operation.py":
                        self._run_validation(script.name)
                
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
                logger.error(f"Error in validation cycle: {e}")
                self._handle_validation_error(e)
                time.sleep(1)

    def _run_validation(self, script_name: str):
        """Run a single validation script."""
        script_path = self.queue_dir / script_name
        if not script_path.exists():
            logger.warning(f"Validation script not found: {script_name}")
            return
        
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Validation passed: {script_name}")
            self._log_validation_result(script_name, True, result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Validation failed: {script_name}")
            self._log_validation_result(script_name, False, e.stderr)
            raise

    def _log_validation_result(self, script_name: str, success: bool, details: str):
        """Log the validation result."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "script": script_name,
            "success": success,
            "details": details,
            "cycle_count": self.cycle_count
        }
        
        log_file = self.queue_dir / "validation_results.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def _handle_validation_error(self, error: Exception):
        """Handle validation errors."""
        logger.error(f"Validation error: {error}")
        self.cycle_count = 0  # Reset cycle count on error
        
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

def run_all_validations(queue_dir: Path):
    """Run all validations and ensure continuous operation."""
    runner = ValidationRunner(queue_dir)
    runner.run_validations()

if __name__ == "__main__":
    queue_dir = Path(__file__).parent
    run_all_validations(queue_dir) 