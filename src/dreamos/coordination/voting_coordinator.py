import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from dreamos.coordination.agent_bus import AgentBus, EventType  # Assuming these exist

logger = logging.getLogger(__name__)

class VotingCoordinator:
    """
    Manages voting sessions initiated within the Dream.OS swarm.

    Listens for VOTE_INITIATED events, collects AGENT_VOTE events,
    tallies results based on timeout or quorum, and publishes VOTE_RESULTS.
    """

    def __init__(self, agent_bus: AgentBus):
        self.agent_bus = agent_bus
        self.active_vote_session: Optional[Dict[str, Any]] = None
        self.votes_received: Dict[str, str] = {}  # agent_id: vote
        self.vote_task: Optional[asyncio.Task] = None
        self.agent_bus.register_handler(EventType.COORDINATION, self.handle_coordination_event)
        logger.info("VotingCoordinator initialized and listening for events.")

    async def handle_coordination_event(self, event: Dict[str, Any]):
        """Handles incoming coordination events."""
        event_type = event.get('type')
        if event_type == 'VOTE_INITIATED':
            await self.start_vote_session(event)
        elif event_type == 'AGENT_VOTE' and self.active_vote_session:
            await self.record_vote(event)

    async def start_vote_session(self, initiation_event: Dict[str, Any]):
        """Starts a new voting session if none is active."""
        if self.active_vote_session:
            logger.warning(f"Cannot start new vote on topic '{initiation_event.get('topic_id')}': session '{self.active_vote_session['topic_id']}' already active.")
            # Optionally notify initiator about the conflict
            return

        topic_id = initiation_event.get('topic_id')
        duration_seconds = initiation_event.get('duration_seconds', 60)
        quorum = initiation_event.get('quorum') # Optional quorum

        if not topic_id:
            logger.error("Received VOTE_INITIATED event without topic_id.")
            return

        self.active_vote_session = {
            'topic_id': topic_id,
            'question': initiation_event.get('question', 'N/A'),
            'options': initiation_event.get('options', ['yes', 'no']),
            'duration_seconds': duration_seconds,
            'quorum': quorum,
            'start_time': datetime.now(timezone.utc),
            'end_time': datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
        }
        self.votes_received = {}

        logger.info(f"Voting session started for topic '{topic_id}'. Duration: {duration_seconds}s, Quorum: {quorum}")

        # Schedule the end of the voting session
        self.vote_task = asyncio.create_task(self.end_vote_session_after_delay(duration_seconds))

    async def record_vote(self, vote_event: Dict[str, Any]):
        """Records a vote if it belongs to the active session."""
        if not self.active_vote_session or vote_event.get('topic_id') != self.active_vote_session['topic_id']:
            logger.debug(f"Ignoring vote for inactive or different topic: {vote_event.get('topic_id')}")
            return

        agent_id = vote_event.get('agent_id')
        vote = vote_event.get('vote')
        valid_options = self.active_vote_session.get('options', [])

        if not agent_id or not vote:
            logger.warning(f"Ignoring invalid vote event: {vote_event}")
            return

        if agent_id in self.votes_received:
            logger.warning(f"Agent '{agent_id}' already voted on topic '{self.active_vote_session['topic_id']}'. Ignoring duplicate vote.")
            return

        if vote not in valid_options:
            logger.warning(f"Agent '{agent_id}' cast invalid vote '{vote}' for options {valid_options}. Ignoring.")
            return

        self.votes_received[agent_id] = vote
        logger.info(f"Vote recorded from '{agent_id}' for topic '{self.active_vote_session['topic_id']}': {vote}")

        # Check if quorum is met
        quorum = self.active_vote_session.get('quorum')
        if quorum is not None and len(self.votes_received) >= quorum:
            logger.info(f"Quorum of {quorum} reached for topic '{self.active_vote_session['topic_id']}'. Ending session early.")
            if self.vote_task and not self.vote_task.done():
                self.vote_task.cancel()
            await self.tally_and_publish_results()

    async def end_vote_session_after_delay(self, delay: int):
        """Coroutine that waits for the duration and then ends the session."""
        await asyncio.sleep(delay)
        logger.info(f"Voting duration ended for topic '{self.active_vote_session['topic_id']}'.")
        await self.tally_and_publish_results()

    async def tally_and_publish_results(self):
        """Tallies votes and publishes the results."""
        if not self.active_vote_session:
            return

        topic_id = self.active_vote_session['topic_id']
        results = defaultdict(int)
        for vote in self.votes_received.values():
            results[vote] += 1

        # Simple majority determines outcome (can be customized)
        outcome = "failed" # Default
        sorted_results = sorted(results.items(), key=lambda item: item[1], reverse=True)

        if not sorted_results:
            outcome = "failed (no votes)"
        elif len(sorted_results) == 1:
            outcome = f"passed ({sorted_results[0][0]})" # Unanimous or only one option voted
        elif sorted_results[0][1] > sorted_results[1][1]:
            outcome = f"passed ({sorted_results[0][0]})" # Clear majority
        elif sorted_results[0][1] == sorted_results[1][1]:
            outcome = "tied"
        else: # Should not happen with sorted results, but as a fallback
             outcome = "failed (inconclusive)"

        logger.info(f"Voting session ended for topic '{topic_id}'. Results: {dict(results)}, Outcome: {outcome}")

        results_event = {
            'type': 'VOTE_RESULTS',
            'topic_id': topic_id,
            'question': self.active_vote_session.get('question'),
            'outcome': outcome,
            'results': dict(results),
            'votes_cast': dict(self.votes_received)
        }
        await self.agent_bus.dispatch_event(EventType.COORDINATION, results_event)

        # Clean up session
        self.active_vote_session = None
        self.votes_received = {}
        self.vote_task = None

    async def stop(self):
        """Cleanly stops the coordinator."""
        if self.vote_task and not self.vote_task.done():
            self.vote_task.cancel()
            logger.info("Cancelled active voting session task.")
        self.agent_bus.unregister_handler(EventType.COORDINATION, self.handle_coordination_event)
        logger.info("VotingCoordinator stopped.")

# Example Usage (requires an event loop and AgentBus instance)
# async def main():
#     bus = AgentBus()
#     coordinator = VotingCoordinator(bus)
#     # ... keep running or simulate events
#     await coordinator.stop()
#
# if __name__ == "__main__":
#     asyncio.run(main()) 