import yaml
import os
import logging
import time
import datetime # For timestamped logging
from pathlib import Path
import subprocess # To simulate agent execution, or actually run them
import sys # For stderr

# --- Configuration ---
# Assumes the script is run from the workspace root where 'runtime' is a subdirectory.
BASE_DIR = Path(".").resolve()
DEPLOYMENT_CONFIG_PATH = BASE_DIR / "runtime/agent_comms/deployments/multi_agent_deployment.yaml"
AGENT_MAILBOX_DIR = BASE_DIR / "runtime/agent_comms/agent_mailboxes"
AGENT_DEVLOG_DIR = BASE_DIR / "runtime/devlog/agents"
CONTROLLER_LOG_FILE = BASE_DIR / "runtime/devlog/dreamscape_controller.log"
TASK_BACKLOG_FILE = BASE_DIR / "task_backlog.json" # Path for agents to log to

# Define a placeholder for how an agent might "run".
# In a real system, this would involve more complex IPC or process management.
AGENT_SCRIPT_PLACEHOLDER = "python" # Command to run a generic python agent script
AGENT_MAIN_SCRIPT_NAME = "agent_main.py" # A hypothetical main script for each agent

# --- Logging Setup ---
def setup_logging():
    """Sets up global logging for the controller."""
    # Ensure devlog directories exist first
    AGENT_DEVLOG_DIR.mkdir(parents=True, exist_ok=True)
    if CONTROLLER_LOG_FILE.parent != AGENT_DEVLOG_DIR: # Ensure controller log dir also exists
        CONTROLLER_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    AGENT_MAILBOX_DIR.mkdir(parents=True, exist_ok=True) # Ensure mailboxes exist
    if TASK_BACKLOG_FILE.exists() and TASK_BACKLOG_FILE.parent != BASE_DIR:
        TASK_BACKLOG_FILE.parent.mkdir(parents=True, exist_ok=True)


    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout), # Log to console
            logging.FileHandler(CONTROLLER_LOG_FILE)
        ]
    )
    logger.info(f"Logging initialized. Controller logs at: {CONTROLLER_LOG_FILE}")
    logger.info(f"Agent devlogs will be in: {AGENT_DEVLOG_DIR}")

logger = logging.getLogger("DreamscapeController")

# --- Agent Representation ---
class AgentInstance:
    def __init__(self, agent_id, codename, role, tasks, prompt_content, devlog_path):
        self.agent_id = agent_id
        self.codename = codename
        self.role = role
        self.tasks = tasks
        self.prompt_content = prompt_content if prompt_content else "No prompt content loaded."
        self.devlog_path = devlog_path
        self.process = None # To store the subprocess.Popen object
        self.status = "pending" # pending, launching, running, completed, failed, stopped, killed

    def __str__(self):
        return f"Agent(id={self.agent_id}, codename='{self.codename}', role='{self.role}', status='{self.status}')"

    def launch(self):
        """
        Simulates launching the agent and initializes its devlog.
        Actual agent execution logic (e.g., subprocess) would go here.
        """
        self.status = "launching"
        logger.info(f"Initializing and launching {self}...")
        try:
            self.devlog_path.parent.mkdir(parents=True, exist_ok=True) # Ensure agent's devlog dir exists
            with open(self.devlog_path, 'w', encoding='utf-8') as f: # Overwrite previous devlog on new launch
                f.write(f"--- {datetime.datetime.now(datetime.timezone.utc).isoformat()} - AGENT {self.codename} INITIALIZED BY CONTROLLER ---\n")
                f.write(f"ID: {self.agent_id}\n")
                f.write(f"Codename: {self.codename}\n")
                f.write(f"Role: {self.role}\n\n")
                f.write("Initial Tasks:\n")
                if self.tasks:
                    for task in self.tasks:
                        f.write(f"  - {task}\n")
                else:
                    f.write("  - No specific tasks assigned in deployment config.\n")
                f.write("\n--- PROMPT ---\n")
                f.write(self.prompt_content + "\n")
                f.write("---------------\n\n")
            logger.info(f"Devlog for {self.codename} initialized at {self.devlog_path}")

            # Placeholder for actual agent execution:
            # agent_script_to_run = AGENT_MAILBOX_DIR / self.agent_id / AGENT_MAIN_SCRIPT_NAME # Example
            # if agent_script_to_run.exists():
            #   logger.info(f"Attempting to start subprocess for {self.codename} with script {agent_script_to_run}...")
            #   self.process = subprocess.Popen([AGENT_SCRIPT_PLACEHOLDER, str(agent_script_to_run), self.agent_id, str(self.devlog_path)],
            #                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            #   self.status = "running"
            #   logger.info(f"{self.codename} subprocess started (PID: {self.process.pid}).")
            # else:
            #   logger.warning(f"Agent script {agent_script_to_run} not found for {self.codename}. Simulating run.")
            #   self.status = "simulated_running" # Mark as simulated
            
            # For now, purely simulate without starting a subprocess
            logger.info(f"Simulated launch for {self.codename}. In a real system, a subprocess would be started here.")
            self.status = "running" # For simulation, directly transition to "running"
            
        except Exception as e:
            logger.error(f"Failed to initialize/launch {self.codename}: {e}", exc_info=True)
            self.status = "failed_to_launch"
        return self.status in ["running", "simulated_running"]


    def monitor(self):
        """Monitors the agent's status. Adapts if subprocess is used or pure simulation."""
        if self.process and self.status == "running":
            poll_result = self.process.poll()
            if poll_result is None:
                # Still running
                pass
            else:
                try:
                    stdout, stderr = self.process.communicate()
                    log_output = f"Agent {self.codename} (PID: {self.process.pid}) exited with code {poll_result}.\n"
                    log_output += f"STDOUT:\n{stdout.decode(errors='replace')}\n"
                    log_output += f"STDERR:\n{stderr.decode(errors='replace')}\n"
                    logger.info(log_output)
                    with open(self.devlog_path, 'a', encoding='utf-8') as f:
                        f.write(f"\n--- AGENT PROCESS EXITED ({datetime.datetime.now(datetime.timezone.utc).isoformat()}) ---\n")
                        f.write(log_output)

                    if poll_result == 0:
                        self.status = "completed"
                        logger.info(f"Agent {self.codename} completed successfully.")
                    else:
                        self.status = "failed"
                        logger.error(f"Agent {self.codename} failed with return code {poll_result}.")
                except Exception as e:
                    logger.error(f"Error during agent process communication for {self.codename}: {e}", exc_info=True)
                    self.status = "failed" # Mark as failed if communication error occurs
                finally:
                    self.process = None # Clear process once it's finished or if an error occurred

        # For simulated agents, they remain 'running' until explicitly stopped or complete by other logic.
        return self.status

    def stop(self):
        """Stops the agent, terminating subprocess if it exists."""
        logger.info(f"Attempting to stop agent {self.codename} (current status: {self.status})...")
        if self.process and self.process.poll() is None: # If there's an active subprocess
            try:
                logger.info(f"Terminating subprocess for {self.codename} (PID: {self.process.pid})...")
                self.process.terminate()
                try:
                    self.process.wait(timeout=5) # wait for termination
                    logger.info(f"Agent {self.codename} subprocess terminated gracefully.")
                    self.status = "stopped"
                except subprocess.TimeoutExpired:
                    logger.warning(f"Agent {self.codename} subprocess did not terminate in time, attempting to kill.")
                    self.process.kill()
                    self.process.wait() # Wait for kill
                    logger.info(f"Agent {self.codename} subprocess killed.")
                    self.status = "killed"
            except Exception as e:
                logger.error(f"Error stopping/terminating subprocess for {self.codename}: {e}", exc_info=True)
                self.status = "error_stopping"
        elif self.status in ["running", "simulated_running", "launching", "pending"]: # For simulated or non-process agents
             logger.info(f"Marking agent {self.codename} as stopped (was {self.status}).")
             self.status = "stopped"
        else:
             logger.info(f"Agent {self.codename} already in a terminal state ({self.status}) or no active process.")
        return self.status in ["stopped", "killed", "completed", "failed"]

# --- Controller Logic ---
def load_deployment_config(config_path: Path) -> dict | None:
    """Loads the agent deployment YAML configuration."""
    logger.info(f"Loading deployment configuration from: {config_path}")
    if not config_path.exists():
        logger.error(f"Deployment configuration file not found: {config_path}")
        return None
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"Successfully loaded deployment: {config.get('deployment_name', 'Unnamed Deployment')}")
        return config
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error loading deployment configuration: {e}", exc_info=True)
        return None

def load_agent_prompt(agent_id: str, codename: str) -> str | None:
    """Loads the prompt for a given agent from its mailbox."""
    prompt_filename = f"prompt_{agent_id}.md"
    prompt_path = AGENT_MAILBOX_DIR / agent_id / prompt_filename
    
    logger.info(f"Attempting to load prompt for agent {codename} (ID: {agent_id}) from: {prompt_path}")
    if not prompt_path.exists():
        logger.error(f"Prompt file not found for agent {codename} (ID: {agent_id}) at {prompt_path}.")
        return f"ERROR: Prompt file not found at {prompt_path}. Agent cannot be properly initialized."
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
        logger.info(f"Successfully loaded prompt for agent {codename} (ID: {agent_id}). Length: {len(prompt_content)} chars.")
        return prompt_content
    except Exception as e:
        logger.error(f"Error loading prompt for agent {codename} (ID: {agent_id}): {e}", exc_info=True)
        return f"ERROR: Could not load prompt from {prompt_path}: {e}"

def initialize_agents(config: dict) -> list[AgentInstance]:
    """Initializes AgentInstance objects based on the deployment configuration."""
    agents = []
    if not config or 'agents' not in config or not isinstance(config['agents'], list):
        logger.error("No 'agents' list found or format is incorrect in deployment configuration.")
        return agents

    for agent_config in config['agents']:
        if not isinstance(agent_config, dict):
            logger.warning(f"Skipping invalid agent config item (not a dict): {agent_config}")
            continue

        agent_id = agent_config.get('id')
        codename = agent_config.get('codename', f"Agent_{agent_id if agent_id else 'Unknown'}")
        
        if not agent_id:
            logger.warning(f"Skipping agent with missing ID in config: {agent_config}")
            continue

        role = agent_config.get('role', 'N/A')
        tasks = agent_config.get('tasks', [])
        prompt_content = load_agent_prompt(agent_id, codename)

        # Use codename for devlog if available and valid for filename, else agent_id
        devlog_safe_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in codename)
        devlog_filename = f"{devlog_safe_name}_{agent_id}.md"
        devlog_path = AGENT_DEVLOG_DIR / devlog_filename

        agent = AgentInstance(
            agent_id=agent_id,
            codename=codename,
            role=role,
            tasks=tasks,
            prompt_content=prompt_content, # Will contain error message if load failed
            devlog_path=devlog_path
        )
        agents.append(agent)
        logger.info(f"Prepared agent for launch: {agent.codename} (ID: {agent.agent_id})")
    return agents

def run_controller():
    """Main controller loop to manage agents."""
    setup_logging() # Call this first
    logger.info(f"--- Dreamscape Controller Initializing (Version {datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')}) ---")
    logger.info(f"Workspace Base Directory: {BASE_DIR.resolve()}")
    logger.info(f"Deployment Config Path: {DEPLOYMENT_CONFIG_PATH.resolve()}")
    logger.info(f"Agent Mailbox Directory: {AGENT_MAILBOX_DIR.resolve()}")
    logger.info(f"Agent DevLog Directory: {AGENT_DEVLOG_DIR.resolve()}")
    logger.info(f"Controller Log File: {CONTROLLER_LOG_FILE.resolve()}")

    deployment_config = load_deployment_config(DEPLOYMENT_CONFIG_PATH)
    if not deployment_config:
        logger.critical("Failed to load deployment configuration. Controller cannot start. Please check config path and format.")
        return

    active_agents = initialize_agents(deployment_config)
    if not active_agents:
        logger.warning("No agents initialized based on the configuration. Exiting.")
        return

    logger.info(f"--- Launching {len(active_agents)} Agents as per '{deployment_config.get('deployment_name', 'Unnamed Deployment')}' ---")
    launched_count = 0
    for agent in active_agents:
        if agent.prompt_content and "ERROR: Prompt file not found" in agent.prompt_content:
             logger.error(f"Cannot launch agent {agent.codename} (ID: {agent.agent_id}) due to missing prompt. {agent.prompt_content}")
             agent.status = "failed_to_launch"
        elif agent.launch(): # launch() now also initializes devlog
            launched_count +=1
    
    if launched_count == 0 and active_agents:
        logger.critical("No agents were successfully launched. Controller will exit.")
        return

    logger.info(f"--- {launched_count}/{len(active_agents)} agents launched (simulated/actual). Entering monitoring loop (Ctrl+C to stop). ---")
    
    try:
        simulation_cycles = 0
        max_simulation_cycles = 5 # Exit after N cycles if all agents are simulated and don't self-terminate
        
        while True:
            active_process_found = False
            all_simulated_and_running = True # Assume true, prove false
            any_agent_still_active = False # Tracks if any agent is in a non-terminal state

            for agent in active_agents:
                agent.monitor() # Update status based on subprocess or simulation state
                if agent.process and agent.status == "running":
                    active_process_found = True
                if not (agent.process or agent.status in ["running", "simulated_running"]):
                    all_simulated_and_running = False
                
                if agent.status not in ["completed", "failed", "stopped", "killed", "failed_to_launch"]:
                    any_agent_still_active = True

            if not any_agent_still_active:
                 logger.info("All agents have reached a terminal state (completed, failed, stopped, etc.). Exiting monitoring loop.")
                 break
            
            if all_simulated_and_running and not active_process_found:
                simulation_cycles +=1
                logger.info(f"All active agents are simulated. Cycle {simulation_cycles}/{max_simulation_cycles}.")
                if simulation_cycles >= max_simulation_cycles:
                    logger.info(f"Reached max simulation cycles ({max_simulation_cycles}). Stopping simulated agents.")
                    break # Exit outer while loop

            time.sleep(5)  # Monitoring interval

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Initiating graceful shutdown...")
    except Exception as e:
        logger.critical(f"Unexpected error in controller main loop: {e}", exc_info=True)
    finally:
        logger.info("--- Controller Shutting Down ---")
        for agent in active_agents:
            logger.info(f"Requesting stop for {agent.codename}...")
            agent.stop()
        # Brief pause to allow logs to flush
        time.sleep(1)
        logger.info(f"All agents instructed to stop. Dreamscape Controller version {datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')} exiting.")

if __name__ == "__main__":
    run_controller() 