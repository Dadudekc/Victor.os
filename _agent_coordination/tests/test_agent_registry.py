"""
Tests for the agent registry and basic agent instantiation/execution.
"""

import pytest
import sys
import os

# Adjust path to ensure modules can be found
# Assuming tests are run from project root (where _agent_coordination is)
# This might need adjustment depending on the test runner setup
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import necessary components AFTER potentially adjusting path
from _agent_coordination.utils.agent_registry import get_registered_agents, register_agent, AGENT_REGISTRY
# Need to ensure agent modules are imported so the decorator runs
from _agent_coordination.agents import reflection_agent # This import triggers registration


# --- Fixtures (Optional) ---
@pytest.fixture(autouse=True)
def clear_registry_before_each():
    """Ensures the registry is clean before each test function."""
    # Store original registry
    original_registry = AGENT_REGISTRY.copy()
    AGENT_REGISTRY.clear()
    # Re-register known agents if needed, or let tests do it
    # This ensures tests are isolated if they modify the registry
    # Re-importing ReflectionAgent to re-register it for subsequent tests if cleared
    if 'ReflectionAgent' not in AGENT_REGISTRY:
         register_agent(reflection_agent.ReflectionAgent)

    yield # Run the test

    # Restore original registry state after test
    AGENT_REGISTRY.clear()
    AGENT_REGISTRY.update(original_registry)


# --- Test Cases ---

def test_reflection_agent_registered():
    """Verify that ReflectionAgent is automatically registered upon import."""
    agents = get_registered_agents()
    assert "ReflectionAgent" in agents
    assert agents["ReflectionAgent"] == reflection_agent.ReflectionAgent

def test_get_agent_class():
    """Test retrieving a registered agent class."""
    from _agent_coordination.utils.agent_registry import get_agent_class
    cls = get_agent_class("ReflectionAgent")
    assert cls == reflection_agent.ReflectionAgent

def test_get_unknown_agent_class():
    """Test that retrieving an unknown agent raises KeyError."""
    from _agent_coordination.utils.agent_registry import get_agent_class
    with pytest.raises(KeyError):
        get_agent_class("NonExistentAgent")

def test_agent_instantiation_and_run_smoke():
    """Basic smoke test to instantiate and run registered agents."""
    print("\n--- Running Agent Instantiation Smoke Test ---")
    agents = get_registered_agents()
    print(f"Found registered agents: {list(agents.keys())}")
    assert "ReflectionAgent" in agents, "ReflectionAgent should be registered"

    for name, cls in agents.items():
        print(f"\nInstantiating {name}...")
        try:
            # Provide a basic agent_id
            agent = cls(agent_id=f"{name.lower()}_smoke_test")
            print(f"Running {agent}...")
            # Call the run method - assumes it takes no specific args for smoke test
            result = agent.run()
            print(f"Agent {name} ran successfully. Result: {result}")
            # Basic check on expected return type (optional)
            assert isinstance(result, dict), f"{name}.run() should return a dict"
            assert "status" in result, f"{name}.run() result missing 'status' key"
        except Exception as e:
            pytest.fail(f"Failed to instantiate or run agent {name}: {e}")

    print("--- Agent Instantiation Smoke Test Finished ---")

# Optional: Test preventing duplicate registration
def test_duplicate_registration_error():
    """Verify that registering the same name twice raises ValueError."""
    # First registration happens via import and fixture
    assert "ReflectionAgent" in AGENT_REGISTRY

    # Try to register manually again
    with pytest.raises(ValueError):
        register_agent(reflection_agent.ReflectionAgent) 
