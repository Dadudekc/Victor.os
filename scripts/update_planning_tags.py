#!/usr/bin/env python3
"""
Planning Tag Updater for Dream.OS

This utility adds or updates planning_step tags in episode YAML files
and tasks to comply with the Planning + Context Management Protocol.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EPISODES_DIR = PROJECT_ROOT / "episodes"
RUNTIME_TASKS_DIR = PROJECT_ROOT / "runtime" / "tasks"


def load_yaml_file(file_path: Path) -> Dict:
    """Load YAML file contents."""
    try:
        import yaml
        
        with open(file_path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error loading YAML file {file_path}: {e}")
        return {}


def save_yaml_file(file_path: Path, data: Dict) -> bool:
    """Save YAML file contents."""
    try:
        import yaml
        
        with open(file_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
        
        print(f"Updated {file_path}")
        return True
    except Exception as e:
        print(f"Error saving YAML file {file_path}: {e}")
        return False


def load_json_file(file_path: Path) -> Dict:
    """Load JSON file contents."""
    try:
        import json
        
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON file {file_path}: {e}")
        return {}


def save_json_file(file_path: Path, data: Dict) -> bool:
    """Save JSON file contents."""
    try:
        import json
        
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"Updated {file_path}")
        return True
    except Exception as e:
        print(f"Error saving JSON file {file_path}: {e}")
        return False


def update_episode_yaml(episode_file: Path, planning_stage: int) -> bool:
    """Update episode YAML with planning_stage."""
    data = load_yaml_file(episode_file)
    
    if not data:
        return False
    
    # Update planning_stage
    data["planning_stage"] = planning_stage
    
    # Update tasks with planning_step if they exist
    if "tasks" in data:
        for task in data["tasks"]:
            if isinstance(task, dict) and "planning_step" not in task:
                task["planning_step"] = planning_stage
    
    # Update task_board with planning_step if it exists
    if "task_board" in data:
        for task_id, task in data["task_board"].items():
            if isinstance(task, dict) and "planning_step" not in task:
                task["planning_step"] = planning_stage
    
    return save_yaml_file(episode_file, data)


def update_task_json(task_file: Path, planning_step: int, task_filter: Optional[str] = None) -> bool:
    """Update tasks in a JSON file with planning_step."""
    data = load_json_file(task_file)
    
    if not data:
        return False
    
    # Check if the data is a list of tasks
    if isinstance(data, list):
        for task in data:
            if isinstance(task, dict):
                # Apply task filter if provided
                if task_filter and task_filter not in task.get("task_id", ""):
                    continue
                
                if "planning_step" not in task:
                    task["planning_step"] = planning_step
    
    # Check if the data is a dictionary with tasks
    elif isinstance(data, dict):
        # If it's a dictionary of tasks (key: task)
        if all(isinstance(task, dict) for task in data.values()):
            for task_id, task in data.items():
                # Apply task filter if provided
                if task_filter and task_filter not in task_id:
                    continue
                
                if "planning_step" not in task:
                    task["planning_step"] = planning_step
        
        # If it has a 'tasks' list
        elif "tasks" in data and isinstance(data["tasks"], list):
            for task in data["tasks"]:
                if isinstance(task, dict):
                    # Apply task filter if provided
                    if task_filter and task_filter not in task.get("task_id", ""):
                        continue
                    
                    if "planning_step" not in task:
                        task["planning_step"] = planning_step
    
    return save_json_file(task_file, data)


def update_episode(episode_id: str, planning_stage: int) -> bool:
    """Update an episode and its tasks with planning information."""
    # Find episode file
    episode_file = EPISODES_DIR / f"episode-{episode_id}.yaml"
    if not episode_file.exists():
        episode_file = EPISODES_DIR / f"episode_{episode_id}.yaml"
    
    if not episode_file.exists():
        print(f"Episode file for ID {episode_id} not found")
        return False
    
    # Update episode YAML
    if not update_episode_yaml(episode_file, planning_stage):
        print(f"Failed to update episode file {episode_file}")
        return False
    
    # Find and update related task files
    task_file = RUNTIME_TASKS_DIR / "episodes" / f"parsed_episode_{episode_id}_tasks.json"
    if task_file.exists():
        if not update_task_json(task_file, planning_stage):
            print(f"Warning: Failed to update task file {task_file}")
    
    print(f"Successfully updated episode {episode_id} with planning stage {planning_stage}")
    return True


def update_all_tasks(planning_step: int) -> bool:
    """Update all task files with planning step."""
    success = True
    
    # Update working tasks
    working_tasks_file = RUNTIME_TASKS_DIR / "working_tasks.json"
    if working_tasks_file.exists():
        if not update_task_json(working_tasks_file, planning_step):
            print(f"Warning: Failed to update working tasks file {working_tasks_file}")
            success = False
    
    # Update future tasks
    future_tasks_file = RUNTIME_TASKS_DIR / "future_tasks.json"
    if future_tasks_file.exists():
        if not update_task_json(future_tasks_file, planning_step):
            print(f"Warning: Failed to update future tasks file {future_tasks_file}")
            success = False
    
    # Update agent-claimed tasks
    working_dir = RUNTIME_TASKS_DIR / "working"
    if working_dir.exists():
        for task_file in working_dir.glob("working_tasks_agent-*_claimed.json"):
            if not update_task_json(task_file, planning_step):
                print(f"Warning: Failed to update agent claimed tasks file {task_file}")
                success = False
    
    print(f"Finished updating task files with planning step {planning_step}")
    return success


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Dream.OS Planning Tag Updater")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Update episode command
    episode_parser = subparsers.add_parser("episode", help="Update episode with planning stage")
    episode_parser.add_argument("episode_id", help="Episode ID (e.g., '08')")
    episode_parser.add_argument("--planning-stage", "-p", type=int, required=True, choices=[1, 2, 3, 4], 
                              help="Planning stage (1-4)")
    
    # Update tasks command
    tasks_parser = subparsers.add_parser("tasks", help="Update tasks with planning step")
    tasks_parser.add_argument("--planning-step", "-p", type=int, required=True, choices=[1, 2, 3, 4], 
                            help="Planning step (1-4)")
    tasks_parser.add_argument("--task-filter", "-f", help="Only update tasks containing this string (optional)")
    
    # Update both command
    both_parser = subparsers.add_parser("both", help="Update both episode and tasks")
    both_parser.add_argument("episode_id", help="Episode ID (e.g., '08')")
    both_parser.add_argument("--planning-stage", "-p", type=int, required=True, choices=[1, 2, 3, 4], 
                           help="Planning stage (1-4)")
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    if args.command == "episode":
        success = update_episode(args.episode_id, args.planning_stage)
    elif args.command == "tasks":
        success = update_all_tasks(args.planning_step)
    elif args.command == "both":
        success = update_episode(args.episode_id, args.planning_stage)
        if success:
            success = update_all_tasks(args.planning_stage)
    else:
        print("No command specified. Use --help for usage information.")
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 