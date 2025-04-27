import os
import time
import json
import logging
from dreamos.memory.blob_channel_memory import LocalBlobChannel

logger = logging.getLogger("SupervisorAgent")
logger.setLevel(logging.INFO)

DEFAULT_DIRECTIVE_PATH = os.getenv("HUMAN_DIRECTIVE_PATH", "human_directive.json")
RESULTS_OUTPUT = os.getenv("SUPERVISOR_RESULTS_PATH", "supervisor_results.json")

class SupervisorAgent:
    """Orchestrates tasks between ChatGPT WebAgents and Cursor workers."""
    def __init__(self, directive_path=DEFAULT_DIRECTIVE_PATH):
        self.directive_path = directive_path
        self.channel = LocalBlobChannel()
        self.dispatched = set()

    def load_directives(self):
        try:
            with open(self.directive_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Support both 'tasks' and 'directives' keys
            tasks = data.get('tasks') or data.get('directives', [])
        except Exception as e:
            logger.debug(f"Failed to load directives: {e}")
            return []
        return tasks

    def dispatch_tasks(self, tasks):
        for task in tasks:
            task_id = task.get('task_id') or task.get('id')
            if not task_id or task_id in self.dispatched:
                continue
            payload = task.get('payload', task)
            logger.info(f"Dispatching task {task_id} to channel.")
            self.channel.push_task({"id": task_id, "payload": payload})
            self.dispatched.add(task_id)

    def gather_results(self):
        collected = []
        # Pull all available results
        results = self.channel.pull_results()
        while results:
            for r in results:
                logger.info(f"Collected result for {r.get('id')}")
                collected.append(r)
            results = self.channel.pull_results()
        return collected

    def save_results(self, results):
        try:
            with open(RESULTS_OUTPUT, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results written to {RESULTS_OUTPUT}")
        except Exception as e:
            logger.error(f"Failed to write results: {e}")

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
    logging.basicConfig()
    agent = SupervisorAgent()
    agent.run_loop() 
