#!/usr/bin/env python3
"""
AutoTaskClaimer Agent
- Periodically scans all master_tasks_*.json for unclaimed tasks
- Claims the first PENDING task by setting its status to "CLAIMED" and "claimed_by" to this agent's ID
- Uses file_lock_manager for atomic JSON operations
"""
import time
import logging
from pathlib import Path
from _agent_coordination.tools.file_lock_manager import read_json, write_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AGENT_ID = "agent_005"
TASKS_DIR = Path(__file__).resolve().parent.parent / 'tasks'
GLOB_PATTERN = 'master_tasks_*.json'
POLL_INTERVAL = 5  # seconds between scans


def claim_next_task():
    for task_file in TASKS_DIR.glob(GLOB_PATTERN):
        tasks = read_json(task_file)
        if not isinstance(tasks, list):
            continue
        for idx, task in enumerate(tasks):
            if task.get('status') == 'PENDING':
                task['status'] = 'CLAIMED'
                task['claimed_by'] = AGENT_ID
                # Write updated tasks list back
                write_json(task_file, tasks)
                logger.info(f"Claimed task from {task_file.name}: {task.get('description', task)}")
                return True
    return False


def main():
    logger.info("AutoTaskClaimer started.")
    while True:
        claimed = claim_next_task()
        if claimed:
            logger.info("Task claimed, exiting AutoTaskClaimer loop.")
            break
        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main() 
