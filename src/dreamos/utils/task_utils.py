from pathlib import Path
from typing import Any, Optional, List
from dreamos.utils.base import load_json_file, save_json_file

def read_tasks(task_list_path: Any) -> Optional[List[dict]]:
    """Read tasks list from JSON file."""
    try:
        tasks = load_json_file(Path(task_list_path))
        # Ensure failure_count field exists
        for t in tasks:
            if 'failure_count' not in t:
                t['failure_count'] = 0
        return tasks
    except Exception:
        return None


def write_tasks(task_list_path: Any, tasks: List[dict]) -> None:
    """Write tasks list to JSON file."""
    save_json_file(tasks, Path(task_list_path))


def update_task_status(task_list_path: Any, task_id: str, status: str, **kwargs) -> bool:
    """Update a task's status and optionally increment failure count."""
    path = Path(task_list_path)
    try:
        tasks = load_json_file(path)
        updated = False
        for t in tasks:
            if 'failure_count' not in t:
                t['failure_count'] = 0
            if t.get('task_id') == task_id:
                t['status'] = status
                # Increment failure count when rescue is pending
                if status == 'RESCUE_PENDING':
                    t['failure_count'] += 1
                updated = True
        if updated:
            save_json_file(tasks, path)
        return updated
    except Exception:
        return False 
