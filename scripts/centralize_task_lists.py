#!/usr/bin/env python3
"""
Centralize Task Lists Script

This script centralizes all task lists into a single location:
- Merges tasks from working_tasks.json, completed_tasks.json, task_backlog.json, task_ready_queue.json
- Extracts tasks from episode YAML files
- Creates a central task_board.json file with all tasks
- Maintains original task status and metadata
- Creates backups of original files
- Updates references in onboarding documentation
"""

import argparse
import datetime
import json
import logging
import os
import shutil
import sys
import yaml
import glob
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# --- Configuration ---
DEFAULT_BACKUP_DIR = "runtime/task_migration_backups"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
CENTRAL_TASK_DIR = "runtime/central_tasks"
CENTRAL_TASK_FILE = "task_board.json"

# --- Logger Setup ---
logger = logging.getLogger("CentralizeTaskLists")

def setup_logging(log_level_str: str = "INFO", log_file: Optional[Path] = None):
    """Configures logging for the script."""
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logger.setLevel(log_level)

    formatter = logging.Formatter(LOG_FORMAT)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if log_file:
        # File handler
        fh = logging.FileHandler(log_file)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        logger.info(f"Logging to file: {log_file}")

def create_backup(source_files: List[Path], backup_base_dir: Path) -> Optional[Path]:
    """Creates timestamped backups of source files. Returns backup directory path or None on failure."""
    logger.info(f"Attempting to back up files: {', '.join(map(str, source_files))}")
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = backup_base_dir / f"backup_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        for src_file in source_files:
            if src_file.exists():
                shutil.copy2(src_file, backup_dir / src_file.name)
                logger.info(f"Backed up {src_file} to {backup_dir / src_file.name}")
            else:
                logger.warning(f"Source file {src_file} not found for backup. Skipping.")
        logger.info(f"Backup completed in directory: {backup_dir}")
        return backup_dir
    except Exception as e:
        logger.error(f"Backup failed: {e}", exc_info=True)
        return None

def read_json_file(file_path: Path) -> List[Dict]:
    """Reads a JSON file and returns a list of dictionaries. Handles errors."""
    tasks = []
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}. Returning empty list.")
        return tasks
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
            if isinstance(content, list):
                tasks = content
            else:
                logger.error(f"Expected list in {file_path}, got {type(content)}. Cannot process.")
                return []
        logger.info(f"Successfully read {len(tasks)} tasks from {file_path}")
        return tasks
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {file_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to read or parse {file_path}: {e}", exc_info=True)
        return []

def extract_tasks_from_episodes(episodes_dir: Path = Path("episodes")) -> List[Dict]:
    """
    Extracts tasks from episode YAML files.
    Returns a list of task dictionaries.
    """
    tasks = []
    episode_files = list(episodes_dir.glob("*.yaml")) + list(episodes_dir.glob("*.yml"))
    
    if not episode_files:
        logger.warning(f"No episode files found in {episodes_dir}")
        return tasks
    
    for episode_file in episode_files:
        try:
            logger.info(f"Processing episode file: {episode_file}")
            with open(episode_file, "r", encoding="utf-8") as f:
                episode_data = yaml.safe_load(f)
            
            # Extract episode metadata
            episode_id = episode_data.get("id", os.path.splitext(episode_file.name)[0])
            episode_title = episode_data.get("title", "Unknown Episode")
            
            # Look for task board or tasks section
            task_board = episode_data.get("task_board", [])
            if isinstance(task_board, list):
                # List of tasks
                for task in task_board:
                    if not isinstance(task, dict):
                        continue
                    
                    # Create a standardized task
                    task_id = task.get("task_id", task.get("id", f"EP-{episode_id}-{len(tasks) + 1}"))
                    
                    standardized_task = {
                        "task_id": task_id,
                        "name": task.get("name", task.get("intent", f"Task from {episode_title}")),
                        "description": task.get("description", ""),
                        "status": task.get("status", "PENDING"),
                        "priority": task.get("priority", "MEDIUM"),
                        "assigned_agent": task.get("owner", task.get("assigned_to", None)),
                        "_source_episode": str(episode_file),
                        "_episode_id": episode_id,
                        "_episode_title": episode_title,
                        "history": [{
                            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "agent": "CentralizeTaskListsScript",
                            "action": "EXTRACTED_FROM_EPISODE",
                            "details": f"Task extracted from episode file {episode_file}"
                        }]
                    }
                    
                    # Copy any additional fields
                    for key, value in task.items():
                        if key not in standardized_task and key not in ["id", "owner", "intent"]:
                            standardized_task[key] = value
                    
                    tasks.append(standardized_task)
            elif isinstance(task_board, dict):
                # Dictionary with task entries
                for task_id, task_data in task_board.items():
                    if not isinstance(task_data, dict):
                        continue
                    
                    standardized_task = {
                        "task_id": task_id,
                        "name": task_data.get("name", task_data.get("intent", f"Task from {episode_title}")),
                        "description": task_data.get("description", ""),
                        "status": task_data.get("status", "PENDING"),
                        "priority": task_data.get("priority", "MEDIUM"),
                        "assigned_agent": task_data.get("owner", task_data.get("assigned_to", None)),
                        "_source_episode": str(episode_file),
                        "_episode_id": episode_id,
                        "_episode_title": episode_title,
                        "history": [{
                            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "agent": "CentralizeTaskListsScript",
                            "action": "EXTRACTED_FROM_EPISODE",
                            "details": f"Task extracted from episode file {episode_file}"
                        }]
                    }
                    
                    # Copy any additional fields
                    for key, value in task_data.items():
                        if key not in standardized_task and key not in ["owner", "intent"]:
                            standardized_task[key] = value
                    
                    tasks.append(standardized_task)
            
            # Look for milestones section which might contain tasks
            milestones = episode_data.get("milestones", [])
            if isinstance(milestones, list):
                for milestone in milestones:
                    if not isinstance(milestone, dict):
                        continue
                    
                    # Create a task from milestone
                    milestone_id = milestone.get("id", f"MS-{episode_id}-{len(tasks) + 1}")
                    
                    milestone_task = {
                        "task_id": milestone_id,
                        "name": milestone.get("title", "Unnamed Milestone"),
                        "description": milestone.get("description", ""),
                        "status": "PENDING",  # Milestones typically don't have status
                        "priority": "HIGH",   # Milestones are typically high priority
                        "task_type": "MILESTONE",
                        "_source_episode": str(episode_file),
                        "_episode_id": episode_id,
                        "_episode_title": episode_title,
                        "_is_milestone": True,
                        "history": [{
                            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "agent": "CentralizeTaskListsScript",
                            "action": "EXTRACTED_FROM_EPISODE_MILESTONE",
                            "details": f"Milestone extracted from episode file {episode_file}"
                        }]
                    }
                    
                    tasks.append(milestone_task)
            
            logger.info(f"Extracted {len(tasks)} tasks from episode {episode_file}")
            
        except Exception as e:
            logger.error(f"Error processing episode file {episode_file}: {e}", exc_info=True)
    
    logger.info(f"Total tasks extracted from all episodes: {len(tasks)}")
    return tasks

def normalize_task(task: Dict, source_file: str) -> Dict:
    """Normalizes a task to ensure consistent format across all sources."""
    # Add source information
    task["_source"] = source_file
    
    # Ensure task_id exists
    if "task_id" not in task:
        if "id" in task:
            task["task_id"] = task["id"]
        else:
            # Generate a random task_id if none exists
            import uuid
            task["task_id"] = f"MIGRATED-{uuid.uuid4()}"
            logger.warning(f"Generated task_id {task['task_id']} for task without ID from {source_file}")
    
    # Add migration timestamp
    task["_migrated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Add history entry for migration if history exists
    if "history" in task and isinstance(task["history"], list):
        task["history"].append({
            "timestamp": task["_migrated_at"],
            "agent": "CentralizeTaskListsScript",
            "action": "MIGRATED",
            "details": f"Task migrated from {source_file} to central task board"
        })
    else:
        task["history"] = [{
            "timestamp": task["_migrated_at"],
            "agent": "CentralizeTaskListsScript",
            "action": "MIGRATED",
            "details": f"Task migrated from {source_file} to central task board"
        }]
    
    return task

def merge_tasks(source_files: Dict[str, Path], output_file: Path, include_episodes: bool = True, dry_run: bool = False) -> Tuple[int, int]:
    """
    Merges tasks from multiple source files into a single output file.
    Returns tuple of (success_count, error_count)
    """
    all_tasks = []
    task_ids_seen = set()
    success_count = 0
    error_count = 0
    
    # Read and normalize tasks from each source
    for source_name, source_path in source_files.items():
        tasks = read_json_file(source_path)
        for task in tasks:
            try:
                normalized_task = normalize_task(task, source_name)
                task_id = normalized_task.get("task_id")
                
                if task_id in task_ids_seen:
                    logger.warning(f"Duplicate task_id {task_id} found in {source_name}. Using first occurrence only.")
                    error_count += 1
                    continue
                
                all_tasks.append(normalized_task)
                task_ids_seen.add(task_id)
                success_count += 1
            except Exception as e:
                logger.error(f"Error processing task from {source_name}: {e}", exc_info=True)
                error_count += 1
    
    # Extract and add tasks from episode files if requested
    if include_episodes:
        episode_tasks = extract_tasks_from_episodes()
        for task in episode_tasks:
            try:
                task_id = task.get("task_id")
                
                if task_id in task_ids_seen:
                    logger.warning(f"Duplicate task_id {task_id} found in episode. Using first occurrence only.")
                    error_count += 1
                    continue
                
                all_tasks.append(task)
                task_ids_seen.add(task_id)
                success_count += 1
            except Exception as e:
                logger.error(f"Error processing task from episode: {e}", exc_info=True)
                error_count += 1
    
    logger.info(f"Merged {success_count} tasks with {error_count} errors")
    
    if not dry_run:
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write merged tasks to output file
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(all_tasks, f, indent=2)
            logger.info(f"Successfully wrote {len(all_tasks)} tasks to {output_file}")
        except Exception as e:
            logger.error(f"Failed to write merged tasks to {output_file}: {e}", exc_info=True)
            error_count += 1
    else:
        logger.info(f"Dry run: Would write {len(all_tasks)} tasks to {output_file}")
    
    return success_count, error_count

def update_documentation(central_task_path: Path, dry_run: bool = False) -> bool:
    """
    Updates references to task files in documentation.
    Returns True if successful, False otherwise.
    """
    # List of documentation files to update
    doc_files = [
        Path("docs/agents/AGENT_ONBOARDING_CHECKLIST.md"),
        Path("docs/agents/onboarding/AGENT_ONBOARDING_CHECKLIST.md"),
        Path("docs/api/integrations/legacy_tools_docs/project_board_interaction.md")
    ]
    
    success = True
    for doc_file in doc_files:
        if not doc_file.exists():
            logger.warning(f"Documentation file {doc_file} not found. Skipping.")
            continue
        
        try:
            with open(doc_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Replace references to old task files with central task file
            updated_content = content
            replacements = [
                ("runtime/agent_comms/project_boards/working_tasks.json", str(central_task_path)),
                ("runtime/agent_comms/project_boards/completed_tasks.json", str(central_task_path)),
                ("runtime/agent_comms/project_boards/task_backlog.json", str(central_task_path)),
                ("runtime/agent_comms/project_boards/task_ready_queue.json", str(central_task_path)),
                ("working_tasks.json", CENTRAL_TASK_FILE),
                ("completed_tasks.json", CENTRAL_TASK_FILE),
                ("task_backlog.json", CENTRAL_TASK_FILE),
                ("task_ready_queue.json", CENTRAL_TASK_FILE)
            ]
            
            for old, new in replacements:
                updated_content = updated_content.replace(old, new)
            
            if updated_content != content:
                if not dry_run:
                    with open(doc_file, "w", encoding="utf-8") as f:
                        f.write(updated_content)
                    logger.info(f"Updated references in {doc_file}")
                else:
                    logger.info(f"Dry run: Would update references in {doc_file}")
            else:
                logger.info(f"No references to update in {doc_file}")
        
        except Exception as e:
            logger.error(f"Failed to update documentation file {doc_file}: {e}", exc_info=True)
            success = False
    
    return success

def create_readme(central_task_dir: Path, dry_run: bool = False) -> bool:
    """
    Creates a README.md file in the central task directory.
    Returns True if successful, False otherwise.
    """
    readme_content = """# Centralized Task Board

This directory contains the centralized task board for Dream.OS agents.

## Files

- `task_board.json`: The main task board containing all tasks from:
  - Previously separate task files (working_tasks.json, completed_tasks.json, task_backlog.json, task_ready_queue.json)
  - Tasks extracted from episode files

## Task Structure

Tasks follow a standardized format with these key fields:

```
{{
  "task_id": "UNIQUE_TASK_ID",
  "name": "Task name",
  "description": "Task description",
  "status": "PENDING|WORKING|COMPLETED|FAILED|BLOCKED",
  "priority": "HIGH|MEDIUM|LOW",
  "assigned_agent": "AgentID",
  "history": [
    {{
      "timestamp": "ISO-8601 timestamp",
      "agent": "AgentID",
      "action": "ACTION",
      "details": "Details of the action"
    }}
  ]
}}
```

## Migration Information

Tasks were centralized on {date} using the `centralize_task_lists.py` script.
Original task files are backed up in {backup_dir}.

## Usage Guidelines

1. All agents should use this central task board for task management
2. Use the ProjectBoardManager API to interact with the task board
3. Maintain task history with appropriate timestamps and actions
"""
    
    readme_content = readme_content.format(
        date=datetime.datetime.now().strftime("%Y-%m-%d"),
        backup_dir=DEFAULT_BACKUP_DIR
    )
    
    readme_path = central_task_dir / "README.md"
    
    try:
        if not dry_run:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_content)
            logger.info(f"Created README.md in {central_task_dir}")
        else:
            logger.info(f"Dry run: Would create README.md in {central_task_dir}")
        return True
    except Exception as e:
        logger.error(f"Failed to create README.md in {central_task_dir}: {e}", exc_info=True)
        return False

def main():
    parser = argparse.ArgumentParser(description="Centralize task lists into a single location")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without making changes")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Set the logging level")
    parser.add_argument("--log-file", type=Path, help="Path to log file")
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR,
                        help=f"Directory for backups (default: {DEFAULT_BACKUP_DIR})")
    parser.add_argument("--output-dir", type=Path, default=CENTRAL_TASK_DIR,
                        help=f"Output directory for centralized task board (default: {CENTRAL_TASK_DIR})")
    parser.add_argument("--skip-episodes", action="store_true", help="Skip extracting tasks from episode files")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    
    # Source files to merge
    source_files = {
        "working_tasks": Path("runtime/agent_comms/project_boards/working_tasks.json"),
        "completed_tasks": Path("runtime/agent_comms/project_boards/completed_tasks.json"),
        "task_backlog": Path("runtime/agent_comms/project_boards/task_backlog.json"),
        "task_ready_queue": Path("runtime/agent_comms/project_boards/task_ready_queue.json")
    }
    
    # Output file path
    output_file = Path(args.output_dir) / CENTRAL_TASK_FILE
    
    logger.info(f"Starting task centralization {'(dry run)' if args.dry_run else ''}")
    
    # Create backups
    backup_dir = create_backup(list(source_files.values()), Path(args.backup_dir))
    if not backup_dir and not args.dry_run:
        logger.error("Failed to create backups. Aborting.")
        sys.exit(1)
    
    # Merge tasks
    success_count, error_count = merge_tasks(source_files, output_file, not args.skip_episodes, args.dry_run)
    
    # Create README
    create_readme(Path(args.output_dir), args.dry_run)
    
    # Update documentation
    update_documentation(output_file, args.dry_run)
    
    logger.info(f"Task centralization {'would have ' if args.dry_run else ''}completed with {success_count} successes and {error_count} errors")
    
    if not args.dry_run:
        logger.info(f"Tasks centralized to {output_file}")
        logger.info(f"Original files backed up to {backup_dir}")
    
    if error_count > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()