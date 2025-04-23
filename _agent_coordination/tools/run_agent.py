"""
CLI tool to dynamically instantiate and run a registered agent.
"""

import argparse
import sys
import json
import logging
import os

# Ensure the parent directory (_agent_coordination) is implicitly
# part of the path if run directly from tools/
# This helps find the utils/ and agents/ packages
# Note: Running via `python -m _agent_coordination.tools.run_agent` is preferred
# script_dir = os.path.dirname(os.path.abspath(__file__))
# project_coord_dir = os.path.dirname(script_dir)
# if project_coord_dir not in sys.path:
#     sys.path.insert(0, project_coord_dir)

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(
        description="Run a registered agent by class name.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "agent_class_name",
        help="The exact class name of the agent to run (must be registered)."
    )
    parser.add_argument(
        "--agent-id",
        required=True,
        help="A unique ID to assign to this agent instance."
    )
    parser.add_argument(
        "--init-kwargs-json",
        default="{}",
        help="JSON string representing keyword arguments for agent __init__ (e.g., \"{\\\"analysis_depth\\\": 2}\")."
    )
    parser.add_argument(
        "--run-args-json",
        default="[]",
        help="JSON string representing positional arguments for agent run() (e.g., \"[\\\"arg1\\\", 123]\")."
    )
    parser.add_argument(
        "--run-kwargs-json",
        default="{}",
        help="JSON string representing keyword arguments for agent run() (e.g., \"{\\\"force\\\": true}\")."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose DEBUG logging for this script and potentially agents."
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled for run_agent.py")

    try:
        logger.info(f"Attempting to run agent: {args.agent_class_name} with ID: {args.agent_id}")

        # Import necessary functions AFTER potentially adjusting path
        # Need to import agent modules to ensure registration occurs
        logger.debug("Importing agent modules to ensure registration...")
        from _agent_coordination.agents import reflection_agent # Import known agents
        # Add imports for other agent modules here as they are created
        # Example: from _agent_coordination.agents import proposal_agent

        logger.debug("Importing registry...")
        from _agent_coordination.utils.agent_registry import get_agent_class

        # Parse JSON arguments
        try:
            init_kwargs = json.loads(args.init_kwargs_json)
            if not isinstance(init_kwargs, dict):
                raise ValueError("--init-kwargs-json must be a JSON object.")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Invalid --init-kwargs-json: {e}")
            sys.exit(1)

        try:
            run_args = json.loads(args.run_args_json)
            if not isinstance(run_args, list):
                raise ValueError("--run-args-json must be a JSON array.")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Invalid --run-args-json: {e}")
            sys.exit(1)

        try:
            run_kwargs = json.loads(args.run_kwargs_json)
            if not isinstance(run_kwargs, dict):
                raise ValueError("--run-kwargs-json must be a JSON object.")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Invalid --run-kwargs-json: {e}")
            sys.exit(1)

        # Get the agent class from the registry
        logger.debug(f"Looking up agent class '{args.agent_class_name}'...")
        AgentClass = get_agent_class(args.agent_class_name)
        logger.debug(f"Found agent class: {AgentClass}")

        # Instantiate the agent
        logger.info(f"Instantiating {args.agent_class_name}...")
        agent_instance = AgentClass(agent_id=args.agent_id, **init_kwargs)
        logger.info(f"Agent instantiated: {agent_instance}")

        # Run the agent
        logger.info(f"Calling run() on {agent_instance}...")
        result = agent_instance.run(*run_args, **run_kwargs)
        logger.info(f"Agent run finished. Result:")
        # If the agent returned generated code, apply it to the target file
        if isinstance(result, dict) and 'generated_code' in result and 'target_file' in result:
            import subprocess, tempfile
            # Write generated code to a temporary file
            with tempfile.NamedTemporaryFile('w+', delete=False, suffix='.txt') as tmp_file:
                tmp_file.write(result['generated_code'])
                tmp_file.flush()
                tmp_path = tmp_file.name

            # Invoke the code_applicator tool
            cmd = [
                sys.executable,
                os.path.join(os.path.dirname(__file__), 'code_applicator.py'),
                '--target', result['target_file'],
                '--source', tmp_path,
                '--backup'
            ]
            subprocess.run(cmd, check=True)
            print(f"Applied generated code to {result['target_file']}")
        else:
            # Pretty print result if it's complex
            if isinstance(result, (dict, list)):
                print(json.dumps(result, indent=2))
            else:
                print(result)

        logger.info("run_agent.py finished successfully.")
        sys.exit(0)

    except KeyError as e:
        logger.error(f"Failed to find agent class: {e}")
        sys.exit(1)
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        logger.error("Ensure this script is run correctly (e.g., from project root or using `python -m`) and required __init__.py files exist.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during agent execution: {e}", exc_info=args.verbose)
        sys.exit(1)

if __name__ == "__main__":
    main() 