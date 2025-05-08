# src/dreamos/tools/maintenance/augment_task_tags.py
"""Script to bulk-add specific tags (e.g., monetization) to tasks in a task list.

Uses TaskNexus (or potentially ShadowTaskNexus) to load, modify, and save tasks.
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional, Set

# TODO: Need robust way to import TaskNexus/ShadowTaskNexus and Task model
# This might involve adjusting sys.path or relying on package installation

# Placeholder imports - adjust paths as needed
try:
    from dreamos.core.tasks.nexus.task_nexus import TaskNexus, Task
except ImportError:
    try:
        # Try importing ShadowTaskNexus as fallback or primary if needed
        from dreamos.agents.agent_1.shadow_task_nexus import ShadowTaskNexus as TaskNexus, Task # type: ignore
    except ImportError:
        print("ERROR: Failed to import TaskNexus or ShadowTaskNexus. Ensure dreamos package is installed or paths are correct.", file=sys.stderr)
        sys.exit(1)

logger = logging.getLogger(__name__)

# Default tags to add if not specified via args
DEFAULT_TAGS_TO_ADD = {
    "REVENUE_IMPACT": "low",
    "MARKET_READY": "false",
}

def augment_tasks_with_tags(task_file_path: Path, tags_to_add: Dict[str, str]):
    """Loads tasks, adds specified tags if missing, and saves back."""
    logger.info(f"Loading tasks from: {task_file_path}")
    # TODO: Determine whether to use TaskNexus or ShadowTaskNexus based on context or args
    nexus = TaskNexus(task_file=task_file_path)

    all_tasks = nexus.get_all_tasks() # Works with list-based Nexus
    if not all_tasks:
        logger.warning("No tasks found to augment.")
        return

    logger.info(f"Found {len(all_tasks)} tasks. Augmenting with tags: {tags_to_add}")
    updated_count = 0

    # --- EDIT START: Implement augmentation logic ---
    modified_tasks = []
    needs_save = False
    for task in all_tasks:
        task_modified = False
        # Create a dict of existing uppercase keys for quick lookup
        current_tags_dict = {}
        for tag in task.tags:
            if ':' in tag:
                key, value = tag.split(':', 1)
                current_tags_dict[key.upper()] = value

        for tag_key, default_value in tags_to_add.items():
            upper_key = tag_key.upper()
            if upper_key not in current_tags_dict:
                new_tag = f"{upper_key}:{default_value}"
                task.tags.append(new_tag)
                logger.debug(f"Adding tag '{new_tag}' to task {task.task_id}")
                task_modified = True

        if task_modified:
            # Update timestamp to reflect change
            task.updated_at = datetime.utcnow().isoformat()
            updated_count += 1
            needs_save = True

        modified_tasks.append(task) # Add task whether modified or not

    if needs_save:
        logger.info(f"Saving {updated_count} updated tasks back to {task_file_path}")
        # Replace the internal list and save
        # This assumes nexus allows direct manipulation or has a save_all method
        # For JSON nexus, modifying the list and calling _save is typical
        nexus.tasks = modified_tasks
        nexus._save()
    else:
        logger.info("No tasks required tag augmentation.")
    # --- EDIT END ---

def parse_args():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Bulk add tags to tasks.")
    parser.add_argument(
        "--task_file",
        type=Path,
        # TODO: Get default path from TaskNexus/ShadowTaskNexus or config?
        # default=DEFAULT_TASK_FILE,
        required=True, # Make required for now
        help="Path to the task JSON file (e.g., task_backlog.json, shadow_backlog.json)"
    )
    parser.add_argument(
        "--tags",
        nargs='*',
        help="Tags to add in KEY:value format (e.g., REVENUE_IMPACT:high MARKET_READY:true). Overrides defaults."
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging."
    )
    return parser.parse_args()

def main():
    """Main script execution."""
    args = parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    tags_to_process = DEFAULT_TAGS_TO_ADD.copy()
    if args.tags:
        try:
            parsed_tags = {tag.split(':')[0].upper(): tag.split(':', 1)[1] for tag in args.tags if ':' in tag}
            tags_to_process.update(parsed_tags) # Override defaults with provided tags
        except Exception:
            logger.error("Invalid format for --tags argument. Use KEY:value pairs separated by space.", exc_info=True)
            sys.exit(1)

    if not args.task_file.is_file():
        logger.error(f"Task file not found: {args.task_file}")
        sys.exit(1)

    augment_tasks_with_tags(args.task_file, tags_to_process)

if __name__ == "__main__":
    main() 