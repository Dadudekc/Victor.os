"""
Provides a registry for dynamically discovering and managing Agent classes.
"""

from typing import Dict, Type, Any

# Global registry dictionary
# Maps agent class name (str) to the agent class itself (Type)
AGENT_REGISTRY: Dict[str, Type[Any]] = {}

def register_agent(agent_cls: Type[Any]) -> Type[Any]:
    """
    Class decorator to automatically register agent classes in the AGENT_REGISTRY.

    Args:
        agent_cls: The agent class to register.

    Returns:
        The original agent class, unmodified.

    Raises:
        ValueError: If an agent with the same name is already registered.
    """
    agent_name = agent_cls.__name__
    if agent_name in AGENT_REGISTRY:
        # Potentially allow overwriting in debug/dev mode?
        # For now, raise an error to prevent accidental overwrites.
        raise ValueError(f"Agent class '{agent_name}' is already registered.")

    AGENT_REGISTRY[agent_name] = agent_cls
    # Optional: Add logging here if desired
    # print(f"DEBUG: Registered agent: {agent_name}")
    return agent_cls


def get_agent_class(agent_name: str) -> Type[Any]:
    """
    Retrieves an agent class from the registry by name.

    Args:
        agent_name: The name of the agent class to retrieve.

    Returns:
        The agent class.

    Raises:
        KeyError: If the agent name is not found in the registry.
    """
    if agent_name not in AGENT_REGISTRY:
        raise KeyError(f"Agent class '{agent_name}' not found in registry. Available: {list(AGENT_REGISTRY.keys())}")
    return AGENT_REGISTRY[agent_name]


def get_registered_agents() -> Dict[str, Type[Any]]:
    """
    Returns a copy of the agent registry.
    """
    return AGENT_REGISTRY.copy() 
