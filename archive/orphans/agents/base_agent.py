# src/dreamos/agents/base_agent.py
import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Coroutine, Optional

from dreamos.core.comms.mailbox_utils import (
    delete_message,
    list_mailbox_messages,
    read_message,
    validate_mailbox_message_schema,
)

# Assuming these might be needed, import placeholders/actual implementations
from dreamos.core.config import AppConfig
from dreamos.core.coordination.agent_bus import AgentBus

# ADDED: Import utilities from agent_utils
from .utils.agent_utils import (
    AgentError,  # Base error class for agents
    MessageHandlingError,  # Specific error for message processing
    safe_create_task,
    with_error_handling,
)

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all DreamOS agents."""

    def __init__(self, agent_id: str, config: AppConfig, agent_bus: AgentBus, **kwargs):
        """
        Initializes the BaseAgent.

        Args:
            agent_id: The unique identifier for this agent instance.
            config: The global application configuration.
            agent_bus: The system-wide event bus for communication.
            **kwargs: Absorbs extra arguments from subclasses or instantiation.
        """
        self.agent_id = agent_id
        self.config = config
        self.agent_bus = agent_bus
        self._current_status: str = "INITIALIZING"  # Example status tracking
        self.logger = logging.getLogger(f"Agent.{self.agent_id}")
        self.logger.info(f"BaseAgent {self.agent_id} initialized.")
        self._extra_kwargs = kwargs
        # TODO: Consider adding PerformanceLogger instance here if performance tracking is desired
        # self.perf_logger = PerformanceLogger(f"Agent.{self.agent_id}")

    @property
    def status(self) -> str:
        """Returns the current status of the agent."""
        return self._current_status

    async def set_status(self, status: str, details: Optional[dict] = None):
        """Sets the agent's status and optionally publishes an event."""
        # Basic status update, subclasses might override
        old_status = self._current_status
        self._current_status = status
        self.logger.info(
            f"Agent {self.agent_id} status changed: {old_status} -> {status}"
        )
        # TODO: Implement event publishing (requires EventType, Payloads)
        # Example:
        # if self.agent_bus:
        #     from dreamos.core.coordination.event_payloads import AgentStatusChangePayload
        #     from dreamos.core.coordination.events import AgentStatusChangeEvent # Assuming exists
        #     payload = AgentStatusChangePayload(agent_id=self.agent_id, new_status=status, old_status=old_status)
        #     event = AgentStatusChangeEvent(data=payload) # Need full event structure
        #     await self.agent_bus.publish(f"agent.{self.agent_id}.status", event.model_dump())

    @abstractmethod
    @with_error_handling(error_class=AgentError)
    async def run_autonomous_loop(self):
        """The main autonomous execution loop for the agent."""
        pass

    @with_error_handling(error_class=MessageHandlingError)
    async def _handle_bus_message(self, topic: str, data: dict):
        """Placeholder for handling messages received from the bus."""
        self.logger.debug(
            f"Agent {self.agent_id} received message on topic {topic}: {data.keys()}"
        )
        pass

    @with_error_handling(error_class=AgentError)
    async def _scan_and_process_mailbox(self, specific_mailbox_path: Path):
        """
        Scans the specified mailbox directory for messages and processes them.
        This is a generic mailbox scanning loop that agents can use.

        Args:
            specific_mailbox_path: The Path object pointing to the inbox to scan.
        """
        self.logger.debug(
            f"[{self.agent_id}] Scanning mailbox: {specific_mailbox_path}"
        )
        try:
            if not await asyncio.to_thread(specific_mailbox_path.exists):
                self.logger.warning(
                    f"[{self.agent_id}] Mailbox inbox directory not found: {specific_mailbox_path}"
                )
                return

            messages = await list_mailbox_messages(specific_mailbox_path)
            if not messages:
                self.logger.debug(
                    f"[{self.agent_id}] Mailbox {specific_mailbox_path} empty."
                )
                return

            self.logger.info(
                f"[{self.agent_id}] Found {len(messages)} messages in {specific_mailbox_path}."
            )
            for msg_file_path in messages:
                message_content = None
                processed_ok = False
                try:
                    message_content = await read_message(msg_file_path)
                    if message_content:
                        self.logger.debug(
                            f"[{self.agent_id}] Processing message file: {msg_file_path.name}"
                        )
                        processed_ok = await self._process_message(message_content)
                    else:
                        self.logger.warning(
                            f"[{self.agent_id}] Failed to read message content from {msg_file_path.name}. Marked as not processed."
                        )
                except Exception as msg_read_err:
                    self.logger.error(
                        f"[{self.agent_id}] Error reading message file {msg_file_path.name}: {msg_read_err}",
                        exc_info=True,
                    )
                finally:
                    if processed_ok:
                        try:
                            await delete_message(msg_file_path)
                            self.logger.info(
                                f"[{self.agent_id}] Processed and deleted message: {msg_file_path.name}"
                            )
                        except Exception as del_err:
                            self.logger.error(
                                f"[{self.agent_id}] Failed to delete message {msg_file_path.name} after successful processing: {del_err}",
                                exc_info=True,
                            )
                    else:
                        self.logger.warning(
                            f"[{self.agent_id}] Message {msg_file_path.name} not processed successfully or failed to read. Leaving in mailbox."
                        )

        except Exception as scan_err:
            self.logger.error(
                f"[{self.agent_id}] Error scanning mailbox {specific_mailbox_path}: {scan_err}",
                exc_info=True,
            )

    @with_error_handling(error_class=MessageHandlingError)
    async def _process_message(self, message_content: dict) -> bool:
        """
        Processes a single message received in the agent's mailbox.
        Base implementation. Subclasses can override for specific message handling logic
        and should call super()._process_message() if they wish to include this base logging and validation.
        Returns True if basic processing (like validation) passes and no errors occur at this level, False otherwise.
        """
        message_id = message_content.get("message_id", "no_id")
        message_type = message_content.get("type", "unknown")

        self.logger.info(
            f"Agent {self.agent_id} received mailbox message ID '{message_id}' of type '{message_type}'."
        )

        if not validate_mailbox_message_schema(message_content):
            self.logger.error(
                f"Agent {self.agent_id}: Mailbox message ID '{message_id}' failed schema validation. Discarding."
            )
            # TODO: Consider moving to a malformed_messages folder instead of just logging and discarding.
            return False  # Indicate processing failure

        # Base class considers the message processed if schema validation passes.
        # Subclasses should override to implement specific logic and manage their own success/failure return.
        self.logger.debug(
            f"Agent {self.agent_id}: Base processing for message ID '{message_id}' complete."
        )
        return True

    @with_error_handling(error_class=AgentError)
    async def initialize(self):
        """Optional asynchronous initialization steps for the agent."""
        self.logger.info(f"[{self.agent_id}] Performing async initialization...")
        await self.set_status("IDLE")
        self.logger.info(f"[{self.agent_id}] Initialized and IDLE.")
        # Example: Subscribe to relevant topics
        # await self.agent_bus.subscribe(f"agent.{self.agent_id}.command", self._handle_bus_message)

    @with_error_handling(error_class=AgentError)
    async def shutdown(self):
        """Optional asynchronous cleanup steps for the agent."""
        self.logger.info(f"[{self.agent_id}] Shutting down...")
        await self.set_status("SHUTDOWN")
        # Example: Unsubscribe from topics
        # await self.agent_bus.unsubscribe(f"agent.{self.agent_id}.command", self._handle_bus_message)

    # ADDED: Helper for safe task creation
    async def _safe_create_task(
        self, coro: Coroutine, *, name: Optional[str] = None
    ) -> asyncio.Task:
        """Creates an asyncio Task safely, ensuring exceptions are logged.

        Args:
            coro: The coroutine to run.
            name: Optional name for the task.

        Returns:
            The created asyncio Task.
        """
        # Uses the safe_create_task utility, passing the agent's logger instance
        return await safe_create_task(coro, name=name, logger_instance=self.logger)


# Need to import asyncio if used above
