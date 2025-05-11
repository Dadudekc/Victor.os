"""
MIDNIGHT.MISSION.RUNNER
Core system for overnight operation cycles.

Features:
- State management and persistence
- Recovery protocols
- Night cycle detection and handling
- Resource optimization
- Health monitoring
- Event logging
"""

import json
import logging
import queue
import signal
import sys
import time
from datetime import datetime
from datetime import time as dtime
from pathlib import Path
from typing import Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("runtime/logs/midnight_runner.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class MidnightRunner:
    def __init__(self):
        self.state_file = Path("runtime/state/midnight_runner_state.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.event_queue = queue.Queue()
        self.is_running = False
        self.current_cycle = 0
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
        self.state = self._load_state()

        # Night cycle configuration
        self.night_start = dtime(22, 0)  # 10 PM
        self.night_end = dtime(6, 0)  # 6 AM
        self.resource_reduction = 0.5  # 50% resource reduction during night

    def _load_state(self) -> Dict:
        """Load runner state from persistent storage."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
        return {
            "last_cycle": 0,
            "recovery_count": 0,
            "last_error": None,
            "night_mode": False,
            "active_tasks": [],
            "health_metrics": {},
        }

    def _save_state(self):
        """Persist current state to storage."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def is_night_cycle(self) -> bool:
        """Determine if current time is within night cycle."""
        current_time = datetime.now().time()
        return current_time >= self.night_start or current_time < self.night_end

    def adjust_resources(self):
        """Adjust system resources based on cycle time."""
        if self.is_night_cycle():
            logger.info("Night cycle detected - reducing resource usage")
            # Implement resource reduction logic here
            self.state["night_mode"] = True
        else:
            logger.info("Day cycle detected - normal resource usage")
            self.state["night_mode"] = False
        self._save_state()

    def monitor_health(self):
        """Monitor system health metrics."""
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "cycle": self.current_cycle,
            "recovery_attempts": self.recovery_attempts,
            "night_mode": self.is_night_cycle(),
            "active_tasks": len(self.state["active_tasks"]),
            "memory_usage": self._get_memory_usage(),
            "cpu_usage": self._get_cpu_usage(),
        }
        self.state["health_metrics"] = metrics
        self._save_state()
        return metrics

    def _get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        try:
            import psutil

            return psutil.Process().memory_percent()
        except ImportError:
            return 0.0

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            import psutil

            return psutil.Process().cpu_percent()
        except ImportError:
            return 0.0

    def handle_recovery(self, error: Exception):
        """Handle system recovery from errors."""
        self.recovery_attempts += 1
        self.state["last_error"] = str(error)
        self.state["recovery_count"] = self.recovery_attempts

        if self.recovery_attempts > self.max_recovery_attempts:
            logger.error(
                "Max recovery attempts exceeded - initiating emergency shutdown"
            )
            self.emergency_shutdown()
        else:
            logger.warning(
                f"Recovery attempt {self.recovery_attempts}/{self.max_recovery_attempts}"
            )
            self._save_state()
            self._execute_recovery_protocol()

    def _execute_recovery_protocol(self):
        """Execute system recovery protocols."""
        # 1. Save current state
        self._save_state()

        # 2. Clear event queue
        while not self.event_queue.empty():
            self.event_queue.get()

        # 3. Reset critical components
        self._reset_components()

        # 4. Verify system state
        if self._verify_system_state():
            logger.info("Recovery protocol completed successfully")
            self.recovery_attempts = 0
        else:
            logger.error("Recovery protocol failed - system may be unstable")

    def _reset_components(self):
        """Reset critical system components."""
        # Implement component reset logic here
        pass

    def _verify_system_state(self) -> bool:
        """Verify system state after recovery."""
        # Implement state verification logic here
        return True

    def emergency_shutdown(self):
        """Execute emergency shutdown procedures."""
        logger.critical("Initiating emergency shutdown")
        self._save_state()
        self.is_running = False
        # Implement cleanup and shutdown logic here
        sys.exit(1)

    def run_cycle(self):
        """Execute a single operation cycle."""
        try:
            self.current_cycle += 1
            logger.info(f"Starting cycle {self.current_cycle}")

            # 1. Check and adjust resources
            self.adjust_resources()

            # 2. Monitor health
            health_metrics = self.monitor_health()
            logger.info(f"Health metrics: {health_metrics}")

            # 3. Process events
            self._process_events()

            # 4. Update state
            self.state["last_cycle"] = self.current_cycle
            self._save_state()

            logger.info(f"Cycle {self.current_cycle} completed successfully")

        except Exception as e:
            logger.error(f"Error in cycle {self.current_cycle}: {e}")
            self.handle_recovery(e)

    def _process_events(self):
        """Process pending events in the queue."""
        while not self.event_queue.empty():
            try:
                event = self.event_queue.get_nowait()
                self._handle_event(event)
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    def _handle_event(self, event: Dict):
        """Handle a single event."""
        event_type = event.get("type")
        if event_type == "TASK_COMPLETE":
            self._handle_task_completion(event)
        elif event_type == "ERROR":
            self._handle_error_event(event)
        elif event_type == "STATE_CHANGE":
            self._handle_state_change(event)
        else:
            logger.warning(f"Unknown event type: {event_type}")

    def _handle_task_completion(self, event: Dict):
        """Handle task completion event."""
        task_id = event.get("task_id")
        if task_id in self.state["active_tasks"]:
            self.state["active_tasks"].remove(task_id)
            logger.info(f"Task {task_id} completed and removed from active tasks")

    def _handle_error_event(self, event: Dict):
        """Handle error event."""
        error = event.get("error")
        logger.error(f"Error event received: {error}")
        self.handle_recovery(Exception(error))

    def _handle_state_change(self, event: Dict):
        """Handle state change event."""
        new_state = event.get("new_state")
        logger.info(f"State change event received: {new_state}")
        self.state.update(new_state)
        self._save_state()

    def start(self):
        """Start the midnight runner."""
        logger.info("Starting MIDNIGHT.MISSION.RUNNER")
        self.is_running = True

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        try:
            while self.is_running:
                self.run_cycle()
                time.sleep(60)  # Run cycle every minute
        except Exception as e:
            logger.error(f"Fatal error in runner: {e}")
            self.emergency_shutdown()

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received shutdown signal {signum}")
        self.is_running = False
        self._save_state()
        sys.exit(0)


if __name__ == "__main__":
    runner = MidnightRunner()
    runner.start()
