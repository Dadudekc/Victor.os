#!/usr/bin/env python3
import os, json
from pathlib import Path

def main():
    base = Path(os.getcwd()) / '_agent_coordination' / 'tasks'
    complete_dir = base / 'complete'
    complete_file = complete_dir / 'completed_tasks.json'

    # Load existing completed tasks
    completed = []
    if complete_file.exists():
        try:
            completed = json.loads(complete_file.read_text(encoding='utf-8'))
        except:
            completed = []

    # Iterate over task list files
    for file in base.glob('*.json'):
        # Skip schema and completed/pending files
        if file.name in ['task_list.schema.json', 'completed_tasks.json', 'pending_tasks.json']:
            continue
        try:
            tasks = json.loads(file.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"Skipping {file.name}: invalid JSON ({e})")
            continue
        new_tasks = []
        for task in tasks:
            if task.get('status') == 'COMPLETED':
                completed.append(task)
            else:
                # Reset to unclaimed pending
                task['status'] = 'PENDING'
                task.pop('claimed_by', None)
                task.pop('completed_by', None)
                new_tasks.append(task)
        # Write reset tasks back
        file.write_text(json.dumps(new_tasks, indent=2), encoding='utf-8')
        print(f"Reset tasks in {file.name}: {len(new_tasks)} tasks remain pending.")
    # Ensure complete directory exists
    complete_dir.mkdir(parents=True, exist_ok=True)
    # Write aggregated completed tasks
    complete_file.write_text(json.dumps(completed, indent=2), encoding='utf-8')
    print(f"Aggregated {len(completed)} completed tasks.")

if __name__ == '__main__':
    main() 