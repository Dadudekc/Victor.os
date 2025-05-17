"""
Utilities for agents to participate in the election process.
This includes detecting election events, deciding on candidacy/voting,
and publishing appropriate events to the AgentBus by writing event files.
"""

import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Assuming EventType is available, and AgentBus publishing means writing a file here
from .event_types import EventType 
# from .agent_bus import AgentBus # Not strictly needed if only writing files

logger = logging.getLogger(__name__)

AGENT_BUS_EVENT_DIR = Path("runtime/bus/events")

def check_agent_eligibility(agent_id: str, eligibility_list: List[str]) -> bool:
    """Checks if the agent_id is in the provided eligibility list."""
    return agent_id in eligibility_list

def decide_to_run_for_captain(agent_id: str) -> bool:
    """Placeholder logic for an agent to decide if it wants to run."""
    # For now, 50/50 chance if eligible. Could be based on self-assessment, role, etc.
    decision = random.choice([True, False])
    logger.info(f"Agent {agent_id} decision to run for captain: {decision}")
    return decision

def generate_platform_statement(agent_id: str, cycle_count: int) -> str:
    """Placeholder for an agent to generate its platform statement."""
    statements = [
        f"I, {agent_id}, will focus on task efficiency and reducing blockers in cycle {cycle_count + 1}!",
        f"Vote {agent_id} for proactive error handling and improved system stability in cycle {cycle_count + 1}.",
        f"As Captain, {agent_id} will prioritize codebase organization and documentation in cycle {cycle_count + 1}.",
        f"{agent_id}: Dedicated to optimizing resource usage and streamlining agent communication for cycle {cycle_count + 1}."
    ]
    statement = random.choice(statements)
    logger.info(f"Agent {agent_id} generated platform: '{statement}'")
    return statement

async def publish_event_to_bus(event_type: str, payload: Dict[str, Any]):
    """Writes an event JSON file, mimicking AgentBus.publish for agents."""
    logger.info(f"Agent publishing event: {event_type} - {payload}")
    AGENT_BUS_EVENT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{event_type.replace('.', '_')}_{int(datetime.utcnow().timestamp())}.json"
    file_path = AGENT_BUS_EVENT_DIR / filename
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"event_type": event_type, "payload": payload, "timestamp": datetime.utcnow().isoformat()}, f, indent=2)
        logger.info(f"Agent event [{event_type}] written to {file_path}")
    except IOError as e:
        logger.error(f"Agent failed to write event [{event_type}] to file: {e}")

async def handle_election_start(agent_id: str, event_data: Dict[str, Any]):
    """
    Logic for an agent to process an ELECTION_START event.
    This would be called by an agent's main loop when it detects such an event.
    """
    logger.info(f"Agent {agent_id} processing ELECTION_START: {event_data}")
    eligible_candidates_pool = event_data.get("eligible_candidates", [])
    cycle_count = event_data.get("cycle_count", 0)

    if check_agent_eligibility(agent_id, eligible_candidates_pool):
        logger.info(f"Agent {agent_id} is eligible to run for Captain in cycle {cycle_count}.")
        if decide_to_run_for_captain(agent_id):
            platform = generate_platform_statement(agent_id, cycle_count)
            candidacy_payload = {
                "agent_id": agent_id,
                "platform_statement": platform,
                "cycle_count": cycle_count # Optional: good for context
            }
            await publish_event_to_bus(EventType.DECLARE_CANDIDACY, candidacy_payload)
            # Agent might also claim the DECLARE-CANDIDACY-001 task here
            logger.info(f"Agent {agent_id} has declared candidacy.")
        else:
            logger.info(f"Agent {agent_id} decided not to run for Captain this cycle.")
    else:
        logger.info(f"Agent {agent_id} is not eligible to run for Captain in cycle {cycle_count}.")

async def handle_voting_period_start(agent_id: str, candidates: List[Dict[str,Any]], current_election_cycle: int, eligible_voters_pool: List[str]):
    """
    Logic for an agent to decide and cast its vote.
    This would be called when the agent determines the voting period is open.
    `candidates` would be a list of dicts, e.g. from ElectionManager or by observing DECLARE_CANDIDACY.
    Example candidate dict: {"agent_id": "Agent-X", "platform_statement": "..."}
    """
    logger.info(f"Agent {agent_id} entering voting logic for cycle {current_election_cycle}. Candidates: {len(candidates)}")
    if not check_agent_eligibility(agent_id, eligible_voters_pool):
        logger.info(f"Agent {agent_id} is not eligible to vote in cycle {current_election_cycle}.")
        return

    if not candidates:
        logger.warning(f"Agent {agent_id}: No candidates to vote for in cycle {current_election_cycle}.")
        return

    # Placeholder: Simple voting logic - pick a random candidate
    # In a real scenario, agent would review platforms, assess, etc.
    chosen_candidate = random.choice(candidates)
    chosen_candidate_id = chosen_candidate.get("agent_id")
    logger.info(f"Agent {agent_id} has chosen to vote for {chosen_candidate_id}.")

    vote_payload = {
        "agent_id": agent_id,
        "vote": chosen_candidate_id,
        "confidence": round(random.uniform(0.7, 1.0), 2), # Random confidence
        "cycle_count": current_election_cycle
    }
    await publish_event_to_bus(EventType.AGENT_VOTE, vote_payload)
    logger.info(f"Agent {agent_id} has cast vote for {chosen_candidate_id}.")

# How agents get notified/detect these state changes (ELECTION_START, voting period open) is an agent loop concern.
# An agent might subscribe to AgentBus events or periodically check a state file managed by ElectionManager.

# Example of how an agent might integrate this in its loop (pseudo-code like):
# async def agent_main_loop(self):
#     # ... other loop logic ...
#     detected_events = self.check_event_bus_for_new([EventType.ELECTION_START])
#     for event_type, event_data in detected_events:
#         if event_type == EventType.ELECTION_START:
#             await agent_election_utils.handle_election_start(self.agent_id, event_data)
#     
#     if self.election_module.is_voting_period_active(self.agent_id):
#          candidates_list = self.election_module.get_candidates_platforms()
#          await agent_election_utils.handle_voting_period_start(self.agent_id, candidates_list, self.election_module.current_cycle)
#     # ... other loop logic ... 