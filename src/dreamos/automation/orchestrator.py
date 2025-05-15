"""
Episode Orchestrator Module
Manages the overall execution flow of episodes.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json
import asyncio

from .episode import EpisodeManager
from .tasks import TaskManager
from .identity import IdentityManager
from ..agents.utils.agent_identity import AgentAwareness
from ..core.tasks.execution.task_executor import TaskExecutor
from ..core.tasks.nexus.task_nexus import TaskNexus

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        self.episode_manager = EpisodeManager()
        self.task_manager = TaskManager()
        self.identity_manager = IdentityManager()
        self.agent_awareness = AgentAwareness()
        self.current_episode: Optional[Dict[str, Any]] = None
        self.is_running = False
        
        # EDIT START: Add TaskExecutor and TaskNexus
        self.task_nexus = TaskNexus()  # Using default task file path
        self.task_executor = TaskExecutor(self.task_nexus)
        # EDIT END

    def start_episode(self, episode_path: str) -> bool:
        """Start execution of an episode."""
        try:
            # Load and validate episode
            if not self.episode_manager.load_episode(episode_path):
                logger.error("Failed to load episode")
                return False

            self.current_episode = self.episode_manager.episode_data

            # Initialize components
            if not self._initialize_components():
                logger.error("Failed to initialize components")
                return False

            # Generate documentation
            if not self.episode_manager.generate_documentation():
                logger.error("Failed to generate documentation")
                return False

            # Start execution
            self.is_running = True
            logger.info(f"Started episode: {self.current_episode['metadata']['title']}")
            return True

        except Exception as e:
            logger.error(f"Error starting episode: {str(e)}")
            return False

    def _initialize_components(self) -> bool:
        """Initialize all required components."""
        try:
            # Initialize task board
            if not self.task_manager.initialize_tasks(self.current_episode['task_board']):
                return False

            # Initialize agent identities and awareness
            if not self.identity_manager.initialize_identities(
                self.current_episode['agent_awareness']
            ):
                return False

            # Initialize agent awareness system
            if not self.agent_awareness.initialize_from_config(
                self.current_episode['agent_awareness']
            ):
                return False

            return True
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
            return False

    def execute_loop(self) -> bool:
        """Execute one iteration of the episode loop."""
        if not self.is_running or not self.current_episode:
            return False

        try:
            # Check for completion
            if self.task_manager.check_completion():
                self._handle_completion()
                return False

            # Process each agent's tasks
            for agent_id in self.current_episode['agent_awareness']['agent_prefixes']:
                # EDIT START: Use asyncio.run to handle async _process_agent_tasks
                success = asyncio.run(self._process_agent_tasks(agent_id))
                if not success:
                    logger.warning(f"Failed to process tasks for agent {agent_id}")
                # EDIT END

            return True

        except Exception as e:
            logger.error(f"Error in execution loop: {str(e)}")
            return False

    # EDIT START: Update _process_agent_tasks to be async and use TaskExecutor
    async def _process_agent_tasks(self, agent_id: str) -> bool:
        """Process tasks for a specific agent."""
        try:
            # Confirm agent identity and log awareness
            if not self.agent_awareness.confirm_identity(agent_id):
                logger.warning(f"Failed to confirm identity for agent {agent_id}")
                return False

            # Log identity confirmation
            self.identity_manager.log_identity_confirmation(agent_id)

            # Get agent's tasks
            tasks = self.task_manager.get_agent_tasks(agent_id)
            if not tasks:
                return True

            # Process each task
            for task in tasks:
                if task['status'] == 'pending':
                    # Use TaskExecutor for actual execution
                    success = await self.task_executor.execute_task(task['id'], agent_id)
                    if not success:
                        logger.warning(f"Failed to execute task {task['id']}")

            return True

        except Exception as e:
            logger.error(f"Error processing tasks for agent {agent_id}: {str(e)}")
            return False
    # EDIT END

    def _handle_completion(self) -> None:
        """Handle episode completion."""
        try:
            self.is_running = False
            completion_time = datetime.now().isoformat()
            
            # Log completion
            log_entry = {
                "timestamp": completion_time,
                "episode": self.current_episode['metadata']['title'],
                "status": "completed",
                "agent_awareness": {
                    agent_id: self.agent_awareness.get_awareness_level(agent_id)
                    for agent_id in self.current_episode['agent_awareness']['agent_prefixes']
                }
            }

            log_path = Path("runtime/logs/episodes")
            log_path.mkdir(parents=True, exist_ok=True)
            
            log_file = log_path / f"episode_{self.current_episode['metadata']['id']}_completion.log"
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, indent=2))

            logger.info(f"Episode completed: {self.current_episode['metadata']['title']}")

        except Exception as e:
            logger.error(f"Error handling completion: {str(e)}")

    def stop_episode(self) -> None:
        """Stop the current episode."""
        self.is_running = False
        logger.info("Episode stopped") 