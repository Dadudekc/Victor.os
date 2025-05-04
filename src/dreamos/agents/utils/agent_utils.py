"""Shared utilities for agent functionality."""

import asyncio
import logging  # Added for logging potential errors within utils
import traceback
from functools import wraps
from typing import Any, Callable, Dict, Optional

from dreamos.coordination.agent_bus import AgentBus  # CORRECTED PATH
from dreamos.core.coordination.event_payloads import (  # Import the payload
    SupervisorAlertPayload,
)
from dreamos.core.coordination.event_types import EventType
from dreamos.core.coordination.message_patterns import (
    TaskMessage,
)
from dreamos.core.events.base_event import BaseDreamEvent
from dreamos.core.memory.governance_memory_engine import log_event
from dreamos.core.utils.performance_logger import PerformanceLogger
from dreamos.utils.common_utils import get_utc_iso_timestamp

# Setup a logger for utility functions
util_logger = logging.getLogger("core.utils")


class AgentError(Exception):
    """Base exception for agent-related errors."""

    pass


class TaskProcessingError(AgentError):
    """Error during task processing."""

    pass


class MessageHandlingError(AgentError):
    """Error during message handling."""

    pass


def with_error_handling(error_class: type = AgentError):
    """Decorator for functions that need standardized error handling and logging."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Identify self/agent_id if method is called on an agent instance
            agent_id = "unknown_agent"
            if args and hasattr(args[0], "agent_id"):
                agent_id = args[0].agent_id
            elif "self" in kwargs and hasattr(kwargs["self"], "agent_id"):
                agent_id = kwargs["self"].agent_id

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Log the error using standard logger if available on self, otherwise use util_logger  # noqa: E501
                logger_instance = getattr(
                    args[0] if args else None, "logger", util_logger
                )

                error_msg = f"Error in {func.__name__}: {e}"
                logger_instance.error(error_msg, exc_info=True)

                # Log governance event
                error_details = {
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "function": func.__name__,
                    "args": str(args[1:]) if args else "()",  # Don't log self
                    "kwargs": str(kwargs),
                }
                try:
                    log_event("AGENT_UTIL_ERROR", agent_id, error_details)
                except Exception as log_e:
                    logger_instance.error(
                        f"Failed to log governance event for agent error: {log_e}"
                    )

                # Re-raise the specified error class
                raise error_class(error_msg) from e

        return wrapper

    return decorator


def with_performance_tracking(operation_name: str):
    """Decorator for tracking operation performance. Assumes 'self' is the first arg and has 'perf_logger'."""  # noqa: E501

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Ensure self has perf_logger attribute
            if not hasattr(self, "perf_logger") or not isinstance(
                self.perf_logger, PerformanceLogger
            ):
                util_logger.warning(
                    f"Performance tracking skipped for {operation_name}: 'perf_logger' not found or invalid on {self}."  # noqa: E501
                )
                return await func(self, *args, **kwargs)

            # Use the performance logger from the instance
            with self.perf_logger.track_operation(operation_name):
                return await func(self, *args, **kwargs)

        return wrapper

    return decorator


async def publish_task_update(
    bus: AgentBus,  # Use specific type hint
    task: TaskMessage,
    agent_id: str,
    # correlation_id: Optional[str] = None # Correlation ID is part of TaskMessage now
) -> None:
    """Publish task status update event to the bus using a topic."""
    # OLD TOPIC: event_topic = f"system.tasks.updates.{task.task_id}"
    # NEW TOPIC Convention: <Scope>.<Domain>.<Resource>[.<Instance>].<Action>[.<Status>]
    event_topic = f"system.task.{task.task_id}.event.updated"
    message_content = {
        "sender_id": agent_id,
        "correlation_id": task.correlation_id,  # Use correlation ID from task
        "timestamp_utc": get_utc_iso_timestamp(),
        "data": task.to_dict(),  # Send full task data
    }

    try:
        # Publish to a dynamic topic including task ID
        await bus.publish(event_topic, message_content)
        util_logger.debug(
            f"Published task update for {task.task_id} ({task.status.name}) to {event_topic}"  # noqa: E501
        )
    except Exception as e:
        util_logger.error(
            f"Failed to publish task update for {task.task_id} to {event_topic}: {e}",
            exc_info=True,
        )


async def publish_error(
    bus: AgentBus,  # Use specific type hint
    error_message: str,
    agent_id: str,
    correlation_id: Optional[str],  # Correlation ID might be None
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Publish an error message to the system error topic and potentially a response topic."""  # noqa: E501
    # Publish to a general system error topic
    # OLD TOPIC: system_error_topic = "system.error"
    # NEW TOPIC:
    system_error_topic = EventType.SYSTEM_ERROR.value  # Use standard enum
    error_data = {
        "error": error_message,
        "source_agent": agent_id,
        "traceback": traceback.format_exc(),  # Consider omitting traceback from bus? Logged locally.  # noqa: E501
        **(details or {}),  # Merge additional details
    }
    error_message_payload = {
        "sender_id": agent_id,
        "correlation_id": correlation_id,
        "timestamp_utc": get_utc_iso_timestamp(),
        "data": error_data,
    }
    try:
        await bus.publish(system_error_topic, error_message_payload)
        util_logger.debug(
            f"Published error from {agent_id} to {system_error_topic} (CorrID: {correlation_id})"  # noqa: E501
        )
    except Exception as e:
        util_logger.error(
            f"Failed to publish system error message from {agent_id}: {e}",
            exc_info=True,
        )

    # If a correlation ID exists, also publish error to the specific response topic
    if correlation_id:
        # OLD TOPIC: response_topic = f"system.response.{correlation_id}"
        # NEW TOPIC: Distinguish error response from success result
        response_topic = (
            f"system.response.{correlation_id}.error"  # Changed from .result
        )
        try:
            # Re-use the same payload for the specific error response
            # Publish to a dynamic topic based on correlation ID
            await bus.publish(response_topic, error_message_payload)
            util_logger.debug(
                f"Published error response from {agent_id} to {response_topic}"
            )
        except Exception as e:
            util_logger.error(
                f"Failed to publish error response message to {response_topic}: {e}",
                exc_info=True,
            )

    # Original publish logic using MessageType.ERROR commented out
    # content = {
    #     "error": error_message,
    #     "traceback": traceback.format_exc()
    # }
    # if details:
    #     content.update(details)
    # await bus.publish(Message(
    #     type=MessageType.ERROR,
    #     sender=agent_id,
    #     content=content,
    #     correlation_id=correlation_id
    # ))


async def handle_task_cancellation(
    task_id: str,
    active_tasks: Dict[str, asyncio.Task],
    bus: AgentBus,  # Use specific type hint
    agent_id: str,
    correlation_id: Optional[str],  # Correlation ID might be None
) -> None:
    """Handle task cancellation request by cancelling the task and publishing results."""  # noqa: E501
    active_task = active_tasks.get(task_id)
    # OLD TOPIC: response_topic = f"system.response.{correlation_id}" if correlation_id else None  # noqa: E501
    # NEW TOPIC:
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
        util_logger.info(f"Cancelling active task {task_id} as requested.")
        active_task.cancel()
        try:
            # Allow cancellation to propagate if needed
            await asyncio.sleep(0)  # Yield control briefly
        except asyncio.CancelledError:
            pass  # Expected if task handles cancellation quickly

        # Publish success response
        response_payload["data"] = {
            "status": "success",
            "message": f"Cancellation requested for task {task_id}.",
        }
        if response_topic:
            try:
                # Publish to a dynamic topic based on correlation ID
                await bus.publish(response_topic, response_payload)
                util_logger.debug(
                    f"Published cancellation confirmation to {response_topic}"
                )
            except Exception as e:
                util_logger.error(
                    f"Failed to publish cancellation confirmation to {response_topic}: {e}",  # noqa: E501
                    exc_info=True,
                )
        else:
            util_logger.warning(
                f"Cannot send cancellation confirmation for task {task_id}: No correlation ID."  # noqa: E501
            )

        # Note: The actual task status (CANCELLED) should be set and published
        # by the _process_single_task exception handling in BaseAgent when the await task raises CancelledError.  # noqa: E501

        # Original MessageType.RESPONSE publish commented out
        # await bus.publish(Message(
        #     type=MessageType.RESPONSE,
        #     sender=agent_id,
        #     content={"status": "success", "message": f"Task {task_id} cancelled"},
        #     correlation_id=correlation_id
        # ))
    else:
        # Task not found or already done
        error_msg = f"Task {task_id} not found or already completed/cancelled."
        util_logger.warning(error_msg)
        await publish_error(bus, error_msg, agent_id, correlation_id)


def log_task_performance(
    task: TaskMessage, agent_id: str, perf_logger: PerformanceLogger
) -> None:
    """Log task performance metrics using PerformanceLogger."""
    # Ensure necessary timestamps are available
    start_time_iso = task.created_at.isoformat() if task.created_at else None
    end_time_iso = (
        task.updated_at.isoformat() if task.updated_at else get_utc_iso_timestamp()
    )

    try:
        perf_logger.log_outcome(
            task_id=task.task_id,
            agent_id=agent_id,
            task_type=task.task_type,
            status=task.status.name,  # Use status enum name
            start_time=start_time_iso,
            end_time=end_time_iso,
            error_message=task.error,
            input_summary=str(task.input_data)[:500],  # Limit summary size
            output_summary=str(task.result)[:500],  # Limit summary size
        )
        util_logger.debug(f"Logged performance for task {task.task_id}")
    except Exception as e:
        error_details = {
            "error": f"Failed to log performance outcome for task {task.task_id}: {e}",
            "details": str(e),
        }
        util_logger.error(error_details["error"], exc_info=True)
        try:
            # Log failure to log performance as a separate governance event
            log_event("PERF_LOGGING_FAILED", agent_id, error_details)
        except Exception as log_e:
            util_logger.error(
                f"CRITICAL: Failed even to log the performance logging failure: {log_e}"
            )


def format_agent_report(
    agent_id: str, task: str, status: str, action: str, agent_name: Optional[str] = None
) -> str:
    """Formats the standard agent report header and body.

    Args:
        agent_id: The reporting agent's ID (e.g., "Agent2", "Agent-8").
        task: A brief description of the current or completed task.
        status: The current status (e.g., "🟡 Executing", "✅ Complete", "🔴 Blocked").
        action: A short statement of the action just taken, the next step,
                or the reason for being blocked/standby.
        agent_name: The optional operational name of the agent (e.g., "Nexus").

    Returns:
        A formatted markdown string for the agent's report.
    """
    # Use name if available, otherwise fall back to Agent ID
    header_name = agent_name if agent_name else f"Agent {agent_id}"
    header = f"**{header_name} Reporting:**"
    body = f"- **Current Task:** {task}\n- **Current Status:** {status}\n- **Action Taken or Standby Action:** {action}"  # noqa: E501
    return f"{header}\n\n{body}"


async def publish_supervisor_alert(
    bus: AgentBus,
    source_agent_id: str,
    blocker_summary: str,
    blocking_task_id: Optional[str] = None,
    details_reference: Optional[str] = None,
) -> str:
    """Constructs and publishes a supervisor alert event.

    Args:
        bus: The AgentBus instance.
        source_agent_id: The ID of the agent raising the alert.
        blocker_summary: A concise summary of the critical blocker.
        blocking_task_id: Optional ID of the task being blocked.
        details_reference: Optional path to a file with more details.

    Returns:
        The alert_id of the published alert.
    """
    payload = SupervisorAlertPayload(
        source_agent_id=source_agent_id,
        blocking_task_id=blocking_task_id,
        blocker_summary=blocker_summary,
        details_reference=details_reference,
        status="NEW",  # Always publish as NEW
    )

    alert_event = BaseDreamEvent(
        event_type=EventType.SUPERVISOR_ALERT,
        source_id=source_agent_id,
        data=payload.__dict__,  # Convert payload dataclass to dict for BaseEvent
        # correlation_id is not typically needed for alerts
    )

    try:
        await bus.dispatch_event(
            alert_event
        )  # Use dispatch_event which takes BaseEvent
        util_logger.info(
            f"Agent {source_agent_id} raised supervisor alert {payload.alert_id}: {blocker_summary}"  # noqa: E501
        )
        return payload.alert_id
    except Exception as e:
        util_logger.error(
            f"Failed to publish supervisor alert from {source_agent_id}: {e}",
            exc_info=True,
        )
        raise  # Re-raise the exception so the caller knows publish failed
