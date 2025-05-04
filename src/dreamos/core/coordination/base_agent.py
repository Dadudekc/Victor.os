"""Base agent class providing common functionality for all Dream.OS agents."""

import asyncio
import logging  # Added for standard logger
import shlex  # Added for safe command construction
import subprocess  # Added for running external validation tools
import sys  # EDIT: Added sys import
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

# REMOVED obsolete dreamforge comments/imports
# Assuming agent_utils is now in core/utils # This comment is incorrect, it's in agents/utils  # noqa: E501
from dreamos.agents.utils.agent_utils import (  # publish_task_update, # Will be replaced by internal event publishing; publish_error,       # Will be replaced by internal event publishing  # noqa: E501
    AgentError,
    MessageHandlingError,
    TaskProcessingError,
    handle_task_cancellation,
    log_task_performance,
    with_error_handling,
    with_performance_tracking,
)

# Update imports to use 'core' or relative paths
# REMOVED obsolete dreamforge comment
from dreamos.coordination.agent_bus import (  # CORRECTED PATH
    AgentBus,
    BaseEvent,
)

# EDIT START: Import PBM
from dreamos.coordination.project_board_manager import ProjectBoardManager

# EDIT END
from dreamos.core.config import AppConfig  # EDIT: Import AppConfig from config.py

# REMOVED obsolete path comment
# REMOVED obsolete dreamforge comment
from dreamos.core.coordination.message_patterns import (
    TaskMessage,
    TaskPriority,
    TaskStatus,
)

# from dreamos.core.memory.governance_memory_engine import log_event
from dreamos.core.memory.governance_memory_engine import log_event

# from dreamos.core.utils.performance_logger import PerformanceLogger
from dreamos.core.utils.performance_logger import PerformanceLogger

# {{ EDIT START: Import payload dataclasses }}
from .event_payloads import (
    AgentContractStatusPayload,
    ErrorEventPayload,  # EDIT: Replaces AgentErrorPayload, SystemAgentErrorPayload
    TaskCompletionPayload,
    TaskEventPayload,
    TaskFailurePayload,
    TaskProgressPayload,
    TaskValidationFailedPayload,
)

# EDIT START: Import EventType from canonical source
from .event_types import EventType

# from dreamos.core.logging.swarm_logger import (  # Removed unused import
#     log_agent_event,
# )


# REMOVED obsolete config manager imports


# EDIT START: Remove obsolete TODO comment & import
# EDIT END

# EDIT START: Remove redundant EventType import comment
# EDIT END


# {{ EDIT END }}

# EDIT START: Remove placeholder definitions/comments
# REMOVED global constant comment

# {{ EDIT START: Remove placeholder statuses/payloads/event types - defined elsewhere }}
# {{ EDIT END }}

# {{ EDIT START: Placeholder for new event payload for validation failure }}
# {{ EDIT END }}

# {{ EDIT START: Placeholder for new EventType - should move to enum }}
# {{ EDIT END }}
# EDIT END


# EDIT END


class BaseAgent(ABC):
    """Base class for all Dream.OS agents providing common functionality."""

    # EDIT START: Modify __init__ signature and logic
    def __init__(
        self,
        agent_id: str,
        config: AppConfig,  # EDIT: Moved mandatory config before optional args
        pbm: ProjectBoardManager,  # Require PBM
        agent_bus: Optional[AgentBus] = None,
        # project_root: Path = Path("."), # Now derived from AppConfig
        # task_list_path: Optional[Path] = None, # EDIT: Removed obsolete
        # capabilities: Optional[List[str]] = None, # EDIT: Removed capabilities
    ):
        """Initializes the BaseAgent.

        Args:
            agent_id: Unique identifier for the agent.
            config: Application configuration object.
            pbm: Project Board Manager instance.
            agent_bus: An instance of AgentBus for communication.
            # project_root: Root directory for resolving relative paths. Now derived from AppConfig.
            # task_list_path: Optional path to the persistent task list file. # EDIT: Removed obsolete
            # capabilities: List of capabilities this agent possesses. # EDIT: Removed capabilities doc
        """  # noqa: E501
        self.logger = logging.getLogger(agent_id)
        self.agent_id = agent_id
        self.config = config
        # EDIT START: Store PBM
        self.pbm = pbm
        # EDIT END
        self.agent_bus = agent_bus or self._get_default_agent_bus()
        self._subscription_id = None
        self._running = False
        self._active_tasks = {}
        self._task_queue = asyncio.PriorityQueue()
        self._command_handlers: Dict[
            str, Callable[[TaskMessage], Awaitable[Dict[str, Any]]]
        ] = {}
        self.logger.debug(f"Initializing BaseAgent for {agent_id}")

        # EDIT START: Use config directly and validate it exists
        if not config or not config.paths or not config.paths.project_root:
            from ..core.errors import ConfigurationError

            raise ConfigurationError(
                "AppConfig must provide a valid project_root path."
            )
        self._project_root = config.paths.project_root.resolve()
        self.logger.info(f"Using project root from config: {self._project_root}")
        # EDIT END: Remove old project root logic

        # OLD Logic - Removed
        # # EDIT START: Robust project root determination
        # if config:
        #     self._project_root = config.paths.project_root
        #     self.logger.info(f"Using provided project root: {self._project_root}")
        # else:
        #     # Try environment variable
        #     env_root = os.environ.get("DREAMOS_PROJECT_ROOT")
        #     if env_root:
        #         self._project_root = Path(env_root).resolve()
        #         self.logger.info(
        #             f"Using project root from DREAMOS_PROJECT_ROOT env var: {self._project_root}"  # noqa: E501
        #         )
        #     # Try ConfigManager if available
        #     elif config: # This check is redundant now
        #         cfg_root = config.paths.project_root
        #         if cfg_root:
        #             self._project_root = Path(cfg_root).resolve()
        #             self.logger.info(
        #                 f"Using project root from config: {self._project_root}"
        #             )
        #         else:
        #             # Fallback: Search upwards for a marker file (e.g., pyproject.toml)  # noqa: E501
        #             self._project_root = self._find_project_root()
        #             self.logger.warning(
        #                 f"Project root not specified via param/env/config. Found via marker search: {self._project_root}"  # noqa: E501
        #             )
        #     else:
        #         # Final fallback: Search upwards
        #         self._project_root = self._find_project_root()
        #         self.logger.warning(
        #             f"Project root not specified and config manager unavailable. Found via marker search: {self._project_root}"  # noqa: E501
        #         )
        # # EDIT END

        self.logger.debug("Initializing PerformanceLogger...")
        try:
            # Pass project root to Perf Logger if needed, or ensure it finds it
            self.perf_logger = PerformanceLogger(
                agent_id
            )  # Assuming it doesn't need explicit root path
            self.logger.info(
                f"PerformanceLogger initialized. Log path: {self.perf_logger.log_path}"
            )
        except Exception as e:
            self.logger.critical(
                f"CRITICAL ERROR initializing PerformanceLogger: {e}", exc_info=True
            )
            self.perf_logger = None

        # Remove comments/logic related to capabilities and obsolete task_list_path
        # self.capabilities = set(capabilities) if capabilities else set()
        # Capability registration now handled via CapabilityRegistry

        # EDIT START: Remove obsolete task_list_path logic comment
        # TODO: Refactor/Remove: This task_list_path logic seems outdated due to PBM/dual-queue.  # noqa: E501
        # self.task_list_path = task_list_path or (self._project_root / "task_list.json")  # noqa: E501
        # self.logger.info(f"Using persistent task list: {self.task_list_path}")
        # EDIT END

        self.agent_bus = agent_bus or self._get_default_agent_bus()
        # self.capabilities = set(capabilities) if capabilities else set() # EDIT: Removed capabilities assignment  # noqa: E501
        # Capability registration now handled via CapabilityRegistry

    @with_error_handling(AgentError)
    async def start(self):
        """Start the agent, subscribe to topics, and launch task processor."""
        self.logger.info(f"Starting agent {self.agent_id}...")
        log_event("AGENT_START", self.agent_id, {"version": "1.0.0"})
        self._running = True

        # Subscribe to command messages using topic string
        # OLD TOPIC: command_topic = f"agent.{self.agent_id}.command"
        # PREVIOUS TOPIC: command_topic = f"agent.{self.agent_id}.task.command"
        # NEW HIERARCHICAL TOPIC:
        command_topic = f"dreamos.agent.{self.agent_id}.task.command"
        # self._subscription_id = await self.agent_bus.subscribe(
        #     MessageType.COMMAND,
        #     self._handle_command
        # )
        # Assuming subscribe now returns a subscription object or ID for unsubscribing
        # self._subscription_id = await self.agent_bus.subscribe(command_topic, self._handle_command)  # noqa: E501
        # {{ EDIT: Store topic and handler for unsubscribe }}
        self._command_topic = command_topic
        self._command_handler_ref = (
            self._handle_command
        )  # Store actual method reference
        # Subscribe to agent-specific command topic (dynamic topic)
        await self.agent_bus.subscribe(self._command_topic, self._command_handler_ref)
        # {{ EDIT END }}
        self.logger.info(f"Subscribed to command topic: {self._command_topic}")

        # {{ EDIT START: Subscribe to AGENT_CONTRACT_QUERY }}
        # Use the EventType enum directly for system-wide topics
        self._contract_query_topic = (
            EventType.AGENT_CONTRACT_QUERY.value
        )  # Use enum value as topic
        self._contract_query_handler_ref = self._handle_contract_query
        # Subscribe to agent-specific contract query topic (if applicable, currently system-wide)  # noqa: E501
        await self.agent_bus.subscribe(
            self._contract_query_topic, self._contract_query_handler_ref
        )
        self.logger.info(
            f"Subscribed to contract query topic: {self._contract_query_topic}"
        )
        # {{ EDIT END }}

        # Start task processor
        self._task_processor_task = asyncio.create_task(self._process_task_queue())
        self.logger.info("Task processor started.")

        # Start the message bus (if BaseAgent is responsible for its lifecycle)
        # NOTE: Typically, AgentBus lifecycle is managed externally.
        # Consider removing this if the bus is started elsewhere.
        # await self.agent_bus.start()
        # self.logger.info("AgentBus start requested (if managed internally)." )

        # Call agent-specific startup
        await self._on_start()
        self.logger.info(f"Agent {self.agent_id} started successfully.")

    @with_error_handling(AgentError)
    async def stop(self):
        """Stop the agent, cancel tasks, unsubscribe, and shutdown."""
        self.logger.info(f"Stopping agent {self.agent_id}...")
        self._running = False

        # Cancel the task processor first
        if hasattr(self, "_task_processor_task") and self._task_processor_task:
            self._task_processor_task.cancel()
            try:
                await self._task_processor_task
            except asyncio.CancelledError:
                self.logger.info("Task processor stopped.")

        # Cancel all active tasks managed by the queue processing
        self.logger.info(f"Cancelling {len(self._active_tasks)} active task(s)...")
        for task_id, task in list(self._active_tasks.items()):  # Iterate over copy
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    self.logger.info(f"Cancelled active task {task_id}.")
                    log_event(
                        "AGENT_TASK_CANCELLED", self.agent_id, {"task_id": task_id}
                    )
                # Ensure removal even if await fails
                self._active_tasks.pop(task_id, None)

        # Clear the queue (optional, prevents processing stale tasks on restart)
        while not self._task_queue.empty():
            try:
                self._task_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self.logger.info("Task queue cleared.")

        # Unsubscribe from bus
        # {{ EDIT: Use topic and handler for unsubscribe }}
        # if self._subscription_id:
        if hasattr(self, "_command_topic") and hasattr(self, "_command_handler_ref"):
            try:
                # Assuming unsubscribe takes the topic pattern and handler
                # await self.agent_bus.unsubscribe(self._subscription_id)
                await self.agent_bus.unsubscribe(
                    self._command_topic, self._command_handler_ref
                )
                self.logger.info(
                    f"Unsubscribed from command topic: {self._command_topic}"
                )
            except Exception as e:
                self.logger.error(f"Error unsubscribing from agent bus: {e}")
        else:
            self.logger.warning(
                "Command topic/handler reference not found for unsubscription."
            )
        # {{ EDIT END }}

        # {{ EDIT START: Unsubscribe from AGENT_CONTRACT_QUERY }}
        if hasattr(self, "_contract_query_topic") and hasattr(
            self, "_contract_query_handler_ref"
        ):
            try:
                await self.agent_bus.unsubscribe(
                    self._contract_query_topic, self._contract_query_handler_ref
                )
                self.logger.info(
                    f"Unsubscribed from contract query topic: {self._contract_query_topic}"  # noqa: E501
                )
            except Exception as e:
                self.logger.error(f"Error unsubscribing from contract query topic: {e}")
        else:
            self.logger.warning(
                "Contract query topic/handler reference not found for unsubscription."
            )
        # {{ EDIT END }}

        # Shutdown the message bus (if BaseAgent is responsible)
        # NOTE: Typically, AgentBus lifecycle is managed externally.
        # Consider removing this if the bus is shutdown elsewhere.
        # await self.agent_bus.shutdown()
        # self.logger.info("AgentBus shutdown requested (if managed internally)." )

        # Call agent-specific shutdown
        await self._on_stop()

        log_event("AGENT_STOP", self.agent_id, {"reason": "Shutdown requested"})
        self.logger.info(f"Agent {self.agent_id} stopped successfully.")

    def register_command_handler(
        self,
        command_type: str,
        handler: Callable[[TaskMessage], Awaitable[Dict[str, Any]]],
    ):
        """Register a handler for a specific command type (task_type)."""
        self.logger.debug(f"Registering command handler for type: {command_type}")
        self._command_handlers[command_type] = handler

    # --- Standardized Event Publishing Helpers ---

    async def _publish_event(
        self,
        event_type: EventType,
        payload_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ):
        """Helper method to publish a standardized event to the AgentBus.

        Args:
            event_type: The type of event to publish.
            payload_data: The dictionary containing the event payload data.
            correlation_id: Optional correlation ID.
        """
        event = BaseEvent(
            event_type=event_type,
            source_id=self.agent_id,
            data=payload_data,  # Data is now passed directly
            correlation_id=correlation_id,
        )
        try:
            await self.agent_bus.dispatch_event(event)
            # Log only essential info for reduced noise, consider logging payload at DEBUG  # noqa: E501
            self.logger.debug(
                f"Published event: {event_type.name}, CorrID: {correlation_id}"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to publish event {event_type.name}: {e}", exc_info=True
            )

    async def publish_task_accepted(self, task: TaskMessage):
        """Publishes a TASK_ACCEPTED event."""
        # {{ EDIT START: Use TaskEventPayload }}
        payload = TaskEventPayload(
            task_id=task.task_id,
            status=TaskStatus.ACCEPTED,  # Status is key part of this event
            task_type=task.task_type,
            agent_id=self.agent_id,
        )
        await self._publish_event(
            EventType.TASK_ACCEPTED, payload.__dict__, task.correlation_id
        )
        # {{ EDIT END }}

    async def publish_task_started(self, task: TaskMessage):
        """Publishes a TASK_STARTED event."""
        # {{ EDIT START: Use TaskEventPayload }}
        payload = TaskEventPayload(
            task_id=task.task_id,
            status=TaskStatus.RUNNING,  # Status is key part of this event
            task_type=task.task_type,
            agent_id=self.agent_id,
        )
        await self._publish_event(
            EventType.TASK_STARTED, payload.__dict__, task.correlation_id
        )
        # {{ EDIT END }}

    async def publish_task_progress(
        self, task: TaskMessage, progress: float, details: Optional[str] = None
    ):
        """Publishes a TASK_PROGRESS event."""
        # {{ EDIT START: Use TaskProgressPayload }}
        # Note: TaskProgressPayload inherits from TaskEventPayload
        payload = TaskProgressPayload(
            task_id=task.task_id,
            status=TaskStatus.RUNNING,  # Task is still running when progress occurs
            task_type=task.task_type,
            agent_id=self.agent_id,
            progress=progress,
            details=details,
        )
        await self._publish_event(
            EventType.TASK_PROGRESS, payload.__dict__, task.correlation_id
        )
        # {{ EDIT END }}

    async def publish_task_completed(
        self, task: TaskMessage, result: Optional[Dict[str, Any]] = None
    ):
        """Publishes a TASK_COMPLETED event."""
        # {{ EDIT START: Use TaskCompletionPayload }}
        payload = TaskCompletionPayload(
            task_id=task.task_id,
            status=TaskStatus.COMPLETED,
            task_type=task.task_type,
            agent_id=self.agent_id,
            result=result if result is not None else {},
        )
        await self._publish_event(
            EventType.TASK_COMPLETED, payload.__dict__, task.correlation_id
        )
        # {{ EDIT END }}

    async def publish_task_failed(
        self,
        task: TaskMessage,
        error: str,
        is_final: bool = False,
        details: Optional[str] = None,
    ):
        """Publishes a TASK_FAILED or TASK_PERMANENTLY_FAILED event."""
        # {{ EDIT START: Use TaskFailurePayload }}
        payload = TaskFailurePayload(
            task_id=task.task_id,
            status=TaskStatus.FAILED,
            task_type=task.task_type,
            agent_id=self.agent_id,
            error=error,
            is_final=is_final,
            details=details,  # Add optional details here if needed
        )
        event_type = (
            EventType.TASK_PERMANENTLY_FAILED if is_final else EventType.TASK_FAILED
        )
        await self._publish_event(event_type, payload.__dict__, task.correlation_id)
        # {{ EDIT END }}

    async def publish_agent_error(
        self,
        error_message: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        task_id: Optional[str] = None,
        exc_info=False,
        # EDIT: Add new parameters from ErrorEventPayload if needed directly
        exception_type: Optional[str] = None,
        traceback_str: Optional[str] = None,
    ):
        """Publish an AGENT_ERROR event using ErrorEventPayload."""
        self.logger.error(f"Publishing agent error: {error_message}", exc_info=exc_info)
        tb_str = None
        exc_type_name = exception_type
        if exc_info:
            exc_type, exc_value, exc_tb = sys.exc_info()
            if exc_type:
                tb_str = traceback_str or "\n".join(
                    traceback.format_exception(exc_type, exc_value, exc_tb)
                )
                exc_type_name = exception_type or exc_type.__name__

        # EDIT: Use ErrorEventPayload
        payload = ErrorEventPayload(
            error_message=error_message,
            agent_id=self.agent_id,  # Include agent_id
            task_id=task_id,
            exception_type=exc_type_name,
            traceback=tb_str,
            details=details or {},
        )

        await self._publish_event(
            EventType.AGENT_ERROR,
            payload_data=payload.to_dict(),  # Assuming payload needs serialization
            correlation_id=correlation_id,
        )

    # --- End Standardized Event Publishing Helpers ---

    @with_error_handling(
        MessageHandlingError, error_publisher=publish_agent_error
    )  # Pass error publisher
    @with_performance_tracking("handle_command")
    async def _handle_command(self, topic: str, message: Dict[str, Any]):
        """Handle incoming command messages, parse TaskMessage, and queue."""
        self.logger.debug(f"Received message on topic '{topic}': {message}")
        correlation_id = message.get("correlation_id")

        # Parse TaskMessage from the 'data' field
        task_data = message.get("data")
        if not task_data or not isinstance(task_data, dict):
            self.logger.error(
                f"Invalid or missing task data in command message: {message}"
            )
            await self.publish_agent_error(
                "Invalid command payload: Missing or invalid 'data' field.",
                details=message,
                correlation_id=correlation_id,
            )
            return

        try:
            # Reconstruct TaskMessage
            task = TaskMessage.from_dict(task_data)
            if task.target_agent_id and task.target_agent_id != self.agent_id:
                self.logger.warning(
                    f"Received task {task.task_id} intended for {task.target_agent_id}. Discarding."  # noqa: E501
                )
                return  # Ignore tasks not for this agent

            # Log reception and publish accepted event
            self.logger.info(
                f"Received and accepted task {task.task_id} (Type: {task.task_type}, CorrID: {correlation_id})"  # noqa: E501
            )
            log_agent_event(  # noqa: F821
                self.agent_id,
                "task_received",
                task.task_id,
                "success",
                {**task.to_dict(), "topic": topic},
            )
            await self.publish_task_accepted(task)  # Use new helper

            # Add task to the priority queue
            priority_val = self._get_priority_value(task.priority)
            await self._task_queue.put((priority_val, task))
            self.logger.debug(
                f"Task {task.task_id} added to queue with priority {priority_val}."
            )

        except KeyError as e:
            self.logger.error(
                f"Failed to parse TaskMessage from command data: Missing key {e}. Data: {task_data}",  # noqa: E501
                exc_info=True,
            )
            await self.publish_agent_error(
                f"Invalid TaskMessage structure: Missing key {e}",
                details=task_data,
                correlation_id=correlation_id,
            )
        except Exception as e:
            self.logger.error(
                f"Error handling command: {e}. Message: {message}", exc_info=True
            )
            # Publish generic agent error if task object couldn't be created
            await self.publish_agent_error(
                f"Error processing command message: {e}",
                details=message,
                correlation_id=correlation_id,
            )

    def _get_priority_value(self, priority: TaskPriority) -> int:
        """Convert TaskPriority enum to an integer for the queue (lower number = higher priority)."""  # noqa: E501
        priority_map = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
            TaskPriority.BACKGROUND: 4,
        }
        return priority_map.get(priority, priority_map[TaskPriority.MEDIUM])

    @with_error_handling(
        TaskProcessingError, error_publisher=publish_agent_error
    )  # Pass error publisher
    async def _process_task_queue(self):
        """Continuously process tasks from the priority queue."""
        self.logger.info("Task processing loop started.")
        while self._running:
            try:
                # Wait for a task from the queue
                priority, task = await self._task_queue.get()
                correlation_id = task.correlation_id  # Get correlation ID from task
                self.logger.info(
                    f"Dequeued task {task.task_id} (Priority: {priority}, Type: {task.task_type}, CorrID: {correlation_id})"  # noqa: E501
                )
                log_agent_event(  # noqa: F821
                    self.agent_id,
                    "task_dequeued",
                    task.task_id,
                    "pending",
                    task.to_dict(),
                )

                # Launch task processing in the background
                # Ensure task is not already active (e.g., due to race condition or restart)  # noqa: E501
                if task.task_id in self._active_tasks:
                    self.logger.warning(
                        f"Task {task.task_id} is already active. Skipping duplicate execution."  # noqa: E501
                    )
                    log_agent_event(  # noqa: F821
                        self.agent_id,
                        "task_skipped_duplicate",
                        task.task_id,
                        "warning",
                        task.to_dict(),
                    )
                    self._task_queue.task_done()  # Mark as done even if skipped
                    continue

                # Create and store the asyncio Task for processing
                async_task = asyncio.create_task(
                    self._process_single_task(task, correlation_id)
                )
                self._active_tasks[task.task_id] = async_task
                self.logger.debug(f"Created asyncio task for {task.task_id}")

                # Optional: Add a callback to remove the task from _active_tasks upon completion/cancellation  # noqa: E501
                async_task.add_done_callback(
                    lambda fut, tid=task.task_id: self._active_tasks.pop(tid, None)
                )

            except asyncio.CancelledError:
                self.logger.info("Task processing loop cancelled.")
                break  # Exit loop if agent is stopping
            except Exception as e:
                # Log critical error in the queue processor itself
                self.logger.critical(
                    f"CRITICAL ERROR in task processing loop: {e}", exc_info=True
                )
                log_agent_event(  # noqa: F821
                    self.agent_id,
                    "queue_processor_error",
                    outcome="failure",
                    details={"error": str(e), "traceback": traceback.format_exc()},
                    escalation=True,
                )
                await self.publish_agent_error(
                    f"Critical error in task queue processing: {e}",
                    details={"traceback": traceback.format_exc()},
                )
                # Avoid tight loop on persistent errors
                await asyncio.sleep(5)
            finally:
                # Important: Mark task as done in the queue regardless of outcome
                # This happens implicitly in the loop now, but good practice if structure changes.  # noqa: E501
                # self._task_queue.task_done() # Not needed here if get() is awaited
                pass

        self.logger.info("Task processing loop stopped.")

    @with_error_handling(
        TaskProcessingError
    )  # Error handled internally, decorator for safety net
    @with_performance_tracking("process_single_task")
    async def _process_single_task(
        self, task: TaskMessage, correlation_id: Optional[str]
    ):
        """Process a single task from the queue."""
        self.logger.info(f"Processing task {task.task_id}: {task.command_type}")
        log_agent_event(  # noqa: F821
            self.agent_id,
            "TASK_PROCESSING_START",
            task_id=task.task_id,
            details=f"Command: {task.command_type}",
        )

        handler = self._command_handlers.get(task.command_type)
        if not handler:
            error_msg = f"No handler registered for command type '{task.command_type}'"
            self.logger.error(error_msg)
            # EDIT START: Persist failure
            try:
                await self.pbm.update_working_task(
                    task.task_id,
                    {"status": TaskStatus.FAILED.value, "error_details": error_msg},
                )
                self.logger.info(
                    f"Persisted FAILED status for task {task.task_id} (no handler). "
                )
            except Exception as persist_err:
                self.logger.error(
                    f"Failed to persist FAILED status for task {task.task_id} (no handler): {persist_err}"  # noqa: E501
                )
                # Continue to publish event anyway?
            # EDIT END
            await self.publish_task_failed(
                task,
                error=error_msg,
                is_final=True,  # No handler means permanent failure
            )
            return

        result = None
        try:
            # Persist working status
            try:
                await self.pbm.update_working_task(
                    task.task_id, {"status": TaskStatus.WORKING.value}
                )
                self.logger.info(f"Persisted WORKING status for task {task.task_id}. ")
            except Exception as persist_err:
                self.logger.error(
                    f"Failed to persist WORKING status for task {task.task_id}: {persist_err}"  # noqa: E501
                )
                # Should we proceed if we can't update status?
                # For now, log and continue, but publish failure later if needed.

            await self.publish_task_started(task)

            # Execute the handler
            result = await handler(task)
            self.logger.info(f"Task {task.task_id} handler completed.")

            # Validate the result before marking as complete
            is_valid, validation_details = await self._validate_task_completion(
                task, result, result.get("modified_files", [])
            )

            if not is_valid:
                self.logger.warning(
                    f"Task {task.task_id} validation failed: {validation_details}"
                )
                # EDIT START: Persist validation failure
                try:
                    await self.pbm.update_working_task(
                        task.task_id,
                        {
                            "status": TaskStatus.VALIDATION_FAILED.value,
                            "validation_details": validation_details,
                        },
                    )
                    self.logger.info(
                        f"Persisted VALIDATION_FAILED status for task {task.task_id}. "
                    )
                except Exception as persist_err:
                    self.logger.error(
                        f"Failed to persist VALIDATION_FAILED status for task {task.task_id}: {persist_err}"  # noqa: E501
                    )
                    # Continue to publish event anyway?
                # EDIT END
                await self.publish_validation_failed(task, validation_details)
                return

            # If validation passed, proceed to completion
            # EDIT START: Persist completion via move
            try:
                move_success = await self.pbm.move_task_to_completed(
                    task.task_id,
                    final_updates={
                        "status": TaskStatus.COMPLETED.value,  # Ensure status is set
                        "result_summary": result.get(
                            "summary", "Completed without summary."
                        ),  # Example: store summary
                        "result": result,  # Store full result if desired/schema allows
                    },
                )
                if move_success:
                    self.logger.info(
                        f"Successfully persisted COMPLETION for task {task.task_id} via PBM move."  # noqa: E501
                    )
                    await self.publish_task_completed(task, result)
                else:
                    # This case shouldn't happen if move_task_to_completed raises errors on failure  # noqa: E501
                    self.logger.error(
                        f"PBM.move_task_to_completed returned False for task {task.task_id}. Persistence failed."  # noqa: E501
                    )
                    # Publish failure because persistence failed
                    await self.publish_task_failed(
                        task,
                        error="Failed to persist completion status.",
                        is_final=True,
                    )

            except Exception as persist_err:
                self.logger.error(
                    f"Failed to persist COMPLETION status for task {task.task_id} via PBM move: {persist_err}",  # noqa: E501
                    exc_info=True,
                )
                # Publish failure because persistence failed
                await self.publish_task_failed(
                    task,
                    error=f"Failed to persist completion status: {persist_err}",
                    is_final=True,
                )
            # EDIT END

        except asyncio.CancelledError:
            self.logger.warning(f"Task {task.task_id} was cancelled.")
            # EDIT START: Persist cancellation
            try:
                await self.pbm.update_working_task(
                    task.task_id, {"status": TaskStatus.CANCELLED.value}
                )
                self.logger.info(
                    f"Persisted CANCELLED status for task {task.task_id}. "
                )
            except Exception as persist_err:
                self.logger.error(
                    f"Failed to persist CANCELLED status for task {task.task_id}: {persist_err}"  # noqa: E501
                )
            # EDIT END
            await handle_task_cancellation(task, self.agent_id)  # Keep existing helper
            log_agent_event(  # noqa: F821
                self.agent_id, "TASK_CANCELLED", task_id=task.task_id
            )  # Swarm logger

        except Exception as e:
            error_msg = f"Error processing task {task.task_id}: {e}"
            self.logger.exception(error_msg)
            # EDIT START: Persist failure from handler exception
            try:
                await self.pbm.update_working_task(
                    task.task_id,
                    {
                        "status": TaskStatus.FAILED.value,
                        "error_details": error_msg,
                        "traceback": traceback.format_exc(),
                    },
                )
                self.logger.info(
                    f"Persisted FAILED status for task {task.task_id} (handler error). "
                )
            except Exception as persist_err:
                self.logger.error(
                    f"Failed to persist FAILED status for task {task.task_id} (handler error): {persist_err}"  # noqa: E501
                )
                # Continue to publish event anyway?
            # EDIT END
            # Publish specific agent error event
            await self.publish_agent_error(
                error_message=error_msg,
                task_id=task.task_id,
                correlation_id=correlation_id,
                details={"traceback": traceback.format_exc()},
                exc_info=True,
            )
            # Publish generic task failure event (now redundant if agent error is published?)  # noqa: E501
            # await self.publish_task_failed(task, error=str(e), is_final=True)
            log_agent_event(  # noqa: F821
                self.agent_id,
                "TASK_PROCESSING_ERROR",
                task_id=task.task_id,
                details=error_msg,
                error=str(e),
            )

        finally:
            self.logger.debug(f"Finished processing task {task.task_id}.")
            log_task_performance(self.perf_logger, "process_single_task", task.task_id)

    async def _validate_task_completion(
        self,
        task: TaskMessage,
        result: Dict[str, Any],
        modified_files: List[str] = None,
    ) -> tuple[bool, str]:
        """Performs basic and advanced validation checks on task results.

        Args:
            task: The task message object.
            result: The result dictionary returned by the handler.
            modified_files: A list of file paths reported as modified by the handler.

        Returns:
            A tuple (is_valid: bool, details: str).
        """
        validation_errors = []

        # --- Basic Checks --- (Existing)
        if not isinstance(result, dict):
            validation_errors.append("Result is not a dictionary.")
            return False, "; ".join(validation_errors)

        if not result:
            validation_errors.append("Result dictionary is empty.")
            # Allow empty dict for now, maybe revisit
            # return False, "; ".join(validation_errors)

        # Example: Check for mandatory summary field
        if "summary" not in result or not result["summary"]:
            self.logger.warning(f"Task {task.task_id} result missing 'summary' field.")
            # Don't fail validation for missing summary yet, just warn
            # validation_errors.append("Result missing mandatory 'summary' field.")

        # {{ EDIT START: Add flake8 linting validation }}
        # --- Flake8 Linting Check ---
        if modified_files:
            python_files_to_lint = [
                f for f in modified_files if isinstance(f, str) and f.endswith(".py")
            ]
            if python_files_to_lint:
                self.logger.info(
                    f"Running flake8 validation on: {python_files_to_lint}"
                )
                try:
                    # EDIT START: Use configurable flake8 path
                    flake8_path = getattr(
                        self.config, "validation_flake8_path", sys.executable
                    )
                    flake8_args = getattr(
                        self.config, "validation_flake8_args", ["-m", "flake8"]
                    )
                    # Determine if using executable directly or via python -m
                    if flake8_path == sys.executable:  # Default: use python -m flake8
                        command = [flake8_path] + flake8_args + python_files_to_lint
                    else:  # Use specified executable directly
                        command = (
                            [flake8_path] + python_files_to_lint
                        )  # Assume args are baked into path or not needed?
                        # Consider adding flake8_args here too if the executable needs them  # noqa: E501
                    # TODO: Remove the addressed TODO comment below
                    # TODO: Make flake8 path configurable?
                    self.logger.debug(f"Using flake8 command: {' '.join(command)}")
                    # EDIT END

                    # Note: Running directly might be slow for many files.
                    # Consider alternative approaches if performance becomes an issue.
                    process = await asyncio.to_thread(
                        subprocess.run,
                        command,
                        capture_output=True,
                        text=True,
                        check=False,  # Don't raise exception on non-zero exit code
                        cwd=self._project_root,  # Run from project root
                    )

                    if process.returncode != 0:
                        error_details = (
                            f"flake8 failed (exit code {process.returncode})."
                        )
                        if process.stdout:
                            error_details += f"\nOutput:\n{process.stdout[:1000]}..."  # Limit output length  # noqa: E501
                        if process.stderr:
                            error_details += f"\nErrors:\n{process.stderr[:1000]}..."  # Limit output length  # noqa: E501
                        validation_errors.append(error_details)
                        self.logger.warning(
                            f"Flake8 validation failed for task {task.task_id}: {error_details}"  # noqa: E501
                        )
                    else:
                        self.logger.info(
                            f"Flake8 validation passed for task {task.task_id}."
                        )

                except FileNotFoundError:
                    err_msg = (
                        "flake8 command not found. Cannot perform linting validation."
                    )
                    validation_errors.append(err_msg)
                    self.logger.error(err_msg)
                except Exception as e:
                    err_msg = f"Error running flake8: {e}"
                    validation_errors.append(err_msg)
                    self.logger.error(err_msg, exc_info=True)
        # {{ EDIT END }}

        # --- Pytest Execution Check (Future Enhancement) ---
        # TODO: Investigate feasibility of running pytest based on task metadata
        # Requires careful consideration of test discovery, environment, security.
        # Example structure:
        # if "test_modules" in task.metadata:
        #    run_pytest(task.metadata["test_modules"])
        # {{ EDIT START: Implement Pytest Validation }}
        test_modules = task.metadata.get("test_modules") if task.metadata else None
        if test_modules:
            if isinstance(test_modules, str):
                test_modules = [test_modules]  # Ensure it's a list

            if isinstance(test_modules, list) and test_modules:
                self.logger.info(f"Running pytest validation on: {test_modules}")
                try:
                    # Allow configuration of pytest path/args via ConfigManager in the future  # noqa: E501
                    pytest_path = getattr(
                        self.config, "validation_pytest_path", sys.executable
                    )
                    pytest_args = getattr(
                        self.config, "validation_pytest_args", ["-m", "pytest", "-v"]
                    )  # Default to verbose

                    if pytest_path == sys.executable:  # Default: use python -m pytest
                        command = [pytest_path] + pytest_args + test_modules
                    else:  # Use specified executable directly
                        # Assume args might be needed depending on the executable structure  # noqa: E501
                        command = [pytest_path] + pytest_args + test_modules

                    self.logger.debug(
                        f"Using pytest command: {' '.join(map(shlex.quote, command))}"
                    )  # Use shlex.quote for safety

                    process = await asyncio.to_thread(
                        subprocess.run,
                        command,
                        capture_output=True,
                        text=True,
                        check=False,  # Don't raise exception on non-zero exit code
                        cwd=self._project_root,  # Run from project root
                    )

                    if process.returncode != 0:
                        # Use specific pytest exit codes if needed (e.g., 5 means no tests collected)  # noqa: E501
                        error_details = (
                            f"pytest failed (exit code {process.returncode})."
                        )
                        if process.stdout:
                            error_details += f"\nOutput:\n{process.stdout[-1000:]}..."  # Limit output length (show end)  # noqa: E501
                        if process.stderr:
                            error_details += f"\nErrors:\n{process.stderr[:1000]}..."  # Limit output length  # noqa: E501
                        validation_errors.append(error_details)
                        self.logger.warning(
                            f"Pytest validation failed for task {task.task_id}: {error_details}"  # noqa: E501
                        )
                    else:
                        self.logger.info(
                            f"Pytest validation passed for task {task.task_id}."
                        )

                except FileNotFoundError:
                    # Check if it was 'python -m pytest' or a direct path
                    tool_name = (
                        "pytest (via python -m)"
                        if pytest_path == sys.executable
                        else f"pytest executable '{pytest_path}'"
                    )
                    err_msg = f"{tool_name} not found. Cannot perform test validation."
                    validation_errors.append(err_msg)
                    self.logger.error(err_msg)
                except Exception as e:
                    err_msg = f"Error running pytest: {e}"
                    validation_errors.append(err_msg)
                    self.logger.error(err_msg, exc_info=True)
            elif not isinstance(test_modules, list):
                self.logger.warning(
                    f"Task {task.task_id} metadata 'test_modules' is not a list or string, skipping pytest."  # noqa: E501
                )
            # else: test_modules list is empty, do nothing.

        # {{ EDIT END }}

        if validation_errors:
            details = "; ".join(validation_errors)
            # Update task status directly here before returning
            # TODO: Replace with PBM update call
            # self.persist_task_update(task.task_id, {"status": STATUS_VALIDATION_FAILED, "validation_notes": details})  # noqa: E501
            return False, details
        else:
            return True, "Validation passed."

    async def publish_validation_failed(
        self, task: TaskMessage, validation_details: str
    ):
        """Publish an event indicating task validation failed."""
        self.logger.warning(f"Publishing validation failure for task {task.task_id}")
        payload = TaskValidationFailedPayload(
            agent_id=self.agent_id,
            task_id=task.task_id,
            timestamp=datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            + "Z",
            details=validation_details,
            # Add other relevant fields if needed
        )
        await self._publish_event(
            # {{ EDIT START: Use EventType enum }}
            event_type=EventType.TASK_VALIDATION_FAILED,
            # {{ EDIT END }}
            payload_data=(
                payload.model_dump()
                if hasattr(payload, "model_dump")
                else vars(payload)
            ),  # Adapt for Pydantic v1/v2
            correlation_id=task.correlation_id,
        )

    # {{ EDIT END }}

    # Method to handle explicit cancellation requests (e.g., via another command)
    async def _handle_cancel_task(self, cancel_request: TaskMessage):
        """Handle requests to cancel an ongoing task."""
        task_id_to_cancel = cancel_request.payload.get("task_id")
        if not task_id_to_cancel:
            self.logger.error("Received cancel request without task_id.")
            await self.publish_agent_error(
                "Invalid cancel request: Missing task_id",
                details=cancel_request.to_dict(),
                correlation_id=cancel_request.correlation_id,
            )
            return

        self.logger.info(f"Attempting to cancel task {task_id_to_cancel}...")
        if task_id_to_cancel in self._active_tasks:
            async_task = self._active_tasks[task_id_to_cancel]
            if async_task and not async_task.done():
                async_task.cancel()
                self.logger.info(
                    f"Cancellation requested for active task {task_id_to_cancel}."
                )
                # Status update will be handled within _process_single_task's exception handling  # noqa: E501
                # Publish confirmation of cancellation attempt?
                event_data = cancel_request.to_dict()
                event_data["task_id"] = task_id_to_cancel
                await self._publish_event(
                    EventType.TASK_CANCEL_REQUESTED,
                    event_data,
                    cancel_request.correlation_id,
                )
            else:
                self.logger.warning(
                    f"Task {task_id_to_cancel} found in active list but is already done or invalid."  # noqa: E501
                )
        else:
            self.logger.warning(
                f"Could not cancel task {task_id_to_cancel}: Not found in active tasks."
            )
            # Publish failure to cancel?
            event_data = cancel_request.to_dict()
            event_data["task_id"] = task_id_to_cancel
            event_data["error"] = "Task not found or not running"
            await self._publish_event(
                EventType.TASK_CANCEL_FAILED, event_data, cancel_request.correlation_id
            )

    # {{ EDIT START: Add handler method for AGENT_CONTRACT_QUERY }}
    async def _handle_contract_query(self, event: BaseEvent):
        """Handle a request for agent contract/status information."""
        self.logger.info(f"Received contract query: {event.event_type}")

        try:
            # Assuming get_status and get_capabilities are synchronous for now
            # Adapt if they become async
            current_status = self.get_status()  # Example: AgentStatus.IDLE.value
            capabilities_list = (
                self.get_capabilities()
            )  # Example: ["python_dev", "code_review"]
            agent_version = getattr(
                self, "version", "0.1.0"
            )  # Example: Get version attribute or default

            # EDIT: Use AgentStatusEventPayload for status reporting if appropriate,
            # or keep specific AgentContractStatusPayload if needed.
            # For now, sticking to AgentContractStatusPayload as it's specific.
            payload = AgentContractStatusPayload(
                agent_id=self.agent_id,
                version=agent_version,
                operational_status=current_status,
                compliance_status="Compliant",  # Placeholder - needs real logic
                capabilities=capabilities_list,
                last_checked_utc=datetime.now(timezone.utc).isoformat(),
            )

            response_event = BaseEvent(
                event_type=EventType.AGENT_CONTRACT_STATUS,
                source_id=self.agent_id,
                data=payload.to_dict(),  # Assuming payload needs serialization
                correlation_id=event.correlation_id,  # Respond with same correlation ID
            )
            await self.agent_bus.dispatch_event(response_event)
            self.logger.info(
                f"Published AGENT_CONTRACT_STATUS response for {self.agent_id}"
            )

        except Exception as e:
            self.logger.error(f"Error handling contract query: {e}", exc_info=True)
            # Publish an error event about the failure to handle the query
            await self.publish_agent_error(
                f"Failed to process contract query: {e}",
                correlation_id=event.correlation_id,
                exc_info=True,
            )

    # {{ EDIT END }}

    # --- Abstract methods for subclasses --- (Keep as is)
    @abstractmethod
    async def _on_start(self):
        """Subclasses implement their specific startup logic here."""
        pass

    @abstractmethod
    async def _on_stop(self):
        """Subclasses implement their specific shutdown logic here."""
        pass

    def _setup_logger(self):
        """Sets up the logger for the agent."""
        # This method is now empty as the logger setup is handled in the __init__ method
        pass

    # Helper methods (example - implement if needed)
    def get_status(self) -> str:
        # Simple example, replace with actual status logic
        return "IDLE" if not self._active_tasks else "BUSY"

    def get_capabilities(self) -> List[str]:
        # Simple example, replace with actual capability logic
        return list(self._command_handlers.keys())
