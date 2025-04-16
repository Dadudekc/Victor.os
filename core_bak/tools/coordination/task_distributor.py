"""
D:/dream.os/_agent_coordination/agent_tools
task_distributor.py

This module implements TaskDistributor – a production-ready tool for scanning the Dream.OS 
project, detecting Python files missing a '__main__' usage block, and dynamically distributing 
real tasks to agent mailboxes as well as updating a shared project board.

Agents that call this tool will find their mailbox (task_list.json) updated with new tasks. 
This is real logic for distributed agent communication – no simulations.
"""

import os
import json
import datetime
from pathlib import Path


# === CONFIGURATION ===
PROJECT_ROOT = Path("D:/Dream.OS/").resolve()
AGENT_IDS = [1, 2, 3, 4, 5, 6, 7, 8]  # Expand as needed
PROJECT_BOARD = PROJECT_ROOT / "project_board.json"


def now_str():
    return datetime.datetime.utcnow().isoformat() + "Z"


class TaskDistributor:
    def __init__(self, project_root: Path = PROJECT_ROOT, agent_ids=None, verbose: bool = True):
        self.project_root = project_root
        self.agent_ids = agent_ids if agent_ids is not None else []
        self.verbose = verbose
        self.project_board = PROJECT_BOARD

    def log(self, message: str):
        if self.verbose:
            print(message)

    def agent_mailbox(self, agent_id: int):
        agent_dir = self.project_root / "mailbox" / f"agent_{agent_id}"
        return {
            "dir": agent_dir,
            "tasks": agent_dir / "task_list.json",
            "inbox": agent_dir / "inbox" / "usage_block_status.json",
            "outbox": agent_dir / "outbox"
        }

    def init_mailbox_if_needed(self, agent_id: int):
        mailbox = self.agent_mailbox(agent_id)
        for path in [mailbox["tasks"], mailbox["inbox"]]:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                with open(path, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=2)
        return mailbox

    def add_task_to_mailbox(self, mailbox: dict, task: dict):
        tasks_file = mailbox["tasks"]
        with open(tasks_file, "r+", encoding="utf-8") as f:
            try:
                tasks = json.load(f)
            except json.JSONDecodeError:
                tasks = []
            # Avoid duplicate tasks based on the task_id
            if not any(t.get("task_id") == task.get("task_id") for t in tasks):
                tasks.append(task)
                f.seek(0)
                json.dump(tasks, f, indent=2)
                f.truncate()

    def add_project_board_update(self, entry: dict):
        self.project_board.parent.mkdir(parents=True, exist_ok=True)
        if self.project_board.exists():
            with open(self.project_board, "r+", encoding="utf-8") as f:
                try:
                    board = json.load(f)
                except json.JSONDecodeError:
                    board = []
                board.append(entry)
                f.seek(0)
                json.dump(board, f, indent=2)
                f.truncate()
        else:
            with open(self.project_board, "w", encoding="utf-8") as f:
                json.dump([entry], f, indent=2)

    @staticmethod
    def file_has_main_block(file_path: Path) -> bool:
        """Check if file contains the '__main__' block. In case of errors, assume it has one."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return 'if __name__ == "__main__"' in f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            return True

    def enqueue_tasks_to_all_agents(self, file_path: Path):
        abs_path = str(file_path.resolve())
        filename = file_path.name
        task_id = f"INJECT_USAGE_BLOCK_{filename}"
        timestamp = now_str()

        board_entry = {
            "component": filename,
            "usage_block": "missing",
            "last_checked": timestamp,
            "path": abs_path
        }
        self.add_project_board_update(board_entry)
        self.log(f"[BOARD] Updated board for component {filename}")

        for agent_id in self.agent_ids:
            mailbox = self.init_mailbox_if_needed(agent_id)
            task = {
                "agent_id": f"agent_{agent_id}",
                "task_id": task_id,
                "description": f"Inject and validate __main__ usage block for {filename}",
                "status": "pending",
                "priority": "high",
                "file": abs_path,
                "timestamp": timestamp
            }
            self.add_task_to_mailbox(mailbox, task)
            self.log(f"[QUEUED] {filename} → agent_{agent_id}")

    def scan_for_usage_block_tasks(self):
        for root, _, files in os.walk(self.project_root):
            for filename in files:
                if filename.endswith(".py") and "__pycache__" not in root:
                    full_path = Path(root) / filename
                    # Only enqueue if the file lacks a main block
                    if not self.file_has_main_block(full_path):
                        self.enqueue_tasks_to_all_agents(full_path)

    def run(self):
        self.log(">>> 🧠 Scanning for usage block gaps...")
        self.scan_for_usage_block_tasks()
        self.log(">>> ✅ Tasks distributed to agent mailboxes.")


if __name__ == "__main__":
    # === Dynamic Example Usage (Real Logic) ===
    # This main block lets you run the task distributor as a standalone tool.
    # In production, you might call TaskDistributor().run() periodically or from a job scheduler.
    distributor = TaskDistributor(agent_ids=AGENT_IDS, verbose=True)
    distributor.run()