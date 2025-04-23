from dream_mode.task_nexus.task_nexus import TaskNexus
import logging
import json

logger = logging.getLogger(__name__)

class TheaAutoPlanner:
    """
    TheaAutoPlanner ingests failure feedback and generates new directives
    to improve system stability.
    """
    def __init__(self, nexus: TaskNexus = None, task_file: str = "runtime/task_list.json"):
        # Initialize TaskNexus for adding new tasks
        self.nexus = nexus or TaskNexus(task_file=task_file)
        logger.info("TheaAutoPlanner initialized.")

    def analyze_feedback_and_generate_next(self, feedback_list: list) -> list:
        """
        Analyze feedback entries and produce a list of new task directives.

        Each directive is a dict appropriate for TaskNexus.add_task().
        """
        directives = []
        # Attempt to read per-agent stats to guide directives
        stats_path = 'runtime/agent_stats.json'
        try:
            with open(stats_path, 'r', encoding='utf-8') as sf:
                stats = json.load(sf)
        except Exception:
            stats = {}
        # If any failures recorded, schedule a retry of failed tasks
        failed_count = stats.get('failed', 0)
        if failed_count > 0:
            directive = {
                'task_id': 'retry_failed_tasks',
                'task_type': 'recovery',
                'action': 'Retry previously failed tasks based on recent stats.',
                'params': {}
            }
            directives.append(directive)
        logger.info(f"Generated {len(directives)} directives from feedback and stats.")
        return directives

    def inject_task(self, directive: dict) -> None:
        """
        Inject a new directive into the task nexus for execution.
        """
        try:
            self.nexus.add_task(directive)
            logger.info(f"Injected new directive: {directive.get('id')}")
        except Exception as e:
            logger.error(f"Failed to inject directive {directive}: {e}", exc_info=True) 