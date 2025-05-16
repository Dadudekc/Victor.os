"""
JARVIS Core Architecture
Provides the foundation for the JARVIS-inspired AI assistant system.

This module implements the core components of JARVIS including:
- Natural language understanding and processing
- Context management and memory systems
- Task orchestration and execution
- Multi-agent coordination
"""

import asyncio
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from ..core.config import AppConfig
except ImportError:
    # For tests, create a simple config class
    class AppConfig:
        @classmethod
        def load(cls, config_path=None):
            return {}


from ..utils.memory_manager import MemoryManager

try:
    from ..agents.utils.agent_identity import AgentAwareness
except ImportError:
    # Mock for tests
    class AgentAwareness:
        def __init__(self):
            pass


logger = logging.getLogger(__name__)


class JarvisCore:
    """Core implementation of the JARVIS system architecture."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        config_dict: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the JARVIS core system.

        Args:
            config_path: Optional path to a custom configuration file
            config_dict: Optional configuration dictionary (for tests)
        """
        try:
            self.config = (
                AppConfig.load(config_path) if config_path else AppConfig.load()
            )
        except Exception as e:
            logger.warning(f"Error loading AppConfig: {str(e)}, using default config")
            self.config = config_dict or {}

        self.memory = MemoryManager()
        self.agent_awareness = AgentAwareness()
        self.is_active = False
        self.lock = threading.RLock()
        self.event_loop = None
        self.tasks = []
        self.context_window = {}
        self.last_interaction = datetime.now()

        # Store memory path for consistent access
        self.memory_path = self._get_memory_path()
        logger.info(f"Initialized JarvisCore with memory path: {self.memory_path}")

    def _get_memory_path(self) -> Path:
        """Get the memory path from config or use default.

        Returns:
            Path to memory file
        """
        memory_path = Path("runtime/jarvis/memory.json")

        # Try to get from config if it exists
        try:
            if isinstance(self.config, dict) and "jarvis" in self.config:
                if "memory_path" in self.config["jarvis"]:
                    memory_path = Path(self.config["jarvis"]["memory_path"])
                    logger.info(f"Using config dict memory path: {memory_path}")
            elif hasattr(self.config, "jarvis") and self.config.jarvis:
                if hasattr(self.config.jarvis, "memory_path"):
                    memory_path = Path(self.config.jarvis.memory_path)
                    logger.info(f"Using config memory path: {memory_path}")
                elif (
                    isinstance(self.config.jarvis, dict)
                    and "memory_path" in self.config.jarvis
                ):
                    memory_path = Path(self.config.jarvis["memory_path"])
                    logger.info(f"Using config dict memory path: {memory_path}")
        except Exception as e:
            logger.warning(f"Error accessing memory path from config: {str(e)}")

        return memory_path

    def activate(self) -> bool:
        """Activate the JARVIS system.

        Returns:
            bool: True if activation was successful, False otherwise
        """
        try:
            with self.lock:
                if self.is_active:
                    logger.warning("JARVIS is already active")
                    return True

                logger.info("Activating JARVIS core systems")

                # Initialize event loop for async operations
                self.event_loop = asyncio.new_event_loop()

                # Load persistent memory
                self._load_memory()

                # Initialize context window
                self.context_window = {
                    "system_state": self._get_system_state(),
                    "active_tasks": [],
                    "recent_interactions": [],
                }

                # Mark as active
                self.is_active = True
                self.last_interaction = datetime.now()

                logger.info("JARVIS core systems activated successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to activate JARVIS: {str(e)}")
            return False

    def deactivate(self) -> bool:
        """Deactivate the JARVIS system.

        Returns:
            bool: True if deactivation was successful, False otherwise
        """
        try:
            with self.lock:
                if not self.is_active:
                    logger.warning("JARVIS is not active")
                    return True

                logger.info("Deactivating JARVIS core systems")

                # Save memory state
                self._save_memory()

                # Clear context window
                self.context_window = {}

                # Close event loop
                if self.event_loop:
                    self.event_loop.close()
                    self.event_loop = None

                # Mark as inactive
                self.is_active = False

                logger.info("JARVIS core systems deactivated successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to deactivate JARVIS: {str(e)}")
            return False

    def process_input(self, input_text: str, source: str = "user") -> Dict[str, Any]:
        """Process input text and generate appropriate response.

        Args:
            input_text: The input text to process
            source: Source of the input (user, system, agent, etc.)

        Returns:
            Dict containing the response and any actions to take
        """
        if not self.is_active:
            logger.warning("Attempted to process input while JARVIS is inactive")
            return {"error": "JARVIS is not active"}

        try:
            with self.lock:
                # Update last interaction time
                self.last_interaction = datetime.now()

                # Add to context window
                self.context_window["recent_interactions"].append(
                    {
                        "timestamp": self.last_interaction.isoformat(),
                        "source": source,
                        "content": input_text,
                    }
                )

                # Keep context window at reasonable size
                if len(self.context_window["recent_interactions"]) > 10:
                    self.context_window["recent_interactions"] = self.context_window[
                        "recent_interactions"
                    ][-10:]

                # Process the input (NLU)
                intent, entities = self._understand_input(input_text)

                # Generate response based on intent and entities
                response = self._generate_response(intent, entities)

                # Update memory with this interaction
                self.memory.add_interaction(
                    {
                        "timestamp": self.last_interaction.isoformat(),
                        "source": source,
                        "input": input_text,
                        "intent": intent,
                        "response": response,
                    }
                )

                return response

        except Exception as e:
            logger.error(f"Error processing input: {str(e)}")
            return {"error": f"Failed to process input: {str(e)}"}

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific task.

        Args:
            task: Task definition including ID, description, and parameters

        Returns:
            Dict containing the result of the task execution
        """
        if not self.is_active:
            logger.warning("Attempted to execute task while JARVIS is inactive")
            return {"error": "JARVIS is not active"}

        try:
            with self.lock:
                # Add task to active tasks
                self.context_window["active_tasks"].append(task)

                # Log task execution
                logger.info(
                    f"Executing task: {task.get('id', 'unknown')} - {task.get('description', 'No description')}"
                )

                # Execute task based on type
                task_type = task.get("type", "unknown")
                result = {
                    "task_id": task.get("id"),
                    "status": "error",
                    "message": "Unknown task type",
                }

                if task_type == "file_operation":
                    result = self._execute_file_task(task)
                elif task_type == "system_command":
                    result = self._execute_system_command(task)
                elif task_type == "agent_coordination":
                    result = self._coordinate_with_agent(task)
                else:
                    logger.warning(f"Unknown task type: {task_type}")

                # Update task status in context window
                for i, active_task in enumerate(self.context_window["active_tasks"]):
                    if active_task.get("id") == task.get("id"):
                        self.context_window["active_tasks"][i]["status"] = result.get(
                            "status"
                        )
                        self.context_window["active_tasks"][i]["result"] = result
                        break

                # Clean up completed tasks
                self.context_window["active_tasks"] = [
                    t
                    for t in self.context_window["active_tasks"]
                    if t.get("status") not in ["completed", "failed"]
                ]

                return result

        except Exception as e:
            logger.error(f"Error executing task: {str(e)}")
            return {"error": f"Failed to execute task: {str(e)}"}

    def _understand_input(self, input_text: str) -> Tuple[str, Dict[str, Any]]:
        """Understand the intent and entities in the input text.

        Args:
            input_text: The input text to understand

        Returns:
            Tuple of (intent, entities)
        """
        # Simple intent detection for now - can be enhanced with ML models
        intent = "unknown"
        entities = {}

        input_lower = input_text.lower()

        if any(word in input_lower for word in ["help", "assist", "support"]):
            intent = "request_help"
        elif any(word in input_lower for word in ["status", "report", "how are you"]):
            intent = "status_request"
        elif any(
            word in input_lower for word in ["task", "do", "execute", "run", "perform"]
        ):
            intent = "task_execution"
            # Extract task details (simplified)
            if "file" in input_lower:
                entities["task_type"] = "file_operation"
            elif "system" in input_lower or "command" in input_lower:
                entities["task_type"] = "system_command"
        elif any(word in input_lower for word in ["remember", "recall", "memory"]):
            intent = "memory_recall"

        return intent, entities

    def _generate_response(
        self, intent: str, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a response based on the understood intent and entities.

        Args:
            intent: The detected intent
            entities: The detected entities

        Returns:
            Dict containing the response and any actions
        """
        response = {"content": "I'm not sure how to respond to that.", "actions": []}

        if intent == "request_help":
            response["content"] = (
                "I'm JARVIS, your AI assistant. I can help with tasks, answer questions, and coordinate with other agents."
            )
        elif intent == "status_request":
            system_state = self._get_system_state()
            response["content"] = (
                f"I'm operational. System status: {system_state['status']}. {len(self.context_window.get('active_tasks', []))} active tasks."
            )
        elif intent == "task_execution":
            task_type = entities.get("task_type", "unknown")
            response["content"] = f"I'll handle that {task_type} task for you."
            response["actions"].append({"type": "create_task", "task_type": task_type})
        elif intent == "memory_recall":
            memories = self.memory.retrieve_recent(5)
            memory_summary = f"I recall {len(memories)} recent interactions."
            response["content"] = memory_summary

        return response

    def _execute_file_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a file operation task.

        Args:
            task: Task definition

        Returns:
            Dict containing the result
        """
        # Simplified implementation
        operation = task.get("operation", "read")
        file_path = task.get("file_path", "")

        if not file_path:
            return {"status": "failed", "message": "No file path provided"}

        try:
            path = Path(file_path)

            if operation == "read":
                if not path.exists():
                    return {
                        "status": "failed",
                        "message": f"File not found: {file_path}",
                    }
                content = path.read_text(encoding="utf-8")
                return {"status": "completed", "content": content}
            elif operation == "write":
                content = task.get("content", "")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                return {"status": "completed", "message": f"File written: {file_path}"}
            else:
                return {
                    "status": "failed",
                    "message": f"Unsupported operation: {operation}",
                }
        except Exception as e:
            return {"status": "failed", "message": f"File operation error: {str(e)}"}

    def _execute_system_command(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a system command task.

        Args:
            task: Task definition

        Returns:
            Dict containing the result
        """
        # Placeholder - in a real implementation, this would use subprocess with security measures
        return {
            "status": "failed",
            "message": "System commands not implemented for security reasons",
        }

    def _coordinate_with_agent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate with another agent.

        Args:
            task: Task definition

        Returns:
            Dict containing the result
        """
        agent_id = task.get("agent_id", "")
        message = task.get("message", "")

        if not agent_id or not message:
            return {"status": "failed", "message": "Missing agent_id or message"}

        try:
            # Prepare message for agent
            agent_message = {
                "from": "JARVIS",
                "timestamp": datetime.now().isoformat(),
                "content": message,
            }

            # Write to agent's inbox
            inbox_path = Path(
                f"runtime/agent_comms/agent_mailboxes/{agent_id}/inbox.json"
            )
            inbox_path.parent.mkdir(parents=True, exist_ok=True)

            # Read existing inbox if it exists
            existing_messages = []
            if inbox_path.exists():
                try:
                    with open(inbox_path, "r") as f:
                        existing_messages = json.load(f)
                except Exception:
                    existing_messages = []

            # Add new message and write back
            if not isinstance(existing_messages, list):
                existing_messages = []
            existing_messages.append(agent_message)

            with open(inbox_path, "w") as f:
                json.dump(existing_messages, f, indent=2)

            return {"status": "completed", "message": f"Message sent to {agent_id}"}

        except Exception as e:
            return {
                "status": "failed",
                "message": f"Agent coordination error: {str(e)}",
            }

    def _get_system_state(self) -> Dict[str, Any]:
        """Get the current system state.

        Returns:
            Dict containing system state information
        """
        return {
            "status": "operational" if self.is_active else "inactive",
            "last_interaction": self.last_interaction.isoformat(),
            "memory_size": self.memory.size(),
            "active_tasks": len(self.context_window.get("active_tasks", [])),
        }

    def _load_memory(self) -> None:
        """Load memory from persistent storage."""
        try:
            # Use the stored memory path
            memory_path = self.memory_path

            if memory_path.exists():
                self.memory.load(memory_path)
                logger.info(f"Loaded {self.memory.size()} memory items")
            else:
                logger.info("No existing memory file found, starting with empty memory")
        except Exception as e:
            logger.error(f"Error loading memory: {str(e)}")

    def _save_memory(self) -> None:
        """Save memory to persistent storage."""
        try:
            # Use the stored memory path
            memory_path = self.memory_path

            # Ensure the directory exists
            memory_path.parent.mkdir(parents=True, exist_ok=True)

            # Save the memory
            success = self.memory.save(memory_path)
            if success:
                logger.info(f"Saved {self.memory.size()} memory items to {memory_path}")
            else:
                logger.error(f"Failed to save memory to {memory_path}")

            # Verify file exists after save
            if memory_path.exists():
                logger.info(f"Verified memory file exists at {memory_path}")
            else:
                logger.error(f"Memory file does not exist after save at {memory_path}")

        except Exception as e:
            logger.error(f"Error saving memory: {str(e)}")
