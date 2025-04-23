#!/usr/bin/env python3
"""
Auto-claim all PENDING tasks across _agent_coordination/tasks for agent_002.
"""
import os
import json

AGENT_ID = "agent_002"
TASKS_DIR = os.path.join(os.getcwd(), "_agent_coordination", "tasks")

def main():
    for fname in os.listdir(TASKS_DIR):
        if not fname.endswith('.json') or fname.endswith('schema.json'):
            continue
        path = os.path.join(TASKS_DIR, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
        except Exception:
            continue
        updated = False
        for task in tasks:
            status = task.get('status', '').upper()
            if status in ('PENDING',):
                task['status'] = 'IN_PROGRESS'
                task['claimed_by'] = AGENT_ID
                updated = True
        if updated:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, indent=2)
            print(f"[CLAIM] Updated {fname}")

if __name__ == '__main__':
    main() 