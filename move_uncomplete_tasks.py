#!/usr/bin/env python3
import os
import json
from glob import glob

def main():
    # Define paths relative to this script's location
    root = os.path.dirname(os.path.realpath(__file__))
    mailbox_dir = os.path.join(root, '_agent_coordination', 'shared_mailboxes')
    output_file = os.path.join(root, '_agent_coordination', 'tasks', 'task_list.json')

    uncompleted = []
    # Iterate all mailbox JSONs except the schema
    for path in glob(os.path.join(mailbox_dir, '*.json')):
        if path.endswith('.schema.json'):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Skipping {path}: {e}")
            continue
        if isinstance(data, list):
            for task in data:
                if task.get('status', '').upper() != 'COMPLETED':
                    uncompleted.append(task)
        elif isinstance(data, dict) and isinstance(data.get('tasks'), list):
            for task in data['tasks']:
                if task.get('status', '').upper() != 'COMPLETED':
                    uncompleted.append(task)

    # Enforce simple schema defaults
    for idx, task in enumerate(uncompleted, start=1):
        if 'task_id' not in task:
            task['task_id'] = f'mailbox_task_{idx}'
        task.setdefault('status', 'PENDING')
        task.setdefault('task_type', 'general')

    # Write tasks_list.json for agents to pick up
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(uncompleted, f, indent=2)

    print(f"Moved {len(uncompleted)} uncompleted tasks to {output_file}")

if __name__ == '__main__':
    main() 