#!/usr/bin/env python3
"""
scripts/testing/claim_one_task_agent_002.py

Simulates Agent 002 claiming exactly one PENDING task from JSON task lists.
Finds the first PENDING task, marks it as CLAIMED, adds claimed_by, saves the file.

MOVED FROM: src/dreamos/tools/scripts/ by Agent 5 (2025-04-28)
"""

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Define project root dynamically
# Assumes script is in PROJECT_ROOT/scripts/testing
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TASKS_DIR = PROJECT_ROOT / "tasks"  # Default to top-level tasks dir
DEFAULT_AGENT_ID = "agent_002"


def claim_one_task(tasks_dir: Path, agent_id: str):
    logging.info(
        f"Agent '{agent_id}' attempting to claim one PENDING task in {tasks_dir}..."
    )
    if not tasks_dir.is_dir():
        logging.error(f"Tasks directory not found: {tasks_dir}")
        return None

    for file_path in sorted(tasks_dir.glob("*.json")):
        if (
            file_path.name.endswith("schema.json")
            or file_path.name == "tasks_deduplicated.json"
        ):  # Skip schema/output files
            continue

        logging.debug(f"Checking file: {file_path.name}")
        tasks = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tasks = json.load(f)
            if not isinstance(tasks, list):  # Expect a list of tasks
                logging.warning(
                    f"Skipping file with non-list structure: {file_path.name}"
                )
                continue
        except json.JSONDecodeError:
            logging.warning(f"Skipping invalid JSON file: {file_path.name}")
            continue
        except Exception as e:
            logging.warning(f"Error reading file {file_path.name}: {e}")
            continue

        updated = False
        claimed_task_id = None
        for task in tasks:
            if isinstance(task, dict) and task.get("status", "").upper() == "PENDING":
                task["status"] = "CLAIMED"
                task["claimed_by"] = agent_id
                task["claimed_at_utc"] = datetime.now(timezone.utc).isoformat()
                updated = True
                claimed_task_id = task.get("task_id", task.get("id", "UNKNOWN_ID"))
                logging.info(
                    f"Agent '{agent_id}' claimed task '{claimed_task_id}' in {file_path.name}"  # noqa: E501
                )
                break  # Claim only one task per file scan

        if updated:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(tasks, f, indent=2, ensure_ascii=False)
                logging.debug(f"Successfully updated file: {file_path.name}")
                return claimed_task_id  # Return the ID of the claimed task
            except Exception as e:
                logging.error(f"Failed to write updates to {file_path.name}: {e}")
                # Should we revert the in-memory change? For simplicity, no.
                return None  # Indicate failure

    logging.info(f"Agent '{agent_id}' found no PENDING tasks to claim.")
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Simulate an agent claiming one PENDING task."
    )
    parser.add_argument(
        "--tasks-dir",
        default=str(DEFAULT_TASKS_DIR),
        type=Path,
        help=f"Directory containing task JSON files (default: {DEFAULT_TASKS_DIR})",
    )
    parser.add_argument(
        "--agent-id",
        default=DEFAULT_AGENT_ID,
        help=f"The ID of the agent claiming the task (default: {DEFAULT_AGENT_ID})",
    )
    args = parser.parse_args()

    claimed_id = claim_one_task(tasks_dir=args.tasks_dir, agent_id=args.agent_id)
    if claimed_id:
        print(f"Claimed Task ID: {claimed_id}")  # Print ID for potential scripting use
        exit(0)
    else:
        # No task claimed or error occurred
        exit(1)
