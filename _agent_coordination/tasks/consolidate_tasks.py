#!/usr/bin/env python3
"""
Scan all JSON files in this directory, merge their arrays, and split into master JSON files
of about 200 lines each."""
import os
import json
import glob
import math

def load_all_tasks(dir_path):
    tasks = []
    # Load all task lists from JSON files in this directory (excluding master shims and reports)
    # Include JSON files in the root tasks directory and in the proposals subdirectory
    json_files = glob.glob(os.path.join(dir_path, '*.json')) + glob.glob(os.path.join(dir_path, 'proposals', '*.json'))
    # Exclude proposal files since tasks have been extracted and replaced with placeholders
    json_files = [f for f in json_files if not f.startswith(os.path.join(dir_path, 'proposals'))]
    for file_path in json_files:
        name = os.path.basename(file_path)
        # Skip master files (will be regenerated), reports, and task archive directories
        if name.startswith('master_tasks_') or name in ('master_task_list.json', 'cleanup_report.md', 'research_report.md', 'tasks_consolidated.json'):
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

def split_and_write(tasks, dir_path, max_lines=400):
    # Roughly estimate lines per task by dumping one and counting
    sample = json.dumps(tasks[:1], indent=2).count('\n') or 1
    tasks_per_chunk = max(1, max_lines // sample)
    part_count = 0
    for i in range(0, len(tasks), tasks_per_chunk):
        part_count += 1
        chunk = tasks[i:i+tasks_per_chunk]
        index = part_count
        out_file = os.path.join(dir_path, f'master_tasks_{index}.json')
        out_data = {
            "meta": {"source": "converged_tasks", "batch": "2025-04", "part": index},
            "tasks": chunk
        }
        with open(out_file, 'w', encoding='utf-8') as of:
            json.dump(out_data, of, indent=2)
        print(f"Written {len(chunk)} tasks to {out_file}")
    return part_count

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
    parts = split_and_write(pending_tasks, dir_path)

    # Insert placeholder tasks field in each proposal JSON
    proposal_dir = os.path.join(dir_path, 'proposals')
    for file_path in glob.glob(os.path.join(proposal_dir, '*.json')):
        try:
            with open(file_path, 'r', encoding='utf-8') as pf:
                prop = json.load(pf)
            placeholder = (
                f"EXTRACTED — now in master_tasks_1.json"
                if parts == 1
                else f"EXTRACTED — now in master_tasks_1.json ... master_tasks_{parts}.json"
            )
            prop['tasks'] = placeholder
            with open(file_path, 'w', encoding='utf-8') as pf:
                json.dump(prop, pf, indent=2)
        except Exception:
            continue

if __name__ == '__main__':
    main() 