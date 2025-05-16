"""
Coordinates voting sessions within the Dream.OS swarm.

Listens for vote initiation events, collects agent votes, handles timeouts
and quorum logic (partially implemented), and publishes results.
Uses the AgentBus for event-driven communication and Pydantic models for data validation.
"""

import asyncio  # noqa: I001
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import ValidationError

# Use AgentBus and publish/subscribe model
from dreamos.core.coordination.agent_bus import AgentBus, EventType

# Import voting schemas/constants
from dreamos.core.coordination.schemas.voting_patterns import (
    AgentVote,
    VoteInitiated,
    VoteResults,
)

# Updated import path
from dreamos.utils.common_utils import get_utc_iso_timestamp

# from .agent_bus import AgentBus, EventType # OLD relative import
# from dreamos.core.coordination.base_agent import BaseAgent # REMOVED Unused Import causing circular dep
# REMOVED: Import of non-existent VoteInitiatedPayload
# from dreamos.core.coordination.event_payloads import (
#     VoteInitiatedPayload,
# )

logger = logging.getLogger(__name__)

# Define standard topics
# VOTE_INITIATED_TOPIC = "system.voting.session.event.initiated" # Replaced by EventType
# VOTE_CAST_TOPIC = "system.voting.session.event.cast"         # Replaced by EventType
# VOTE_RESULTS_TOPIC = "system.voting.session.event.results" # REMOVED, using EventType.COORDINATION_PROPOSAL now  # noqa: E501


class VotingCoordinator:
    """
    Manages voting sessions initiated within the Dream.OS swarm using standard pub/sub.

    Listens for events on VOTE_INITIATED_TOPIC, collects votes from VOTE_CAST_TOPIC,
    tallies results based on timeout or quorum, and publishes results to VOTE_RESULTS_TOPIC.
    """  # noqa: E501

    def __init__(
        self, agent_bus: AgentBus, coordinator_id: str = "VotingCoordinator"
    ):  # Add an ID
        """Initializes the VotingCoordinator.

        Args:
            agent_bus: The system-wide AgentBus instance for communication.
            coordinator_id: A unique identifier for this coordinator instance.
        """
        self.agent_bus = agent_bus
        self.coordinator_id = coordinator_id  # ID for publishing
        self.active_vote_session: Optional[Dict[str, Any]] = None
        self.votes_received: Dict[str, AgentVote] = (
            {}
        )  # EDIT: Store AgentVote model directly
        self.vote_task: Optional[asyncio.Task] = None
        self._subscriptions = []  # Store subscription IDs/objects
        # REMOVED: self.agent_bus.register_handler(EventType.COORDINATION, self.handle_coordination_event)  # noqa: E501
        logger.info("VotingCoordinator initialized.")

    async def start(self):
        """Subscribe to relevant voting topics."""
        try:
            # {{ EDIT START: Use EventType enum values for subscription }}
            sub_init = await self.agent_bus.subscribe(
                EventType.VOTE_INITIATED.value, self._handle_vote_initiated
            )
            sub_cast = await self.agent_bus.subscribe(
                EventType.AGENT_VOTE.value, self._handle_agent_vote
            )
            # {{ EDIT END }}
            self._subscriptions.extend([sub_init, sub_cast])
            # {{ EDIT START: Update log message to use EventType values }}
            logger.info(
                f"VotingCoordinator listening on {EventType.VOTE_INITIATED.value} and {EventType.AGENT_VOTE.value}"  # noqa: E501
            )
            # {{ EDIT END }}
        except Exception as e:
            logger.error(f"Failed to subscribe VotingCoordinator: {e}", exc_info=True)
            raise

    # Renamed handle_coordination_event and split logic
    async def _handle_vote_initiated(self, topic: str, message: Dict[str, Any]):
        """Handles incoming vote initiation messages."""
        logger.debug(f"Received message on {topic}: {message}")
        # {{ EDIT START: Implement Pydantic Validation }}
        # Validate basic structure - TODO: More robust validation using schemas -> DONE (Basic Pydantic)  # noqa: E501
        if not all(
            k in message
            for k in ["sender_id", "correlation_id", "timestamp_utc", "data"]
        ):
            logger.warning(
                f"Ignoring malformed message on {topic}: Missing standard AgentBus fields."  # noqa: E501
            )
            return

        try:
            # Assuming message["data"] should conform to VoteInitiated
            initiation_data: VoteInitiated = VoteInitiated(**message["data"])
            # EDIT: Remove model_dump - pass model directly if start_vote_session is updated  # noqa: E501
            # initiation_data_dict = initiation_data.model_dump()
        except ValidationError as e:
            logger.warning(
                f"Ignoring invalid VOTE_INITIATED data on {topic}: Validation failed: {e}"  # noqa: E501
            )
            return
        except Exception as e:
            logger.error(
                f"Unexpected error parsing VOTE_INITIATED data on {topic}: {e}",
                exc_info=True,
            )
            return
        # {{ EDIT END }}

        # EDIT: Pass the validated Pydantic model directly
        await self.start_vote_session(initiation_data, message["correlation_id"])

    async def _handle_agent_vote(self, topic: str, message: Dict[str, Any]):
        """Handles incoming agent vote messages."""
        logger.debug(f"Received message on {topic}: {message}")
        # {{ EDIT START: Implement Pydantic Validation }}
        if not all(
            k in message
            for k in ["sender_id", "correlation_id", "timestamp_utc", "data"]
        ):
            logger.warning(
                f"Ignoring malformed message on {topic}: Missing standard AgentBus fields."  # noqa: E501
            )
            return

        try:
            # Assuming message["data"] should conform to AgentVote
            vote_data: AgentVote = AgentVote(**message["data"])
            # EDIT: Remove model_dump - pass model directly
            # vote_data_dict = vote_data.model_dump()
        except ValidationError as e:
            logger.warning(
                f"Ignoring invalid AGENT_VOTE data on {topic}: Validation failed: {e}"
            )
            return
        except Exception as e:
            logger.error(
                f"Unexpected error parsing AGENT_VOTE data on {topic}: {e}",
                exc_info=True,
            )
            return
        # {{ EDIT END }}

        if self.active_vote_session:
            # EDIT: Pass the validated Pydantic model directly
            await self.record_vote(vote_data)
        else:
            logger.debug(
                f"Ignoring vote cast when no session is active: {vote_data}"  # Log model directly  # noqa: E501
            )

    async def start_vote_session(
        self, initiation_data: VoteInitiated, correlation_id: str
    ):
        """Starts a new voting session if none is active."""
        vote_id = initiation_data.vote_id
        if self.active_vote_session:
            active_vote_id = self.active_vote_session["vote_id"]
            error_msg = f"Cannot start new vote '{vote_id}': session '{active_vote_id}' already active."  # noqa: E501
            logger.warning(error_msg)
            # Optionally notify initiator about the conflict
            # {{ EDIT START: Publish error response }}
            # TODO: Publish an error response back using correlation_id -> DONE
            error_payload = {
                "sender_id": self.coordinator_id,
                "correlation_id": correlation_id,  # Use original request's correlation ID  # noqa: E501
                "timestamp_utc": get_utc_iso_timestamp(),
                "data": {
                    "error_code": "VOTE_SESSION_ACTIVE",
                    "message": error_msg,
                    "active_vote_id": active_vote_id,
                },
            }
            try:
                await self.agent_bus.publish(
                    EventType.SYSTEM_ERROR.value, error_payload
                )
                logger.info(
                    f"Published error notification for active session conflict (vote '{vote_id}')."  # noqa: E501
                )
            except Exception as e:
                logger.error(
                    f"Failed to publish active session conflict error for vote '{vote_id}': {e}",  # noqa: E501
                    exc_info=True,
                )
            # {{ EDIT END }}
            return

        # EDIT: Convert model to dict for storing internally (can be revisited later)
        # Keep internal session representation as dict for now for minimal changes
        self.active_vote_session = initiation_data.model_dump()
        self.votes_received = {}  # Reset votes for the new session

        # Add correlation_id to the session data if needed for later responses
        self.active_vote_session["correlation_id"] = correlation_id

        # Use a sensible default if duration_seconds is not provided or invalid
        # duration_seconds = initiation_data.get("duration_seconds", 60)
        # EDIT: Handle potential deadline - TBD: Need logic to calculate duration from deadline  # noqa: E501
        duration_seconds = 60  # Placeholder duration
        if initiation_data.voting_deadline_utc:
            try:
                deadline = datetime.fromisoformat(
                    initiation_data.voting_deadline_utc.replace("Z", "+00:00")
                )
                now = datetime.now(timezone.utc)
                if deadline > now:
                    duration_seconds = (deadline - now).total_seconds()
                else:
                    logger.warning(
                        f"Vote '{vote_id}' deadline is in the past: {initiation_data.voting_deadline_utc}. Using default duration."  # noqa: E501
                    )
                    duration_seconds = 60  # Fallback duration
            except ValueError:
                logger.warning(
                    f"Invalid deadline format for vote '{vote_id}': {initiation_data.voting_deadline_utc}. Using default duration."  # noqa: E501
                )
                duration_seconds = 60  # Fallback duration
        else:
            # If no deadline, use a default duration (e.g., 60 seconds) or make it indefinite?  # noqa: E501
            # For now, using 60s default if no deadline provided.
            logger.debug(
                f"No deadline provided for vote '{vote_id}'. Using default duration: {duration_seconds}s"  # noqa: E501
            )

        # quorum = initiation_data.get("quorum") # EDIT: Access from model
        quorum = (
            initiation_data.quorum if hasattr(initiation_data, "quorum") else None
        )  # Example if quorum added

        logger.info(
            f"Starting vote session '{vote_id}'. Duration: {duration_seconds}s, Quorum: {quorum}"  # noqa: E501
        )

        # Cancel any existing timer task before starting a new one
        if self.vote_task and not self.vote_task.done():
            self.vote_task.cancel()

        self.vote_task = asyncio.create_task(
            self.end_vote_session_after_delay(int(duration_seconds))
        )

    async def record_vote(self, vote_data: AgentVote):
        """Records an agent's vote for the active session.

        Checks if a session is active, the vote ID matches, and the agent
        hasn't voted already. Stores the validated AgentVote model.
        Placeholder for quorum check logic.

        Args:
            vote_data: The validated AgentVote Pydantic model.
        """
        if not self.active_vote_session:
            logger.warning("Attempted to record vote, but no session is active.")
            return

        session_vote_id = self.active_vote_session["vote_id"]
        incoming_vote_id = vote_data.vote_id
        agent_id = vote_data.agent_id

        if session_vote_id != incoming_vote_id:
            logger.warning(
                f"Ignoring vote for '{incoming_vote_id}' from {agent_id}: Active session is '{session_vote_id}'."  # noqa: E501
            )
            return

        if agent_id in self.votes_received:
            logger.warning(
                f"Agent {agent_id} already voted in session '{session_vote_id}'. Ignoring duplicate."  # noqa: E501
            )
            return

        # Store the validated Pydantic model directly
        self.votes_received[agent_id] = vote_data
        logger.info(
            f"Recorded vote from {agent_id} for session '{session_vote_id}'. Total votes: {len(self.votes_received)}"  # noqa: E501
        )

        # Check for quorum if defined
        # quorum = self.active_vote_session.get("quorum")
        # if quorum and len(self.votes_received) >= quorum:
        #      logger.info(f"Quorum ({quorum}) reached for vote '{session_vote_id}'. Ending session early.")  # noqa: E501
        #      if self.vote_task and not self.vote_task.done():
        #          self.vote_task.cancel() # Cancel timer
        #      await self.tally_and_publish_results() # Tally immediately

    async def end_vote_session_after_delay(self, delay: int):
        """Waits for a specified delay then triggers vote tallying and publishing.

        This coroutine is typically launched as an asyncio.Task when a vote session starts.
        It handles graceful cancellation if the session ends early (e.g., by quorum).

        Args:
            delay: The number of seconds to wait before ending the session.
        """
        try:
            await asyncio.sleep(delay)
            if (
                self.active_vote_session
            ):  # Check if session wasn't ended early by quorum
                logger.info(
                    f"Voting duration ended for vote '{self.active_vote_session['vote_id']}'."  # noqa: E501
                )
                await self.tally_and_publish_results()
        except asyncio.CancelledError:
            logger.info(
                f"Vote timer cancelled for vote '{self.active_vote_session['vote_id'] if self.active_vote_session else 'unknown'}' (likely ended early)."  # noqa: E501
            )

    async def tally_and_publish_results(self):
        """Tallies collected votes, determines an outcome, publishes results, and resets.

        FIXME: Current tallying and outcome determination logic is placeholder
               and needs to be implemented based on specific voting rules.
        Publishes results to the AgentBus and then resets the session state.
        """
        if not self.active_vote_session:
            logger.warning("Tally requested, but no session active.")
            return

        session_vote_id = self.active_vote_session["vote_id"]
        original_correlation_id = self.active_vote_session.get("correlation_id")
        logger.info(f"Tallying results for vote session '{session_vote_id}'.")

        # --- Tallying Logic Placeholder ---
        # FIXME: Implement actual tallying logic based on the expected vote structure
        #        (e.g., single choice, multiple choice, ranked choice, specific questions).
        #        The current implementation assumes a single question with simple choices.
        tally: Dict[str, Any] = defaultdict(Counter)
        participants = list(self.votes_received.keys())
        confidence_scores = {}
        rationales = {}

        for agent_id, vote in self.votes_received.items():
            # Assuming single question, single choice for simplicity
            if vote.choices:
                choice = str(vote.choices[0])  # Ensure string key
                tally["question_1"][choice] += 1  # Example tally structure
            if vote.confidence is not None:
                confidence_scores[agent_id] = vote.confidence
            if vote.rationale:
                rationales[agent_id] = vote.rationale

        # --- Determine Outcome Placeholder ---
        # FIXME: Implement outcome determination logic based on tallying results
        #        and the specific rules of the vote (e.g., majority, consensus).
        outcome = "Undetermined"  # Default
        if tally["question_1"]:
            # Find the choice with the most votes
            most_common = tally["question_1"].most_common(1)
            if most_common:
                outcome = f"Decision: {most_common[0][0]}"
            else:
                outcome = "Tie or No Votes"
        else:
            outcome = "No votes received"

        logger.info(f"Outcome for vote '{session_vote_id}': {outcome}")

        # --- Publish Results ---
        # EDIT: Construct VoteResults using the Pydantic model
        try:
            results_data = VoteResults(
                vote_id=session_vote_id,
                results_summary=dict(tally),  # Convert defaultdict to dict for model
                participating_agents=participants,
                outcome=outcome,
                tally_timestamp_utc=get_utc_iso_timestamp(),
            )
        except ValidationError as e:
            logger.error(
                f"Failed to create VoteResults model for '{session_vote_id}': {e}"
            )
            # Handle error - maybe publish a failure?
            self.reset_session()
            return

        results_payload = {
            "sender_id": self.coordinator_id,
            "correlation_id": original_correlation_id,  # Respond to original initiator if possible  # noqa: E501
            "timestamp_utc": get_utc_iso_timestamp(),
            "data": results_data.model_dump(),  # Dump model to dict for sending
        }

        # Publish results to a general results topic or a specific response topic
        # Using EventType.VOTE_RESULT for general notification
        try:
            await self.agent_bus.publish(EventType.VOTE_RESULT.value, results_payload)
            logger.info(
                f"Published results for vote '{session_vote_id}' to {EventType.VOTE_RESULT.value}."  # noqa: E501
            )
        except Exception as e:
            logger.error(
                f"Failed to publish vote results for '{session_vote_id}': {e}",
                exc_info=True,
            )

        # Reset state after publishing
        self.reset_session()

    def reset_session(self):
        """Resets the state of the current voting session.

        Clears active session data, received votes, and cancels any active
        timeout task.
        """
        logger.debug("Resetting voting session state.")
        self.active_vote_session = None
        self.votes_received = {}
        if self.vote_task and not self.vote_task.done():
            self.vote_task.cancel()
        self.vote_task = None

    async def stop(self):
        """Stops the VotingCoordinator gracefully.

        Cancels any active voting session timer task and unsubscribes from
        all AgentBus topics.
        """
        logger.info("Stopping VotingCoordinator...")
        if self.vote_task and not self.vote_task.done():
            self.vote_task.cancel()
            try:
                await self.vote_task  # Allow cancellation to complete
            except asyncio.CancelledError:
                pass  # Expected
            logger.info("Cancelled active voting session task.")

        # Unsubscribe from topics
        for sub_id in self._subscriptions:
            try:
                await self.agent_bus.unsubscribe(sub_id)
            except Exception as e:
                logger.error(f"Error unsubscribing {sub_id}: {e}")
        self._subscriptions = []
        logger.info("VotingCoordinator unsubscribed and stopped.")


# Example Usage remains similar but would involve starting the coordinator
# async def main():
#     bus = AgentBus() # Get bus instance
#     coordinator = VotingCoordinator(bus)
#     await coordinator.start() # Start listening
#     # ... keep running or simulate events
#     await asyncio.sleep(300) # Example run duration
#     await coordinator.stop()
#
# if __name__ == "__main__":
#     # Basic logging setup for testing
#     logging.basicConfig(level=logging.INFO)
#     asyncio.run(main())
