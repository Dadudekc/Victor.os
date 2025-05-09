"""
Agent9: Response Injector Agent for ChatGPT Scraped Events.

Listens for CHATGPT_RESPONSE_SCRAPED events on the AgentBus, creates a
"cursor_inject_prompt" task, and dispatches it as a TASK_COMMAND event for
Agent2 (or a configurable CURSOR_INJECTION_AGENT_ID) to handle.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type, cast

from dreamos.core.coordination.agent_bus import AgentBus, BaseEvent, EventType

# Core Dream.OS imports aligned with BaseAgent
from dreamos.core.config import AppConfig

# FIXME: BaseAgent import path should be consistent across all agents.
#        Using dreamos.core.coordination.base_agent here. Ensure this is the canonical path.
from dreamos.core.coordination.base_agent import BaseAgent
from dreamos.core.tasks.models import TaskMessage, TaskPriority, TaskStatus

# from dreamos.core.coordination.message_patterns import create_task_message # Removed unused import  # noqa: E501
# Assuming time_utils exists and provides this
# from dreamos.core.utils.time_utils import utc_now_iso

# Basic logging configuration (can be refined)
# FIXME: Module-level basicConfig can interfere; configure logging at app entry point.
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# )
logger = logging.getLogger("Agent9ResponseInjector")

# FIXME: CURSOR_INJECTION_AGENT_ID should be configurable via AppConfig.
CURSOR_INJECTION_AGENT_ID = "Agent2"

from dreamos.core.coordination.agent_bus import (
    BusError,
    Event,
)

from dreamos.core.coordination.agent_bus import (
    BusError,
    Event,
)

class Agent9ResponseInjector(BaseAgent):
    """Listens for CHATGPT_RESPONSE_SCRAPED events and triggers Cursor injection tasks."""  # noqa: E501

    def __init__(
        self, agent_id: str, config: AppConfig, agent_bus: AgentBus, **kwargs
    ) -> None:
        # FIXME: AgentBus should be a mandatory injected dependency.
        #        Fallback creation is for testing/standalone and can hide issues.
        if agent_bus is None:
            logger.warning(
                "AgentBus not provided to Agent9ResponseInjector, attempting to create one (may not be shared!)"
            )
            from dreamos.coordination.agent_bus import (
                AgentBus as FallbackAgentBus,
            )

            agent_bus = FallbackAgentBus()

        if config is None:
            raise ValueError(
                "AppConfig instance is required for Agent9ResponseInjector"
            )

        super().__init__(
            agent_id=agent_id, config=config, agent_bus=agent_bus, **kwargs
        )
        logger.info(f"Agent9ResponseInjector '{self.agent_id}' initialized.")

    async def initialize(self) -> None:
        """Subscribe to scraped response events at startup."""
        try:
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
                await self.publish_agent_error(
                    "Configuration Error: EventType.CHATGPT_RESPONSE_SCRAPED missing."
                )
        except Exception as e:
            self.logger.error(f"Error during subscription: {e}", exc_info=True)
            await self.publish_agent_error(f"Subscription failed: {e}")
        await super().initialize()

    async def shutdown(self) -> None:
        """Ensure cleanup on stop."""
        self.logger.info("Stopping Agent9ResponseInjector...")
        try:
            if hasattr(EventType, "CHATGPT_RESPONSE_SCRAPED"):
                await self.agent_bus.unsubscribe(
                    EventType.CHATGPT_RESPONSE_SCRAPED, self._handle_scraped_response
                )
                self.logger.info(
                    f"Unsubscribed from {EventType.CHATGPT_RESPONSE_SCRAPED.name} events."
                )
            else:
                self.logger.warning(
                    "EventType.CHATGPT_RESPONSE_SCRAPED not found! Cannot unsubscribe."
                )
        except Exception as e:
            self.logger.error(f"Error during unsubscription: {e}", exc_info=True)
        await super().shutdown()
        self.logger.info("Agent9ResponseInjector stopped.")

    async def _handle_scraped_response(self, event: BaseEvent) -> None:
        """Handle incoming scraped ChatGPT response event."""
        try:
            if not isinstance(event.data, dict):
                self.logger.warning(
                    f"Received {event.event_type.name} event with invalid data type: {type(event.data)}. Ignoring."
                )
                return

            payload = event.data
            source_event_id = event.event_id
            self.logger.info(
                f"Handling {event.event_type.name} event (ID: {source_event_id}). Author: {payload.get('author')}, Source: {payload.get('source')}"
            )
            self.logger.debug(f"Payload: {payload}")

            content_to_inject = payload.get("content")
            if not content_to_inject:
                self.logger.warning(
                    f"Scraped event (ID: {source_event_id}) missing 'content'. Ignoring."
                )
                return

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

            command_event = BaseEvent(
                event_type=EventType.TASK_COMMAND,
                source_id=self.agent_id,
                # FIXME: Verify if TaskMessage uses .model_dump() (Pydantic v2+)
                #        or .to_dict() (Pydantic v1 or custom). Using .model_dump() assuming Pydantic v2+.
                data=injection_task_msg.model_dump(),
                correlation_id=correlation_id,
            )
            await self.agent_bus.dispatch_event(command_event)
            self.logger.info(
                f"Published event {EventType.TASK_COMMAND.name} for task '{injection_task_msg.task_type}' ({new_task_id}) (CorrID: {correlation_id})"
            )

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
            await self.publish_agent_error(
                error_message=f"Failed to handle scraped response: {e}",
                details=error_details,
                correlation_id=event.correlation_id,
            )


# Example of how to run the agent (requires AgentBus setup)
async def main():
    logging.basicConfig(level=logging.DEBUG)
    logger.info("Setting up Agent9 Response Injector...")

    from dreamos.coordination.agent_bus import (
        AgentBus as ExampleAgentBus,
    )

    bus = ExampleAgentBus()
    await bus.start()

    try:
        config = AppConfig.load()
    except Exception as e:
        logger.error(f"Failed to load AppConfig for Agent9 standalone run: {e}")
        await bus.shutdown()
        return

    agent9 = Agent9ResponseInjector(
        agent_id="Agent9-Injector-Test", config=config, agent_bus=bus
    )
    await agent9.start()

    logger.info("Agent9 started. Waiting for CHATGPT_RESPONSE_SCRAPED events...")
    logger.info("Publishing a dummy event for testing...")

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
            source_id="TestScraperAgent",
            data=dummy_event_payload,
        )
        await bus.dispatch_event(dummy_event)
    else:
        logger.error(
            "Cannot publish dummy event: EventType.CHATGPT_RESPONSE_SCRAPED missing."
        )

    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Main task cancelled.")
    finally:
        logger.info("Shutting down Agent9...")
        await agent9.stop()
        await bus.shutdown()
        logger.info("Agent9 and Bus stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Agent9 manually interrupted.")
