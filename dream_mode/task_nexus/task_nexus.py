import os
import json
import threading
from collections import Counter

class TaskNexus:
    def __init__(self, task_file="runtime/task_list.json"):
        # Path to the shared task list file
        self.task_file = task_file
        # Lock to synchronize file writes
        self._lock = threading.Lock()
        # Load existing tasks or start with empty list
        self.tasks = self._load()

    def _load(self):
        # Return list of tasks from file, or empty list if missing
        if not os.path.exists(self.task_file):
            return []
        with open(self.task_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save(self):
        # Ensure directory exists
        dirpath = os.path.dirname(self.task_file)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)
        # Write tasks to file
        with open(self.task_file, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, indent=2)

    def get_next_task(self, agent_id=None, type_filter=None):
        """
        Claim and return the next pending task, optionally filtered by type.
        Marks the task as 'claimed' and records the agent who claimed it.
        """
        with self._lock:
            # Reload tasks to get latest state
            self.tasks = self._load()
            for task in self.tasks:
                if task.get("status") == "pending":
                    if type_filter and task.get("type") != type_filter:
                        continue
                    # Claim this task
                    task["status"] = "claimed"
                    if agent_id:
                        task["claimed_by"] = agent_id
                    self._save()
                    return task
        return None

    def add_task(self, task_dict):
        """
        Add a new task to the queue with default status 'pending'.
        """
        with self._lock:
            self.tasks = self._load()
            task_dict.setdefault("status", "pending")
            self.tasks.append(task_dict)
            self._save()

    def update_task_status(self, task_id, status):
        """
        Update the status of a task by its ID. Returns True on success.
        """
        with self._lock:
            self.tasks = self._load()
            for task in self.tasks:
                if task.get("id") == task_id:
                    task["status"] = status
                    self._save()
                    return True
        return False

    def get_all_tasks(self, status=None):
        """
        Return all tasks, optionally filtered by status.
        """
        # Always load fresh state
        self.tasks = self._load()
        if status is not None:
            return [t for t in self.tasks if t.get("status") == status]
        return list(self.tasks)

    def stats(self):
        """
        Return a Counter of task statuses for dashboarding.
        """
        # Load latest tasks
        self.tasks = self._load()
        return Counter(task.get("status", "unknown") for task in self.tasks) 