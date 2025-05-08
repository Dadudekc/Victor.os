"""Lifecycle methods (start, stop) separated from BaseAgent for modularity."""

import asyncio
from typing import TYPE_CHECKING

# Import error types if needed for specific handling within start/stop
# from ..core.errors import AgentError
# Import decorators if they are defined elsewhere and used here
from ...agents.utils.agent_utils import with_error_handling
# Import log_event if used directly here
from ..memory.governance_memory_engine import log_event

# Import EventType for subscriptions
from .event_types import EventType

if TYPE_CHECKING:
    from .base_agent import BaseAgent  # Use typing guard for BaseAgent hint


class BaseAgentLifecycleMixin:
    """Mixin containing start and stop logic for BaseAgent."""

    # Type hint self to BaseAgent using the TYPE_CHECKING guard
    self: "BaseAgent"

    @with_error_handling(Exception)  # Use broader Exception for now
    async def start(self):
        """Start the agent, subscribe to topics, and launch task processor."""
        self.logger.info(f"Starting agent {self.agent_id}...")
        log_event("AGENT_START", self.agent_id, {"version": "1.0.0"})
        self._running = True

        # Subscribe to command messages using topic string
        command_topic = f"dreamos.agent.{self.agent_id}.task.command"
        self._command_topic = command_topic
        self._command_handler_ref = (
            self._handle_command
        )  # Store actual method reference
        await self.agent_bus.subscribe(self._command_topic, self._command_handler_ref)
        self.logger.info(f"Subscribed to command topic: {self._command_topic}")

        # Subscribe to AGENT_CONTRACT_QUERY
        self._contract_query_topic = EventType.AGENT_CONTRACT_QUERY.value
        self._contract_query_handler_ref = self._handle_contract_query
        await self.agent_bus.subscribe(
            self._contract_query_topic, self._contract_query_handler_ref
        )
        self.logger.info(
            f"Subscribed to contract query topic: {self._contract_query_topic}"
        )

        # Start task processor
        self._task_processor_task = asyncio.create_task(self._process_task_queue())
        self.logger.info("Task processor started.")

        # Call agent-specific startup
        await self._on_start()
        self.logger.info(f"Agent {self.agent_id} started successfully.")

    @with_error_handling(Exception)  # Use broader Exception for now
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
        if hasattr(self, "_command_topic") and hasattr(self, "_command_handler_ref"):
            try:
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

        # Call agent-specific shutdown
        await self._on_stop()

        log_event("AGENT_STOP", self.agent_id, {"reason": "Shutdown requested"})
        self.logger.info(f"Agent {self.agent_id} stopped successfully.")
