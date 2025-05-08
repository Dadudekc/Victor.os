# src/dreamos/agents/context_router_agent.py
"""
Defines the ContextRouterAgent, responsible for dynamically routing task events
to appropriate target agents based on contextual metadata and configurable rules.

It subscribes to task events, inspects their context, and if a routing rule
matches, re-dispatches the event with a new target agent ID.
"""

import logging
from typing import Any, Dict, Optional

# REMOVE try/except block and dummy fallbacks
# try:
from ..coordination.event_payloads import BaseEvent

# from ..coordination.project_board_manager import ProjectBoardManager # Not directly used here
from ..core.config import AppConfig
from ..core.coordination.agent_bus import AgentBus, EventType  # Import EventType here
from .base_agent import BaseAgent

# AGENT_COMPONENTS_AVAILABLE = True
# except ImportError as e:
#     # ... (fallback logic removed) ...
#     AGENT_COMPONENTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class ContextRouterAgent(BaseAgent):
    """Dynamically routes incoming requests (e.g., scraped prompts)
    to specific target agents based on context metadata.
    """

    AGENT_ID = "context_router_agent"  # Define a unique ID for this agent type

    def __init__(self, config: AppConfig, agent_bus: AgentBus, **kwargs):
        """Initializes the ContextRouterAgent."""
        super().__init__(
            agent_id=self.AGENT_ID, config=config, agent_bus=agent_bus, **kwargs
        )
        self.logger.info(f"{self.AGENT_ID} initializing...")
        self.routing_rules = self._load_routing_rules()
        self.logger.info(
            f"ContextRouterAgent initialized with {len(self.routing_rules.get('rules', []))} rules. Default: {self.routing_rules.get('default_agent')}"  # noqa: E501
        )

    def _load_routing_rules(self) -> Dict:
        """Loads routing rules from the application configuration."""
        if hasattr(self.config, "context_router") and self.config.context_router:
            router_config = self.config.context_router
            # TODO: Consider using Pydantic rule models directly in _determine_target_agent
            #       instead of converting to dicts here, to retain Pydantic benefits.
            rules_dict = {
                "rules": [rule.dict() for rule in router_config.rules],
                "default_agent": router_config.default_agent,
            }
            self.logger.info("Loaded routing rules from config.")
            return rules_dict
        else:
            self.logger.warning(
                "ContextRouterConfig not found in AppConfig. Using empty rules."
            )
            return {"rules": [], "default_agent": None}

    async def initialize(self):
        """Subscribe to relevant task events when the agent starts."""
        # Subscribe to task events that might need routing
        # Example: Subscribe to TASK_ASSIGNED
        task_event_type = EventType.TASK_ASSIGNED
        try:
            # Use a specific handler for task events
            await self.agent_bus.subscribe(
                task_event_type.value, self._handle_task_event
            )
            self.logger.info(f"Subscribed to {task_event_type.value} events.")
            # Optionally subscribe to other task types like TASK_DIRECT
            # await self.agent_bus.subscribe(EventType.TASK_DIRECT.value, self._handle_task_event)  # noqa: E501
            # self.logger.info(f"Subscribed to {EventType.TASK_DIRECT.value} events.")
        except Exception as e:
            self.logger.exception(f"Failed to subscribe to task events: {e}")
        await super().initialize()

    async def shutdown(self):
        """Unsubscribe from events on shutdown."""
        self.logger.info(f"Shutting down {self.AGENT_ID}...")
        task_event_type = EventType.TASK_ASSIGNED
        try:
            await self.agent_bus.unsubscribe(
                task_event_type.value, self._handle_task_event
            )
            self.logger.info(f"Unsubscribed from {task_event_type.value} events.")
            # Unsubscribe from others if needed
        except Exception as e:
            self.logger.exception(f"Failed to unsubscribe from task events: {e}")
        await super().shutdown()

    # RENAMED and REFACTORED handler
    async def _handle_task_event(self, event: BaseEvent):
        """Handles incoming task events that may require routing."""
        self.logger.debug(
            f"Received task event: {event.event_type.value} ID: {event.event_id}"
        )

        # --- Loop Prevention ---
        # Check if this event was already routed by us
        if event.data.get("routed_by") == self.AGENT_ID:
            self.logger.debug(f"Ignoring already routed event: {event.event_id}")
            return

        # Extract task details and context (adjust keys based on actual TASK event structure)  # noqa: E501
        task_details = event.data.get("task", {})
        original_target_agent_id = event.data.get(
            "target_agent_id", task_details.get("assigned_agent_id")
        )
        context_metadata = event.data.get(
            "context_metadata", task_details.get("context", {})
        )  # Get context from event or task
        correlation_id = event.data.get(
            "correlation_id", task_details.get("correlation_id")
        )

        if not original_target_agent_id:
            self.logger.warning(
                f"Task event {event.event_id} missing target agent ID. Cannot route."
            )
            return

        # Determine the new target based on context
        new_target_agent_id = self._determine_target_agent(context_metadata)

        # --- Routing Decision ---
        if new_target_agent_id and new_target_agent_id != original_target_agent_id:
            self.logger.info(
                f"Routing task {event.event_id} from {original_target_agent_id} -> {new_target_agent_id} based on context: {context_metadata}"  # noqa: E501
            )

            # Modify the original event's data
            # Create a mutable copy if BaseEvent data is immutable
            modified_data = event.data.copy()  # Or deepcopy if needed
            modified_data["target_agent_id"] = new_target_agent_id
            modified_data["original_target_agent_id"] = (
                original_target_agent_id  # Keep track
            )
            modified_data["routed_by"] = self.AGENT_ID  # Add routing flag
            if "task" in modified_data:  # Update task details if nested
                modified_data["task"] = modified_data["task"].copy()
                modified_data["task"]["assigned_agent_id"] = new_target_agent_id

            # Re-dispatch the *same event type* but with modified data
            routed_event = BaseEvent(
                event_type=event.event_type,  # Use the original event type
                source_id=self.AGENT_ID,  # Mark router as the source of the *dispatch action*  # noqa: E501
                event_id=event.event_id,  # Keep original event ID for tracing
                correlation_id=correlation_id,  # Propagate correlation ID
                data=modified_data,
            )
            try:
                # IMPORTANT: Dispatching might trigger this handler again, loop prevention is key  # noqa: E501
                await self.agent_bus.dispatch_event(routed_event)
                self.logger.debug(
                    f"Re-dispatched event {event.event_id} to {new_target_agent_id}."
                )
            except Exception as e:
                self.logger.exception(
                    f"Failed to re-dispatch routed event {event.event_id} for {new_target_agent_id}: {e}"  # noqa: E501
                )
        else:
            # No routing needed or failed to determine new target, let original event proceed  # noqa: E501
            self.logger.debug(
                f"No routing action needed for event {event.event_id}. Original target: {original_target_agent_id}"  # noqa: E501
            )
            # If target couldn't be determined AT ALL (new_target_agent_id is None), maybe log error?  # noqa: E501
            if not new_target_agent_id:
                self.logger.error(
                    f"Could not determine target agent for task {event.event_id} based on context: {context_metadata}. Task may be lost if {original_target_agent_id} isn't listening."  # noqa: E501
                )

    def _determine_target_agent(
        self, context_metadata: Dict[str, Any]
    ) -> Optional[str]:
        """Determines the target agent based on routing rules and context."""
        # TODO: Current context matching is simple keyword search in stringified metadata.
        #       Consider more structured matching (e.g., specific field checks, regex, DSL)
        #       if more complex routing logic is required.
        context_str = str(context_metadata).lower()

        # Use the loaded rules
        for rule in self.routing_rules.get("rules", []):
            target_agent_id = rule.get("target_agent_id")
            keywords = rule.get("keywords", [])
            if not target_agent_id:
                continue  # Skip invalid rule

            for keyword in keywords:
                if keyword.lower() in context_str:
                    self.logger.debug(
                        f"Routing rule matched: keyword '{keyword}' -> {target_agent_id}"  # noqa: E501
                    )
                    return target_agent_id

        # Fallback to default agent from loaded rules
        default_agent = self.routing_rules.get("default_agent")
        if default_agent:
            self.logger.debug(
                f"No specific rule matched. Using default agent: {default_agent}"
            )
            return default_agent

        self.logger.warning("No routing rule matched and no default agent configured.")
        return None
