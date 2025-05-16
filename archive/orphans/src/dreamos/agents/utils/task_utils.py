"""Task-related utilities for agent functionality."""

import asyncio
import logging
from typing import Dict, Optional

from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.core.coordination.message_patterns import TaskMessage

from ...utils.common_utils import get_utc_iso_timestamp

logger = logging.getLogger(__name__)


async def publish_task_update(
    bus: AgentBus,
    task: TaskMessage,
    agent_id: str,
) -> None:
    """Publish task status update event to the bus using a topic."""
    event_topic = f"system.task.{task.task_id}.event.updated"
    message_content = {
        "sender_id": agent_id,
        "correlation_id": task.correlation_id,
        "timestamp_utc": get_utc_iso_timestamp(),
        "data": task.model_dump(),
    }

    try:
        await bus.publish(event_topic, message_content)
        logger.debug(
            f"Published task update for {task.task_id} ({task.status.name}) to {event_topic}"
        )
    except Exception as e:
        logger.error(
            f"Failed to publish task update for {task.task_id} to {event_topic}: {e}",
            exc_info=True,
        )


async def handle_task_cancellation(
    task_id: str,
    active_tasks: Dict[str, asyncio.Task],
    bus: AgentBus,
    agent_id: str,
    correlation_id: Optional[str],
) -> None:
    """Handle task cancellation request by cancelling the task and publishing results."""
    active_task = active_tasks.get(task_id)
    response_topic = (
        f"system.response.{correlation_id}.result" if correlation_id else None
    )
    response_payload = {
        "sender_id": agent_id,
        "correlation_id": correlation_id,
        "timestamp_utc": get_utc_iso_timestamp(),
        "data": {},
    }

    if active_task and not active_task.done():
        logger.info(f"Cancelling active task {task_id} as requested.")
        active_task.cancel()
        try:
            await asyncio.sleep(0)
        except asyncio.CancelledError:
            pass

        response_payload["data"] = {
            "status": "success",
            "message": f"Cancellation requested for task {task_id}.",
        }
        if response_topic and bus:
            try:
                await bus.publish(response_topic, response_payload)
                logger.debug(
                    f"Published cancellation response for {task_id} to {response_topic}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to publish cancellation response for {task_id} to {response_topic}: {e}",
                    exc_info=True,
                )
        else:
            logger.warning(
                f"Cannot send cancellation confirmation for task {task_id}: No correlation ID or bus."
            )
    else:
        error_msg = f"Task {task_id} not found in active tasks or already done."
        logger.warning(error_msg)
        response_payload["data"] = {
            "status": "error",
            "message": f"Task {task_id} not found or already completed, cannot cancel.",
        }

        if response_topic and bus:
            try:
                await bus.publish(response_topic, response_payload)
                logger.debug(
                    f"Published cancellation response for {task_id} to {response_topic}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to publish cancellation response for {task_id} to {response_topic}: {e}",
                    exc_info=True,
                )


async def safe_create_task(coro, *, name=None, logger_instance=None):
    """Safely create an asyncio task with error handling."""

    def _task_done_callback(task: asyncio.Task):
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if logger_instance:
                logger_instance.error(f"Task {name} failed: {e}", exc_info=True)
            else:
                logger.error(f"Task {name} failed: {e}", exc_info=True)

    task = asyncio.create_task(coro, name=name)
    task.add_done_callback(_task_done_callback)
    return task
