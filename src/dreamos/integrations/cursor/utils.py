"""Utility functions for Cursor integration."""

# Initially empty, content will be moved here.

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

# Assuming AgentBus is accessible, potentially via a singleton or context
# Adjust import based on actual AgentBus location and access pattern
from ...core.coordination.agent_bus import AgentBus, EventType, get_agent_bus
from ...core.coordination.event_payloads import CursorInjectRequestPayload

logger = logging.getLogger(__name__)

# Standardized Topic Name
# CURSOR_INJECT_REQUEST_TOPIC = "system.cursor.prompt.request.inject"


async def publish_cursor_inject_event(
    target_agent_id: str,
    prompt: str,
    target_file: Optional[str] = None,
    source_agent_id: str = "AgentController",  # Default sender ID
    correlation_id: Optional[str] = None,
    bus: Optional[AgentBus] = None,  # Allow passing bus instance directly
) -> bool:
    """
    Publishes an event requesting the CursorOrchestrator to inject a prompt
    into a specific agent's Cursor instance using the standardized topic and payload.

    Args:
        target_agent_id: The target agent ID (e.g., "Agent1", "Agent2").
        prompt: The text prompt to inject.
        target_file: Optional target file path for context within Cursor.
        source_agent_id: The ID of the agent or system publishing the event.
        correlation_id: Optional ID to link this request to potential responses.
                         Generates one if not provided.
        bus: Optional AgentBus instance. If None, attempts to get via get_agent_bus(),
             but passing explicitly is recommended for clarity and testability.

    Returns:
        True if publishing was successful (or attempted), False otherwise.
    """
    effective_bus = bus
    if effective_bus is None:
        logger.warning(
            "AgentBus instance not provided to publish_cursor_inject_event. Attempting singleton access via get_agent_bus(). Explicit passing is preferred."
        )
        try:
            effective_bus = get_agent_bus()  # Assuming a singleton accessor
        except Exception as e:
            logger.error(f"Failed to get AgentBus instance via get_agent_bus(): {e}")
            effective_bus = None  # Ensure bus is None if retrieval fails

    if not effective_bus:
        logger.error("Cannot publish cursor inject event: AgentBus not available.")
        return False

    if not correlation_id:
        correlation_id = str(uuid.uuid4())

    # Define payload based on expected structure (adapt if needed)
    try:
        payload_obj = CursorInjectRequestPayload(
            target_file=target_file,
            content=prompt,  # Map prompt to content field
            correlation_id=correlation_id,
        )
        if hasattr(payload_obj, "model_dump"):
            event_payload_dict = payload_obj.model_dump()
        else:
            event_payload_dict = payload_obj.__dict__
            logger.debug(
                "CursorInjectRequestPayload does not have model_dump, using .__dict__."
            )
    except Exception as e:
        logger.error(f"Failed to create CursorInjectRequestPayload: {e}", exc_info=True)
        return False

    try:
        await effective_bus.publish(
            EventType.CURSOR_INJECT_REQUEST, event_payload_dict
        )  # Publish the dict
        logger.info(
            f"Published {EventType.CURSOR_INJECT_REQUEST.name} event for target {target_agent_id} (CorrID: {correlation_id})"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to publish cursor inject event: {e}", exc_info=True)
        return False


# Example Usage might need adjusting if moved
