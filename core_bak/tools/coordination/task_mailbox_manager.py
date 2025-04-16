"""
D:/dream.os/_agent_coordination/agent_tools
task_mailbox_manager.py

This module implements TaskMailboxManager—a tool for atomic task claiming,
completion, and failure reporting for distributed agents working on placeholder
replacement in Dream.OS.

This is a production-ready, real-world tool. Agents can import and run this module
to:
    - Atomically claim tasks from a shared mailbox (using OS-level file moves).
    - Read tasks, process them with real logic, and write out completion results.
    - Optionally, broadcast heartbeat updates so that other agents know what is being worked on.

Agents are expected to integrate this into their loops for real agent communication and coordination.
"""

import os
import json
import shutil
import time
from pathlib import Path
from typing import Optional, Dict, List, Callable, Any
from uuid import uuid4
from dataclasses import dataclass, asdict, field


@dataclass
class Task:
    task_id: str
    file: str
    line_start: int
    line_end: int
    description: str
    status: str = "unclaimed"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(
            task_id=data.get("task_id", str(uuid4())),
            file=data["file"],
            line_start=data["line_start"],
            line_end=data["line_end"],
            description=data.get("description", ""),
            status=data.get("status", "unclaimed"),
            metadata=data.get("metadata", {})
        )

    @classmethod
    def from_file(cls, path: Path) -> "Task":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TaskMailboxManager:
    """
    D:/dream.os/_agent_coordination/agent_tools
    TaskMailboxManager
    ------------------
    Provides atomic task claiming, task reading, completion reporting, and failure
    management for distributed agents working on placeholder replacement in Dream.OS.
    Optionally supports heartbeat updates for real-time monitoring.
    """

    def __init__(
        self,
        agent_id: str,
        base_mailbox_dir: Path = Path("mailboxes"),
        verbose: bool = True,
        heartbeat_enabled: bool = False,
    ):
        self.agent_id = agent_id
        self.base_mailbox_dir = base_mailbox_dir
        self.verbose = verbose
        self.heartbeat_enabled = heartbeat_enabled

        self.shared_tasks_dir = self.base_mailbox_dir / "shared" / "tasks_to_claim"
        self.agent_inbox = self.base_mailbox_dir / self.agent_id / "inbox"
        self.agent_outbox = self.base_mailbox_dir / self.agent_id / "outbox"
        self.agent_failed = self.base_mailbox_dir / self.agent_id / "failed"
        self.heartbeat_dir = (
            self.base_mailbox_dir / "shared" / "heartbeat"
            if self.heartbeat_enabled
            else None
        )

        self._ensure_dirs()

    def _log(self, message: str):
        if self.verbose:
            print(f"[{self.agent_id}] {message}")

    def _ensure_dirs(self):
        """Ensure all necessary mailbox directories exist."""
        for path in [
            self.shared_tasks_dir,
            self.agent_inbox,
            self.agent_outbox,
            self.agent_failed,
        ]:
            path.mkdir(parents=True, exist_ok=True)
        if self.heartbeat_enabled and self.heartbeat_dir:
            self.heartbeat_dir.mkdir(parents=True, exist_ok=True)

    def claim_next_task(
        self, task_filter: Optional[Callable[[Task], bool]] = None
    ) -> Optional[Task]:
        """
        Atomically claim the next available task from the shared task pool.
        Optionally, a task_filter can be provided to select tasks based on agent capability.

        Returns:
            The claimed Task object, or None if no unclaimed tasks are available.
        """
        for task_file in sorted(self.shared_tasks_dir.glob("task-*.json")):
            try:
                claimed_path = self.agent_inbox / task_file.name
                os.rename(task_file, claimed_path)  # atomic move = claim
                task = Task.from_file(claimed_path)
                if task_filter and not task_filter(task):
                    # If task does not match filter, move it back
                    os.rename(claimed_path, self.shared_tasks_dir / task_file.name)
                    continue
                self._log(f"Claimed task {task.task_id}")
                self._update_heartbeat(task)
                return task
            except FileNotFoundError:
                continue  # Task already claimed by another agent.
            except Exception as e:
                self._log(f"Error claiming task from {task_file.name}: {e}")
                continue
        return None

    def read_task(self, task_file: Path) -> Optional[Task]:
        """
        Read and return the Task from the given file path.
        """
        try:
            return Task.from_file(task_file)
        except Exception as e:
            self._log(f"Failed to read task {task_file.name}: {e}")
            return None

    def complete_task(self, task: Task, new_code: str) -> Path:
        """
        Write a task completion report to the agent's outbox,
        remove the task from the inbox, and clear any active heartbeat.

        Args:
            task: The claimed Task object.
            new_code: The replacement code that implements the fix.

        Returns:
            The path to the completion report.
        """
        result = {
            "task_id": task.task_id,
            "agent_id": self.agent_id,
            "file": task.file,
            "line_start": task.line_start,
            "line_end": task.line_end,
            "new_code": new_code,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        out_path = self.agent_outbox / f"completed-{task.task_id}.json"
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            self._log(f"Completed task {task.task_id}")
        except Exception as e:
            self._log(f"Error completing task {task.task_id}: {e}")

        # Remove the task file from the inbox if it still exists.
        inbox_file = self.agent_inbox / f"task-{task.task_id}.json"
        if inbox_file.exists():
            inbox_file.unlink()

        self._clear_heartbeat()
        return out_path

    def fail_task(self, task: Task, task_file: Path, error_message: str):
        """
        Move a failed task file to the failed folder and log the error.

        Args:
            task: The Task object.
            task_file: The original file path of the task.
            error_message: A description of the failure reason.
        """
        failed_path = self.agent_failed / task_file.name
        try:
            shutil.move(str(task_file), str(failed_path))
            self._log(f"Task {task.task_id} moved to failed. Reason: {error_message}")
        except Exception as e:
            self._log(f"Error moving failed task {task.task_id}: {e}")

    def list_my_tasks(self) -> List[Task]:
        """
        List all tasks currently claimed in the agent's inbox.

        Returns:
            A list of Task objects.
        """
        tasks = []
        for task_file in self.agent_inbox.glob("task-*.json"):
            task = self.read_task(task_file)
            if task:
                tasks.append(task)
        return tasks

    def list_completed_tasks(self) -> List[Path]:
        """
        List all completion report files in the agent's outbox.
        """
        return list(self.agent_outbox.glob("completed-*.json"))

    def _update_heartbeat(self, task: Task):
        """
        Update the heartbeat file with the current task information.

        The heartbeat file is written to the shared heartbeat directory as:
            <agent_id>.json
        """
        if self.heartbeat_enabled and self.heartbeat_dir:
            heartbeat_file = self.heartbeat_dir / f"{self.agent_id}.json"
            heartbeat_data = {
                "agent_id": self.agent_id,
                "current_task": task.description,
                "task_id": task.task_id,
                "file": task.file,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "status": "in_progress",
            }
            try:
                with open(heartbeat_file, "w", encoding="utf-8") as f:
                    json.dump(heartbeat_data, f, indent=2)
            except Exception as e:
                self._log(f"Failed to update heartbeat: {e}")

    def _clear_heartbeat(self):
        """
        Clear the heartbeat file after task completion.
        """
        if self.heartbeat_enabled and self.heartbeat_dir:
            heartbeat_file = self.heartbeat_dir / f"{self.agent_id}.json"
            if heartbeat_file.exists():
                try:
                    heartbeat_file.unlink()
                except Exception as e:
                    self._log(f"Failed to clear heartbeat: {e}")


if __name__ == "__main__":
    # ---- Dynamic Example Usage (Real Logic) ----
    # This block simulates an agent using TaskMailboxManager.
    # In production, your agent's main loop would continuously call these methods.
    agent_id = "agent_cursor_demo"
    manager = TaskMailboxManager(agent_id=agent_id, heartbeat_enabled=True)

    # Simulate: an external process (or agent) pre-populated a task into the shared mailbox.
    # In practice, a separate PlaceholderScannerAgent would create such tasks.
    sample_task = Task(
        task_id=str(uuid4()),
        file="dreamos/module/sample.py",
        line_start=100,
        line_end=110,
        description="Replace simulated logic in sample.py with real implementation."
    )
    # Write the sample task to the shared mailbox (for demo purposes)
    sample_task_path = manager.shared_tasks_dir / f"task-{sample_task.task_id}.json"
    with open(sample_task_path, "w", encoding="utf-8") as f:
        json.dump(sample_task.to_dict(), f, indent=2)
    manager._log(f"Pre-populated sample task {sample_task.task_id} to shared mailbox.")

    # An agent tries to claim the next available task.
    claimed_task = manager.claim_next_task()
    if claimed_task:
        manager._log(f"Processing task: {claimed_task.task_id}")
        # Here you would run your real logic to generate the replacement code.
        # For demonstration, we generate a simple replacement.
        generated_code = (
            "def new_function():\n"
            "    # Real implementation goes here\n"
            "    return 'Real implementation executed'\n"
        )
        # Complete the task.
        manager.complete_task(claimed_task, generated_code)
        manager._log(f"Task {claimed_task.task_id} completed.")
    else:
        manager._log("No unclaimed tasks available.")