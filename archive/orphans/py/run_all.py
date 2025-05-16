import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from monitor_health import monitor_health
from run_system import run_system
from validate_tasks import validate_all_tasks

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemOrchestrator:
    def __init__(self, queue_dir: Path):
        self.queue_dir = queue_dir
        self.cycle_count = 0
        self.min_cycles = 25
        self.processes = {}
        self.is_running = False

    def start(self):
        """Start all system components."""
        logger.info("Starting system orchestrator")
        self.is_running = True
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        
        # Start all components
        self._start_components()
        
        while self.is_running:
            try:
                # Check component health
                self._check_components()
                
                # Run validations
                validate_all_tasks(self.queue_dir)
                
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
                logger.error(f"Error in orchestrator cycle: {e}")
                self._handle_error(e)
                time.sleep(1)

    def _start_components(self):
        """Start all system components."""
        # Start system
        self.processes["system"] = subprocess.Popen(
            [sys.executable, str(self.queue_dir / "run_system.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info("Started system component")
        
        # Start health monitor
        self.processes["health"] = subprocess.Popen(
            [sys.executable, str(self.queue_dir / "monitor_health.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info("Started health monitor component")

    def _check_components(self):
        """Check the health of all components."""
        for name, process in self.processes.items():
            if process.poll() is not None:
                logger.error(f"Component {name} has stopped")
                self._restart_component(name)

    def _restart_component(self, name: str):
        """Restart a component."""
        logger.info(f"Restarting component {name}")
        
        # Terminate existing process
        if name in self.processes:
            self.processes[name].terminate()
            self.processes[name].wait()
        
        # Start new process
        if name == "system":
            self.processes[name] = subprocess.Popen(
                [sys.executable, str(self.queue_dir / "run_system.py")],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        elif name == "health":
            self.processes[name] = subprocess.Popen(
                [sys.executable, str(self.queue_dir / "monitor_health.py")],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        
        logger.info(f"Component {name} restarted")

    def _handle_signal(self, signum, frame):
        """Handle system signals."""
        logger.info(f"Received signal {signum}")
        self.is_running = False
        
        # Terminate all processes
        for name, process in self.processes.items():
            process.terminate()
            process.wait()
            logger.info(f"Terminated component {name}")

    def _handle_error(self, error: Exception):
        """Handle orchestrator errors."""
        logger.error(f"Orchestrator error: {error}")
        self.cycle_count = 0  # Reset cycle count
        
        # Log the error
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "orchestrator_error",
            "error": str(error),
            "cycle_count": self.cycle_count
        }
        
        log_file = self.queue_dir / "orchestrator_errors.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

def run_all(queue_dir: Path):
    """Run all system components and ensure continuous operation."""
    orchestrator = SystemOrchestrator(queue_dir)
    orchestrator.start()

if __name__ == "__main__":
    queue_dir = Path(__file__).parent
    run_all(queue_dir) 