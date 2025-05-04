import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dreamos.core.coordination.event_types import EventType
from dreamos.core.coordination.schemas.voting_patterns import (
    AgentVote,
    VoteChoice,
    VoteInitiated,
)

logger = logging.getLogger(__name__)


class AgentVoterMixin:
    """
    A mixin for Agents to automatically participate in voting sessions using standard pub/sub.

    Agents using this mixin should have `agent_id`, `agent_bus` attributes.
    Subscribes to VOTE_INITIATED_TOPIC and publishes votes to VOTE_CAST_TOPIC.
    Provides a default handler to cast a simple vote.
    """  # noqa: E501

    def __init__(self, *args, **kwargs):
        # Ensure agent_id and agent_bus are available
        if not hasattr(self, "agent_id") or not hasattr(self, "agent_bus"):
            raise AttributeError(
                "AgentVoterMixin requires the agent to have 'agent_id' and 'agent_bus' attributes."  # noqa: E501
            )

        self._voting_subscription = None  # Store subscription ID

        # Call super().__init__ if used in multiple inheritance
        super().__init__(*args, **kwargs)

        # Register the vote handler - Handled by agent's start method now
        # REMOVED: self.agent_bus.register_handler(EventType.COORDINATION, self.handle_vote_initiation)  # noqa: E501
        # logger.info(f"Agent '{self.agent_id}' enabled voting participation via AgentVoterMixin.")  # noqa: E501

    async def start_voting_listener(self):
        """Subscribe to the vote initiation topic. Call this in agent's start()."""
        try:
            self._voting_subscription = await self.agent_bus.subscribe(
                EventType.VOTE_INITIATED.value, self._handle_vote_initiation
            )
            logger.info(
                f"Agent '{self.agent_id}' subscribed to voting topic: {EventType.VOTE_INITIATED.value}"  # noqa: E501
            )
        except Exception as e:
            logger.error(
                f"Agent '{self.agent_id}' failed to subscribe to voting topic: {e}",
                exc_info=True,
            )
            # Decide if this should prevent agent start
            raise

    async def _handle_vote_initiation(self, topic: str, message: Dict[str, Any]):
        """Handles VOTE_INITIATED events by casting a vote."""
        logger.debug(
            f"Agent '{self.agent_id}' received vote initiation message on topic '{topic}'"  # noqa: E501
        )
        try:
            # EDIT START: Validate and parse using Pydantic model
            initiation_data_dict = message.get("data", {})
            correlation_id = message.get("correlation_id")
            try:
                initiation_data: VoteInitiated = VoteInitiated(**initiation_data_dict)
            except (
                Exception
            ) as validation_error:  # Catch Pydantic's ValidationError and others
                logger.warning(
                    f"Agent '{self.agent_id}' received invalid VoteInitiated data: {validation_error}"  # noqa: E501
                )
                return
            # EDIT END

            vote_id = initiation_data.vote_id

            if not vote_id:
                logger.warning("Received vote initiation without vote_id, ignoring.")
                return

            # Decision logic - call the method to be implemented by the concrete agent
            logger.info(f"Agent '{self.agent_id}' deciding on vote '{vote_id}'.")
            # EDIT: Pass the Pydantic model to decide_vote
            choices: List[VoteChoice] = self.decide_vote(initiation_data)

            # Cast the vote
            if choices:  # Only cast if a decision was made
                await self.cast_vote(vote_id, choices, correlation_id)
            else:
                logger.info(
                    f"Agent '{self.agent_id}' abstained or did not decide on vote '{vote_id}'."  # noqa: E501
                )

        except Exception as e:
            # Use vote_id in log if available, otherwise use a placeholder
            current_vote_id = (
                initiation_data.vote_id
                if "initiation_data" in locals() and hasattr(initiation_data, "vote_id")
                else "unknown"
            )
            logger.error(
                f"Agent '{self.agent_id}' error handling vote initiation '{current_vote_id}': {e}",  # noqa: E501
                exc_info=True,
            )

    def decide_vote(self, initiation_data: VoteInitiated) -> List[VoteChoice]:
        """
        Agent's logic to decide on votes for all questions.
        Override this method for custom logic.
        Default implementation votes 'yes' for the first question if possible.
        Returns a list of choices, one for each question.
        """
        questions = initiation_data.questions  # Access attribute directly
        choices = []
        if questions:
            # Example: Vote 'yes' on first question if it looks like a simple yes/no
            first_question_text = questions[0].text.lower()  # Access attribute directly
            if "yes" in first_question_text or "approve" in first_question_text:
                choices.append("yes")
            else:
                choices.append("abstain")
            # Add placeholders for other questions if any
            for _ in range(len(questions) - 1):
                choices.append("abstain")
        return choices

    async def cast_vote(
        self, vote_id: str, choices: List[VoteChoice], correlation_id: Optional[str]
    ):
        """Constructs and publishes the AGENT_VOTE event to the standard topic."""
        # EDIT START: Instantiate AgentVote model
        try:
            vote_data = AgentVote(
                vote_id=vote_id,
                agent_id=self.agent_id,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
                choices=choices,
                # Add confidence/rationale if implemented
                confidence=0.9,  # Example
                rationale=f"Default mixin vote: {choices[0] if choices else 'N/A'}",  # Example  # noqa: E501
            )
        except Exception as validation_error:  # Catch Pydantic validation errors
            logger.error(
                f"Agent '{self.agent_id}' failed to create AgentVote model for '{vote_id}': {validation_error}"  # noqa: E501
            )
            return  # Cannot cast vote if model creation fails
        # EDIT END

        vote_payload = {
            "sender_id": self.agent_id,
            "correlation_id": correlation_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            # EDIT: Dump the model to dict for the bus payload
            "data": vote_data.model_dump(),
        }

        try:
            # EDIT: Use correct EventType for casting a vote
            vote_topic = EventType.VOTE_CAST.value
            await self.agent_bus.publish(vote_topic, vote_payload)
            logger.info(
                f"Agent '{self.agent_id}' cast vote for '{vote_id}' to {vote_topic}. Choices: {choices}"  # noqa: E501
            )
        except Exception as e:
            logger.error(
                f"Agent '{self.agent_id}' failed to cast vote for '{vote_id}': {e}",
                exc_info=True,
            )

    async def stop_voting_listener(self):
        """Unregister the handler when the agent stops. Call this in agent's stop()."""
        if hasattr(self, "agent_bus") and self._voting_subscription:
            try:
                await self.agent_bus.unsubscribe(self._voting_subscription)
                logger.info(f"Agent '{self.agent_id}' unsubscribed voting mixin.")
                self._voting_subscription = None
            except Exception as e:
                logger.error(
                    f"Agent '{self.agent_id}' failed to unsubscribe voting mixin: {e}"
                )


# Example usage update:
# class MyVotingAgent(AgentVoterMixin, BaseAgent):
#     ...
#     async def start(self):
#         await super().start() # Call BaseAgent start (which subscribes to commands)
#         await self.start_voting_listener() # Subscribe to votes
#
#     def decide_vote(self, initiation_data: VoteInitiated) -> List[VoteChoice]:
#         # Custom logic here
#         ...
#
#     async def stop(self):
#         await self.stop_voting_listener() # Unsubscribe from votes
#         await super().stop() # Call BaseAgent stop
