#!/usr/bin/env python3
"""
Organize task pool v1:
Scan _agent_coordination/tasks, group tasks by their status into separate JSON files.
"""
import os, json, glob

def main():
    task_dir = os.path.join('_agent_coordination', 'tasks')
    all_tasks = []
    for file in glob.glob(os.path.join(task_dir, '*.json')):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_tasks.extend(data)
        except Exception:
            continue

    pending = [t for t in all_tasks if t.get('status') != 'COMPLETED']
    completed = [t for t in all_tasks if t.get('status') == 'COMPLETED']

    out_pending = os.path.join(task_dir, 'tasks_pending.json')
    out_completed = os.path.join(task_dir, 'tasks_completed.json')

    with open(out_pending, 'w', encoding='utf-8') as f:
        json.dump(pending, f, indent=2)
    with open(out_completed, 'w', encoding='utf-8') as f:
        json.dump(completed, f, indent=2)

    print(f"Organized {len(all_tasks)} tasks into {len(pending)} pending and {len(completed)} completed.")

if __name__ == '__main__':
    main() 