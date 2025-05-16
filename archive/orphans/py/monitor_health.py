import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthMonitor:
    def __init__(self, queue_dir: Path):
        self.queue_dir = queue_dir
        self.health_log = queue_dir / "health_log.jsonl"
        self.cycle_count = 0
        self.min_cycles = 25
        self.process = None
        self.is_running = False

    def start(self):
        """Start monitoring system health."""
        logger.info("Starting health monitor")
        self.is_running = True
        
        while self.is_running:
            try:
                # Check system health
                health_status = self._check_health()
                
                # Log health status
                self._log_health(health_status)
                
                # Increment cycle count
                self.cycle_count += 1
                if self.cycle_count % 5 == 0:
                    logger.info(f"Health check milestone reached: {self.cycle_count}")
                
                # Check if we've met minimum cycles
                if self.cycle_count >= self.min_cycles:
                    logger.info("Minimum cycles met")
                
                # Sleep briefly to prevent CPU overload
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in health check cycle: {e}")
                self._handle_error(e)
                time.sleep(1)

    def _check_health(self):
        """Check the health of the system."""
        health_status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cycle_count": self.cycle_count,
            "system_health": self._check_system_health(),
            "process_health": self._check_process_health(),
            "file_health": self._check_file_health(),
            "overall_health": True
        }
        
        # Update overall health
        health_status["overall_health"] = all([
            health_status["system_health"],
            health_status["process_health"],
            health_status["file_health"]
        ])
        
        return health_status

    def _check_system_health(self):
        """Check the health of the system resources."""
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                logger.warning(f"High CPU usage: {cpu_percent}%")
                return False
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                logger.warning(f"High memory usage: {memory.percent}%")
                return False
            
            # Check disk usage
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                logger.warning(f"High disk usage: {disk.percent}%")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return False

    def _check_process_health(self):
        """Check the health of required processes."""
        try:
            # Check if Python process is running
            python_running = False
            for proc in psutil.process_iter(['name']):
                if 'python' in proc.info['name'].lower():
                    python_running = True
                    break
            
            if not python_running:
                logger.warning("Python process not running")
                return False
            
            # Check if required processes are running
            required_processes = ["run_continuous_operation.py", "validate_tasks.py"]
            for process_name in required_processes:
                process_running = False
                for proc in psutil.process_iter(['cmdline']):
                    if proc.info['cmdline'] and process_name in proc.info['cmdline'][-1]:
                        process_running = True
                        break
                
                if not process_running:
                    logger.warning(f"Required process {process_name} not running")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking process health: {e}")
            return False

    def _check_file_health(self):
        """Check the health of required files."""
        try:
            # Check if required files exist
            required_files = [
                "tasks.jsonl",
                "completed_tasks.jsonl",
                "failed_tasks.jsonl",
                "health_log.jsonl"
            ]
            
            for file_name in required_files:
                if not (self.queue_dir / file_name).exists():
                    logger.warning(f"Required file {file_name} not found")
                    return False
            
            # Check if files are accessible
            for file_name in required_files:
                try:
                    with open(self.queue_dir / file_name, "a") as f:
                        pass
                except Exception as e:
                    logger.warning(f"File {file_name} not accessible: {e}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking file health: {e}")
            return False

    def _log_health(self, health_status):
        """Log the health status."""
        with open(self.health_log, "a") as f:
            f.write(json.dumps(health_status) + "\n")

    def _handle_error(self, error: Exception):
        """Handle health check errors."""
        logger.error(f"Health check error: {error}")
        self.cycle_count = 0  # Reset cycle count
        
        # Log the error
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "health_check_error",
            "error": str(error),
            "cycle_count": self.cycle_count
        }
        
        with open(self.health_log, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

def monitor_health(queue_dir: Path):
    """Monitor system health and ensure continuous operation."""
    monitor = HealthMonitor(queue_dir)
    monitor.start()

if __name__ == "__main__":
    queue_dir = Path(__file__).parent
    monitor_health(queue_dir) 