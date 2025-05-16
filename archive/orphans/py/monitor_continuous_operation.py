import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from continuous_operation import ContinuousOperationHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContinuousOperationMonitor:
    def __init__(self, queue_dir: Path):
        self.queue_dir = queue_dir
        self.handler = ContinuousOperationHandler(queue_dir)
        self.check_interval = 10  # seconds
        self.last_check = datetime.now(timezone.utc)
        self.alert_threshold = 3  # number of consecutive unhealthy checks before alert

    def check_operation_health(self) -> bool:
        """Check the health of continuous operation."""
        current_time = datetime.now(timezone.utc)
        time_diff = (current_time - self.last_check).total_seconds()
        
        if time_diff < self.check_interval:
            return True
        
        self.last_check = current_time
        status = self.handler.get_operation_status()
        
        if not status["is_healthy"]:
            logger.warning(f"Operation health check failed: {status}")
            self._handle_unhealthy_operation()
            return False
        
        if status["cycle_count"] % 5 == 0:
            logger.info(f"Operation milestone reached: {status}")
        
        return True

    def _handle_unhealthy_operation(self):
        """Handle unhealthy operation state."""
        logger.error("Unhealthy operation detected")
        self.handler.reset_cycle_count()
        
        # Log the unhealthy state
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "unhealthy_operation",
            "status": self.handler.get_operation_status()
        }
        self._append_to_log(log_entry)

    def _append_to_log(self, entry: Dict):
        """Append an entry to the monitor log."""
        log_file = self.queue_dir / "monitor_log.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def start_monitoring(self):
        """Start monitoring continuous operation."""
        logger.info("Starting continuous operation monitoring")
        
        while True:
            try:
                if not self.check_operation_health():
                    logger.error("Operation health check failed")
                
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring: {e}")
                self._handle_unhealthy_operation()
                time.sleep(self.check_interval)

def start_monitoring(queue_dir: Path):
    """Start the continuous operation monitor."""
    monitor = ContinuousOperationMonitor(queue_dir)
    monitor.start_monitoring()

if __name__ == "__main__":
    queue_dir = Path(__file__).parent
    start_monitoring(queue_dir) 