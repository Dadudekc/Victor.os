#!/usr/bin/env python3
"""
agents/autofix_agent.py

AutoFixerAgent for Dream.OS: continuously polls for 'autofix' tasks,
invokes the v7 orchestrator loop, handles errors/back-off, and shuts down gracefully.
"""
import time
import random
import signal
import sys
import logging

from dream_os.services.task_nexus import get_all_tasks, claim_task
from orchestrator import run_cycle
from config import Config

# Agent shutdown flag
shutdown_flag = False


def _signal_handler(sig, frame):
    global shutdown_flag
    logging.info("Received shutdown signal: %s", sig)
    shutdown_flag = True


def main(
    agent_id: str = None,
    poll_interval: float = 5.0,
    backoff_base: float = 1.0,
    backoff_max: float = 60.0
) -> None:
    """
    Main loop for the AutoFixerAgent.
    - Polls for 'autofix' tasks
    - Claims tasks via TaskNexus
    - Executes run_cycle(task_context)
    - Implements exponential back-off and jitter on errors
    - Responds to SIGINT/SIGTERM for graceful shutdown
    """
    agent_id = agent_id or Config.AGENT_ID
    # Setup signal handlers for graceful exit
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    backoff = backoff_base
    logging.info("AutoFixerAgent starting for agent '%s'", agent_id)

    while not shutdown_flag:
        try:
            tasks = get_all_tasks()
            for task in tasks:
                if task.get("type") != "autofix":
                    continue
                # Attempt to claim the task
                if not claim_task(agent_id):
                    continue
                context = task.get("content", {}) or {}
                task_id = task.get("id")
                logging.info("Claimed autofix task %s, context=%s", task_id, context)
                try:
                    result = run_cycle(context)
                    logging.info("run_cycle result for %s: %s", task_id, result)
                except Exception as e:
                    logging.exception("Error during run_cycle for %s: %s", task_id, e)
                # Reset backoff on success or handled failure
                backoff = backoff_base
            # No tasks or after processing, sleep with jitter
            sleep_time = poll_interval + random.uniform(0, poll_interval)
            time.sleep(sleep_time)
        except Exception as e:
            logging.exception("AutoFixerAgent encountered error: %s", e)
            # Exponential back-off with cap
            delay = backoff + random.uniform(0, backoff)
            time.sleep(delay)
            backoff = min(backoff * 2, backoff_max)

    logging.info("AutoFixerAgent shutting down gracefully.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    main() 