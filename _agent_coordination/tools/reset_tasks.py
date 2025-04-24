#!/usr/bin/env python3
import os
from pathlib import Path
from _agent_coordination.tools.file_lock_manager import read_json, write_json

def main():
    base = Path(os.getcwd()) / '_agent_coordination' / 'tasks'
    complete_dir = base / 'complete'
    complete_file = complete_dir / 'completed_tasks.json'

    # Load existing completed tasks atomically
    completed = read_json(complete_file) or []

    # Iterate over task list files
    for file in base.glob('*.json'):
        # Skip schema and completed/pending files
        if file.name in ['task_list.schema.json', 'completed_tasks.json', 'pending_tasks.json']:
            continue
        # Load tasks atomically
        try:
            tasks = read_json(file) or []
        except Exception as e:
            print(f"Skipping {file.name}: invalid JSON ({e})")
            continue
        new_tasks = []
        for task in tasks:
            # Skip entries that are not task objects
            if not isinstance(task, dict):
                continue
            if task.get('status') == 'COMPLETED':
                completed.append(task)
            else:
                # Reset to unclaimed pending
                task['status'] = 'PENDING'
                task.pop('claimed_by', None)
                task.pop('completed_by', None)
                new_tasks.append(task)
        # Write reset tasks atomically
        write_json(file, new_tasks)
        print(f"Reset tasks in {file.name}: {len(new_tasks)} tasks remain pending.")
    # Ensure complete directory exists
    complete_dir.mkdir(parents=True, exist_ok=True)
    # Write aggregated completed tasks atomically
    write_json(complete_file, completed)
    print(f"Aggregated {len(completed)} completed tasks.")

if __name__ == '__main__':
    main() 