import json
import argparse
import hashlib
from pathlib import Path
from collections import defaultdict


def load_tasks(task_dir: Path):
    tasks = []
    for path in task_dir.rglob('*.json'):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except Exception:
            continue
        if isinstance(data, list):
            for t in data:
                if isinstance(t, dict):
                    t['_source'] = str(path)
                    tasks.append(t)
        elif isinstance(data, dict) and 'task_id' in data:
            data['_source'] = str(path)
            tasks.append(data)
    return tasks


def task_hash(task: dict) -> str:
    name = task.get('name', '').strip().lower()
    desc = task.get('description', '').strip().lower()
    return hashlib.md5(f'{name}|{desc}'.encode()).hexdigest()


def find_duplicates(tasks):
    groups = defaultdict(list)
    for t in tasks:
        h = task_hash(t)
        groups[h].append(t)
    return {h: g for h, g in groups.items() if len(g) > 1}


def main(task_dir: str, output: str):
    tasks = load_tasks(Path(task_dir))
    duplicates = find_duplicates(tasks)
    if duplicates:
        report = []
        for h, group in duplicates.items():
            report.append({'hash': h, 'tasks': group})
        with open(output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f'Found {len(duplicates)} duplicate groups. Report saved to {output}')
    else:
        print('No duplicate tasks found.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Detect duplicate tasks across task boards')
    parser.add_argument('--task-dir', default='runtime/agent_comms/central_task_boards', help='Path to task boards directory')
    parser.add_argument('--output', default='runtime/reports/task_duplicates.json', help='Output JSON file for duplicates report')
    args = parser.parse_args()
    main(args.task_dir, args.output)
