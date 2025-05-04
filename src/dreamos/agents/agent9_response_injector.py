"""Agent9: Response Injector Agent for ChatGPT Scraped Events."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dreamos.coordination.agent_bus import AgentBus, BaseEvent, EventType

# Core Dream.OS imports aligned with BaseAgent
from dreamos.core.coordination.base_agent import BaseAgent
from dreamos.core.tasks.models import TaskMessage, TaskPriority, TaskStatus

# from dreamos.core.coordination.message_patterns import create_task_message # Removed unused import  # noqa: E501
# Assuming time_utils exists and provides this
# from dreamos.core.utils.time_utils import utc_now_iso

# Basic logging configuration (can be refined)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Agent9ResponseInjector")

# Define the target agent responsible for handling cursor injection tasks
# This might be configurable later
CURSOR_INJECTION_AGENT_ID = "Agent2"


class Agent9ResponseInjector(BaseAgent):
    """Listens for CHATGPT_RESPONSE_SCRAPED events and triggers Cursor injection tasks."""  # noqa: E501

    # Align __init__ with BaseAgent
    def __init__(
        self,
        agent_id: str = "Agent9",
        agent_bus: Optional[AgentBus] = None,
        task_list_path: Optional[Path] = None,
    ) -> None:
        # Ensure AgentBus is provided (dependency injection)
        if agent_bus is None:
            # In a real scenario, AgentBus would likely be injected by the framework
            # This is a fallback for potential standalone use/testing, but not ideal
            logger.warning(
                "AgentBus not provided to Agent9ResponseInjector, attempting to create one (may not be shared!)"  # noqa: E501
            )
            # This part needs careful handling based on how AgentBus is managed globally
            # Update import path here
            from dreamos.coordination.agent_bus import (
                AgentBus as FallbackAgentBus,  # Use canonical path and alias if needed
            )

            agent_bus = FallbackAgentBus()  # Use canonical AgentBus

        super().__init__(agent_id, agent_bus, task_list_path)
        logger.info(f"Agent9ResponseInjector '{self.agent_id}' initialized.")

    async def _on_start(self) -> None:
        """Subscribe to scraped response events at startup."""
        try:
            # Ensure EventType has the required member (assuming Step 4 completed)
            if hasattr(EventType, "CHATGPT_RESPONSE_SCRAPED"):
                await self.agent_bus.subscribe(
                    EventType.CHATGPT_RESPONSE_SCRAPED, self._handle_scraped_response
                )
                self.logger.info(
                    f"Subscribed to {EventType.CHATGPT_RESPONSE_SCRAPED.name} events."
                )
            else:
                self.logger.error(
                    "EventType.CHATGPT_RESPONSE_SCRAPED not found! Cannot subscribe."
                )
                # Potentially stop the agent or enter an error state
                await self.publish_agent_error(
                    "Configuration Error: EventType.CHATGPT_RESPONSE_SCRAPED missing."
                )
        except Exception as e:
            self.logger.error(f"Error during subscription: {e}", exc_info=True)
            await self.publish_agent_error(f"Subscription failed: {e}")
        # Call superclass _on_start if it has logic
        await super()._on_start()

    async def _on_stop(self) -> None:
        """Ensure cleanup on stop."""
        self.logger.info("Stopping Agent9ResponseInjector...")
        # Add specific cleanup if needed
        # Unsubscribe from events
        try:
            if hasattr(EventType, "CHATGPT_RESPONSE_SCRAPED"):
                await self.agent_bus.unsubscribe(
                    EventType.CHATGPT_RESPONSE_SCRAPED, self._handle_scraped_response
                )
                self.logger.info(
                    f"Unsubscribed from {EventType.CHATGPT_RESPONSE_SCRAPED.name} events."  # noqa: E501
                )
            else:
                self.logger.warning(
                    "EventType.CHATGPT_RESPONSE_SCRAPED not found! Cannot unsubscribe."
                )
        except Exception as e:
            self.logger.error(f"Error during unsubscription: {e}", exc_info=True)

        await super()._on_stop()
        self.logger.info("Agent9ResponseInjector stopped.")

    async def _handle_scraped_response(self, event: BaseEvent) -> None:
        """Handle incoming scraped ChatGPT response event."""
        try:
            # Validate payload structure (basic check)
            if not isinstance(event.data, dict):
                self.logger.warning(
                    f"Received {event.event_type.name} event with invalid data type: {type(event.data)}. Ignoring."  # noqa: E501
                )
                return

            payload = event.data
            source_event_id = event.event_id
            self.logger.info(
                f"Handling {event.event_type.name} event (ID: {source_event_id}). Author: {payload.get('author')}, Source: {payload.get('source')}"  # noqa: E501
            )
            self.logger.debug(f"Payload: {payload}")

            content_to_inject = payload.get("content")
            if not content_to_inject:
                self.logger.warning(
                    f"Scraped event (ID: {source_event_id}) missing 'content'. Ignoring."  # noqa: E501
                )
                return

            # --- Create and Dispatch Cursor Injection Task ---
            new_task_id = f"inject_{self.agent_id}_{uuid.uuid4()}"
            correlation_id = event.correlation_id or str(uuid.uuid4())

            task_params = {
                "prompt": content_to_inject,
            }

            injection_task_msg = TaskMessage(
                task_id=new_task_id,
                task_type="cursor_inject_prompt",
                params=task_params,
                priority=TaskPriority.HIGH,
                status=TaskStatus.PENDING,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                source_agent_id=self.agent_id,
                target_agent_id=CURSOR_INJECTION_AGENT_ID,
                correlation_id=correlation_id,
            )

            # Publish a standard TASK_COMMAND event
            # The routing/dispatching mechanism should handle getting this to the right agent.  # noqa: E501
            command_event = BaseEvent(
                event_type=EventType.TASK_COMMAND,
                source_id=self.agent_id,
                data=injection_task_msg.to_dict(),  # Send TaskMessage as payload
                correlation_id=correlation_id,
            )
            await self.agent_bus.dispatch_event(command_event)
            self.logger.info(
                f"Published event {EventType.TASK_COMMAND.name} for task '{injection_task_msg.task_type}' ({new_task_id}) (CorrID: {correlation_id})"  # noqa: E501
            )

            # Optionally publish an event confirming the task request was sent (REDUNDANT now?)  # noqa: E501
            # await self._publish_event(EventType.TASK_REQUEST_SENT, injection_task_msg.to_dict(), correlation_id)  # noqa: E501

        except Exception as e:
            error_details = {
                "event_id": event.event_id,
                "payload": event.data,
                "error": str(e),
            }
            self.logger.error(
                f"Failed to handle scraped response event {event.event_id}: {e}",
                exc_info=True,
            )
            # Corrected publish_agent_error call
            await self.publish_agent_error(
                error_message=f"Failed to handle scraped response: {e}",
                details=error_details,
                correlation_id=event.correlation_id,
            )


# Example of how to run the agent (requires AgentBus setup)
async def main():
    logging.basicConfig(level=logging.DEBUG)  # Use DEBUG for detailed logs
    logger.info("Setting up Agent9 Response Injector...")

    # --- AgentBus Setup (Example - Replace with actual shared bus) ---
    # Update import path here
    from dreamos.coordination.agent_bus import (
        AgentBus as ExampleAgentBus,  # Use canonical path and alias
    )

    bus = ExampleAgentBus()
    await bus.start()  # Start the bus
    # --- End AgentBus Setup ---

    agent9 = Agent9ResponseInjector(agent_bus=bus)
    await agent9.start()

    logger.info("Agent9 started. Waiting for CHATGPT_RESPONSE_SCRAPED events...")
    logger.info("Publishing a dummy event for testing...")

    # --- Dummy Event Publishing (For Testing) ---
    if hasattr(EventType, "CHATGPT_RESPONSE_SCRAPED"):
        dummy_event_payload = {
            "source": "chatgpt",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "author": "assistant",
            "content": "This is a test response scraped from ChatGPT.",
            "conversation_id": "conv_123",
            "message_id": "msg_456",
        }
        dummy_event = BaseEvent(
            event_type=EventType.CHATGPT_RESPONSE_SCRAPED,
            source_id="TestScraperAgent",  # Simulate source
            data=dummy_event_payload,
        )
        await bus.dispatch_event(dummy_event)
    else:
        logger.error(
            "Cannot publish dummy event: EventType.CHATGPT_RESPONSE_SCRAPED missing."
        )
    # --- End Dummy Event Publishing ---

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Main task cancelled.")
    finally:
        logger.info("Shutting down Agent9...")
        await agent9.stop()
        await bus.shutdown()  # Shutdown the bus
        logger.info("Agent9 and Bus stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Execution interrupted by user.")
