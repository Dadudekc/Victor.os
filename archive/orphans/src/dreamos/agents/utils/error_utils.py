"""Error handling and reporting utilities for agent functionality."""

import logging
import traceback
from typing import Any, Dict, Optional

from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.core.coordination.event_types import EventType

from ...utils.common_utils import get_utc_iso_timestamp

logger = logging.getLogger(__name__)


async def publish_error(
    bus: AgentBus,
    error_message: str,
    agent_id: str,
    correlation_id: Optional[str],
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Publish an error message to the system error topic and potentially a response topic."""
    system_error_topic = EventType.SYSTEM_ERROR.value
    error_data = {
        "error": error_message,
        "source_agent": agent_id,
        "traceback": traceback.format_exc(),
        **(details or {}),
    }
    error_message_payload = {
        "sender_id": agent_id,
        "correlation_id": correlation_id,
        "timestamp_utc": get_utc_iso_timestamp(),
        "data": error_data,
    }

    try:
        await bus.publish(system_error_topic, error_message_payload)
        logger.debug(
            f"Published error from {agent_id} to {system_error_topic} (CorrID: {correlation_id})"
        )
    except Exception as e:
        logger.error(
            f"Failed to publish system error message from {agent_id}: {e}",
            exc_info=True,
        )

    if correlation_id:
        response_topic = f"system.response.{correlation_id}.error"
        try:
            await bus.publish(response_topic, error_message_payload)
            logger.debug(
                f"Published error response from {agent_id} to {response_topic}"
            )
        except Exception as e:
            logger.error(
                f"Failed to publish error response message to {response_topic}: {e}",
                exc_info=True,
            )
