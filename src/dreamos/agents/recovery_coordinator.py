from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from dreamos.coordination.agent_bus import AgentBus, BaseEvent, EventType

# Core Dream.OS components
from dreamos.core.coordination.base_agent import BaseAgent, TaskMessage, TaskStatus
from dreamos.core.logging.swarm_logger import log_agent_event  # Added Swarm Logger
from dreamos.core.memory.task_memory_api import PersistentTaskMemoryAPI

# Assume settings are available, e.g., from a config module
# from dreamos.config import settings # Example import

# --- Configuration (Replace with actual config loading) ---
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY_SECONDS = 60  # 1 minute delay between retries
DEFAULT_POLL_INTERVAL_SECONDS = 300  # Check for failed/stuck tasks every 5 minutes
DEFAULT_TASK_TIMEOUT_SECONDS = (
    900  # Timeout for tasks stuck in RUNNING state (15 minutes)
)
# --- End Configuration ---

logger = logging.getLogger(__name__)

# Define Event Topics
TASK_TIMEOUT_EVENT_TOPIC = "system.recovery.event.timeout"


class RecoveryCoordinatorAgent(BaseAgent):
    """
    Monitors for failed and timed-out tasks.
    Attempts retries for failed tasks based on a configured strategy.
    Marks tasks as permanently failed if retries are exhausted or critical errors occur.
    Marks tasks as failed if they run longer than the configured timeout.
    """

    def __init__(
        self,
        agent_id: str,
        agent_bus: AgentBus,
        task_memory: PersistentTaskMemoryAPI,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay_seconds: int = DEFAULT_RETRY_DELAY_SECONDS,
        poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
        task_timeout_seconds: int = DEFAULT_TASK_TIMEOUT_SECONDS,
    ):  # Added task_timeout_seconds
        """
        Initialize the Recovery Coordinator.

        Args:
            agent_id: Unique ID for this agent.
            agent_bus: The shared AgentBus instance.
            task_memory: The PersistentTaskMemoryAPI instance.
            max_retries: Maximum number of times to retry a failed task.
            retry_delay_seconds: Minimum delay before retrying a failed task.
            poll_interval_seconds: How often to check for failed/running tasks.
            task_timeout_seconds: Maximum allowed runtime for a task before being marked as failed.
        """  # noqa: E501
        super().__init__(agent_id, agent_bus)
        self.task_memory = task_memory
        self.max_retries = max_retries
        self.retry_delay = timedelta(seconds=retry_delay_seconds)
        self.poll_interval = poll_interval_seconds
        self.task_timeout = timedelta(
            seconds=task_timeout_seconds
        )  # Store timeout threshold
        self._monitor_task: Optional[asyncio.Task] = None

        logger.info(
            f"RecoveryCoordinatorAgent '{agent_id}' initialized. "
            f"Max Retries: {self.max_retries}, Delay: {self.retry_delay}, Poll Interval: {self.poll_interval}s, "  # noqa: E501
            f"Task Timeout: {self.task_timeout}"  # Log timeout
        )

    async def _on_start(self):
        """Start the background monitoring task when the agent starts."""
        await super()._on_start()  # Call base class start logic if any
        if not self._monitor_task or self._monitor_task.done():
            logger.info("Starting task monitoring loop (Failed & Running)...")
            self._monitor_task = asyncio.create_task(self._monitor_tasks())
        else:
            logger.warning("Monitoring task already running.")

    async def _on_stop(self):
        """Stop the background monitoring task when the agent stops."""
        logger.info("Stopping task monitoring loop...")
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                logger.info("Monitoring task successfully cancelled.")
            except Exception as e:
                logger.error(
                    f"Error during monitoring task cancellation: {e}", exc_info=True
                )
        await super()._on_stop()  # Call base class stop logic

    async def _monitor_tasks(self):
        """Periodically polls the task memory for failed AND stuck tasks and handles them."""  # noqa: E501
        while self._running:
            try:
                # --- Check for FAILED tasks ---
                logger.debug("Checking for FAILED tasks...")
                failed_tasks = await self.task_memory.get_tasks_by_status(
                    TaskStatus.FAILED, limit=100
                )
                if failed_tasks:
                    logger.info(
                        f"Found {len(failed_tasks)} FAILED tasks to evaluate for recovery."  # noqa: E501
                    )
                    for task in failed_tasks:
                        await self._handle_failed_task(task)
                else:
                    logger.debug("No FAILED tasks found.")

                # --- Check for STUCK (Timed Out) tasks ---
                logger.debug("Checking for STUCK (running too long) tasks...")
                # Define statuses that indicate a task is actively running
                stuck_statuses_to_check = [
                    TaskStatus.RUNNING,
                    # Add other relevant states if they are persisted and could get stuck, e.g.:  # noqa: E501
                    # TaskStatus.INJECTING,
                    # TaskStatus.AWAITING_RESPONSE,
                    # TaskStatus.COPYING
                ]
                stuck_tasks = []
                for status in stuck_statuses_to_check:
                    # Fetch tasks potentially stuck in this state
                    # We need tasks sorted by update time to potentially process older ones first if needed  # noqa: E501
                    # The memory API might need enhancement for efficient querying based on time + status.  # noqa: E501
                    # For now, fetch all and filter. Limit fetched tasks per status.
                    candidate_tasks = await self.task_memory.get_tasks_by_status(
                        status, limit=200
                    )
                    if candidate_tasks:
                        stuck_tasks.extend(candidate_tasks)

                if stuck_tasks:
                    logger.info(
                        f"Found {len(stuck_tasks)} potentially STUCK tasks ({'/'.join(s.name for s in stuck_statuses_to_check)}) to evaluate for timeout."  # noqa: E501
                    )
                    now = datetime.now(timezone.utc)
                    for task in stuck_tasks:
                        # Ensure task has an updated_at timestamp to check against
                        if task.updated_at:
                            time_since_update = now - task.updated_at
                            if time_since_update >= self.task_timeout:
                                logger.warning(
                                    f"Task {task.task_id} ({task.status.name}) timed out! "  # noqa: E501
                                    f"Last update was {time_since_update} ago (Threshold: {self.task_timeout})."  # noqa: E501
                                )
                                await self._handle_timed_out_task(task)
                        else:
                            logger.warning(
                                f"Cannot check timeout for task {task.task_id}: Missing 'updated_at' timestamp."  # noqa: E501
                            )
                else:
                    logger.debug("No potentially STUCK tasks found.")
                # --- End STUCK Check ---

            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                # Avoid tight loop on persistent errors
                await asyncio.sleep(self.poll_interval / 2)

            # Wait for the next poll interval
            await asyncio.sleep(self.poll_interval)

        logger.info("Task monitoring loop stopped.")

    async def _handle_failed_task(self, task: TaskMessage):
        """Evaluates a failed task and decides whether to retry or mark as permanent failure."""  # noqa: E501
        if not task or not task.updated_at:
            logger.warning(f"Skipping invalid failed task data: {task}")
            return

        # No need for 'now = datetime.now(timezone.utc)' as it's passed in
        time_since_failure = datetime.now(timezone.utc) - task.updated_at

        # Check retry count
        if task.retry_count < self.max_retries:
            # Check retry delay
            if time_since_failure >= self.retry_delay:
                logger.info(
                    f"Task {task.task_id} eligible for retry ({task.retry_count + 1}/{self.max_retries})."  # noqa: E501
                )
                await self._reschedule_task(task)
            else:
                logger.debug(
                    f"Task {task.task_id} failed too recently ({time_since_failure} < {self.retry_delay}). Waiting."  # noqa: E501
                )
        else:
            # Max retries exceeded
            logger.warning(
                f"Task {task.task_id} exceeded max retries ({self.max_retries}). Marking as permanently failed."  # noqa: E501
            )
            await self._mark_permanently_failed(task)

    async def _reschedule_task(self, task: TaskMessage):
        """Updates task status and publishes a command to re-trigger execution."""
        original_agent_id = task.agent_id
        if not original_agent_id:
            # Log the event
            log_agent_event(
                agent_id=self.agent_id,
                action="reschedule_failed",
                target=task.task_id,
                outcome="failure",
                details={"reason": "Missing original agent ID"},
                escalation=True,
            )
            await self._mark_permanently_failed(
                task, reason="Missing original agent ID"
            )
            return

        # Log retry attempt
        log_agent_event(
            agent_id=self.agent_id,
            action="reschedule_attempt",
            target=task.task_id,
            outcome="pending",
            details={
                "retry_count": task.retry_count + 1,
                "max_retries": self.max_retries,
                "original_agent": original_agent_id,
            },
        )

        # 1. Update task state in memory
        task = update_task_status(  # noqa: F821
            task,
            TaskStatus.PENDING,
            error=f"Retrying after previous failure. Attempt {task.retry_count + 1}.",
        )
        task.retry_count += 1

        update_success = await self.task_memory.add_or_update_task(task)
        if not update_success:
            logger.error(
                f"Failed to update task {task.task_id} status to PENDING for retry."
            )
            log_agent_event(
                agent_id=self.agent_id,
                action="reschedule_failed",
                target=task.task_id,
                outcome="failure",
                details={"reason": "Task memory update failed"},
                escalation=True,
            )
            return

        # 2. Publish a standard TASK_COMMAND event
        try:
            # Create the BaseEvent for the command
            command_event = BaseEvent(
                event_type=EventType.TASK_COMMAND,
                source_id=self.agent_id,  # The recovery agent is issuing the command
                data=task.to_dict(),  # Send the updated task data
                # correlation_id=task.correlation_id # Propagate correlation ID if needed/applicable  # noqa: E501
            )
            # Dispatch the event using the agent bus
            await self.agent_bus.dispatch_event(command_event)

            logger.info(
                f"Published event {EventType.TASK_COMMAND.name} for task retry {task.task_id} (Target: {original_agent_id})"  # noqa: E501
            )
            log_agent_event(
                agent_id=self.agent_id,
                action="reschedule_success",
                target=task.task_id,
                outcome="success",
                details={
                    "retry_count": task.retry_count,
                    "published_event": EventType.TASK_COMMAND.name,
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to publish retry event {EventType.TASK_COMMAND.name} for task {task.task_id}: {e}",  # noqa: E501
                exc_info=True,
            )
            log_agent_event(
                agent_id=self.agent_id,
                action="reschedule_failed",
                target=task.task_id,
                outcome="failure",
                details={"reason": f"dispatch_event error: {e}"},
                escalation=True,  # Updated reason
            )

    async def _mark_permanently_failed(
        self, task: TaskMessage, reason: Optional[str] = None
    ):
        """Updates task status to PERMANENTLY_FAILED in memory and publishes event."""
        # Use update_task_status utility
        failure_reason = f"Permanent failure after {task.retry_count} retries. " + (
            reason or task.error or "No specific reason provided."
        )
        task = update_task_status(  # noqa: F821
            task, TaskStatus.PERMANENTLY_FAILED, error=failure_reason
        )

        # Log the event
        log_agent_event(
            agent_id=self.agent_id,
            action="task_permanently_failed",
            target=task.task_id,
            outcome="failure",
            details={**task.to_dict(), "reason": reason},
            escalation=True,
        )

        # Persist the final status
        update_success = await self.task_memory.add_or_update_task(task)
        if not update_success:
            logger.error(
                f"Failed to mark task {task.task_id} as PERMANENTLY_FAILED in memory."
            )
            # Potential: Publish a system error event?

        # Publish the TASK_PERMANENTLY_FAILED event using the BaseAgent helper
        try:
            await self.publish_task_failed(task, failure_reason, is_final=True)
            logger.info(
                f"Published TASK_PERMANENTLY_FAILED event for task {task.task_id}."
            )
        except Exception as e:
            logger.error(
                f"Failed to publish TASK_PERMANENTLY_FAILED event for {task.task_id}: {e}",  # noqa: E501
                exc_info=True,
            )

    # --- New Handler for Timed Out Tasks ---
    async def _handle_timed_out_task(self, task: TaskMessage):
        """Marks a task that ran too long as FAILED (or TIMED_OUT)."""
        timeout_reason = f"Task exceeded timeout threshold of {self.task_timeout}."

        # Log the timeout event
        log_agent_event(
            agent_id=self.agent_id,
            action="task_timeout",
            target=task.task_id,
            outcome="failure",
            details={
                "reason": timeout_reason,
                "last_status": task.status.name,
                "threshold": str(self.task_timeout),
            },
            escalation=True,
        )

        # Update task status to FAILED in memory
        # Could introduce a TIMED_OUT status, but FAILED works for triggering recovery/escalation  # noqa: E501
        task.status = TaskStatus.FAILED
        task.updated_at = datetime.now(timezone.utc)
        task.error = timeout_reason
        # Reset retry count? Or let normal retry logic handle it?
        # Let's assume timeout counts as a failure needing retry processing.
        # task.retry_count = 0 # Optional: Reset retries if timeout is handled differently  # noqa: E501

        update_success = await self.task_memory.add_or_update_task(task)
        if not update_success:
            logger.error(
                f"Failed to mark timed-out task {task.task_id} as FAILED in memory."
            )
        else:
            logger.info(f"Timed-out task {task.task_id} marked as FAILED.")
            # Publish the failure event via AgentBus (using standard task update mechanism)  # noqa: E501
            # This ensures other systems see the task as failed and it can be potentially retried  # noqa: E501
            event = BaseEvent(
                event_type=EventType.TASK_FAILED,  # Use standard TASK_FAILED event
                source_id=self.agent_id,
                data=task.to_dict(),
            )
            try:
                await self.agent_bus.dispatch_event(event)
            except Exception as e:
                logger.error(
                    f"Failed to dispatch TASK_FAILED event for timed-out task {task.task_id}: {e}"  # noqa: E501
                )


# --- Example Usage (if needed for standalone testing) ---
# async def main():
#     # Setup mock/in-memory bus and task memory
#     # Create agent instance
#     # Start agent
#     # Manually add some failed tasks to memory
#     # Let it run for a while
#     # Stop agent
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')  # noqa: E501
#     # asyncio.run(main())
