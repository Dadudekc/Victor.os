import json
import logging
import time
from pathlib import Path

from dreamos.channels.local_blob_channel import LocalBlobChannel
from dreamos.core.config import AppConfig

logger = logging.getLogger("SupervisorAgent")


class SupervisorAgent:
    """Orchestrates tasks between ChatGPT WebAgents and Cursor workers."""

    def __init__(self, config: AppConfig):
        self.config = config
        # Default paths defined here for clarity if needed, but prefer direct access
        # default_directive = Path("runtime/human_directive.json")
        # default_results = Path("runtime/supervisor_results.json")
        # default_blob_storage = Path("runtime/local_blob")

        # Direct access to config paths, handle potential errors
        try:
            project_root = config.paths.project_root  # Assume project_root is essential
            # Try accessing specific paths, falling back only if absolutely necessary
            # Or better: define these paths explicitly in AppConfig.paths
            directive_rel_path = config.paths.human_directive  # Example direct access
            results_rel_path = config.paths.supervisor_results  # Example direct access
            blob_rel_path = config.paths.local_blob_storage  # Example direct access

            self.directive_path = str(project_root / directive_rel_path)
            self.results_output_path = str(project_root / results_rel_path)
            local_blob_path = str(project_root / blob_rel_path)
            logger.info(f"SupervisorAgent using directive path: {self.directive_path}")
            logger.info(
                f"SupervisorAgent using results path: {self.results_output_path}"
            )
            logger.info(f"SupervisorAgent using blob storage path: {local_blob_path}")

        except AttributeError as e:
            logger.error(
                f"SupervisorAgent configuration error: Missing required path in AppConfig.paths: {e}. Supervisor may not function correctly."  # noqa: E501
            )
            # Decide on fallback behavior: raise error? Use hardcoded defaults? Set paths to None?  # noqa: E501
            # For now, let's set paths to None to prevent operations on invalid paths.
            self.directive_path = None
            self.results_output_path = None
            local_blob_path = None  # Affects channel init
            # Consider raising the error or returning status if init fails critically
            # raise ConfigurationError(f"SupervisorAgent missing config path: {e}") from e  # noqa: E501
        except Exception as e:
            logger.error(
                f"Unexpected error initializing SupervisorAgent paths: {e}",
                exc_info=True,
            )
            self.directive_path = None
            self.results_output_path = None
            local_blob_path = None

        # Initialize channel, handle potential None path
        if local_blob_path:
            self.channel = LocalBlobChannel(base_dir=local_blob_path)
        else:
            logger.error(
                "SupervisorAgent cannot initialize LocalBlobChannel: Blob storage path not configured."  # noqa: E501
            )
            self.channel = None  # Ensure channel is None if path fails

        self.dispatched = set()

    def load_directives(self):
        if not self.directive_path:
            logger.error("Cannot load directives: Directive path not configured.")
            return []
        try:
            with open(self.directive_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            tasks = data.get("tasks") or data.get("directives", [])
        except Exception as e:
            logger.debug(f"Failed to load directives from {self.directive_path}: {e}")
            return []
        return tasks

    def dispatch_tasks(self, tasks):
        for task in tasks:
            task_id = task.get("task_id") or task.get("id")
            if not task_id or task_id in self.dispatched:
                continue
            payload = task.get("payload", task)
            logger.info(f"Dispatching task {task_id} to channel.")
            self.channel.push_task({"id": task_id, "payload": payload})
            self.dispatched.add(task_id)

    def gather_results(self):
        collected = []
        results = self.channel.pull_results()
        while results:
            for r in results:
                logger.info(f"Collected result for {r.get('id')}")
                collected.append(r)
            results = self.channel.pull_results()
        return collected

    def save_results(self, results):
        try:
            output_path = Path(self.results_output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results written to {self.results_output_path}")
        except Exception as e:
            logger.error(f"Failed to write results to {self.results_output_path}: {e}")

    def run_loop(self, interval=5):
        logger.info("SupervisorAgent started.")
        while True:
            tasks = self.load_directives()
            if tasks:
                self.dispatch_tasks(tasks)
                results = self.gather_results()
                if results:
                    self.save_results(results)
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
