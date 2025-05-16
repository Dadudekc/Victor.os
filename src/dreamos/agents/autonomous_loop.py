"""
Dream.OS Autonomous Agent Loop Implementation
Provides the core loop functionality for all agents with validation enforcement.
"""

import asyncio
import json
import logging
import os
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dreamos.automation.validation_utils import (
    ImprovementValidator,
    ValidationResult,
    ValidationStatus,
)
from dreamos.core.config import AppConfig
from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.core.coordination.abstract_base_agent import BaseAgent
from dreamos.core.project_board import ProjectBoardManager
from .validation import StateValidator
from .task_schema import Task, TaskHistory, TASK_STATUS, TASK_PRIORITY, TASK_TYPES
from .message_schema import AgentMessage, MESSAGE_TYPES, PRIORITY_LEVELS
from .utils.response_retriever import ResponseRetriever
from .utils.autonomy_engine import AutonomyEngine

logger = logging.getLogger(__name__)

class AutonomousLoop:
    """Core autonomous loop implementation for Dream.OS agents with validation enforcement."""

    def __init__(
        self,
        agent: BaseAgent,
        config: AppConfig,
        pbm: ProjectBoardManager,
        agent_bus: Optional[AgentBus] = None,
        validation_state_dir: str = "runtime/state",
    ):
        """Initialize the autonomous loop.

        Args:
            agent: The agent instance to run the loop for
            config: Application configuration
            pbm: Project Board Manager instance
            agent_bus: Optional AgentBus instance for communication
            validation_state_dir: Directory for validation state storage
        """
        self.agent = agent
        self.config = config
        self.pbm = pbm
        self.agent_bus = agent_bus
        self.validator = ImprovementValidator(state_dir=validation_state_dir)
        self.cycle_count = 0
        self._running = False
        self.logger = logging.getLogger(f"{agent.agent_id}.autonomous_loop")
        
        # Initialize paths
        self.mailbox_path = Path("runtime/agent_comms/agent_mailboxes") / agent.agent_id
        self.episode_path = Path("episodes/episode-launch-final-lock.yaml")
        
        # Ensure directories exist
        self.mailbox_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.response_retriever = ResponseRetriever(Path("D:/Dream.os"))
        self.autonomy_engine = AutonomyEngine(Path("D:/Dream.os"))
        
        # Load configuration
        self.load_config()
        
    def load_config(self) -> None:
        """Load autonomous loop configuration."""
        try:
            with open(Path("D:/Dream.os/src/dreamos/config/autonomous_loop_config.yaml"), 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.config = {}
        
    async def _process_mailbox(self) -> bool:
        """Process messages in the agent's mailbox.
        
        Returns:
            bool: True if any messages were processed
        """
        inbox_path = self.mailbox_path / "inbox.json"
        if not inbox_path.exists():
            return False
            
        try:
            with open(inbox_path) as f:
                messages = json.load(f)
                
            if not messages:
                return False
                
            for message in messages:
                await self.agent.process_message(message)
                
            # Clear processed messages
            with open(inbox_path, 'w') as f:
                json.dump([], f)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing mailbox: {e}")
            return False
            
    async def _check_working_tasks(self) -> Optional[Dict[str, Any]]:
        """Check for claimed tasks in working_tasks.json.
        
        Returns:
            Optional[Dict[str, Any]]: The current task if one is claimed, None otherwise
        """
        try:
            # Use ProjectBoardManager to get working tasks
            working_tasks = self.pbm.list_working_tasks(agent_id=self.agent.agent_id)
            return working_tasks[0] if working_tasks else None
            
        except Exception as e:
            self.logger.error(f"Error checking working tasks: {e}")
            return None
            
    async def _claim_new_task(self) -> Optional[Dict[str, Any]]:
        """Attempt to claim a new task from the episode file.
        
        Returns:
            Optional[Dict[str, Any]]: The claimed task if successful, None otherwise
        """
        try:
            resolved_path = self.episode_path.resolve()
            self.logger.debug(f"_claim_new_task: Attempting to read episode_path: {resolved_path}")
        except Exception as e:
            self.logger.error(f"_claim_new_task: Error resolving episode_path {self.episode_path}: {e}")
            resolved_path = self.episode_path # Use original path if resolve fails

        if not self.episode_path.exists(): # Check existence on original/assigned path
            self.logger.debug(f"_claim_new_task: Episode file not found at {resolved_path}")
            return None
            
        try:
            with open(self.episode_path, 'r') as f: # Use self.episode_path for opening
                content_for_debug = f.read()
                self.logger.debug(f"_claim_new_task: Content of {resolved_path}:\n{content_for_debug}")
                # Reset file pointer to read again for yaml.safe_load
                f.seek(0) 
                episode_data = yaml.safe_load(f)
                
            self.logger.debug(f"_claim_new_task: Loaded episode_data: {episode_data}")
            tasks = episode_data.get("tasks", [])
            
            # Find highest priority unclaimed task
            for task in sorted(tasks, key=lambda x: x.get("priority", 0), reverse=True):
                if not task.get("claimed_by"):
                    # Use ProjectBoardManager to claim the task
                    self.logger.debug(f"_claim_new_task: Attempting to claim task ID {task.get('id')} via PBM.")
                    if self.pbm.claim_task(task["id"], self.agent.agent_id):
                        self.logger.info(f"_claim_new_task: Successfully claimed task ID {task.get('id')} via PBM.")
                        return task
                    else:
                        self.logger.debug(f"_claim_new_task: PBM denied claim for task ID {task.get('id')}.")
                        
            self.logger.debug("_claim_new_task: No claimable tasks found in episode data.")
            return None
            
        except FileNotFoundError:
            self.logger.error(f"_claim_new_task: FileNotFoundError for {resolved_path}. This should have been caught by exists().")
            return None
        except yaml.YAMLError as e:
            self.logger.error(f"_claim_new_task: YAML error parsing {resolved_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"_claim_new_task: Unexpected error processing {resolved_path}: {e}", exc_info=True)
            return None
            
    async def _check_blockers(self) -> List[Dict[str, Any]]:
        """Check for unresolved blockers or schema errors.
        
        Returns:
            List[Dict[str, Any]]: List of identified blockers
        """
        blockers = []
        
        # Check for schema validation errors
        self.logger.debug("Validator type: %s", type(self.validator))
        validation_result = await self.validator.validate_current_state()
        self.logger.debug("Validation result status: %s, expected to compare with: %s", validation_result.status, ValidationStatus.PASSED)
        if validation_result.status != ValidationStatus.PASSED:
            blockers.append({
                "type": "validation_error",
                "description": validation_result.message,
                "severity": "high"
            })
            
        # Add other blocker checks here as needed
        
        return blockers
        
    async def run(self):
        """Run the autonomous loop."""
        self.logger.info(f"Starting autonomous loop for {self.agent.agent_id}")
        self.logger.info(f"run: self.episode_path at start of run(): {str(self.episode_path)} - Resolved: {self.episode_path.resolve() if self.episode_path.exists() else 'Path does not exist or cannot resolve'}")
        self._running = True
        
        loop_config = self.config.get("loop", {})
        cycle_delay_seconds = loop_config.get("cycle_delay_seconds", 5)

        while self._running:
            try:
                self.cycle_count += 1
                self.logger.debug(f"Starting cycle {self.cycle_count} for agent {self.agent.agent_id}")
                
                active_task = None

                # 1. Check for already claimed working tasks
                self.logger.debug("Checking for active working tasks...")
                active_task = await self._check_working_tasks()
                if active_task:
                    self.logger.info(f"Found active task: {active_task.get('id', 'Unknown ID')}")

                # 2. If no active task, try to claim a new one
                if not active_task:
                    self.logger.debug("No active task. Attempting to claim a new task...")
                    active_task = await self._claim_new_task()
                    if active_task:
                        self.logger.info(f"Successfully claimed new task: {active_task.get('id', 'Unknown ID')}")
                    else:
                        self.logger.debug("No new tasks were claimed.")
                
                # 3. Process Mailbox (Inter-agent communication & coordination)
                # This runs regardless of task status, as messages can be urgent or affect agent state.
                self.logger.debug("Processing agent mailbox...")
                messages_processed = await self._process_mailbox()
                if messages_processed:
                    self.logger.info("Processed messages from mailbox.")
                else:
                    self.logger.debug("No new messages in mailbox.")
                    
                # 4. Execute active task (if any)
                # This is where task-specific logic, including potential Agent-LLM interaction via PyAutoGUI, occurs.
                if active_task:
                    self.logger.info(f"Proceeding to execute task: {active_task.get('id', 'Unknown ID')}")
                    if hasattr(self.agent, 'execute_task') and callable(getattr(self.agent, 'execute_task')):
                        await self.agent.execute_task(active_task)
                        self.logger.info(f"Execution attempt for task {active_task.get('id', 'Unknown ID')} completed.")
                        # Note: Agent's execute_task method is responsible for updating task status (e.g., completed, failed) via PBM.
                    else:
                        self.logger.error(f"CRITICAL: Agent {self.agent.agent_id} is missing the 'execute_task' method.")
                else:
                    self.logger.info("No active task to execute in this cycle.")
                    
                    # 5. If no task, check for blockers or idle
                    self.logger.debug("Checking for blockers...")
                    blockers = await self._check_blockers()
                    if blockers:
                        self.logger.warning(f"Found {len(blockers)} blockers. Agent {self.agent.agent_id} may need to address them.")
                        # Future: Add logic for agent to explicitly handle blockers.
                    else:
                        self.logger.info(f"Agent {self.agent.agent_id} is idle. No tasks or blockers.")
                
                self.logger.debug(f"Cycle {self.cycle_count} ended. Waiting for {cycle_delay_seconds}s.")
                await asyncio.sleep(cycle_delay_seconds)
                
            except asyncio.CancelledError:
                self.logger.info(f"Autonomous loop for {self.agent.agent_id} cancelled.")
                self._running = False
                break # Exit the while loop
            except Exception as e:
                self.logger.error(f"Error in autonomous loop cycle {self.cycle_count} for {self.agent.agent_id}: {e}", exc_info=True)
                # Implement more robust error handling or backoff strategy if needed
                await asyncio.sleep(cycle_delay_seconds * 2) # Longer sleep on error

        self.logger.info(f"Autonomous loop for {self.agent.agent_id} has stopped.")

    def stop(self):
        """Stop the autonomous loop."""
        self._running = False
        self.logger.info("Stopping autonomous loop")

    async def process_message(self, message: Dict[str, Any]):
        """TEMPORARY: Process a message directly. This is likely a test workaround."""
        self.logger.warning(
            f"AutonomousLoop.process_message was called directly with: {message}. "
            f"This method is a temporary workaround for tests and may not reflect actual loop behavior."
        )
        # In a real scenario, messages for the loop/agent might be placed in the mailbox
        # or handled by specific components like AutonomyEngine.
        # For now, this method does nothing beyond logging.
        pass

async def main():
    """Entry point for the autonomous loop."""
    agent_id = "1"  # You can make this configurable
    loop = AutonomousLoop(agent_id)
    try:
        await loop.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, stopping...")
        loop.stop()
    except Exception as e:
        logger.error(f"Fatal error in autonomous loop: {e}")
        loop.stop()

if __name__ == "__main__":
    asyncio.run(main()) 