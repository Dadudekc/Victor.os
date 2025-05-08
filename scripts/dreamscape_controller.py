# scripts/dreamscape_controller.py
import yaml  # Requires PyYAML to be installed (pip install pyyaml)
import json
import os
import datetime
import time
import subprocess # Added for executing external scripts

# --- Path Configuration ---
# These paths are configured assuming the script is in 'scripts/' and the workspace root is one level up.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

BASE_RUNTIME_DIR = os.path.join(WORKSPACE_ROOT, "runtime")
DEPLOYMENT_CONFIG_PATH = os.path.join(BASE_RUNTIME_DIR, "agent_comms", "deployments", "multi_agent_deployment.yaml")
AGENT_MAILBOX_DIR = os.path.join(BASE_RUNTIME_DIR, "agent_comms", "agent_mailboxes")
LOG_DIR = os.path.join(BASE_RUNTIME_DIR, "logs")
OUTPUT_DIR = os.path.join(BASE_RUNTIME_DIR, "dreamscape_output")
AGENT_DEVLOG_DIR = os.path.join(BASE_RUNTIME_DIR, "devlog", "agents")  # Centralized agent devlogs
CHRONICLE_CONVERSATIONS_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "chronicle_conversations.py") # Path to the script

AGENT_POINTS_PATH = os.path.join(LOG_DIR, "agent_points.json")
DEPLOYMENT_STATUS_PATH = os.path.join(LOG_DIR, "deployment_status.yaml")
DREAMSCAPE_ARC_MAP_PATH = os.path.join(LOG_DIR, "dreamscape_arc_map.json")
CONTROLLER_LOG_PATH = os.path.join(LOG_DIR, "dreamscape_controller.log")

# --- Utility Functions ---
def log_message(message, level="INFO"):
    """Logs a message to the console and the controller's log file."""
    timestamp = datetime.datetime.now().isoformat()
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line)
    try:
        with open(CONTROLLER_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(log_line + "\n")
    except Exception as e:
        print(f"CRITICAL: Failed to write to controller log at {CONTROLLER_LOG_PATH}: {e}")

def ensure_dir_exists(dir_path):
    """Ensures a directory exists, creating it if necessary."""
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
            log_message(f"Created directory: {dir_path}", "DEBUG")
        except Exception as e:
            log_message(f"Failed to create directory {dir_path}: {e}", "ERROR")
            # Depending on severity, you might want to raise the error or exit

# --- Agent Class ---
class Agent:
    def __init__(self, agent_id, codename, role, tasks_from_yaml, prompt_path):
        self.id = agent_id
        self.codename = codename
        self.role = role
        self.tasks_from_yaml = tasks_from_yaml  # Tasks as defined in the deployment YAML
        self.prompt_path = prompt_path
        self.points = 0
        self.status = "idle"
        self.current_task_index = 0
        self.devlog_path = os.path.join(AGENT_DEVLOG_DIR, f"{self.id}_devlog.md")
        ensure_dir_exists(os.path.dirname(self.devlog_path)) # Ensure agent's devlog directory exists

    def get_prompt_content(self):
        """Reads and returns the content of the agent's prompt file."""
        try:
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            log_message(f"Prompt file not found for agent {self.id} at {self.prompt_path}", "ERROR")
            return None
        except Exception as e:
            log_message(f"Error reading prompt for agent {self.id}: {e}", "ERROR")
            return None

    def perform_task(self, current_loop_cycle):
        """
        Performs the agent's current task. For Agent-4, it executes chronicle_conversations.py.
        Other agents still simulate tasks.
        """
        self.status = "working"
        log_message(f"Agent {self.codename} ({self.id}) starting task for loop {current_loop_cycle}.", "DEBUG")

        prompt_content = self.get_prompt_content()
        if not prompt_content:
            self.status = "error_no_prompt"
            log_message(f"Agent {self.codename} cannot perform task due to missing prompt.", "WARNING")
            self.write_to_devlog(f"Loop {current_loop_cycle}: Failed to load prompt. Status: {self.status}")
            return

        task_description = "Default simulated action: general processing."
        if self.tasks_from_yaml and self.current_task_index < len(self.tasks_from_yaml):
            task_description = self.tasks_from_yaml[self.current_task_index]
        
        log_message(f"Loop {current_loop_cycle}: Agent {self.codename} performing: '{task_description}'", "INFO")
        
        action_taken_message = f"Loop {current_loop_cycle}: Action: '{task_description}'."
        task_successfully_completed = False

        # --- Agent-Specific Logic Execution ---
        if self.id == "agent-4": # Storyweaver - Real execution
            # Ensure the task description from YAML is relevant to calling chronicle_conversations.py
            # For example, the first task for agent-4 is "Use chronicle_conversations.py..."
            if "chronicle_conversations.py" in task_description.lower():
                log_message(f"Agent {self.codename} attempting to execute {CHRONICLE_CONVERSATIONS_SCRIPT_PATH}", "INFO")
                try:
                    # We assume chronicle_conversations.py is in the SCRIPT_DIR and executable with python
                    # It should handle its own output to runtime/dreamscape_output/ as per its prompt
                    process = subprocess.run(
                        ["python", CHRONICLE_CONVERSATIONS_SCRIPT_PATH],
                        capture_output=True, text=True, check=False, # check=False to handle non-zero exits manually
                        cwd=WORKSPACE_ROOT # Run from workspace root if script relies on relative paths from there
                    )
                    if process.returncode == 0:
                        action_taken_message += f" Successfully executed {CHRONICLE_CONVERSATIONS_SCRIPT_PATH}."
                        log_message(f"Agent {self.codename} successfully executed {CHRONICLE_CONVERSATIONS_SCRIPT_PATH}. Output:\n{process.stdout}", "INFO")
                        if process.stderr:
                             log_message(f"Agent {self.codename} execution of {CHRONICLE_CONVERSATIONS_SCRIPT_PATH} produced stderr:\n{process.stderr}", "WARNING")
                        # Actual saga details for mapping would ideally come from stdout or a file written by the script
                        # For now, we'll use a summary.
                        saga_details_for_mapping = f"Saga generated by {self.codename} via {CHRONICLE_CONVERSATIONS_SCRIPT_PATH}. Output: {process.stdout[:100]}..."
                        map_saga_output_to_task(saga_details_for_mapping, self.id)
                        task_successfully_completed = True
                    else:
                        action_taken_message += f" Failed to execute {CHRONICLE_CONVERSATIONS_SCRIPT_PATH}. Return code: {process.returncode}."
                        log_message(f"Agent {self.codename} failed to execute {CHRONICLE_CONVERSATIONS_SCRIPT_PATH}. Error:\n{process.stderr}\nStdout:\n{process.stdout}", "ERROR")
                        self.status = "error_script_failed"
                except FileNotFoundError:
                    action_taken_message += f" Script {CHRONICLE_CONVERSATIONS_SCRIPT_PATH} not found."
                    log_message(f"Script {CHRONICLE_CONVERSATIONS_SCRIPT_PATH} not found for Agent {self.codename}.", "CRITICAL")
                    self.status = "error_script_not_found"
                except Exception as e:
                    action_taken_message += f" Exception during execution of {CHRONICLE_CONVERSATIONS_SCRIPT_PATH}: {e}"
                    log_message(f"Agent {self.codename} encountered an exception trying to run {CHRONICLE_CONVERSATIONS_SCRIPT_PATH}: {e}", "ERROR")
                    self.status = "error_exception"
            else:
                action_taken_message += " Task description did not match expected trigger for chronicle_conversations.py. Simulating."
                log_message(f"Agent {self.codename} simulating task: {task_description}", "SIMULATION")
                task_successfully_completed = True # Simulate success for non-script tasks for now

        # --- Placeholder for other agents' real logic (Pathfinder, etc.) ---
        elif self.id == "agent-1": # Pathfinder - Example for future
            if "find_orphans.py" in task_description.lower():
                action_taken_message += " Would call 'find_orphans.py' here."
                log_message(f"Agent {self.codename} simulating call to 'find_orphans.py'", "SIMULATION")
                # result = call_script('find_orphans.py')
                # process_pathfinder_output(result)
                task_successfully_completed = True # Simulate success
            else:
                action_taken_message += " Simulating generic task."
                log_message(f"Agent {self.codename} simulating task: {task_description}", "SIMULATION")
                task_successfully_completed = True # Simulate success

        else: # Default simulation for other agents
            action_taken_message += " Status: completed simulation."
            log_message(f"Agent {self.codename} simulating task: {task_description}", "SIMULATION")
            task_successfully_completed = True # Simulate success
        # --- End Agent-Specific Logic ---

        if task_successfully_completed and self.status not in ["error_script_failed", "error_script_not_found", "error_exception"]:
            self.status = "idle" # Reset status after task completion/simulation if no specific error status was set
        
        self.write_to_devlog(action_taken_message + f" Agent Status: {self.status}")
        
        if self.tasks_from_yaml:
            self.current_task_index = (self.current_task_index + 1) % len(self.tasks_from_yaml)
        log_message(f"Agent {self.codename} finished task. Status: {self.status}", "DEBUG")

    def write_to_devlog(self, message):
        """Writes a message to the agent's dedicated devlog file."""
        timestamp = datetime.datetime.now().isoformat()
        try:
            with open(self.devlog_path, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            log_message(f"Error writing to devlog for agent {self.id} at {self.devlog_path}: {e}", "ERROR")

    def award_points(self, points_to_add, reason=""):
        """Awards points to the agent and logs the event."""
        self.points += points_to_add
        log_message(f"Agent {self.codename} awarded {points_to_add} points. Reason: {reason}. Total: {self.points}", "INFO")
        self.write_to_devlog(f"Awarded {points_to_add} points. Reason: {reason}. New total: {self.points}")

# --- Controller Functions ---
def load_deployment_config(config_path):
    """Loads the agent deployment configuration from the specified YAML file."""
    log_message(f"Loading deployment config from: {config_path}", "DEBUG")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        log_message(f"Deployment config file not found at {config_path}", "CRITICAL")
        return None
    except yaml.YAMLError as e:
        log_message(f"Error parsing deployment config YAML at {config_path}: {e}", "CRITICAL")
        return None
    except Exception as e:
        log_message(f"Unexpected error loading deployment config from {config_path}: {e}", "CRITICAL")
        return None

def initialize_agents(config):
    """Initializes Agent objects based on the deployment configuration."""
    agents = []
    if not config or 'agents' not in config:
        log_message("No 'agents' section found in deployment configuration.", "CRITICAL")
        return agents

    for agent_config in config.get('agents', []):
        agent_id = agent_config.get('id')
        if not agent_id:
            log_message(f"Agent configuration missing 'id': {agent_config}", "WARNING")
            continue
        
        # Construct prompt path: e.g., agent-1 -> runtime/.../agent-1/prompt_agent1.md
        agent_num_suffix = agent_id.split('-')[-1] # Extracts '1' from 'agent-1'
        prompt_filename = f"prompt_agent{agent_num_suffix}.md"
        prompt_path = os.path.join(AGENT_MAILBOX_DIR, agent_id, prompt_filename)

        agent = Agent(
            agent_id=agent_id,
            codename=agent_config.get('codename', f"UnnamedAgent-{agent_id}"),
            role=agent_config.get('role', 'Undefined Role'),
            tasks_from_yaml=agent_config.get('tasks', []),
            prompt_path=prompt_path
        )
        agents.append(agent)
        log_message(f"Initialized Agent: {agent.codename} ({agent.id}) with prompt: {prompt_path}", "INFO")
    return agents

def update_agent_points_file(agents):
    """Writes the current points of all agents to the agent_points.json file."""
    points_data = {
        agent.id: {
            "codename": agent.codename,
            "points": agent.points,
            "role": agent.role
        } for agent in agents
    }
    try:
        with open(AGENT_POINTS_PATH, 'w', encoding='utf-8') as f:
            json.dump(points_data, f, indent=2)
        log_message(f"Agent points updated at {AGENT_POINTS_PATH}", "DEBUG")
    except Exception as e:
        log_message(f"Error writing agent points file to {AGENT_POINTS_PATH}: {e}", "ERROR")

def log_deployment_status(loop_cycle, agents, deployment_config, status="running"):
    """Logs the current status of the deployment and all agents to deployment_status.yaml."""
    status_data = {
        'deployment_name': deployment_config.get('deployment_name', 'N/A'),
        'controller_script_version': "0.1.0", # Example version
        'timestamp': datetime.datetime.now().isoformat(),
        'current_loop_cycle': loop_cycle,
        'status': status,
        'agents_count': len(agents),
        'agents': [
            {
                'id': agent.id,
                'codename': agent.codename,
                'role': agent.role,
                'status': agent.status,
                'points': agent.points,
                'current_task_description': agent.tasks_from_yaml[agent.current_task_index] if agent.tasks_from_yaml else "N/A",
                'devlog_path': agent.devlog_path
            } for agent in agents
        ]
    }
    try:
        with open(DEPLOYMENT_STATUS_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(status_data, f, sort_keys=False, indent=2, default_flow_style=False)
        log_message(f"Deployment status logged to {DEPLOYMENT_STATUS_PATH}", "DEBUG")
    except Exception as e:
        # Use print here as log_message might also fail if disk is full, etc.
        print(f"CRITICAL: Error writing deployment status to {DEPLOYMENT_STATUS_PATH}: {e}")


def map_saga_output_to_task(saga_details, source_agent_id):
    """
    Placeholder for mapping saga outputs (or other agent outputs) to actionable tasks.
    This function would typically interact with a task management system or update a backlog.
    """
    log_message(f"Agent {source_agent_id} produced output. Simulating mapping to task: '{str(saga_details)[:70]}...'", "INFO")
    
    arc_entry = {
        'timestamp': datetime.datetime.now().isoformat(),
        'source_agent_id': source_agent_id,
        'output_summary': str(saga_details)[:200] + "...", # Store a brief summary
        'linked_task_id': f"task_{source_agent_id}_{int(time.time())}", # Example generated task ID
        'status': 'pending_review' # Example status
    }
    try:
        arc_map_data = []
        if os.path.exists(DREAMSCAPE_ARC_MAP_PATH):
            try:
                with open(DREAMSCAPE_ARC_MAP_PATH, 'r', encoding='utf-8') as f:
                    arc_map_data = json.load(f)
                    if not isinstance(arc_map_data, list): # Ensure it's a list
                        log_message(f"Warning: {DREAMSCAPE_ARC_MAP_PATH} does not contain a list. Reinitializing.", "WARNING")
                        arc_map_data = []
            except json.JSONDecodeError:
                log_message(f"Warning: {DREAMSCAPE_ARC_MAP_PATH} is not valid JSON. Reinitializing.", "WARNING")
                arc_map_data = []
        
        arc_map_data.append(arc_entry)
        with open(DREAMSCAPE_ARC_MAP_PATH, 'w', encoding='utf-8') as f:
            json.dump(arc_map_data, f, indent=2)
        log_message(f"Saga/output map updated at {DREAMSCAPE_ARC_MAP_PATH}", "DEBUG")
    except Exception as e:
        log_message(f"Error updating saga/output map at {DREAMSCAPE_ARC_MAP_PATH}: {e}", "ERROR")

# --- Main Controller Logic ---
def dreamscape_controller_main():
    """Main function to orchestrate the Dreamscape agent swarm."""
    
    # Initial setup: ensure essential directories exist
    ensure_dir_exists(LOG_DIR)
    ensure_dir_exists(OUTPUT_DIR)
    ensure_dir_exists(AGENT_DEVLOG_DIR)

    log_message("--- Dreamscape Octacore Controller Initializing ---", "INFO")
    
    deployment_config = load_deployment_config(DEPLOYMENT_CONFIG_PATH)
    if not deployment_config:
        log_message("Halting: Deployment configuration could not be loaded.", "CRITICAL")
        return

    agents = initialize_agents(deployment_config)
    if not agents:
        log_message("Halting: No agents were initialized.", "CRITICAL")
        return

    # Initialize persistent state files if they don't exist
    if not os.path.exists(AGENT_POINTS_PATH):
        update_agent_points_file(agents) # Create with initial (0) points
    if not os.path.exists(DREAMSCAPE_ARC_MAP_PATH):
        with open(DREAMSCAPE_ARC_MAP_PATH, 'w', encoding='utf-8') as f:
            json.dump([], f) # Initialize with an empty list

    # Controller settings from deployment config, with defaults
    controller_settings = deployment_config.get("controller_settings", {})
    max_loops = controller_settings.get("max_loops", 5) # Default to 5 loops for testing
    loop_delay_seconds = controller_settings.get("loop_delay_seconds", 2) # Default to 2s delay

    log_message(f"Controller configured: Max Loops={max_loops}, Loop Delay={loop_delay_seconds}s", "INFO")
    log_message(f"Found {len(agents)} agents ready for deployment.", "INFO")

    current_loop_cycle = 0
    try:
        while current_loop_cycle < max_loops:
            current_loop_cycle += 1
            log_message(f"--- Starting Loop Cycle: {current_loop_cycle}/{max_loops} ---", "HEADING") # Custom level for visibility
            log_deployment_status(current_loop_cycle, agents, deployment_config, status="running_cycle")

            for agent in agents:
                agent.perform_task(current_loop_cycle)

                # --- Example: Conditional point awarding and output mapping ---
                # This section should be customized based on actual agent outputs and goals
                if agent.id == "agent-4" and agent.status == "idle": # Storyweaver successfully completed its task
                    # Award points only if the script execution was intended and successful
                    current_task_desc_for_agent4 = agent.tasks_from_yaml[ (agent.current_task_index -1 + len(agent.tasks_from_yaml)) % len(agent.tasks_from_yaml) ] # Get the task that was just performed
                    if "chronicle_conversations.py" in current_task_desc_for_agent4.lower():
                         agent.award_points(150, f"Successfully executed chronicle_conversations.py in loop {current_loop_cycle}")
                    # map_saga_output_to_task is now called within perform_task for agent-4 upon success
                
                elif agent.id == "agent-1" and agent.status == "idle": # Pathfinder completed simulation
                     # Get the task that was just performed
                     current_task_desc_for_agent1 = agent.tasks_from_yaml[ (agent.current_task_index -1 + len(agent.tasks_from_yaml)) % len(agent.tasks_from_yaml) ]
                     if "find_orphans.py" in current_task_desc_for_agent1.lower():
                        agent.award_points(20, f"Simulated find_orphans.py scan in loop {current_loop_cycle}")
                # Add more specific conditions for other agents as needed
                # --- End Example ---

            update_agent_points_file(agents) # Update points after all agents in a cycle have acted
            
            log_message(f"--- Completed Loop Cycle: {current_loop_cycle}/{max_loops} ---", "HEADING")
            if current_loop_cycle < max_loops:
                log_message(f"Delaying for {loop_delay_seconds} seconds before next loop...", "DEBUG")
                time.sleep(loop_delay_seconds)

        log_message(f"All {max_loops} loop cycles completed.", "INFO")
        log_deployment_status(current_loop_cycle, agents, deployment_config, status="completed_all_loops")

    except KeyboardInterrupt:
        log_message("Controller shutdown initiated by user (KeyboardInterrupt).", "WARNING")
        log_deployment_status(current_loop_cycle, agents, deployment_config, status="user_interrupted")
    except Exception as e:
        log_message(f"An unexpected error occurred in the main controller loop: {e}", "CRITICAL")
        log_deployment_status(current_loop_cycle, agents, deployment_config, status="controller_error")
        # Consider re-raising or more detailed error handling here for critical failures
    finally:
        log_message("--- Dreamscape Octacore Controller Shutting Down ---", "INFO")
        update_agent_points_file(agents) # Ensure final points are saved
        log_message("Controller shutdown complete.", "INFO")

if __name__ == "__main__":
    dreamscape_controller_main() 