"""Pending Task Monitor for Dream.OS.

Monitors tasks that have been in PENDING state for too long and handles them
according to configured escalation strategies.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from ..nexus.task_nexus import Task, TaskNexus

logger = logging.getLogger(__name__)


class PendingTaskMonitor:
    """Monitors tasks that have been in PENDING state for too long."""

    def __init__(self, task_nexus: TaskNexus, config: Dict[str, Any]):
        """Initialize the PendingTaskMonitor.

        Args:
            task_nexus: The TaskNexus instance to monitor
            config: Configuration dictionary with keys:
                - pending_timeout_seconds: Time in seconds before a PENDING task is considered stalled
                - escalation_strategy: Strategy for handling stalled tasks
                  (log_only, mark_stalled, reassign, escalate)
        """
        self.task_nexus = task_nexus
        self.config = config
        self.last_check_time = datetime.now(timezone.utc)
        logger.info("PendingTaskMonitor initialized with config: %s", config)

    async def check_pending_tasks(self) -> None:
        """Check for tasks that have been in PENDING state for too long."""
        current_time = datetime.now(timezone.utc)
        pending_tasks = self.task_nexus.get_all_tasks(status="pending")

        logger.debug(f"Checking {len(pending_tasks)} pending tasks")

        stalled_count = 0
        for task in pending_tasks:
            # Parse the created_at timestamp
            try:
                created_at = datetime.fromisoformat(
                    task.created_at.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                logger.warning(f"Invalid timestamp format for task {task.task_id}")
                continue

            # Calculate time in PENDING state
            time_pending = current_time - created_at

            # Check if task has been pending for too long
            timeout_seconds = self.config.get("pending_timeout_seconds", 3600)
            if time_pending.total_seconds() > timeout_seconds:
                await self._handle_stalled_task(task)
                stalled_count += 1

        if stalled_count > 0:
            logger.info(f"Found and handled {stalled_count} stalled tasks")

        self.last_check_time = current_time

    async def _handle_stalled_task(self, task: Task) -> None:
        """Handle a task that has been in PENDING state for too long.

        Args:
            task: The stalled task to handle
        """
        escalation_strategy = self.config.get("escalation_strategy", "log_only")
        logger.info(
            f"Handling stalled task {task.task_id} with strategy: {escalation_strategy}"
        )

        if escalation_strategy == "log_only":
            logger.warning(f"Task {task.task_id} has been PENDING for too long")

        elif escalation_strategy == "mark_stalled":
            self.task_nexus.update_task_status(task.task_id, "stalled")
            logger.info(f"Marked task {task.task_id} as STALLED")

        elif escalation_strategy == "reassign":
            # Logic to reassign the task to another agent
            self.task_nexus.update_task_status(
                task.task_id, "pending"
            )  # Reset to pending
            # Clear claimed_by field if it exists
            # This would require extending the update_task_status method
            logger.info(f"Reset task {task.task_id} to PENDING for reassignment")

        elif escalation_strategy == "escalate":
            # Create a new escalation task
            escalation_task = {
                "task_id": f"escalation_{task.task_id}_{uuid.uuid4().hex[:8]}",
                "description": f"Investigate stalled task: {task.task_id}",
                "priority": "high",
                "tags": ["escalation", "stalled_task"],
                "related_task_id": task.task_id,
            }
            try:
                self.task_nexus.add_task(escalation_task)
                logger.info(
                    f"Created escalation task {escalation_task['task_id']} for stalled task {task.task_id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to create escalation task for {task.task_id}: {e}"
                )
        else:
            logger.warning(f"Unknown escalation strategy: {escalation_strategy}")
