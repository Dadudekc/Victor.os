#!/usr/bin/env python3
"""
CLI to run TheaAutoPlanner: parse feedback and stats, generate new directives, and inject them into TaskNexus.
"""
import argparse
import json
import logging
from dream_mode.task_nexus.task_nexus import TaskNexus
from agents.thea_auto_planner import TheaAutoPlanner

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Run TheaAutoPlanner to generate new directives.')
    parser.add_argument('--feedback', help='Path to JSON feedback list (optional)', required=False)
    parser.add_argument('--task-file', default='runtime/task_list.json', help='Path to the task list file')
    args = parser.parse_args()

    # Load feedback data if provided
    if args.feedback:
        try:
            with open(args.feedback, 'r', encoding='utf-8') as f:
                feedback_list = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load feedback file {args.feedback}: {e}")
            feedback_list = []
    else:
        feedback_list = []

    # Initialize TaskNexus and planner
    nexus = TaskNexus(task_file=args.task_file)
    planner = TheaAutoPlanner(nexus=nexus, task_file=args.task_file)

    # Analyze feedback and generate directives
    directives = planner.analyze_feedback_and_generate_next(feedback_list)
    if not directives:
        logger.info("No new directives generated.")
    else:
        for directive in directives:
            planner.inject_task(directive)

if __name__ == '__main__':
    main() 