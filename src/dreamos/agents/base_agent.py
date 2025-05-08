# src/dreamos/agents/base_agent.py
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import asyncio
from pathlib import Path

# Assuming these might be needed, import placeholders/actual implementations
from dreamos.core.config import AppConfig
from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.core.comms.mailbox_utils import validate_mailbox_message_schema, MailboxMessageType, list_mailbox_messages, read_message, delete_message

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

    @property
    def status(self) -> str:
        """Returns the current status of the agent."""
        return self._current_status

    async def set_status(self, status: str, details: Optional[dict] = None):
        """Sets the agent's status and optionally publishes an event."""
        # Basic status update, subclasses might override
        old_status = self._current_status
        self._current_status = status
        self.logger.info(f"Agent {self.agent_id} status changed: {old_status} -> {status}")
        # TODO: Implement event publishing (requires EventType, Payloads)
        # Example:
        # if self.agent_bus:
        #     from dreamos.core.coordination.event_payloads import AgentStatusChangePayload
        #     from dreamos.core.coordination.events import AgentStatusChangeEvent # Assuming exists
        #     payload = AgentStatusChangePayload(agent_id=self.agent_id, new_status=status, old_status=old_status)
        #     event = AgentStatusChangeEvent(data=payload) # Need full event structure
        #     await self.agent_bus.publish(f"agent.{self.agent_id}.status", event.model_dump())

    @abstractmethod
    async def run_autonomous_loop(self):
        """The main autonomous execution loop for the agent."""
        pass

    async def _handle_bus_message(self, topic: str, data: dict):
        """Placeholder for handling messages received from the bus."""
        self.logger.debug(
            f"Agent {self.agent_id} received message on topic {topic}: {data.keys()}"
        )
        pass

    async def _scan_and_process_mailbox(self, specific_mailbox_path: Path):
        """
        Scans the specified mailbox directory for messages and processes them.
        This is a generic mailbox scanning loop that agents can use.

        Args:
            specific_mailbox_path: The Path object pointing to the inbox to scan.
        """
        self.logger.debug(f"[{self.agent_id}] Scanning mailbox: {specific_mailbox_path}")
        try:
            if not await asyncio.to_thread(specific_mailbox_path.exists):
                self.logger.warning(
                    f"[{self.agent_id}] Mailbox inbox directory not found: {specific_mailbox_path}"
                )
                return

            messages = await list_mailbox_messages(specific_mailbox_path)
            if not messages:
                self.logger.debug(f"[{self.agent_id}] Mailbox {specific_mailbox_path} empty.")
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
                except Exception as msg_proc_err:
                    self.logger.error(
                        f"[{self.agent_id}] Error during processing of message {msg_file_path.name}: {msg_proc_err}",
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
                                exc_info=True
                            )
                    else:
                        self.logger.warning(
                            f"[{self.agent_id}] Message {msg_file_path.name} not processed successfully or failed to read. Leaving in mailbox."
                        )

        except Exception as scan_err:
            self.logger.error(
                f"[{self.agent_id}] Error scanning mailbox {specific_mailbox_path}: {scan_err}", exc_info=True
            )

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
            return False # Indicate processing failure
        
        # Base class considers the message processed if schema validation passes.
        # Subclasses should override to implement specific logic and manage their own success/failure return.
        self.logger.debug(f"Agent {self.agent_id}: Base processing for message ID '{message_id}' complete.")
        return True 

    async def initialize(self):
        """Optional asynchronous initialization steps for the agent."""
        self.logger.info(f"[{self.agent_id}] Performing async initialization...")
        await self.set_status("IDLE")
        self.logger.info(f"[{self.agent_id}] Initialized and IDLE.")
        # Example: Subscribe to relevant topics
        # await self.agent_bus.subscribe(f"agent.{self.agent_id}.command", self._handle_bus_message)

    async def shutdown(self):
        """Optional asynchronous cleanup steps for the agent."""
        self.logger.info(f"[{self.agent_id}] Shutting down...")
        await self.set_status("SHUTDOWN")
        # Example: Unsubscribe from topics
        # await self.agent_bus.unsubscribe(f"agent.{self.agent_id}.command", self._handle_bus_message)


# Need to import asyncio if used above
