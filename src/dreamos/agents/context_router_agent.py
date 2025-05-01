# src/dreamos/agents/context_router_agent.py
import asyncio
import logging
from typing import Any, Dict, Optional

# Assuming BaseAgent and AgentBus are correctly located after potential refactors
# Adjust imports as necessary based on Agent 1/2 work
try:
    from dreamos.agents.base_agent import BaseAgent
    from dreamos.coordination.agent_bus import AgentBus, BaseEvent, EventType

    # Import event types that this agent will listen to (adjust as needed)
    # Example: Assume a new event type from Agent 5 for scraped data
    # from dreamos.coordination.agent_bus import EventType # Already imported
    AGENT_COMPONENTS_AVAILABLE = True
except ImportError as e:
    logging.basicConfig(level=logging.ERROR)
    logging.error(
        f"Failed to import core agent components: {e}. ContextRouterAgent cannot run."
    )
    BaseAgent = object  # Dummy class to prevent NameErrors later
    AgentBus = None
    BaseEvent = None

    # Define potentially missing EventTypes if needed for structure
    class EventType:
        # REMOVE: ROUTING_REQUEST = "placeholder.routing.request" # Example placeholder
        # ADD Actual EventTypes (assuming they exist in coordination.agent_bus)
        TASK_ASSIGNED = "task.assigned"
        TASK_DIRECT = "task.direct"  # Example: May also want to route direct tasks
        CURSOR_INJECT_REQUEST = "placeholder.cursor.inject.request"

    AGENT_COMPONENTS_AVAILABLE = False

# EDIT START: Import AppConfig
from dreamos.core.config import AppConfig

# EDIT END

logger = logging.getLogger(__name__)


class ContextRouterAgent(BaseAgent):
    """Dynamically routes incoming requests (e.g., scraped prompts)
    to specific target agents based on context metadata.
    """

    AGENT_ID = "context_router_agent"  # Define a unique ID for this agent type

    def __init__(self, agent_bus: AgentBus, config: AppConfig, **kwargs):
        """Initializes the ContextRouterAgent."""
        if not AGENT_COMPONENTS_AVAILABLE:
            raise RuntimeError("Core agent components not available.")

        super().__init__(agent_id=self.AGENT_ID, agent_bus=agent_bus, **kwargs)
        self.config = config  # Store the app config
        self.logger.info(f"{self.AGENT_ID} initializing...")
        self.routing_rules = self._load_routing_rules()
        self.logger.info(
            f"ContextRouterAgent initialized with {len(self.routing_rules.get('rules', []))} rules. Default: {self.routing_rules.get('default_agent')}"
        )

    def _load_routing_rules(self) -> Dict:
        """Loads routing rules from the application configuration."""
        # TODO: Load routing rules from config? -> REMOVED TODO
        router_config = self.config.context_router
        if router_config:
            # Convert Pydantic models back to dict for existing logic (or adapt logic)
            rules_dict = {
                "rules": [rule.dict() for rule in router_config.rules],
                "default_agent": router_config.default_agent,
            }
            self.logger.info(f"Loaded routing rules from config.")
            return rules_dict
        else:
            self.logger.warning(
                "ContextRouterConfig not found in AppConfig. Using empty rules."
            )
            return {"rules": [], "default_agent": None}

    async def _on_start(self):
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
            # await self.agent_bus.subscribe(EventType.TASK_DIRECT.value, self._handle_task_event)
            # self.logger.info(f"Subscribed to {EventType.TASK_DIRECT.value} events.")
        except Exception as e:
            self.logger.exception(f"Failed to subscribe to task events: {e}")

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

        # Extract task details and context (adjust keys based on actual TASK event structure)
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
                f"Routing task {event.event_id} from {original_target_agent_id} -> {new_target_agent_id} based on context: {context_metadata}"
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
                source_id=self.AGENT_ID,  # Mark router as the source of the *dispatch action*
                event_id=event.event_id,  # Keep original event ID for tracing
                correlation_id=correlation_id,  # Propagate correlation ID
                data=modified_data,
            )
            try:
                # IMPORTANT: Dispatching might trigger this handler again, loop prevention is key
                await self.agent_bus.dispatch_event(routed_event)
                self.logger.debug(
                    f"Re-dispatched event {event.event_id} to {new_target_agent_id}."
                )
            except Exception as e:
                self.logger.exception(
                    f"Failed to re-dispatch routed event {event.event_id} for {new_target_agent_id}: {e}"
                )
        else:
            # No routing needed or failed to determine new target, let original event proceed
            self.logger.debug(
                f"No routing action needed for event {event.event_id}. Original target: {original_target_agent_id}"
            )
            # If target couldn't be determined AT ALL (new_target_agent_id is None), maybe log error?
            if not new_target_agent_id:
                self.logger.error(
                    f"Could not determine target agent for task {event.event_id} based on context: {context_metadata}. Task may be lost if {original_target_agent_id} isn't listening."
                )

    async def _determine_target_agent(
        self, context_metadata: Dict[str, Any]
    ) -> Optional[str]:
        """Determines the target agent based on routing rules and context."""
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
                        f"Routing rule matched: keyword '{keyword}' -> {target_agent_id}"
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

    async def _on_stop(self):
        """Cleanup resources when the agent stops."""
        self.logger.info(f"{self.AGENT_ID} stopping.")

        # Unsubscribe from events subscribed to in _on_start
        # Match the event type used in _on_start
        event_type_subscribed = EventType.TASK_ASSIGNED
        handler_subscribed = self._handle_task_event
        try:
            # Assuming agent_bus.unsubscribe exists and works with event_type.value and handler ref
            await self.agent_bus.unsubscribe(
                event_type_subscribed.value, handler_subscribed
            )
            self.logger.info(f"Unsubscribed from {event_type_subscribed.name} events.")
        except AttributeError:
            self.logger.error("AgentBus instance or unsubscribe method not available.")
        except Exception as e:
            # Log specific error but allow agent to continue stopping
            self.logger.exception(
                f"Failed to unsubscribe from {event_type_subscribed.name} events: {e}"
            )

        # Call BaseAgent stop logic (which handles command topic unsubscribe)
        await super()._on_stop()


# Example of how this agent might be instantiated and run (conceptual)
async def run_router_agent():
    if not AGENT_COMPONENTS_AVAILABLE:
        print("Cannot run router agent: Core components missing.")
        return

    bus = AgentBus()  # Get singleton
    router = ContextRouterAgent(agent_bus=bus)
    await router.start()
    try:
        # Keep agent running (e.g., wait indefinitely or until external stop signal)
        await asyncio.Event().wait()
    finally:
        await router.stop()


# if __name__ == "__main__":
#     asyncio.run(run_router_agent())
