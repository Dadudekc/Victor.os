"""
Dream.OS Autonomy Engine

A unified system for managing agent interactions, GUI automation, and autonomy features.
Consolidates all pyautogui functionality into a single, modular system.
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pyautogui
import pyperclip
from rich.console import Console
from rich.logging import RichHandler

# Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("autonomy_engine")
console = Console()

class AgentState(Enum):
    """Agent state enumeration."""
    INITIALIZING = "INITIALIZING"
    ONBOARDING = "ONBOARDING"
    READY = "READY"  # Test might use this instead of RUNNING
    BUSY = "BUSY"
    ERROR = "ERROR"
    RESETTING = "RESETTING"
    UNINITIALIZED = "UNINITIALIZED"
    RUNNING = "RUNNING" # ADDED for test compatibility if strictly needed

@dataclass
class Message:
    """Message data structure."""
    id: str
    content: str
    timestamp: str
    priority: int = 0
    metadata: Dict[str, Any] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create a Message from a dictionary."""
        # Ensure timestamp is valid ISO format, otherwise use current time
        raw_timestamp = data.get('timestamp', datetime.utcnow().isoformat())
        try:
            datetime.fromisoformat(raw_timestamp.replace('Z', '+00:00')) # Validate format
            valid_timestamp = raw_timestamp
        except (ValueError, AttributeError):
            logger.warning(f"Invalid timestamp format '{raw_timestamp}'. Using current UTC time.")
            valid_timestamp = datetime.utcnow().isoformat()

        return cls(
            id=data.get('id', str(time.time())), # Consider using uuid
            content=data.get('content', ''),
            timestamp=valid_timestamp,
            priority=data.get('priority', 0),
            metadata=data.get('metadata', {})
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Message to dictionary."""
        return {
            'id': self.id,
            'content': self.content,
            'timestamp': self.timestamp,
            'priority': self.priority,
            'metadata': self.metadata or {}
        }

@dataclass
class Task:
    """Task data structure."""
    id: str
    title: str
    description: str
    status: str
    progress: float = 0.0
    created_at: str = None
    updated_at: str = None
    metadata: Dict[str, Any] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create a Task from a dictionary."""
        return cls(
            id=data.get('id', f"task-{int(time.time())}"),
            title=data.get('title', 'Untitled Task'),
            description=data.get('description', ''),
            status=data.get('status', 'pending'),
            progress=data.get('progress', 0.0),
            created_at=data.get('created_at', datetime.utcnow().isoformat()),
            updated_at=data.get('updated_at', datetime.utcnow().isoformat()),
            metadata=data.get('metadata', {})
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Task to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'progress': self.progress,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'metadata': self.metadata or {}
        }

class AutonomyEngine:
    """Core autonomy engine for managing agent interactions."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the autonomy engine."""
        self.config_path = config_path or Path("runtime/config/autonomy_config.json")
        self.coords_path = Path("runtime/config/cursor_agent_coords.json")
        self.mailbox_path = Path("runtime/agent_comms/agent_mailboxes")
        self.onboarding_path = Path("runtime/onboarding")
        
        # Load configuration
        self.config = self._load_config()
        self.coords = self._load_coordinates()
        
        # Initialize state tracking
        self.agent_states: Dict[str, AgentState] = {}
        self.last_actions: Dict[str, float] = {}
        self.task_progress: Dict[str, Dict[str, float]] = {}
        
        # Timing configuration
        self.timings = {
            "initial_delay": 1.5,
            "paste_delay": 0.5,
            "agent_delay": 8.0,
            "reset_delay": 5.0,
            "error_delay": 3.0
        }
        
        # Initialize all agents
        self._initialize_agents()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load autonomy configuration."""
        try:
            if not self.config_path.exists():
                logger.warning(f"Config not found: {self.config_path}, using defaults")
                return {}
            return json.loads(self.config_path.read_text())
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def _load_coordinates(self) -> Dict[str, Dict[str, Dict[str, int]]]:
        """Load agent coordinates."""
        try:
            if not self.coords_path.exists():
                logger.error(f"Coordinates not found: {self.coords_path}")
                return {}
            return json.loads(self.coords_path.read_text())
        except Exception as e:
            logger.error(f"Error loading coordinates: {e}")
            return {}
    
    def _initialize_agents(self) -> None:
        """Initialize all known agents."""
        for agent_id in self.coords.keys():
            self.agent_states[agent_id] = AgentState.UNINITIALIZED
            self.last_actions[agent_id] = time.time()
            self.task_progress[agent_id] = {}
    
    def get_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Get current state of an agent. 
        Returns dict: {"operation_state": AgentState.value, "last_updated": timestamp, "agent_id": agent_id}
        """
        state_enum = self.agent_states.get(agent_id, AgentState.ERROR)
        return {
            "operation_state": state_enum.value, # Return the string value of the enum
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.last_actions.get(agent_id, time.time()))),
            "agent_id": agent_id
        }
    
    def set_agent_state(self, agent_id: str, state_enum: AgentState) -> None:
        """Set state of an agent using AgentState enum."""
        self.agent_states[agent_id] = state_enum
        self.last_actions[agent_id] = time.time()
        
        # Update status.json
        try:
            agent_mailbox = self.mailbox_path / f"agent-{agent_id}"
            status_path = agent_mailbox / "status.json"
            if status_path.exists(): # Only update if status.json exists
                status_data = json.loads(status_path.read_text())
                status_data["status"] = state_enum.value # Store enum's string value
                status_data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                status_path.write_text(json.dumps(status_data, indent=2))
        except Exception as e:
            logger.error(f"Error updating status.json for {agent_id}: {e}")
    
    def get_mailbox(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get an agent's mailbox contents."""
        if agent_id not in self.coords:
            logger.error(f"❌ Unknown agent: {agent_id}")
            return []
            
        try:
            agent_mailbox = self.mailbox_path / f"agent-{agent_id}"
            inbox_path = agent_mailbox / "inbox"
            
            if not inbox_path.exists():
                return []
                
            messages = []
            for msg_file in inbox_path.glob("*.json"):
                try:
                    msg_data = json.loads(msg_file.read_text())
                    message = Message.from_dict(msg_data)
                    messages.append(message.to_dict())
                except Exception as e:
                    logger.error(f"Error reading message {msg_file}: {e}")
                    continue
                    
            return sorted(messages, key=lambda x: x['timestamp'])
        except Exception as e:
            logger.error(f"Error reading mailbox for {agent_id}: {e}")
            return []
    
    def get_agent_tasks(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get an agent's tasks.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            List[Dict[str, Any]]: List of tasks
        """
        if agent_id not in self.coords:
            logger.error(f"❌ Unknown agent: {agent_id}")
            return []
            
        try:
            agent_mailbox = self.mailbox_path / f"agent-{agent_id}"
            tasks_path = agent_mailbox / "tasks"
            
            if not tasks_path.exists():
                return []
                
            tasks = []
            for task_file in tasks_path.glob("task-*.json"):
                try:
                    task_data = json.loads(task_file.read_text())
                    task = Task.from_dict(task_data)
                    tasks.append(task.to_dict())
                except Exception as e:
                    logger.error(f"Error reading task {task_file}: {e}")
                    continue
                    
            return sorted(tasks, key=lambda x: x['created_at'])
        except Exception as e:
            logger.error(f"Error reading tasks for {agent_id}: {e}")
            return []
    
    def reset_mailbox(self, agent_id: str) -> bool:
        """Reset an agent's mailbox to initial state.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            bool: True if reset was successful, False otherwise
        """
        logger.info(f"Attempting to reset mailbox for {agent_id}") # DEBUG
        if agent_id not in self.coords:
            logger.error(f"❌ Unknown agent during reset: {agent_id}")
            return False
            
        try:
            agent_mailbox_dir_name = f"agent-{agent_id}"
            agent_mailbox = self.mailbox_path / agent_mailbox_dir_name
            logger.info(f"Target mailbox path for reset: {agent_mailbox}") # DEBUG

            if not agent_mailbox.exists():
                logger.warning(f"Mailbox directory {agent_mailbox} does not exist. Nothing to reset for files.")
            else:
                # Clean up all message directories
                for dir_name in ["inbox", "outbox", "processed", "tasks"]:
                    dir_path = agent_mailbox / dir_name
                    if dir_path.exists():
                        files_before_delete = list(dir_path.glob("*.json"))
                        logger.info(f"Files in {dir_path} before delete: {files_before_delete}") # DEBUG
                        for file_item in files_before_delete:
                            try:
                                file_item.unlink()
                                logger.info(f"Deleted {file_item}") # DEBUG
                            except OSError as e:
                                logger.error(f"Error deleting file {file_item}: {e}")
                        files_after_delete = list(dir_path.glob("*.json"))
                        logger.info(f"Files in {dir_path} after delete: {files_after_delete}") # DEBUG
                    else:
                        logger.info(f"Directory {dir_path} does not exist. Skipping delete.") # DEBUG
                        
            # Always re-initialize to ensure correct structure and default status.json
            # This will create dirs if they don't exist and overwrite status.json
            self.initialize_mailbox(agent_id) # This sets status to UNINITIALIZED
                            
            # Reset agent state in memory
            self.agent_states[agent_id] = AgentState.UNINITIALIZED
            self.last_actions[agent_id] = time.time()
            self.task_progress[agent_id] = {}
            
            logger.info(f"✅ Successfully reset mailbox for {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error during full reset_mailbox for {agent_id}: {e}")
            return False
    
    def send_task(self, agent_id: str, task: Dict[str, Any]) -> bool:
        """Send a task to an agent.
        
        Args:
            agent_id: The ID of the agent to send to
            task: The task data
            
        Returns:
            bool: True if task was sent successfully, False otherwise
        """
        if agent_id not in self.coords:
            logger.error(f"❌ Unknown agent: {agent_id}")
            return False
            
        try:
            # Validate task
            if not task or not isinstance(task, dict):
                logger.error("Invalid task: cannot be empty")
                return False
                
            required_fields = ["title", "description"]
            missing_fields = [field for field in required_fields if field not in task]
            if missing_fields:
                logger.error(f"Invalid task: missing required fields ({', '.join(missing_fields)})")
                return False
                
            # Create task object
            task_obj = Task.from_dict(task)
            
            # Ensure mailbox exists
            agent_mailbox = self.mailbox_path / f"agent-{agent_id}"
            tasks_path = agent_mailbox / "tasks"
            tasks_path.mkdir(parents=True, exist_ok=True)
            
            # Save task
            task_file = tasks_path / f"task-{task_obj.id}.json"
            task_file.write_text(json.dumps(task_obj.to_dict(), indent=2))
            
            # Update status
            status_path = agent_mailbox / "status.json"
            if status_path.exists():
                status = json.loads(status_path.read_text())
                status["task_count"] = status.get("task_count", 0) + 1
                status["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                status_path.write_text(json.dumps(status, indent=2))
                
            logger.info(f"✅ Sent task to {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending task to {agent_id}: {e}")
            return False
    
    def update_task_progress(self, agent_id: str, task_id: str, progress: Dict[str, Any]) -> bool:
        """Update progress of a task.
        
        Args:
            agent_id: The ID of the agent
            task_id: The ID of the task
            progress: Progress information
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        if agent_id not in self.coords:
            logger.error(f"❌ Unknown agent: {agent_id}")
            return False
            
        try:
            agent_mailbox = self.mailbox_path / f"agent-{agent_id}"
            task_path = agent_mailbox / "tasks" / f"task-{task_id}.json"
            
            if not task_path.exists():
                logger.error(f"❌ Unknown task: {task_id} for agent {agent_id}")
                return False
                
            # Load and update task
            task_data = json.loads(task_path.read_text())
            task = Task.from_dict(task_data)
            
            # Update progress
            if "status" in progress:
                task.status = progress["status"]
            if "completion_percentage" in progress:
                task.progress = progress["completion_percentage"]
            task.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            
            # Save updated task
            task_path.write_text(json.dumps(task.to_dict(), indent=2))
            
            # Update in-memory progress
            self.task_progress[agent_id][task_id] = task.progress
            
            logger.info(f"✅ Updated progress for task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating task progress for {agent_id}/{task_id}: {e}")
            return False
    
    def initialize_mailbox(self, agent_id: str) -> bool:
        """Initialize a mailbox for an agent.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        if agent_id not in self.coords:
            logger.error(f"❌ Unknown agent: {agent_id}")
            return False
            
        try:
            agent_mailbox_dir_name = f"agent-{agent_id}"
            agent_mailbox = self.mailbox_path / agent_mailbox_dir_name
            
            # Create all required directories
            # Ensure outbox and state are created as per test_mailbox_initialization
            for dir_name in ["inbox", "outbox", "processed", "state", "tasks"]:
                (agent_mailbox / dir_name).mkdir(parents=True, exist_ok=True)
                
            # Initialize status file if it doesn't exist or after a reset
            status_path = agent_mailbox / "status.json"
            # Always ensure status.json reflects a clean/default state after initialization call
            default_status = {
                "agent_id": agent_id,
                "status": AgentState.UNINITIALIZED.value, # Default to UNINITIALIZED on fresh init
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "message_count": 0,
                "task_count": 0
            }
            status_path.write_text(json.dumps(default_status, indent=2))
                
            logger.info(f"✅ Initialized mailbox for {agent_id} (Path: {agent_mailbox})")
            return True
        except Exception as e:
            logger.error(f"Error initializing mailbox for {agent_id}: {e}")
            return False
            
    def send_message(self, agent_id: str, message: Union[str, Dict[str, Any]]) -> bool:
        """Send a message to an agent.
        
        Args:
            agent_id: The ID of the agent to send to
            message: The message content (string or dict)
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if agent_id not in self.coords:
            logger.error(f"❌ No coordinates found for {agent_id}")
            return False
            
        try:
            # Convert string message to dict if needed
            if isinstance(message, str):
                message = {
                    "content": message,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "priority": 0
                }
                
            # Validate message
            if not message or not isinstance(message, dict):
                logger.error("Invalid message: cannot be empty or wrong type")
                return False
            
            # Stricter validation: require a 'type' field for dictionary messages as per test_message_validation expectation
            if isinstance(message, dict) and 'type' not in message:
                logger.error("Invalid message dict: missing 'type' field")
                return False

            if "content" not in message or not message["content"]:
                logger.error("Invalid message: missing or empty content field")
                return False
            
            # Timestamp validation: if send_message receives a dict with an invalid timestamp,
            # it should ideally fail early if strict validation is required by tests.
            raw_timestamp = message.get('timestamp')
            if raw_timestamp:
                try:
                    datetime.fromisoformat(str(raw_timestamp).replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    logger.error(f"Invalid timestamp format '{raw_timestamp}' in provided message dict.")
                    return False # Fail if timestamp is present but invalid
            else:
                # If no timestamp, from_dict will assign one. This is acceptable.
                pass 
                
            # Create message object
            msg = Message.from_dict(message) # from_dict will handle default timestamp if not in dict
            
            # Ensure mailbox exists
            agent_mailbox = self.mailbox_path / f"agent-{agent_id}"
            inbox_path = agent_mailbox / "inbox"
            inbox_path.mkdir(parents=True, exist_ok=True)
            
            # Save message
            msg_file = inbox_path / f"msg-{msg.id}.json"
            msg_file.write_text(json.dumps(msg.to_dict(), indent=2))
            
            # Update status
            status_path = agent_mailbox / "status.json"
            if status_path.exists():
                status = json.loads(status_path.read_text())
                status["message_count"] = status.get("message_count", 0) + 1
                status["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                status_path.write_text(json.dumps(status, indent=2))
                
            logger.info(f"✅ Sent message to {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to {agent_id}: {e}")
            return False
    
    def copy_response(self, agent_id: str) -> Optional[str]:
        """Copy the latest response from an agent."""
        agent = self.coords.get(agent_id, {})
        if not agent:
            logger.error(f"❌ No coordinates found for {agent_id}")
            return None

        try:
            # Click copy button
            pyautogui.click(agent["copy_button"]["x"], agent["copy_button"]["y"])
            time.sleep(self.timings["paste_delay"])
            
            # Get clipboard content
            response = pyperclip.paste()
            logger.info(f"✅ Copied response from {agent_id}")
            return response
        except Exception as e:
            logger.error(f"❌ Error copying response from {agent_id}: {e}")
            return None
    
    def start_agent(self, agent_id: str) -> bool:
        """Start a single agent with onboarding."""
        if agent_id not in self.coords:
            logger.error(f"❌ Unknown agent: {agent_id}")
            return False
            
        console.print(f"\n[cyan]Starting {agent_id}...")
        
        # Initialize mailbox
        if not self.initialize_mailbox(agent_id):
            self.set_agent_state(agent_id, AgentState.ERROR)
            return False
            
        # Send startup message
        startup_msg_content = (
            f"{agent_id}: Welcome to Dream.OS! Your mailbox has been initialized. "
            f"Please check your inbox for the onboarding protocol (use /check_mailbox)."
        )
        startup_message_dict = { # MODIFIED to be a dict
            "type": "agent_startup_notification", # Added a type
            "content": startup_msg_content
            # Timestamp and priority will be handled by send_message/Message.from_dict
        }
        if not self.send_message(agent_id, startup_message_dict): # Pass the structured dictionary
            self.set_agent_state(agent_id, AgentState.ERROR)
            return False
            
        self.set_agent_state(agent_id, AgentState.ONBOARDING)
        return True
    
    def start_all_agents(self) -> bool:
        """Start all agents with onboarding protocol."""
        success = True
        for agent_id in self.coords.keys():
            if not self.start_agent(agent_id):
                success = False
                continue
            time.sleep(self.timings["agent_delay"])

        if success:
            console.print("\n[green]✅ All agents started successfully!")
        else:
            console.print("\n[yellow]⚠️ Some agents failed to start properly")
        
        return success
    
    def reset_agent(self, agent_id: str) -> bool:
        """Reset an agent's state and mailbox."""
        if agent_id not in self.coords:
            logger.error(f"❌ Unknown agent: {agent_id}")
            return False
            
        console.print(f"\n[cyan]Resetting {agent_id}...")
        self.set_agent_state(agent_id, AgentState.RESETTING)
        
        try:
            # Reset mailbox
            agent_mailbox = self.mailbox_path / f"agent-{agent_id}"
            if agent_mailbox.exists():
                for dir_name in ["inbox", "outbox", "processed"]:
                    dir_path = agent_mailbox / dir_name
                    if dir_path.exists():
                        for file in dir_path.glob("*"):
                            try:
                                file.unlink()
                            except Exception as e:
                                logger.error(f"Error deleting {file}: {e}")
                                return False
            
            # Reinitialize
            if not self.initialize_mailbox(agent_id):
                self.set_agent_state(agent_id, AgentState.ERROR)
                return False
                
            # Reset state
            self.set_agent_state(agent_id, AgentState.UNINITIALIZED)
            self.task_progress[agent_id] = {}
            
            logger.info(f"✅ Reset {agent_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error resetting {agent_id}: {e}")
            self.set_agent_state(agent_id, AgentState.ERROR)
            return False
    
    def reset_all_agents(self) -> bool:
        """Reset all agents."""
        success = True
        for agent_id in self.coords.keys():
            if not self.reset_agent(agent_id):
                success = False
                continue
            time.sleep(self.timings["reset_delay"])
            
        if success:
            console.print("\n[green]✅ All agents reset successfully!")
        else:
            console.print("\n[yellow]⚠️ Some agents failed to reset properly")
            
        return success

    def get_task_progress(self, agent_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """Get progress of a specific task for an agent.
        
        Args:
            agent_id: The ID of the agent
            task_id: The ID of the task
            
        Returns:
            Optional[Dict[str, Any]]: Task progress information or None if not found
        """
        if agent_id not in self.coords:
            logger.error(f"❌ Unknown agent: {agent_id}")
            return None
            
        try:
            agent_mailbox = self.mailbox_path / f"agent-{agent_id}"
            task_path = agent_mailbox / "tasks" / f"task-{task_id}.json"
            
            if not task_path.exists():
                logger.error(f"❌ Unknown task: {task_id} for agent {agent_id}")
                return None
                
            task_data = json.loads(task_path.read_text())
            task = Task.from_dict(task_data)
            
            return {
                "task_id": task.id,
                "status": task.status,
                "progress": task.progress,
                "last_updated": task.updated_at
            }
        except Exception as e:
            logger.error(f"Error getting task progress for {agent_id}/{task_id}: {e}")
            return None
            
    def update_agent_state(self, agent_id: str, state: Dict[str, Any]) -> bool:
        """Update an agent's state with new information.
        
        Args:
            agent_id: The ID of the agent to update
            state: New state information
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        if agent_id not in self.coords:
            logger.error(f"❌ Unknown agent: {agent_id}")
            return False
            
        try:
            # Update in-memory state
            if "operation_state" in state:
                try:
                    state_value_str = str(state["operation_state"]).upper()
                    new_state_enum = AgentState[state_value_str]
                    self.agent_states[agent_id] = new_state_enum
                    self.last_actions[agent_id] = time.time()

                    agent_mailbox_path = self.mailbox_path / f"agent-{agent_id}"
                    status_json_path = agent_mailbox_path / "status.json"
                    
                    current_status_data = {}
                    if status_json_path.exists():
                        current_status_data = json.loads(status_json_path.read_text())
                    else:
                        # This case should ideally be rare if initialize_mailbox is called in setUp
                        logger.warning(f"status.json not found for {agent_id} during state update. Re-initializing.")
                        self.initialize_mailbox(agent_id) # Creates a default status.json
                        current_status_data = json.loads(status_json_path.read_text()) # Load the newly created one

                    # CRITICAL: Update the status field with the *exact string value* passed, then other fields
                    current_status_data["status"] = state_value_str # Use the validated string from input
                    
                    # Update other fields from the input state dict if present
                    for key, value in state.items():
                        if key != "operation_state": # Already handled status
                            current_status_data[key] = value
                            
                    current_status_data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    status_json_path.write_text(json.dumps(current_status_data, indent=2))

                except KeyError:
                    logger.error(f"Invalid agent state value: '{state_value_str}'. Not found in AgentState enum.")
                    return False
                except Exception as e:
                    logger.error(f"Error processing state update for {agent_id}: {e}")
                    return False
            
            # If only other fields are updated (not operation_state), still save status.json
            # This part might need refinement if state dict can update non-status fields without operation_state
            elif any(k in state for k in self.agent_states.get(agent_id, AgentState.UNINITIALIZED).value): 
                # Fallback if only non-operation_state fields are being updated, less common use case
                agent_mailbox_path = self.mailbox_path / f"agent-{agent_id}"
                status_json_path = agent_mailbox_path / "status.json"
                if status_json_path.exists():
                    current_status_data = json.loads(status_json_path.read_text())
                    for key, value in state.items():
                        current_status_data[key] = value
                    current_status_data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    status_json_path.write_text(json.dumps(current_status_data, indent=2))
                else:
                    # Cannot update non-existent status.json if operation_state is not provided to trigger creation
                    logger.warning(f"Cannot update non-operation_state fields for {agent_id} as status.json does not exist and no operation_state provided.")
                    # Depending on strictness, this could be a False return
                    pass 

            return True # Return True if no operation_state was in input, but other updates might have occurred or no update needed
        except Exception as e:
            logger.error(f"Outer error updating state for {agent_id}: {e}")
            return False
            
    def mark_message_processed(self, agent_id: str, message_id: str) -> bool:
        """Mark a message as processed in an agent's mailbox.
        
        Args:
            agent_id: The ID of the agent
            message_id: The ID of the message to mark as processed
            
        Returns:
            bool: True if successful, False otherwise
        """
        if agent_id not in self.coords:
            logger.error(f"❌ Unknown agent: {agent_id}")
            return False
            
        try:
            agent_mailbox = self.mailbox_path / f"agent-{agent_id}"
            inbox_path = agent_mailbox / "inbox"
            processed_path = agent_mailbox / "processed"
            
            # Ensure processed directory exists
            processed_path.mkdir(parents=True, exist_ok=True)
            
            # Find and move message file
            for msg_file in inbox_path.glob("*.json"):
                try:
                    msg_data = json.loads(msg_file.read_text())
                    if msg_data.get("id") == message_id:
                        # Move to processed directory
                        processed_file = processed_path / msg_file.name
                        msg_file.rename(processed_file)
                        return True
                except Exception as e:
                    logger.error(f"Error processing message {msg_file}: {e}")
                    continue
                    
            logger.error(f"Message {message_id} not found in {agent_id}'s inbox")
            return False
        except Exception as e:
            logger.error(f"Error marking message as processed for {agent_id}: {e}")
            return False
            
    def broadcast_message(self, message: Dict[str, Any]) -> bool:
        """Broadcast a message to all agents.
        
        Args:
            message: The message to broadcast
            
        Returns:
            bool: True if broadcast was successful to all agents, False otherwise
        """
        if not message or not isinstance(message, dict):
            logger.error("Invalid message: cannot be empty")
            return False
            
        success = True
        for agent_id in self.coords.keys():
            if not self.send_message(agent_id, message):
                success = False
                logger.error(f"Failed to broadcast message to {agent_id}")
                
        return success

def main():
    """Main entry point."""
    engine = AutonomyEngine()
    engine.start_all_agents()

if __name__ == "__main__":
    main() 