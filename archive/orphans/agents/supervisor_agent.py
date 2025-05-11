"""
Reads directives, dispatches them via a channel, collects results, and saves them.

NOTE: This agent currently does NOT inherit from BaseAgent and uses a synchronous loop.
It needs review for alignment with the standard agent framework.
"""

import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

# FIXME: This Agent should likely inherit from BaseAgent and implement the async lifecycle.
from dreamos.channels.local_blob_channel import LocalBlobChannel
from dreamos.core.config import AppConfig
from dreamos.core.errors import ConfigurationError  # Import specific error

logger = logging.getLogger("SupervisorAgent")


class SupervisorAgent:
    """Orchestrates tasks between ChatGPT WebAgents and Cursor workers."""

    def __init__(self, config: AppConfig):
        """
        Initializes the SupervisorAgent.

        Args:
            config: The application configuration object.

        Raises:
            ConfigurationError: If required paths are missing in the config.
        """
        self.config = config
        local_blob_path_str: Optional[str] = None  # Initialize for potential use
        # Default paths defined here for clarity if needed, but prefer direct access
        # default_directive = Path("runtime/human_directive.json")
        # default_results = Path("runtime/supervisor_results.json")
        # default_blob_storage = Path("runtime/local_blob")

        # Direct access to config paths, handle potential errors
        try:
            project_root = config.paths.project_root  # Assume project_root is essential
            # Try accessing specific paths, failing explicitly if missing
            directive_rel_path = config.paths.human_directive
            results_rel_path = config.paths.supervisor_results
            blob_rel_path = config.paths.local_blob_storage

            self.directive_path = str(project_root / directive_rel_path)
            self.results_output_path = str(project_root / results_rel_path)
            local_blob_path_str = str(project_root / blob_rel_path)
            logger.info(f"SupervisorAgent using directive path: {self.directive_path}")
            logger.info(
                f"SupervisorAgent using results path: {self.results_output_path}"
            )
            logger.info(
                f"SupervisorAgent using blob storage path: {local_blob_path_str}"
            )

        except AttributeError as e:
            logger.error(
                f"SupervisorAgent configuration error: Missing required path in AppConfig.paths: {e}."
            )
            # Raise error for critical missing configuration
            raise ConfigurationError(f"SupervisorAgent missing config path: {e}") from e
        except Exception as e:
            logger.error(
                f"Unexpected error initializing SupervisorAgent paths: {e}",
                exc_info=True,
            )
            raise ConfigurationError(f"Unexpected error initializing paths: {e}") from e

        # Initialize channel, handle potential initialization errors
        if local_blob_path_str:
            try:
                self.channel = LocalBlobChannel(base_dir=local_blob_path_str)
            except Exception as e:
                logger.error(
                    f"SupervisorAgent failed to initialize LocalBlobChannel at {local_blob_path_str}: {e}",
                    exc_info=True,
                )
                raise ConfigurationError(
                    f"Failed to initialize LocalBlobChannel: {e}"
                ) from e
        else:
            # This case should now be unreachable due to error handling above, but kept defensively
            logger.error(
                "SupervisorAgent cannot initialize LocalBlobChannel: Blob storage path not configured."
            )
            raise ConfigurationError("LocalBlobChannel path not configured.")

        self.dispatched = set()

    def load_directives(self):
        """Loads tasks/directives from the configured JSON file."""
        if not self.directive_path:
            # Should not happen if __init__ raises error, but check defensively
            logger.error("Cannot load directives: Directive path not configured.")
            return []
        try:
            with open(self.directive_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Support both "tasks" and "directives" keys for flexibility
            tasks = data.get("tasks") or data.get("directives", [])
            if not isinstance(tasks, list):
                logger.error(f"Directives data in {self.directive_path} is not a list.")
                return []
            return tasks
        except FileNotFoundError:
            logger.warning(
                f"Directive file not found: {self.directive_path}. Returning empty list."
            )
            return []
        except json.JSONDecodeError as e:
            logger.error(
                f"Error decoding JSON from directive file {self.directive_path}: {e}"
            )
            return []
        except Exception as e:
            logger.error(
                f"Failed to load directives from {self.directive_path}: {e}",
                exc_info=True,
            )
            return []

    def dispatch_tasks(self, tasks):
        """Dispatches new tasks via the communication channel."""
        if not self.channel:
            logger.error(
                "Cannot dispatch tasks: Communication channel not initialized."
            )
            return

        for task in tasks:
            task_id = task.get("task_id") or task.get("id")
            if not task_id or task_id in self.dispatched:
                continue
            payload = task.get("payload", task)
            logger.info(f"Dispatching task {task_id} to channel.")
            try:
                self.channel.push_task({"id": task_id, "payload": payload})
                self.dispatched.add(task_id)
            except Exception as e:
                logger.error(
                    f"Failed to push task {task_id} to channel: {e}", exc_info=True
                )
                # Decide if we should stop dispatching or just log and continue?
                # Logging and continuing for now.

    def gather_results(self):
        """Gathers all available results from the communication channel."""
        if not self.channel:
            logger.error(
                "Cannot gather results: Communication channel not initialized."
            )
            return []

        collected = []
        try:
            # Assume pull_results gets a batch or None/empty if nothing
            results = self.channel.pull_results()
            while results:
                for r in results:
                    # Basic validation: check if result is a dictionary with an 'id'
                    if isinstance(r, dict) and "id" in r:
                        logger.info(f"Collected result for {r.get('id')}")
                        collected.append(r)
                    else:
                        logger.warning(
                            f"Received invalid result format from channel: {r}"
                        )
                results = self.channel.pull_results()
        except Exception as e:
            logger.error(f"Error pulling results from channel: {e}", exc_info=True)
        return collected

    def save_results(self, results):
        """Saves the collected results to the configured output file."""
        if not self.results_output_path:
            # Should not happen if __init__ raises error, but check defensively
            logger.error("Cannot save results: Results output path not configured.")
            return

        try:
            output_path = Path(self.results_output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # Use atomic write for safety
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                delete=False,
                dir=output_path.parent,
                suffix=".tmp",
            ) as tmp_file:
                json.dump(results, tmp_file, indent=2)
                temp_file_path = tmp_file.name
            os.replace(temp_file_path, output_path)  # Atomic replace
            logger.info(f"Results written atomically to {self.results_output_path}")
        except Exception as e:
            logger.error(
                f"Failed to write results to {self.results_output_path}: {e}",
                exc_info=True,
            )
            # Clean up temporary file if it exists and possible
            if "temp_file_path" in locals() and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e_remove:
                    logger.error(
                        f"Error removing temporary results file {temp_file_path}: {e_remove}"
                    )

    def run_loop(self, interval=5):
        """Runs the main synchronous loop of the supervisor."""
        if not self.channel or not self.directive_path or not self.results_output_path:
            logger.critical(
                "SupervisorAgent cannot run: Initialization failed (missing channel or paths). Exiting loop."
            )
            return

        logger.info(f"SupervisorAgent run_loop started. Interval: {interval}s")
        while True:
            try:
                tasks = self.load_directives()
                if tasks:
                    self.dispatch_tasks(tasks)
                    # Consider if gathering/saving should happen even if no new tasks were dispatched?
                    # Assuming yes for now - maybe results arrived for old tasks.
                    results = self.gather_results()
                    if results:
                        self.save_results(results)
                else:
                    logger.debug("No new directives loaded in this cycle.")
            except Exception as e:
                # Catch unexpected errors in the main loop logic
                logger.error(f"Error in supervisor run_loop: {e}", exc_info=True)
                # Avoid tight loop on errors, wait before next cycle

            time.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        config = AppConfig.load()
        if not config:
            raise ValueError(
                "Failed to load AppConfig for SupervisorAgent standalone run."
            )
    except Exception as e:
        logging.error(f"Cannot start SupervisorAgent standalone: {e}")
        exit(1)

    agent = SupervisorAgent(config=config)
    agent.run_loop()
