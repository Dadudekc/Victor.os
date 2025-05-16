import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from run_continuous_operation import run_continuous_operation
from validate_tasks import validate_all_tasks

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemRunner:
    def __init__(self, queue_dir: Path):
        self.queue_dir = queue_dir
        self.cycle_count = 0
        self.min_cycles = 25
        self.process = None
        self.is_running = False

    def start(self):
        """Start the system and ensure continuous operation."""
        logger.info("Starting system")
        self.is_running = True
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        
        while self.is_running:
            try:
                # Start continuous operation
                self._start_continuous_operation()
                
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
                logger.error(f"Error in system cycle: {e}")
                self._handle_error(e)
                time.sleep(1)

    def _start_continuous_operation(self):
        """Start the continuous operation process."""
        if self.process is None or self.process.poll() is not None:
            # Start new process
            self.process = subprocess.Popen(
                [sys.executable, str(self.queue_dir / "run_continuous_operation.py")],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info("Started continuous operation process")

    def _run_validations(self):
        """Run all validations."""
        try:
            validate_all_tasks(self.queue_dir)
        except Exception as e:
            logger.error(f"Error running validations: {e}")
            self._handle_validation_error(e)

    def _handle_signal(self, signum, frame):
        """Handle system signals."""
        logger.info(f"Received signal {signum}")
        self.is_running = False
        if self.process:
            self.process.terminate()
            self.process.wait()

    def _handle_error(self, error: Exception):
        """Handle system errors."""
        logger.error(f"System error: {error}")
        self.cycle_count = 0  # Reset cycle count
        
        # Log the error
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "system_error",
            "error": str(error),
            "cycle_count": self.cycle_count
        }
        
        log_file = self.queue_dir / "system_errors.jsonl"
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

def run_system(queue_dir: Path):
    """Run the system and ensure continuous operation."""
    runner = SystemRunner(queue_dir)
    runner.start()

if __name__ == "__main__":
    queue_dir = Path(__file__).parent
    run_system(queue_dir) 