import os
import json
import threading
from collections import Counter
import time
from typing import Dict, List

class TaskNexus:
    def __init__(self, task_file="runtime/task_list.json"):
        # Path to the shared task list file
        self.task_file = task_file
        # Lock to synchronize file writes and agent registry
        self._lock = threading.RLock()
        # Load existing tasks or start with empty list
        self.tasks = self._load()
        # Agent registry file
        base_dir = os.path.dirname(self.task_file)
        self.agent_file = os.path.join(base_dir, "agent_registry.json")
        # Load existing agent heartbeats
        self.agents: Dict[str, float] = self._load_agents()
        # Heartbeat TTL in seconds (expire agents after this much inactivity)
        self.heartbeat_ttl = int(os.getenv("HEARTBEAT_TTL_SECONDS", "60"))

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

    def _load_agents(self) -> Dict[str, float]:
        # Load agent heartbeat registry
        if not os.path.exists(self.agent_file):
            return {}
        try:
            with open(self.agent_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_agents(self) -> None:
        # Ensure directory exists
        dirpath = os.path.dirname(self.agent_file)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)
        # Write agent registry
        with open(self.agent_file, 'w', encoding='utf-8') as f:
            json.dump(self.agents, f, indent=2)

    def record_heartbeat(self, agent_name: str, timestamp: float = None) -> None:
        """
        Record or update the heartbeat timestamp for the given agent.
        """
        if timestamp is None:
            timestamp = time.time()
        with self._lock:
            # Reload agents to get latest state
            self.agents = self._load_agents()
            self.agents[agent_name] = timestamp
            self._save_agents()

    def get_all_registered_agents(self) -> Dict[str, float]:
        """
        Return a dict of agent names to last heartbeat timestamps.
        """
        with self._lock:
            # Reload agents and purge stale entries
            self.agents = self._load_agents()
            now = time.time()
            stale = [a for a, ts in self.agents.items() if now - ts > self.heartbeat_ttl]
            for a in stale:
                del self.agents[a]
            # Save updated registry
            self._save_agents()
            return dict(self.agents)

    def get_next_task(self, agent_id=None, type_filter=None):
        """
        Claim and return the next pending task, optionally filtered by type.
        Marks the task as 'claimed' and records the agent who claimed it.
        """
        with self._lock:
            # Reload tasks to get latest state
            self.tasks = self._load()
            # Purge stale claimed tasks (agents with expired heartbeats)
            active_agents = set(self.get_all_registered_agents().keys())
            for task in self.tasks:
                if task.get("status") == "claimed" and task.get("claimed_by") not in active_agents:
                    task["status"] = "pending"
                    task.pop("claimed_by", None)
            # Save any unclaimed tasks
            self._save()
            # Find next pending task
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

    def update_task_status(self, task_id, status, agent_id=None):
        """
        Update the status of a task by its ID. Returns True on success.
        """
        with self._lock:
            self.tasks = self._load()
            for task in self.tasks:
                # match by 'id' or 'task_id'
                if task.get("id") == task_id or task.get("task_id") == task_id:
                    task["status"] = status
                    # Record which agent completed the task if provided
                    if agent_id is not None and status.lower() == "completed":
                        task["completed_by"] = agent_id
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

    def reclaim_stale_tasks(self, stale_after: float = 60.0) -> List[Dict]:
        """
        Scan for tasks in 'claimed' state whose claiming agent heartbeat is older than stale_after seconds,
        reset them to 'pending', remove 'claimed_by', and return the list of reclaimed tasks.
        """
        reclaimed = []
        with self._lock:
            now = time.time()
            # Reload tasks and agents state
            self.tasks = self._load()
            self.agents = self._load_agents()
            for task in self.tasks:
                if task.get("status") == "claimed":
                    agent = task.get("claimed_by")
                    last_hb = self.agents.get(agent)
                    if last_hb is None or (now - last_hb) > stale_after:
                        # Mark task as unclaimed
                        task["status"] = "pending"
                        task.pop("claimed_by", None)
                        reclaimed.append(task)
            if reclaimed:
                self._save()
        return reclaimed 