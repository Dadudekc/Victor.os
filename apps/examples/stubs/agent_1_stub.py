"""
Agent_1 (Stub - Planner)
------------------------
- Simulates a planning agent.
- Listens for GENERATE_TASK_SEQUENCE.
- Immediately completes the task to allow dependent tasks to run.
"""

import logging
from datetime import datetime

# Assume these are accessible via PYTHONPATH or relative imports
from dreamos.coordination.agent_bus import AgentBus
from dreamos.coordination.dispatcher import Event, EventType

logger = logging.getLogger("Agent_1_Stub")
AGENT_ID = "Agent_1"


class Agent1Stub:
    def __init__(self, bus: AgentBus):
        self.bus = bus
        self.bus.register_agent(AGENT_ID, capabilities=["planning_stub"])
        # Listen for the specific planning action
        self.bus.register_handler(EventType.GENERATE_TASK_SEQUENCE, self._handle_plan)
        logger.info(f"{AGENT_ID} stub initialized and listening.")

    def _handle_plan(self, event: Event) -> None:
        task_id = event.data.get("task_id") or event.data.get("correlation_id")
        if not task_id:
            logger.error(
                f"Received GENERATE_TASK_SEQUENCE event without task_id/correlation_id: {event.data}"
            )
            # Cannot dispatch failure without task_id
            return

        action = event.type.name
        goal = event.data.get("params", {}).get("goal", "Unknown goal")
        logger.info(
            f"[{task_id}] Received {action} for goal: '{goal}'. Simulating completion."
        )

        # Immediately dispatch TASK_COMPLETED
        completed_event = Event(
            type=EventType.TASK_COMPLETED,
            source_id=AGENT_ID,
            target_id="TaskExecutorAgent",  # Standard target for status updates
            data={
                "correlation_id": task_id,
                "task_id": task_id,
                "results": f"Planning simulation complete for '{goal}' at {datetime.utcnow().isoformat()}",
                # In a real planner, this might contain the generated task list
            },
        )
        self.bus.dispatch(completed_event)
        logger.info(f"[{task_id}] Dispatched TASK_COMPLETED for {action}.")


# Example of how to integrate into bootstrap (if not automatically loaded)
# if __name__ == '__main__':
#     from dreamos.coordination.agent_bus import AgentBus
#     bus = AgentBus() # Assuming a singleton or shared instance
#     agent1 = Agent1Stub(bus)
#     # Keep alive logic or integrate into main loop
