#!/usr/bin/env python3
"""
Claim exactly one PENDING task for agent_002 across all JSON task lists in _agent_coordination/tasks.
After claiming, update the task file and print the claimed task_id.
"""
import os
import json

AGENT_ID = "agent_002"
TASKS_DIR = os.path.join(os.getcwd(), "_agent_coordination", "tasks")

def claim_one_task():
    for fname in sorted(os.listdir(TASKS_DIR)):
        if not fname.endswith('.json') or fname.endswith('schema.json'):
            continue
        path = os.path.join(TASKS_DIR, fname)
        try:
            tasks = json.load(open(path, 'r', encoding='utf-8'))
        except Exception:
            continue
        for task in tasks:
            if task.get('status', '').upper() == 'PENDING':
                task['status'] = 'CLAIMED'
                task['claimed_by'] = AGENT_ID
                # Save back
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(tasks, f, indent=2)
                print(f"[CLAIM] agent_002 claimed task {task['task_id']} in {fname}")
                return task['task_id']
    print("[CLAIM] No pending tasks found.")
    return None

if __name__ == '__main__':
    claim_one_task() 