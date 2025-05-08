import asyncio
import logging
import time
from typing import Optional, Set

from dreamos.core.config import AppConfig

# Assuming BaseAgent defines the structure correctly
from dreamos.core.coordination.base_agent import BaseAgent
from dreamos.core.coordination.project_board_manager import (
    ProjectBoardError,
    ProjectBoardManager,
    TaskNotFoundError,
)

# Removed direct dependency on AgentBus if not used in this simple loop

# Use the agent's configured logger
logger = logging.getLogger("TaskPromoterAgent")


class TaskPromoterAgent(BaseAgent):
    """
    An agent that periodically scans the task backlog and promotes tasks
    to the ready queue if their dependencies are met.
    """

    def __init__(
        self,
        agent_id: str = "TaskPromoter",  # Default ID
        config: Optional[AppConfig] = None,
        pbm: Optional[ProjectBoardManager] = None,
        poll_interval_seconds: int = 60,
        **kwargs,  # Capture any other BaseAgent args
    ):
        """
        Initializes the TaskPromoterAgent.

        Args:
            agent_id: The unique ID for this agent.
            config: The application configuration.
            pbm: The ProjectBoardManager instance.
            poll_interval_seconds: How often to check for promotable tasks.
        """
        # Ensure required components are available or create defaults if necessary
        # This might deviate from standard agent loading, depending on how it's run
        effective_config = config or AppConfig()
        effective_pbm = pbm or ProjectBoardManager(config=effective_config)

        # Call BaseAgent's __init__ with necessary arguments
        # Note: This assumes BaseAgent's __init__ signature is compatible
        # If BaseAgent requires agent_bus, it needs to be handled.
        try:
            super().__init__(
                agent_id=agent_id, config=effective_config, pbm=effective_pbm, **kwargs
            )
        except TypeError as e:
            logger.error(
                f"Error calling BaseAgent init, potential signature mismatch: {e}. Falling back to basic init."
            )
            # Fallback basic init if super call fails (e.g., missing agent_bus)
            self.agent_id = agent_id
            self.config = effective_config
            self.pbm = effective_pbm
            self.logger = logger  # Use configured logger

        self.poll_interval = poll_interval_seconds
        self.logger.info(
            f"TaskPromoterAgent initialized. Poll interval: {self.poll_interval}s"
        )

    def _get_completed_task_ids(self) -> Set[str]:
        """Safely load completed task IDs."""
        try:
            # Use the PBM's internal load method which handles locking
            completed_tasks = self.pbm._load_completed_tasks()
            return {
                task.get("task_id") for task in completed_tasks if task.get("task_id")
            }
        except Exception as e:
            self.logger.error(f"Failed to load completed tasks: {e}", exc_info=True)
            return set()

    def _get_pending_backlog_tasks(self) -> list:
        """Safely load pending backlog tasks."""
        try:
            # Use the PBM's internal load method which handles locking
            backlog_tasks = self.pbm._load_backlog()
            return [
                task
                for task in backlog_tasks
                if task.get("status", "").upper() == "PENDING" and task.get("task_id")
            ]
        except Exception as e:
            self.logger.error(f"Failed to load backlog tasks: {e}", exc_info=True)
            return []

    def promote_eligible_tasks(self):
        """Identifies and promotes tasks whose dependencies are met."""
        self.logger.debug("Checking for promotable tasks...")
        completed_ids = self._get_completed_task_ids()
        if not completed_ids and self.pbm.completed_tasks_path.exists():
            # Log if loading failed but file exists
            self.logger.warning(
                "Completed task IDs set is empty, promotion check might be inaccurate."
            )

        pending_tasks = self._get_pending_backlog_tasks()

        promoted_count = 0
        for task in pending_tasks:
            task_id = task.get("task_id")
            dependencies = task.get("dependencies", [])

            # Ensure dependencies is a list
            if not isinstance(dependencies, list):
                self.logger.warning(
                    f"Task {task_id} has invalid dependencies format: {dependencies}. Skipping."
                )
                continue

            # Check if all dependencies are in the completed set
            if not dependencies or all(
                dep_id in completed_ids for dep_id in dependencies
            ):
                self.logger.info(
                    f"Task {task_id} dependencies met. Attempting promotion..."
                )
                try:
                    # Use the PBM's public method for promotion
                    if self.pbm.promote_task_to_ready(task_id):
                        self.logger.info(
                            f"✅ Successfully promoted task {task_id} to ready queue."
                        )
                        promoted_count += 1
                    else:
                        # This path might not be reachable if promote_task_to_ready raises exceptions on failure
                        self.logger.warning(
                            f"Promotion call for {task_id} returned False."
                        )
                except (TaskNotFoundError, ProjectBoardError) as e:
                    # Log expected errors during promotion (e.g., task already moved, validation fail)
                    self.logger.warning(f"Could not promote task {task_id}: {e}")
                except Exception as e:
                    # Log unexpected errors during promotion
                    self.logger.error(
                        f"❌ Unexpected error promoting task {task_id}: {e}",
                        exc_info=True,
                    )
            else:
                self.logger.debug(
                    f"Task {task_id} dependencies not met: {dependencies}. Required: {completed_ids}"
                )

        if promoted_count > 0:
            self.logger.info(
                f"Promotion cycle complete. Promoted {promoted_count} task(s)."
            )
        else:
            self.logger.debug("Promotion cycle complete. No tasks promoted.")

    async def _run_cycle(self):
        """Runs a single cycle of the promotion check."""
        try:
            self.promote_eligible_tasks()
        except Exception as e:
            self.logger.error(f"⚠️ Error in TaskPromoterAgent cycle: {e}", exc_info=True)

        # Wait before the next cycle
        await asyncio.sleep(self.poll_interval)

    # Override the main run method if this agent is meant to run continuously
    # using the BaseAgent's lifecycle management (start/stop)
    async def run_main_loop(self):
        """Continuously runs the promotion cycle."""
        self.logger.info(
            f"🔁 TaskPromoterAgent run_main_loop started. Agent ID: {self.agent_id}"
        )
        self._running = True
        while self._running:
            await self._run_cycle()
        self.logger.info("TaskPromoterAgent run_main_loop stopped.")

    # Optional: If run as a standalone script rather than integrated agent
    def run_standalone(self):
        """Runs the agent loop standalone (blocking)."""
        self.logger.info(
            f"🔁 TaskPromoterAgent standalone loop started. Agent ID: {self.agent_id}"
        )
        while True:  # Simple infinite loop for standalone execution
            try:
                self.promote_eligible_tasks()
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                self.logger.info(
                    "KeyboardInterrupt received. Stopping standalone loop."
                )
                break
            except Exception as e:
                self.logger.error(f"⚠️ Error in standalone loop: {e}", exc_info=True)
                # Avoid busy-looping on persistent errors
                time.sleep(min(self.poll_interval, 30))


# Example for potential standalone execution (if needed)
# This part would typically not be in the library file itself,
# but maybe in a separate script/entry point.
if __name__ == "__main__":
    # Setup basic logging if run directly
    # Configure logging to suitable level and format for standalone run
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format)
    # Optionally add a file handler
    # log_file = Path("runtime/logs/task_promoter_agent.log")
    # log_file.parent.mkdir(exist_ok=True, parents=True)
    # file_handler = logging.FileHandler(log_file)
    # file_handler.setFormatter(logging.Formatter(log_format))
    # logging.getLogger().addHandler(file_handler) # Add handler to root logger

    logger.info("Running TaskPromoterAgent directly...")
    # Create necessary objects (consider loading full config if needed)
    try:
        # It's crucial that AppConfig() can be instantiated correctly here
        # It might need environment variables or config files to be present
        app_config = AppConfig()
        project_board_manager = ProjectBoardManager(config=app_config)
        # Pass config and PBM to the agent constructor
        promoter = TaskPromoterAgent(config=app_config, pbm=project_board_manager)
        promoter.run_standalone()
    except Exception as main_err:
        logger.critical(f"Failed to start TaskPromoterAgent: {main_err}", exc_info=True)
