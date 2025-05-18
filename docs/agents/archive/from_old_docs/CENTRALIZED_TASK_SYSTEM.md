# Dream.OS Centralized Task System

**Version:** 1.0
**Date:** {{YYYY-MM-DD}} <!-- To be filled with current date -->
**Status:** ACTIVE

## 1. Introduction & Purpose

This document defines the standardized approach to task management within Dream.OS, utilizing a centralized task system that consolidates all tasks from various sources into a single, unified task board.

The primary goals are:
*   To eliminate fragmentation of tasks across multiple files and locations
*   To provide a single source of truth for all agent tasks
*   To standardize task structure and workflow
*   To incorporate tasks from episode files alongside regular task management
*   To simplify agent onboarding and task discovery

## 2. Centralized Task Location

All Dream.OS tasks are now stored in a single location:

```
runtime/central_tasks/task_board.json
```

This file contains tasks from:
- Previously separate task files (working_tasks.json, completed_tasks.json, task_backlog.json, task_ready_queue.json)
- Tasks extracted from episode YAML files in the `episodes/` directory

## 3. Task Structure

Tasks in the centralized system follow a standardized format with these key fields:

```json
{
  "task_id": "UNIQUE_TASK_ID",
  "name": "Task name",
  "description": "Task description",
  "status": "PENDING|WORKING|COMPLETED|FAILED|BLOCKED",
  "priority": "HIGH|MEDIUM|LOW",
  "assigned_agent": "AgentID",
  "history": [
    {
      "timestamp": "ISO-8601 timestamp",
      "agent": "AgentID",
      "action": "ACTION",
      "details": "Details of the action"
    }
  ]
}
```

Additional fields may be present depending on the task source and type:
- `_source`: Indicates the original file the task came from
- `_source_episode`: For tasks extracted from episode files
- `_episode_id`: For tasks extracted from episode files
- `_episode_title`: For tasks extracted from episode files
- `_is_milestone`: Boolean flag for tasks created from episode milestones

## 4. Agent Interaction with Tasks

### 4.1. Task Discovery

Agents should check the centralized task board to discover available tasks:

```python
from pathlib import Path
import json

def load_tasks():
    task_board_path = Path("runtime/central_tasks/task_board.json")
    if not task_board_path.exists():
        return []
    
    with open(task_board_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Get all pending tasks
tasks = load_tasks()
pending_tasks = [t for t in tasks if t.get("status") == "PENDING"]
```

### 4.2. Task Claiming

When an agent claims a task, they should update the task's status and history:

```python
def claim_task(task_id, agent_id):
    task_board_path = Path("runtime/central_tasks/task_board.json")
    if not task_board_path.exists():
        return False
    
    with open(task_board_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    for task in tasks:
        if task.get("task_id") == task_id:
            task["status"] = "WORKING"
            task["assigned_agent"] = agent_id
            
            # Add history entry
            if "history" not in task or not isinstance(task["history"], list):
                task["history"] = []
            
            import datetime
            task["history"].append({
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "agent": agent_id,
                "action": "CLAIMED",
                "details": f"Task claimed by {agent_id}"
            })
            
            # Write updated tasks back to file
            with open(task_board_path, "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2)
            
            return True
    
    return False
```

### 4.3. Task Completion

When an agent completes a task, they should update the task's status and history:

```python
def complete_task(task_id, agent_id, result_summary=None):
    task_board_path = Path("runtime/central_tasks/task_board.json")
    if not task_board_path.exists():
        return False
    
    with open(task_board_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    for task in tasks:
        if task.get("task_id") == task_id:
            task["status"] = "COMPLETED"
            
            # Add result summary if provided
            if result_summary:
                task["result_summary"] = result_summary
            
            # Add history entry
            if "history" not in task or not isinstance(task["history"], list):
                task["history"] = []
            
            import datetime
            task["history"].append({
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "agent": agent_id,
                "action": "COMPLETED",
                "details": f"Task completed by {agent_id}" + (f": {result_summary}" if result_summary else "")
            })
            
            # Write updated tasks back to file
            with open(task_board_path, "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2)
            
            return True
    
    return False
```

## 5. ProjectBoardManager Integration

The existing ProjectBoardManager class has been updated to work with the centralized task system. Agents should continue to use this class for task management:

```python
from dreamos.coordination.project_board_manager import ProjectBoardManager

pbm = ProjectBoardManager()

# List pending tasks
pending_tasks = pbm.list_tasks(status="PENDING")

# Claim a task
pbm.claim_task("TASK-001", "Agent-1")

# Complete a task
pbm.complete_task("TASK-001", "Agent-1", "Task completed successfully")
```

## 6. Episode Task Integration

Tasks from episode files are now automatically integrated into the centralized task system. When new episode files are added to the `episodes/` directory, run the centralization script to update the task board:

```bash
python scripts/centralize_task_lists.py
```

This will extract tasks from episode files and add them to the centralized task board.

## 7. Migration from Previous System

The migration from the previous task system was performed using the `centralize_task_lists.py` script. This script:

1. Created backups of all original task files in `runtime/task_migration_backups/`
2. Merged tasks from all sources into the centralized task board
3. Updated documentation references to point to the new location
4. Created a README.md file in the central task directory

If you need to run the migration again, use:

```bash
python scripts/centralize_task_lists.py --dry-run
```

This will show what changes would be made without actually making them. Remove the `--dry-run` flag to perform the actual migration.

## 8. Related Protocols

This document should be understood in conjunction with:

*   `docs/agents/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
*   `docs/agents/AGENT_ONBOARDING_CHECKLIST.md`
*   `docs/api/integrations/legacy_tools_docs/project_board_interaction.md`

## 9. Document Version History

*   **v1.0 ({{YYYY-MM-DD}}):** Initial version. 