import argparse
import json
import os
import subprocess
import sys
import time
import logging

# Configure logging
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'runtime', 'logs', 'swarm_controller_debug.log')
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True) # Ensure log directory exists

logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, mode='w'), # Write to a file
        logging.StreamHandler() # Still try to log to console
    ]
)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'runtime', 'config', 'swarm_config.json')
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
active_processes = {} # Global for now, consider class structure later

def load_config():
    """Loads the swarm configuration."""
    logging.debug(f"Attempting to load config from: {CONFIG_PATH}")
    if not os.path.exists(CONFIG_PATH):
        logging.error(f"Configuration file not found: {CONFIG_PATH}")
        return None
    try:
        with open(CONFIG_PATH, 'r') as f:
            data = json.load(f)
        logging.debug(f"Configuration loaded successfully.")
        return data
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {CONFIG_PATH}: {e}")
        return None
    except Exception as e:
        logging.error(f"Failed to load or parse configuration from {CONFIG_PATH}: {e}")
        return None

def launch_agent(agent_id, agent_config):
    """Launches a new agent using its specific script_path."""
    logging.info(f"Attempting to launch agent: {agent_id} with config: {agent_config}")
    
    script_path_relative = agent_config.get('script_path')
    if not script_path_relative:
        logging.error(f"'script_path' not found in agent_config for {agent_id}. Cannot launch.")
        return None

    # Construct absolute path for the script (still useful for os.path.exists check)
    script_path_absolute = os.path.join(WORKSPACE_ROOT, script_path_relative)

    if not os.path.exists(script_path_absolute):
        logging.error(f"Agent script not found at {script_path_absolute} for agent {agent_id}. Cannot launch.")
        return None

    # Prepare environment: Set CWD to the directory containing the 'dreamos' package (i.e., WORKSPACE_ROOT/src)
    # Python will automatically add CWD to sys.path, so 'dreamos' should be importable.
    launch_cwd = os.path.join(WORKSPACE_ROOT, 'src')
    env = os.environ.copy() # Start with a fresh copy of current environment
    # No explicit PYTHONPATH manipulation needed if CWD is correct for module execution.
    
    logging.debug(f"Using launch CWD for agent {agent_id}: {launch_cwd}")

    prompt_file_relative_path = f"runtime/prompts/{agent_id.lower()}.txt"

    # The script_path_absolute is validated to exist, but we run as a module.
    module_path = "dreamos.tools.agent_bootstrap_runner"

    cmd = [
        sys.executable, 
        "-m", module_path,
        '--agent-id', agent_id,
        '--prompt-file', prompt_file_relative_path
    ]
    
    logging.info(f"Launching agent {agent_id} with command: {' '.join(cmd)}")
    logging.info(f"Using CWD: {launch_cwd} and relying on Python to find modules.") # Modified log message

    try:
        process = subprocess.Popen(cmd, cwd=launch_cwd, env=env)
        active_processes[agent_id] = {"pid": process.pid, "process_obj": process, "status": "running"}
        logging.info(f"Agent {agent_id} launched successfully with PID: {process.pid}")
        return active_processes[agent_id]
    except FileNotFoundError: #Handles if sys.executable or script_path_absolute is wrong
        logging.error(f"Failed to launch agent {agent_id}: Command or script not found. Check sys.executable and script path: {script_path_absolute}", exc_info=True)
    except Exception as e:
        logging.error(f"Failed to launch agent {agent_id}: {e}", exc_info=True)
    return None

def terminate_agent(agent_id):
    """Terminates a running agent using its stored PID."""
    logging.info(f"Attempting to terminate agent: {agent_id}")
    if agent_id in active_processes and active_processes[agent_id]["process_obj"]:
        process_info = active_processes[agent_id]
        try:
            process_info["process_obj"].terminate() # Send SIGTERM
            try:
                process_info["process_obj"].wait(timeout=5) # Wait for graceful shutdown
                logging.info(f"Agent {agent_id} (PID: {process_info['pid']}) terminated gracefully.")
            except subprocess.TimeoutExpired:
                logging.warning(f"Agent {agent_id} (PID: {process_info['pid']}) did not terminate gracefully after 5s, sending SIGKILL.")
                process_info["process_obj"].kill()
                logging.info(f"Agent {agent_id} (PID: {process_info['pid']}) killed.")
            process_info["status"] = "terminated"
            # Optionally remove from active_processes or mark as inactive
            # del active_processes[agent_id]
            return {"status": "terminated"}
        except Exception as e:
            logging.error(f"Error terminating agent {agent_id} (PID: {process_info['pid']}): {e}", exc_info=True)
            process_info["status"] = "error_terminating"
            return {"status": "error_terminating", "error": str(e)}
    else:
        logging.warning(f"Agent {agent_id} not found in active processes or no process object available. Cannot terminate.")
        return {"status": "not_found"}

def get_agent_status(agent_id):
    """Checks the status of an agent using its stored process object."""
    logging.info(f"Attempting to get status for agent: {agent_id}")
    if agent_id in active_processes and active_processes[agent_id]["process_obj"]:
        process_info = active_processes[agent_id]
        process_obj = process_info["process_obj"]
        return_code = process_obj.poll()

        if return_code is None:
            logging.info(f"Agent {agent_id} (PID: {process_info['pid']}) is running.")
            process_info["status"] = "running"
            return {"status": "running", "pid": process_info['pid']}
        else:
            logging.info(f"Agent {agent_id} (PID: {process_info['pid']}) has exited with code: {return_code}.")
            process_info["status"] = "exited"
            # Optionally remove from active_processes here if it has exited
            # del active_processes[agent_id]
            return {"status": "exited", "pid": process_info['pid'], "return_code": return_code}
    else:
        logging.warning(f"Agent {agent_id} not found in active processes or no process object. Status unknown.")
        return {"status": "unknown"}

def main():
    print("SWARM_CONTROLLER_MAIN_STARTED_DEBUG_PRINT", flush=True) # Retain one clear print for basic output check
    logging.info("SWARM_CONTROLLER_LOGGING_TEST_INFO") # Retain one clear log for basic output check

    parser = argparse.ArgumentParser(description="Swarm Controller for DreamOS Agents")
    parser.add_argument('--action', choices=['start', 'stop', 'status', 'launch-all'], required=True, help="Action to perform.")
    parser.add_argument('--agent-id', type=str, help="ID of the agent to act upon (for start, stop, status).")

    args = parser.parse_args()
    print(f"DEBUG: Arguments parsed: {args}", flush=True) # Debug print for args
    
    config = load_config()
    print(f"DEBUG: Config object in main after load_config(): {'NOT None' if config else 'None'}", flush=True) # Debug print for config

    if not config:
        logging.error("Failed to load configuration. Exiting.")
        return

    if args.action == 'launch-all':
        if 'managed_agents' not in config or not isinstance(config['managed_agents'], list):
            logging.error("Invalid or missing 'managed_agents' list in swarm_config.json for launch-all.")
            return
        logging.info("Launching all configured agents (from managed_agents list)...")
        for agent_info in config['managed_agents']:
            agent_id = agent_info.get('agent_id')
            if not agent_id:
                logging.warning("Agent entry in 'managed_agents' found without an 'agent_id'. Skipping: {agent_info}")
                continue
            
            launch_agent(agent_id, agent_info)
        logging.info("All agents from 'managed_agents' launched.")

    elif args.action == 'start':
        if not args.agent_id:
            parser.error("--agent-id is required for action 'start'")
        logging.info(f"Starting agent: {args.agent_id}...")
        agent_to_start = next((agent for agent in config.get('managed_agents', []) if agent.get('agent_id') == args.agent_id), None)
        if agent_to_start:
            launch_agent(args.agent_id, agent_to_start)
        else:
            logging.error(f"Agent ID {args.agent_id} not found in 'managed_agents' configuration.")

    elif args.action == 'stop':
        if not args.agent_id:
            parser.error("--agent-id is required for action 'stop'")
        logging.info(f"Stopping agent: {args.agent_id}...")
        terminate_agent(args.agent_id)

    elif args.action == 'status':
        if not args.agent_id:
            # If no agent_id provided, maybe show status for all? For now, require it.
            # Or, implement a "status-all" action.
            # parser.error("--agent-id is required for action 'status'")
            logging.info("Requesting status for all known agents (implementation pending)...")
            # Placeholder: Iterate through a list of known/active agents
            # For now, just logs a message.
        else:
            logging.info(f"Getting status for agent: {args.agent_id}...")
            status = get_agent_status(args.agent_id)
            logging.info(f"Agent {args.agent_id} status: {status}")
    else:
        logging.error(f"Unknown action: {args.action}")

if __name__ == "__main__":
    main() 