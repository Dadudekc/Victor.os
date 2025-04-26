#!/usr/bin/env python3
"""
Supervisor Task Consolidator

This tool merges all JSON task lists under _agent_coordination/tasks and splits them
into master_tasks_*.json files of ~200 lines each.
"""
import os
import json
import glob

# Directory containing individual task lists
TASK_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tasks'))

# Pattern for individual list files (skip master files)
PATTERN = os.path.join(TASK_DIR, '*.json')
MASTER_PREFIX = 'master_tasks_'


def load_all_tasks():
    tasks = []
    for file_path in glob.glob(PATTERN):
        name = os.path.basename(file_path)
        if name.startswith(MASTER_PREFIX):
            continue
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    tasks.extend(data)
        except Exception:
            pass
    return tasks


def split_and_write(tasks, max_lines=200):
    # Estimate lines per task
    sample = json.dumps(tasks[:1], indent=2).count('\n') or 1
    per_chunk = max(1, max_lines // sample)
    total = len(tasks)

    for idx in range(0, total, per_chunk):
        chunk = tasks[idx:idx + per_chunk]
        file_index = idx // per_chunk + 1
        out_file = os.path.join(TASK_DIR, f'{MASTER_PREFIX}{file_index}.json')
        with open(out_file, 'w', encoding='utf-8') as of:
            json.dump(chunk, of, indent=2)
        print(f'Written {len(chunk)} tasks to {out_file}')


def main():
    tasks = load_all_tasks()
    if not tasks:
        print('No tasks to consolidate.')
        return
    split_and_write(tasks)
    # Delete original JSON lists
    for file_path in glob.glob(PATTERN):
        name = os.path.basename(file_path)
        if not name.startswith(MASTER_PREFIX):
            try:
                os.remove(file_path)
                print(f"Deleted original {file_path}")
            except Exception:
                pass


if __name__ == '__main__':
    main() 
