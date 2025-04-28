import logging
from typing import Dict, Any

from dreamos.coordination.agent_bus import AgentBus, EventType # Assuming these exist

logger = logging.getLogger(__name__)

class AgentVoterMixin:
    """
    A mixin for Agents to automatically participate in voting sessions.

    Agents using this mixin should have `agent_id` and `agent_bus` attributes.
    Provides a default handler for VOTE_INITIATED events to cast a simple vote.
    """

    def __init__(self, *args, **kwargs):
        # Ensure agent_id and agent_bus are available
        if not hasattr(self, 'agent_id') or not hasattr(self, 'agent_bus'):
            raise AttributeError("AgentVoterMixin requires the agent to have 'agent_id' and 'agent_bus' attributes.")
        
        # Call super().__init__ if used in multiple inheritance
        super().__init__(*args, **kwargs)
        
        # Register the vote handler
        self.agent_bus.register_handler(EventType.COORDINATION, self.handle_vote_initiation)
        logger.info(f"Agent '{self.agent_id}' enabled voting participation via AgentVoterMixin.")

    async def handle_vote_initiation(self, event: Dict[str, Any]):
        """Handles VOTE_INITIATED events by casting a vote."""
        if event.get('type') == 'VOTE_INITIATED':
            topic_id = event.get('topic_id')
            question = event.get('question')
            options = event.get('options', ['yes', 'no'])
            logger.info(f"Agent '{self.agent_id}' received VOTE_INITIATED for topic '{topic_id}': \"{question}\" Options: {options}")
            
            # Determine vote based on agent logic (default: yes)
            vote_to_cast = self.decide_vote(event)

            if vote_to_cast in options:
                await self.cast_vote(topic_id, vote_to_cast)
            else:
                logger.warning(f"Agent '{self.agent_id}' decided not to cast a valid vote ('{vote_to_cast}') for topic '{topic_id}'.")

    def decide_vote(self, initiation_event: Dict[str, Any]) -> str:
        """
        Agent's logic to decide on a vote. Override this method for custom logic.
        Default implementation votes 'yes' if available.
        """
        options = initiation_event.get('options', [])
        if 'yes' in options:
            return 'yes'
        elif options: # Vote for the first option if 'yes' is not present
            return options[0]
        else:
            return "abstain" # Or some other indicator of not voting
        
    async def cast_vote(self, topic_id: str, vote: str):
        """Constructs and dispatches the AGENT_VOTE event."""
        vote_event = {
            'type': 'AGENT_VOTE',
            'topic_id': topic_id,
            'agent_id': self.agent_id,
            'vote': vote
        }
        await self.agent_bus.dispatch_event(EventType.COORDINATION, vote_event)
        logger.info(f"Agent '{self.agent_id}' cast vote '{vote}' for topic '{topic_id}'.")

    def stop_voting(self):
        """Unregister the handler when the agent stops."""
        if hasattr(self, 'agent_bus'):
            self.agent_bus.unregister_handler(EventType.COORDINATION, self.handle_vote_initiation)
            logger.info(f"Agent '{self.agent_id}' disabled voting participation.")

# Example usage:
# class MyVotingAgent(AgentVoterMixin, BaseAgent):
#     def __init__(self, agent_id: str, agent_bus: AgentBus):
#         # Initialize BaseAgent first if it has its own __init__
#         BaseAgent.__init__(self, agent_id, agent_bus)
#         # Then initialize the mixin
#         AgentVoterMixin.__init__(self)
#
#     def decide_vote(self, initiation_event: Dict[str, Any]) -> str:
#         # Custom logic here - e.g., always vote 'no'
#         if 'no' in initiation_event.get('options', []):
#             return 'no'
#         return super().decide_vote(initiation_event) # Fallback to default
#
#     async def stop(self):
#         await super().stop() # Call BaseAgent stop if exists
#         self.stop_voting() # Call mixin stop 