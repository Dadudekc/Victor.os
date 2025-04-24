#!/usr/bin/env python3
"""
Scan all JSON files in this directory, merge their arrays, and split into master JSON files
of about 200 lines each."""
import os
import json
import glob

def load_all_tasks(dir_path):
    tasks = []
    # Load all task lists from JSON files in this directory (excluding master shims and reports)
    for file_path in glob.glob(os.path.join(dir_path, '*.json')):
        name = os.path.basename(file_path)
        # Skip master files (will be regenerated), reports, and task archive directories
        if name.startswith('master_tasks_') or name in ('master_task_list.json', 'cleanup_report.md', 'research_report.md'):
            continue
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    tasks.extend(data)
        except Exception:
            continue
    return tasks

def dedupe_tasks(tasks):
    """Remove duplicate tasks based on key attributes."""
    seen = set()
    unique = []
    for t in tasks:
        key = (
            t.get('task_id'),
            t.get('file'),
            t.get('category') or t.get('product'),
            tuple(t.get('line_range', [])) if isinstance(t.get('line_range'), list) else None,
            t.get('description')
        )
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique

def split_and_write(tasks, dir_path, max_lines=200):
    # Roughly estimate lines per task by dumping one and counting
    sample = json.dumps(tasks[:1], indent=2).count('\n') or 1
    tasks_per_chunk = max(1, max_lines // sample)
    for i in range(0, len(tasks), tasks_per_chunk):
        chunk = tasks[i:i+tasks_per_chunk]
        index = i // tasks_per_chunk + 1
        out_file = os.path.join(dir_path, f'master_tasks_{index}.json')
        with open(out_file, 'w', encoding='utf-8') as of:
            json.dump(chunk, of, indent=2)
        print(f"Written {len(chunk)} tasks to {out_file}")


def main():
    dir_path = os.path.dirname(__file__)
    tasks = load_all_tasks(dir_path)
    # Deduplicate across all sourced task lists
    tasks = dedupe_tasks(tasks)

    # Separate completed and pending tasks
    completed_dir = os.path.join(dir_path, 'complete')
    os.makedirs(completed_dir, exist_ok=True)
    completed_tasks = [t for t in tasks if t.get('status') == 'COMPLETED']
    pending_tasks = [t for t in tasks if t.get('status') != 'COMPLETED']

    # Write completed tasks archive
    with open(os.path.join(completed_dir, 'completed_tasks.json'), 'w', encoding='utf-8') as cf:
        json.dump(completed_tasks, cf, indent=2)

    # Remove existing master tasks files so only fresh pending tasks are output
    for master_file in glob.glob(os.path.join(dir_path, 'master_tasks_*.json')):
        try:
            os.remove(master_file)
        except OSError:
            pass

    # Consolidate only pending tasks into master files
    if not pending_tasks:
        print("No pending tasks found to consolidate.")
        return
    split_and_write(pending_tasks, dir_path)


if __name__ == '__main__':
    main() 