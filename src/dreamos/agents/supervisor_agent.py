import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path

from dreamos.channels.local_blob_channel import LocalBlobChannel
from dreamos.coordination.agent_bus import AgentBus
from dreamos.coordination.base_agent import BaseAgent

from ..config import AppConfig

logger = logging.getLogger("SupervisorAgent")


class SupervisorAgent:
    """Orchestrates tasks between ChatGPT WebAgents and Cursor workers."""

    def __init__(self, config: AppConfig):
        self.config = config
        default_directive = Path("runtime/human_directive.json")
        default_results = Path("runtime/supervisor_results.json")
        default_blob_storage = Path("runtime/local_blob")

        directive_rel_path = getattr(config.paths, "human_directive", default_directive)
        results_rel_path = getattr(config.paths, "supervisor_results", default_results)
        blob_rel_path = getattr(
            config.paths, "local_blob_storage", default_blob_storage
        )

        self.directive_path = str(config.project_root / directive_rel_path)
        self.results_output_path = str(config.project_root / results_rel_path)
        local_blob_path = str(config.project_root / blob_rel_path)

        self.channel = LocalBlobChannel(base_dir=local_blob_path)
        self.dispatched = set()

    def load_directives(self):
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
        from ..core.config import load_app_config

        config = load_app_config()
        if not config:
            raise ValueError(
                "Failed to load AppConfig for SupervisorAgent standalone run."
            )
    except Exception as e:
        logging.error(f"Cannot start SupervisorAgent standalone: {e}")
        exit(1)

    agent = SupervisorAgent(config=config)
    agent.run_loop()
