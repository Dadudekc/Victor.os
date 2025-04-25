"""
Defines the abstract base class for agents in the Dream.OS swarm.
"""

class BaseAgent:
    """Abstract base class for all autonomous agents in the Dream.OS agent swarm."""

    def __init__(self, agent_id: str, **kwargs):
        """Initializes the base agent.

        Args:
            agent_id: A unique identifier for this agent instance.
            **kwargs: Allow subclasses to accept additional parameters without breaking
                      the base class signature.
        """
        if not agent_id:
            raise ValueError("Agent ID cannot be empty.")
        self.agent_id = agent_id
        # Store any extra arguments for potential use by subclasses or logging
        self._extra_init_kwargs = kwargs

    def run(self, *args, **kwargs):
        """
        The main execution entry point for the agent's primary task or loop.
        Subclasses MUST implement this method.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement the 'run' method.")

    def get_id(self) -> str:
        """Returns the agent's unique ID."""
        return self.agent_id

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(id={self.agent_id})"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id='{self.agent_id}'>" 