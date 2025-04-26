import logging
from typing import Any, Optional, Dict
from ..core.config import CursorCoordinatorConfig
from ..services.ocr_service_tesseract import TesseractOCRService
from ..services.interpreter import DefaultResponseInterpreter
from ..services.dispatcher_bus import AgentBusDispatcher
from ..state_machines.task_execution_state_machine import TaskExecutionStateMachine
from ..bridge_adapters.cursor_bridge_adapter import CursorBridgeAdapter, CursorGoal
from ..agent_bus import agent_bus, EventType, Event

logger = logging.getLogger(__name__)

class CursorChatCoordinator:
    """Stub coordinator for cursor chat tasks under agent coordination."""

    def __init__(
        self,
        instance_controller: Any,
        bridge_adapter: CursorBridgeAdapter,
        state_machine: TaskExecutionStateMachine
    ):
        """
        Constructs the coordinator with DI for core services.
        """
        self.config = CursorCoordinatorConfig()
        self.instance_controller = instance_controller
        self.bridge_adapter = bridge_adapter
        self.state_machine = state_machine
        # Use shared agent bus instance
        self.agent_bus = agent_bus
        # Initialize injected services
        self.ocr = TesseractOCRService(self.config, self.instance_controller)
        self.interpreter = DefaultResponseInterpreter(self.config)
        self.dispatcher = AgentBusDispatcher(self.agent_bus, self.config)
        # Track last responses per instance
        self.instance_states: Dict[str, Optional[str]] = {}

    async def wait_for_response(self, instance_id: str) -> Optional[str]:
        """Waits for new OCR-extracted text from the given instance."""
        last = self.instance_states.get(instance_id) or ""
        return await self.ocr.capture_new_text(
            instance_id, last_text=last, timeout=self.config.ocr_timeout
        )

    def interpret_response(
        self, chat_text: str, task_context: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """Parses chat text into an actionable dict via the interpreter."""
        return self.interpreter.parse(chat_text, task_context)

    async def dispatch_to_agents(
        self,
        action_dict: Dict[str, Any],
        instance_id: Optional[str] = None,
        original_task_id: Optional[str] = None
    ) -> Optional[str]:
        """Routes parsed actions to the AgentBus via the dispatcher."""
        return await self.dispatcher.route(
            action_dict,
            instance_id=instance_id,
            original_task_id=original_task_id
        ) 