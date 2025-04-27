#!/usr/bin/env python3
"""
Deduplicate tasks across JSON files in _agent_coordination/tasks.
"""
import os, json, glob

from collections import OrderedDict

def load_tasks(dir_path):
    tasks = []
    for file in glob.glob(os.path.join(dir_path, '*.json')):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    tasks.extend(data)
        except Exception:
            continue
    return tasks

def dedupe(tasks):
    seen = set()
    unique = []
    for t in tasks:
        key = (
            t.get('task_id'),
            t.get('file'),
            tuple(t.get('line_range', [])),
            t.get('description')
        )
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique

def main():
    task_dir = os.path.join('_agent_coordination', 'tasks')
    tasks = load_tasks(task_dir)
    unique = dedupe(tasks)
    out_file = os.path.join(task_dir, 'tasks_dedup.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(unique, f, indent=2)
    print(f"Deduplicated {len(tasks)-len(unique)} duplicates, saved {len(unique)} tasks to {out_file}")

if __name__ == '__main__':
    main() 
