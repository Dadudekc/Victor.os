from pathlib import Path
from typing import Any, Optional, List
from dreamos.utils.base import load_json_file, save_json_file

def read_tasks(task_list_path: Any) -> Optional[List[dict]]:
    """Read tasks list from JSON file."""
    try:
        return load_json_file(Path(task_list_path))
    except Exception:
        return None


def write_tasks(task_list_path: Any, tasks: List[dict]) -> None:
    """Write tasks list to JSON file."""
    save_json_file(tasks, Path(task_list_path))


def update_task_status(task_list_path: Any, task_id: str, status: str, **kwargs) -> bool:
    """Stub: pretend to update a task's status."""
    return True 
