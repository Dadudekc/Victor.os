"""Broadcasts coordination directives to agents via AgentBus."""

import asyncio
import logging
import uuid
from typing import Any, Dict, Optional

from dreamos.coordination.agent_bus import AgentBus, BaseEvent
from dreamos.core.coordination.event_payloads import BroadcastPayload
from dreamos.core.coordination.event_types import EventType
from dreamos.core.coordination.events import (
    CoordinationDirectiveData,
    CoordinationDirectiveEvent,
)

logger = logging.getLogger(__name__)


async def broadcast_to_agents(
    directive_content: Dict[str, Any],
    agent_bus: AgentBus,  # Explicitly pass AgentBus instance
    source_id: str = "broadcast_tool",  # Identify the source
    dry_run: bool = False,
) -> None:
    """
    Broadcasts a directive to all agents via AgentBus COORDINATION events.

    Args:
        directive_content (Dict[str, Any]): The core content for the directive.
                                           Should contain keys relevant to the directive type.
        agent_bus (AgentBus): The AgentBus instance to use for dispatching.
        source_id (str): Identifier for the source of the broadcast.
        dry_run (bool): If True, logs the intended broadcast but does not actually dispatch.

    Example:
        bus = AgentBus() # Get instance
        await broadcast_to_agents(
            {
                "directive": "UPDATE_STATUS", # The actual command
                "params": { # Parameters for the command
                    "task_id": "12345",
                    "status": "completed"
                 }
            },
            agent_bus=bus,
            source_id="task_monitor"
        )
    """
    # Extract directive and params from content
    directive = directive_content.get("directive", "GENERIC_DIRECTIVE")
    params = directive_content.get("params", {})
    # Include any other top-level keys from directive_content in params for backward compatibility?
    # Or enforce structure? Let's enforce structure for now.
    other_params = {
        k: v for k, v in directive_content.items() if k not in ["directive", "params"]
    }
    if other_params:
        logger.warning(
            f"Extra keys found in directive_content: {other_params.keys()}. Moving to params."
        )
        params.update(other_params)

    event_data = CoordinationDirectiveData(
        # target_agent_id=None, # Default is broadcast
        directive=directive,
        params=params,
    )

    event = CoordinationDirectiveEvent(
        source_id=source_id,
        data=event_data,
        # event_type is set by default in CoordinationDirectiveEvent
    )

    if dry_run:
        # logger.info(f"[DRY RUN] Would broadcast directive via AgentBus: {payload}")
        logger.info(f"[DRY RUN] Would broadcast directive event via AgentBus: {event}")
        return

    # logger.info(f"Broadcasting directive via AgentBus: {payload}")
    logger.info(
        f"Broadcasting directive event via AgentBus: Type={event.event_type.name}, Source={event.source_id}"
    )
    logger.debug(f"Broadcast Event Details: {event}")
    try:
        # await agent_bus.dispatch_event(EventType.COORDINATION_DIRECTIVE, payload)
        await agent_bus.dispatch_event(event)
        # logger.debug(f"Successfully dispatched broadcast event: {payload.get('type')}")
        logger.debug(f"Successfully dispatched broadcast event: {event.event_id}")
    except Exception as e:
        logger.error(
            f"Failed to broadcast directive event via AgentBus: {e}", exc_info=True
        )
        # Optionally, re-raise or handle the error based on requirements


# Note: Removed the __main__ block as this is intended to be used as a library function.
# The original CLI functionality (reading from file/content arg) would need
# to be rebuilt in a dedicated CLI tool or integrated elsewhere if still needed,
# ensuring it gets an AgentBus instance.
