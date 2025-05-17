# run_election_demo.py  (anywhere in repo root)
import asyncio, logging
from dreamos.governance.agent_bus import AgentBus
from dreamos.governance.consensus_manager_stub import ConsensusManager
from dreamos.governance.election_manager import ElectionManager
from dreamos.governance.event_types import EventType

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(name)s: %(message)s")

async def demo():
    bus  = AgentBus()
    cons = ConsensusManager(bus)
    em   = ElectionManager(bus, cons)
    await em.start_services()

    await bus.publish(EventType.ELECTION_START, {
        "cycle_count": 42,
        "eligible_candidates": ["Agent-1", "Agent-2", "Agent-3"],
        "eligible_voters": ["Agent-1", "Agent-2", "Agent-3", "Agent-4"]
    })

    await asyncio.sleep(1)
    await bus.publish(EventType.DECLARE_CANDIDACY, {"agent_id": "Agent-2", "platform_statement": "Order & Speed"})
    await bus.publish(EventType.DECLARE_CANDIDACY, {"agent_id": "Agent-1", "platform_statement": "Stability First"})

    await asyncio.sleep(10)  # shorten constants for fast demo

if __name__ == "__main__":
    asyncio.run(demo()) 