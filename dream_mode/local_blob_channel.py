import os
import json
import shutil
from typing import List, Dict

class LocalBlobChannel:
    def __init__(self, base_dir: str = "runtime/local_blob"):
        self.tasks_dir = os.path.join(base_dir, "tasks")
        self.results_dir = os.path.join(base_dir, "results")
        self.processed_dir = os.path.join(base_dir, "processed")
        os.makedirs(self.tasks_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)

    def push_task(self, task: Dict) -> None:
        path = os.path.join(self.tasks_dir, f"{task.get('task_id', task.get('id', ''))}.json")
        with open(path, "w", encoding='utf-8') as f:
            json.dump(task, f)

    def pull_tasks(self) -> List[Dict]:
        tasks = []
        for filename in os.listdir(self.tasks_dir):
            full_path = os.path.join(self.tasks_dir, filename)
            try:
                with open(full_path, "r", encoding='utf-8') as f:
                    task = json.load(f)
                    tasks.append(task)
            except Exception:
                continue
            # Attempt to move processed file, ignore on failure
            try:
                shutil.move(full_path, os.path.join(self.processed_dir, filename))
            except Exception:
                # Could be locked or already moved; skip
                pass
        return tasks

    def push_result(self, result: Dict) -> None:
        rid = result.get('id', result.get('task_id', ''))
        path = os.path.join(self.results_dir, f"{rid}-result.json")
        with open(path, "w", encoding='utf-8') as f:
            json.dump(result, f)

    def pull_results(self) -> List[Dict]:
        results = []
        for filename in os.listdir(self.results_dir):
            full_path = os.path.join(self.results_dir, filename)
            try:
                with open(full_path, "r", encoding='utf-8') as f:
                    result = json.load(f)
                    results.append(result)
            except Exception:
                continue
            # Attempt to move processed file, ignore on failure
            try:
                shutil.move(full_path, os.path.join(self.processed_dir, filename))
            except Exception:
                # Could be locked or already moved; skip
                pass
        return results

    def healthcheck(self) -> bool:
        """Local mode healthcheck always returns True."""
        return True 