import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TaskValidator:
    def __init__(self, queue_dir: Path):
        self.queue_dir = queue_dir
        self.tasks_file = queue_dir / "tasks.jsonl"
        self.completed_tasks_file = queue_dir / "completed_tasks.jsonl"
        self.failed_tasks_file = queue_dir / "failed_tasks.jsonl"

    def validate_all_tasks(self):
        """Validate all tasks and mark them as complete."""
        logger.info("Starting task validation")
        
        # Read all tasks
        tasks = self._read_tasks()
        if not tasks:
            logger.info("No tasks to validate")
            return
        
        # Validate each task
        for task in tasks:
            try:
                self._validate_task(task)
            except Exception as e:
                logger.error(f"Error validating task {task.get('id')}: {e}")
                self._mark_task_failed(task, str(e))

    def _read_tasks(self):
        """Read all tasks from the tasks file."""
        tasks = []
        if self.tasks_file.exists():
            with open(self.tasks_file, "r") as f:
                for line in f:
                    try:
                        task = json.loads(line.strip())
                        tasks.append(task)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in tasks file: {line}")
        return tasks

    def _validate_task(self, task):
        """Validate a single task."""
        task_id = task.get("id")
        logger.info(f"Validating task {task_id}")
        
        # Check task status
        if task.get("status") == "completed":
            logger.info(f"Task {task_id} already completed")
            return
        
        # Validate task requirements
        if not self._validate_requirements(task):
            raise ValueError(f"Task {task_id} requirements not met")
        
        # Mark task as complete
        self._mark_task_complete(task)
        logger.info(f"Task {task_id} validated and marked complete")

    def _validate_requirements(self, task):
        """Validate task requirements."""
        # Check if all required files exist
        required_files = task.get("required_files", [])
        for file_path in required_files:
            if not (self.queue_dir / file_path).exists():
                logger.error(f"Required file {file_path} not found")
                return False
        
        # Check if all required processes are running
        required_processes = task.get("required_processes", [])
        for process_name in required_processes:
            if not self._is_process_running(process_name):
                logger.error(f"Required process {process_name} not running")
                return False
        
        return True

    def _is_process_running(self, process_name):
        """Check if a process is running."""
        try:
            if sys.platform == "win32":
                cmd = f'tasklist /FI "IMAGENAME eq {process_name}"'
            else:
                cmd = f'pgrep -f {process_name}'
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking process {process_name}: {e}")
            return False

    def _mark_task_complete(self, task):
        """Mark a task as complete."""
        task["status"] = "completed"
        task["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        # Write to completed tasks file
        with open(self.completed_tasks_file, "a") as f:
            f.write(json.dumps(task) + "\n")
        
        # Remove from tasks file
        self._remove_task(task)

    def _mark_task_failed(self, task, error):
        """Mark a task as failed."""
        task["status"] = "failed"
        task["failed_at"] = datetime.now(timezone.utc).isoformat()
        task["error"] = error
        
        # Write to failed tasks file
        with open(self.failed_tasks_file, "a") as f:
            f.write(json.dumps(task) + "\n")
        
        # Remove from tasks file
        self._remove_task(task)

    def _remove_task(self, task):
        """Remove a task from the tasks file."""
        tasks = self._read_tasks()
        tasks = [t for t in tasks if t.get("id") != task.get("id")]
        
        with open(self.tasks_file, "w") as f:
            for t in tasks:
                f.write(json.dumps(t) + "\n")

def validate_all_tasks(queue_dir: Path):
    """Validate all tasks and mark them as complete."""
    validator = TaskValidator(queue_dir)
    validator.validate_all_tasks()

if __name__ == "__main__":
    queue_dir = Path(__file__).parent
    validate_all_tasks(queue_dir) 