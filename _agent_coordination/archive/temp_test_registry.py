"""
Temporary script to test agent registry functionality.
"""
import sys
import os
import logging

# Setup basic logging for visibility
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

print("--- Starting Registry Test Script ---")

try:
    # Ensure the project root is potentially discoverable if needed, although relative imports should work with __init__.py
    # project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    # print(f"DEBUG: Adding {project_root} to path potentially")
    # sys.path.insert(0, project_root)

    print("Importing registry components...")
    from _agent_coordination.utils.agent_registry import get_registered_agents, AGENT_REGISTRY
    print("Importing agent modules (this should trigger registration)...")
    # Explicitly import the agent module to ensure the @register_agent decorator runs
    from _agent_coordination.agents import reflection_agent
    print("Imports successful.")

    print("\n--- Checking Registry Contents ---")
    agents = get_registered_agents()
    print(f"Found registered agents: {list(agents.keys())}")
    if not agents:
        print("ERROR: No agents found in registry!")
        sys.exit(1)

    if "ReflectionAgent" not in agents:
         print("ERROR: ReflectionAgent not found in registry!")
         sys.exit(1)
    else:
        print("ReflectionAgent found in registry.")

    print("\n--- Testing Agent Instantiation and Run ---")
    instantiation_failed = False
    for name, cls in agents.items():
        print(f"\nTesting agent: {name}")
        try:
            agent_id = f"{name.lower()}_script_test"
            print(f"Instantiating {name} with ID: {agent_id}")
            # Passkwargs to handle potential base class init args
            agent = cls(agent_id=agent_id)
            print(f"Successfully instantiated: {agent}")
            print(f"Running {agent}...")
            result = agent.run() # Assumes run() takes no args for test
            print(f"Agent {name} ran. Result: {result}")
            if not isinstance(result, dict) or "status" not in result:
                print(f"WARNING: Unexpected result format from {name}.run(): {result}")

        except Exception as e:
            print(f"ERROR: Failed to instantiate or run agent {name}: {e}")
            logging.exception("Exception details:") # Log traceback
            instantiation_failed = True

    if instantiation_failed:
        print("\n--- Registry Test Script Finished with ERRORS ---")
        sys.exit(1)
    else:
        print("\n--- Registry Test Script Finished Successfully ---")
        sys.exit(0)

except ImportError as e:
    print(f"ERROR: Failed to import modules: {e}")
    print("Please ensure __init__.py files exist and the script is run from the project root or PYTHONPATH is set correctly.")
    logging.exception("Import error details:")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: An unexpected error occurred: {e}")
    logging.exception("Unexpected error details:")
    sys.exit(1) 