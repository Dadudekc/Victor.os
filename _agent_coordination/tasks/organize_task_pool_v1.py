#!/usr/bin/env python3
"""
Organize and consolidate all task files from the _agent_coordination/tasks directory (and subdirectories).
Follow the manual v1 plan precisely.
"""
import os
import json

def is_output_file(fname):
    # Skip files we generate
    return (fname == 'completed_tasks.json' or
            fname.startswith('master_tasks_') or
            fname == 'super_master_tasks.json')


def load_tasks_from_file(fpath):
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get('tasks'), list):
        return data['tasks']
    return []


def main():
    # Determine directories to traverse
    script_dir = os.path.dirname(os.path.realpath(__file__))
    root = script_dir
    complete_dir = os.path.join(root, 'complete')
    os.makedirs(complete_dir, exist_ok=True)
    dirs = [root, os.path.join(root, 'proposals'), os.path.join(complete_dir)]

    completed = []
    active = []
    all_tasks = []
    processed = []

    # Step 1 & 2: Load and classify tasks
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if not fname.endswith('.json') or is_output_file(fname):
                continue
            fpath = os.path.join(d, fname)
            tasks = load_tasks_from_file(fpath)
            if not tasks:
                continue
            for t in tasks:
                all_tasks.append(t)
                status = t.get('status', '').upper()
                claimed = t.get('claimed_by')
                if status == 'COMPLETED' or (claimed and status.lower() == 'done'):
                    completed.append(t)
                else:
                    active.append(t)
            processed.append(fpath)

    # Step 2: Write completed tasks
    completed_path = os.path.join(complete_dir, 'completed_tasks.json')
    with open(completed_path, 'w', encoding='utf-8') as cf:
        json.dump(completed, cf, indent=2)

    # Step 3: Split active tasks into master files (<=200 lines)
    if active:
        sample_lines = json.dumps([active[0]], indent=2).count('\n') or 1
        max_lines = 200
        tasks_per_chunk = max(1, max_lines // sample_lines)
    else:
        tasks_per_chunk = 1

    created = []
    for i in range(0, len(active), tasks_per_chunk):
        chunk = active[i:i+tasks_per_chunk]
        idx = i // tasks_per_chunk + 1
        out_path = os.path.join(root, f'master_tasks_{idx}.json')
        with open(out_path, 'w', encoding='utf-8') as of:
            json.dump(chunk, of, indent=2)
        created.append(out_path)

    # Step 5: Generate super master list
    super_path = os.path.join(root, 'super_master_tasks.json')
    with open(super_path, 'w', encoding='utf-8') as sf:
        json.dump(all_tasks, sf, indent=2)
    created.append(super_path)

    # Step 4: Delete processed source files
    deleted = []
    for fpath in processed:
        try:
            os.remove(fpath)
            deleted.append(fpath)
        except Exception:
            pass

    # Step 6: Print summary
    print("Summary:")
    print(f"✔ Completed tasks moved: {len(completed)}")
    print(f"📝 Active tasks rebatched: {len(active)}")
    print("📁 Files created:")
    for p in created:
        print(f"   - {p}")
    print("🧹 Files deleted:")
    for p in deleted:
        print(f"   - {p}")

if __name__ == '__main__':
    main() 
