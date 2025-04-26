import glob
import os
import json
import logging

from dream_mode.task_nexus.task_nexus import TaskNexus
from agents.core.thea_auto_planner import TheaAutoPlanner

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def load_recent_feedback(limit: int = 5) -> list:
    """
    Load the most recent failure analysis JSON files for Thea.
    """
    pattern = os.path.join('dream_logs', 'feedback', '*.json')
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)[:limit]
    feedback_list = []
    for path in files:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                feedback_list.append(json.load(f))
        except Exception as e:
            logger.error(f"Failed to load feedback file {path}: {e}")
    logger.info(f"Loaded {len(feedback_list)} feedback entries.")
    return feedback_list


def inject_feedback_to_thea(limit: int = 5) -> None:
    """
    Ingest recent feedback into TheaAutoPlanner to generate new directives.
    """
    feedback = load_recent_feedback(limit)
    planner = TheaAutoPlanner()
    directives = planner.analyze_feedback_and_generate_next(feedback)
    logger.info(f"Injecting {len(directives)} new directives into TaskNexus...")
    for directive in directives:
        planner.inject_task(directive)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Ingest feedback into TheaAutoPlanner')
    parser.add_argument('--limit', type=int, default=5, help='Number of recent feedback files to load')
    args = parser.parse_args()
    inject_feedback_to_thea(limit=args.limit) 
