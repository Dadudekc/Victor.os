# _agent_coordination/services/dispatcher_bus.py

import uuid
import asyncio
import logging
from typing import Dict, Any, Optional

from ..services.dispatcher import Dispatcher
from ..core.config import CursorCoordinatorConfig
from ..agent_bus import Event, EventType

logger = logging.getLogger("AgentBusDispatcher")

class AgentBusDispatcher(Dispatcher):
    """
    Dispatcher implementation that routes actions via the AgentBus event system.
    """
    def __init__(self, agent_bus: Any, config: CursorCoordinatorConfig):
        self.agent_bus = agent_bus
        self.config = config
        self.pending_futures: Dict[str, asyncio.Future] = {}

    async def route(
        self,
        action_dict: Dict[str, Any],
        **kwargs
    ) -> Optional[str]:
        action = action_dict.get("action")
        params = action_dict.get("params", {})
        original_task_id = kwargs.get("original_task_id", "unknown")
        instance_id = kwargs.get("instance_id")

        if action == "save_file":
            path = params.get("path")
            content = params.get("content")
            if not path or content is None:
                logger.error("Missing path or content for save_file action.")
                return None
            sub_task_id = f"{original_task_id}_save_{uuid.uuid4().hex[:4]}"
            event_data = {
                "type": "file_write_request",
                "task_id": sub_task_id,
                "agent": "FileManagerAgent",
                "path": path,
                "content": content,
                "source_agent": "CursorChatCoordinator",
                "parent_task_id": original_task_id
            }
            event = Event(type=EventType.TASK, source_id="CursorChatCoordinator", data=event_data)
            try:
                future = asyncio.get_running_loop().create_future()
                self.pending_futures[sub_task_id] = future
                await self.agent_bus._dispatcher.dispatch_event(event)
                return sub_task_id
            except Exception as e:
                logger.error(f"Failed to dispatch save_file event: {e}", exc_info=True)
                return None

        elif action == "execute_cursor_goal":
            # Plan translation and dispatch is managed by the coordinator directly
            logger.warning("execute_cursor_goal should be handled by CursorChatCoordinator.")
            return None

        elif action == "task_complete":
            # No dispatch needed for completion
            logger.info(f"Task {original_task_id} marked complete; no dispatch action.")
            return None

        else:
            logger.warning(f"Unhandled action in dispatcher: {action}")
            return None 