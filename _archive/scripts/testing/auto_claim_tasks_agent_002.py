#!/usr/bin/env python3
"""
scripts/testing/auto_claim_tasks_agent_002.py

Auto-claims all PENDING tasks across JSON files in a specified directory
for a given agent, marking them as IN_PROGRESS.

MOVED FROM: src/dreamos/tools/scripts/ by Agent 5 (2025-04-28)
"""
import argparse
import json
import logging
import os
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


def auto_claim_tasks(tasks_dir: Path, agent_id: str):
    logging.info(
        f"Agent '{agent_id}' auto-claiming all PENDING tasks in {tasks_dir}..."
    )
    if not tasks_dir.is_dir():
        logging.error(f"Tasks directory not found: {tasks_dir}")
        return

    claimed_count = 0
    files_updated = 0

    for file_path in sorted(tasks_dir.glob("*.json")):
        if (
            file_path.name.endswith("schema.json")
            or file_path.name == "tasks_deduplicated.json"
        ):
            continue

        logging.debug(f"Checking file: {file_path.name}")
        tasks = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tasks = json.load(f)
            if not isinstance(tasks, list):
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

        file_needs_update = False
        file_claimed_count = 0
        for task in tasks:
            if isinstance(task, dict) and task.get("status", "").upper() == "PENDING":
                task["status"] = "IN_PROGRESS"  # Mark as IN_PROGRESS directly
                task["claimed_by"] = agent_id
                task["claimed_at_utc"] = datetime.now(timezone.utc).isoformat()
                file_needs_update = True
                file_claimed_count += 1
                claimed_task_id = task.get("task_id", task.get("id", "UNKNOWN_ID"))
                logging.debug(f"  Claimed task '{claimed_task_id}'")

        if file_needs_update:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(tasks, f, indent=2, ensure_ascii=False)
                logging.info(
                    f"Claimed {file_claimed_count} task(s) in {file_path.name}"
                )
                files_updated += 1
                claimed_count += file_claimed_count
            except Exception as e:
                logging.error(f"Failed to write updates to {file_path.name}: {e}")

    logging.info(
        f"Auto-claiming finished for agent '{agent_id}'. Claimed {claimed_count} tasks across {files_updated} files."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Auto-claim all PENDING tasks for an agent."
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
        help=f"The ID of the agent claiming the tasks (default: {DEFAULT_AGENT_ID})",
    )
    args = parser.parse_args()

    auto_claim_tasks(tasks_dir=args.tasks_dir, agent_id=args.agent_id)
