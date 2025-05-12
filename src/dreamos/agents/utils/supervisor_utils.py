"""Supervisor alert utilities for agent functionality."""

import logging
from typing import Optional

from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.core.coordination.event_payloads import SupervisorAlertPayload
from dreamos.core.coordination.event_types import EventType
from ...utils.common_utils import get_utc_iso_timestamp

logger = logging.getLogger(__name__)

async def publish_supervisor_alert(
    bus: AgentBus,
    source_agent_id: str,
    blocker_summary: str,
    blocking_task_id: Optional[str] = None,
    details_reference: Optional[str] = None,
) -> str:
    """Publish a supervisor alert about a blocking issue.
    
    Args:
        bus: The AgentBus instance for publishing the alert.
        source_agent_id: ID of the agent sending the alert.
        blocker_summary: Summary of the blocking issue.
        blocking_task_id: Optional ID of the task being blocked.
        details_reference: Optional reference to additional details.
        
    Returns:
        str: The generated alert ID if successful, empty string if failed.
    """
    alert_id = f"alert_{get_utc_iso_timestamp()}"
    alert_payload = SupervisorAlertPayload(
        alert_id=alert_id,
        source_agent_id=source_agent_id,
        blocker_summary=blocker_summary,
        blocking_task_id=blocking_task_id,
        details_reference=details_reference,
    )

    try:
        await bus.publish(EventType.SUPERVISOR_ALERT.value, alert_payload.model_dump())
        logger.info(f"Published supervisor alert {alert_id} from {source_agent_id}")
        return alert_id
    except Exception as e:
        logger.error(
            f"Failed to publish supervisor alert from {source_agent_id}: {e}",
            exc_info=True,
        )
        return "" 