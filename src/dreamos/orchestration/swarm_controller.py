import argparse
import json
import os
import subprocess
import sys
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Configure logging
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'runtime', 'logs', 'swarm_controller_debug.log')
STATS_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'runtime', 'stats', 'swarm_stats.json')
FEEDBACK_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'runtime', 'feedback', 'swarm_feedback.json')

os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
os.makedirs(os.path.dirname(STATS_FILE_PATH), exist_ok=True)
os.makedirs(os.path.dirname(FEEDBACK_FILE_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, mode='w'),
        logging.StreamHandler()
    ]
)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'runtime', 'config', 'swarm_config.json')
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
active_processes = {}

class SwarmStats:
    def __init__(self):
        self.stats = {
            'agent_stats': {},
            'system_stats': {
                'total_agents': 0,
                'active_agents': 0,
                'failed_agents': 0,
                'total_cycles': 0,
                'last_update': None
            }
        }
        self.load_stats()

    def load_stats(self):
        if os.path.exists(STATS_FILE_PATH):
            try:
                with open(STATS_FILE_PATH, 'r') as f:
                    self.stats = json.load(f)
            except Exception as e:
                logging.error(f"Error loading stats: {e}")

    def save_stats(self):
        try:
            with open(STATS_FILE_PATH, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving stats: {e}")

    def update_agent_stats(self, agent_id: str, status: str, metrics: Dict = None):
        if agent_id not in self.stats['agent_stats']:
            self.stats['agent_stats'][agent_id] = {
                'start_time': datetime.now().isoformat(),
                'status_history': [],
                'metrics': {}
            }
        
        self.stats['agent_stats'][agent_id]['status_history'].append({
            'status': status,
            'timestamp': datetime.now().isoformat()
        })
        
        if metrics:
            self.stats['agent_stats'][agent_id]['metrics'].update(metrics)
        
        self.update_system_stats()
        self.save_stats()

    def update_system_stats(self):
        active = sum(1 for agent in self.stats['agent_stats'].values() 
                    if agent['status_history'][-1]['status'] == 'running')
        failed = sum(1 for agent in self.stats['agent_stats'].values() 
                    if agent['status_history'][-1]['status'] == 'failed')
        
        self.stats['system_stats'].update({
            'total_agents': len(self.stats['agent_stats']),
            'active_agents': active,
            'failed_agents': failed,
            'total_cycles': self.stats['system_stats'].get('total_cycles', 0) + 1,
            'last_update': datetime.now().isoformat()
        })

class SwarmFeedback:
    def __init__(self):
        self.feedback = {
            'agent_feedback': {},
            'system_feedback': {
                'last_update': None,
                'critical_issues': [],
                'optimization_suggestions': []
            }
        }
        self.load_feedback()

    def load_feedback(self):
        if os.path.exists(FEEDBACK_FILE_PATH):
            try:
                with open(FEEDBACK_FILE_PATH, 'r') as f:
                    self.feedback = json.load(f)
            except Exception as e:
                logging.error(f"Error loading feedback: {e}")

    def save_feedback(self):
        try:
            with open(FEEDBACK_FILE_PATH, 'w') as f:
                json.dump(self.feedback, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving feedback: {e}")

    def add_agent_feedback(self, agent_id: str, feedback_type: str, message: str, severity: str = 'info'):
        if agent_id not in self.feedback['agent_feedback']:
            self.feedback['agent_feedback'][agent_id] = []
        
        self.feedback['agent_feedback'][agent_id].append({
            'type': feedback_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        })
        
        if severity == 'critical':
            self.feedback['system_feedback']['critical_issues'].append({
                'agent_id': agent_id,
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
        
        self.feedback['system_feedback']['last_update'] = datetime.now().isoformat()
        self.save_feedback()

    def add_optimization_suggestion(self, suggestion: str, impact: str = 'medium'):
        self.feedback['system_feedback']['optimization_suggestions'].append({
            'suggestion': suggestion,
            'impact': impact,
            'timestamp': datetime.now().isoformat()
        })
        self.save_feedback()

# Initialize stats and feedback
swarm_stats = SwarmStats()
swarm_feedback = SwarmFeedback()

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
        swarm_feedback.add_agent_feedback(agent_id, 'launch_error', 'Missing script_path in config', 'critical')
        return None

    script_path_absolute = os.path.join(WORKSPACE_ROOT, script_path_relative)

    if not os.path.exists(script_path_absolute):
        logging.error(f"Agent script not found at {script_path_absolute} for agent {agent_id}. Cannot launch.")
        swarm_feedback.add_agent_feedback(agent_id, 'launch_error', f'Script not found at {script_path_absolute}', 'critical')
        return None

    launch_cwd = os.path.join(WORKSPACE_ROOT, 'src')
    env = os.environ.copy()
    
    logging.debug(f"Using launch CWD for agent {agent_id}: {launch_cwd}")

    prompt_file_relative_path = f"runtime/prompts/{agent_id.lower()}.txt"
    module_path = "dreamos.tools.agent_bootstrap_runner"

    cmd = [
        sys.executable, 
        "-m", module_path,
        '--agent-id', agent_id,
        '--prompt-file', prompt_file_relative_path
    ]
    
    logging.info(f"Launching agent {agent_id} with command: {' '.join(cmd)}")
    logging.info(f"Using CWD: {launch_cwd} and relying on Python to find modules.")

    try:
        process = subprocess.Popen(cmd, cwd=launch_cwd, env=env)
        active_processes[agent_id] = {"pid": process.pid, "process_obj": process, "status": "running"}
        logging.info(f"Agent {agent_id} launched successfully with PID: {process.pid}")
        
        # Update stats and feedback
        swarm_stats.update_agent_stats(agent_id, 'running', {
            'pid': process.pid,
            'start_time': datetime.now().isoformat()
        })
        swarm_feedback.add_agent_feedback(agent_id, 'launch_success', f'Agent launched with PID {process.pid}')
        
        return active_processes[agent_id]
    except FileNotFoundError:
        error_msg = f"Failed to launch agent {agent_id}: Command or script not found"
        logging.error(error_msg, exc_info=True)
        swarm_feedback.add_agent_feedback(agent_id, 'launch_error', error_msg, 'critical')
    except Exception as e:
        error_msg = f"Failed to launch agent {agent_id}: {e}"
        logging.error(error_msg, exc_info=True)
        swarm_feedback.add_agent_feedback(agent_id, 'launch_error', error_msg, 'critical')
    return None

def terminate_agent(agent_id):
    """Terminates a running agent using its stored PID."""
    logging.info(f"Attempting to terminate agent: {agent_id}")
    if agent_id in active_processes and active_processes[agent_id]["process_obj"]:
        process_info = active_processes[agent_id]
        try:
            process_info["process_obj"].terminate()
            try:
                process_info["process_obj"].wait(timeout=5)
                logging.info(f"Agent {agent_id} (PID: {process_info['pid']}) terminated gracefully.")
                swarm_stats.update_agent_stats(agent_id, 'terminated')
                swarm_feedback.add_agent_feedback(agent_id, 'termination', 'Agent terminated gracefully')
            except subprocess.TimeoutExpired:
                logging.warning(f"Agent {agent_id} (PID: {process_info['pid']}) did not terminate gracefully after 5s, sending SIGKILL.")
                process_info["process_obj"].kill()
                logging.info(f"Agent {agent_id} (PID: {process_info['pid']}) killed.")
                swarm_stats.update_agent_stats(agent_id, 'killed')
                swarm_feedback.add_agent_feedback(agent_id, 'termination', 'Agent killed after timeout', 'warning')
            process_info["status"] = "terminated"
            return {"status": "terminated"}
        except Exception as e:
            error_msg = f"Error terminating agent {agent_id} (PID: {process_info['pid']}): {e}"
            logging.error(error_msg, exc_info=True)
            process_info["status"] = "error_terminating"
            swarm_feedback.add_agent_feedback(agent_id, 'termination_error', error_msg, 'critical')
            return {"status": "error_terminating", "error": str(e)}
    else:
        warning_msg = f"Agent {agent_id} not found in active processes or no process object available"
        logging.warning(warning_msg)
        swarm_feedback.add_agent_feedback(agent_id, 'termination_error', warning_msg, 'warning')
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
            swarm_stats.update_agent_stats(agent_id, 'running')
            return {"status": "running", "pid": process_info['pid']}
        else:
            logging.info(f"Agent {agent_id} (PID: {process_info['pid']}) has exited with code: {return_code}.")
            process_info["status"] = "exited"
            swarm_stats.update_agent_stats(agent_id, 'exited', {'exit_code': return_code})
            swarm_feedback.add_agent_feedback(agent_id, 'exit', f'Agent exited with code {return_code}', 
                                            'critical' if return_code != 0 else 'info')
            return {"status": "exited", "pid": process_info['pid'], "return_code": return_code}
    else:
        warning_msg = f"Agent {agent_id} not found in active processes or no process object"
        logging.warning(warning_msg)
        swarm_feedback.add_agent_feedback(agent_id, 'status_error', warning_msg, 'warning')
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