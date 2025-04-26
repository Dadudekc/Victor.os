import os
import json
import re
from collections import defaultdict

def parse_json_file(path):
    """Parse a JSON task list and return list of (description, file, line) tuples."""
    tasks = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to parse JSON file {path}: {e}")
        return tasks
    # Skip if JSON root is not a list
    if not isinstance(data, list):
        return tasks
    for idx, task in enumerate(data, start=1):
        # Only process entries that are dicts with a description
        if not isinstance(task, dict):
            continue
        desc = task.get('description', '').strip()
        if desc:
            tasks.append((desc, path, idx))
    return tasks


def parse_md_file(path):
    """Parse a Markdown task list and return list of (description, file, line) tuples."""
    tasks = []
    pattern = re.compile(r'^\s*-\s+\[.\]\s*(.+)')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f, start=1):
                m = pattern.match(line)
                if m:
                    desc = m.group(1).strip()
                    tasks.append((desc, path, idx))
    except Exception as e:
        print(f"Failed to parse Markdown file {path}: {e}")
    return tasks


def find_task_files():
    """Discover all task list files in the workspace."""
    task_files = []
    for root, _, files in os.walk('.'):
        for file in files:
            if 'task_list' in file.lower():
                task_files.append(os.path.join(root, file))
    return task_files


def normalize(text):
    """Normalize text for comparison (lowercase, alphanumeric only)."""
    return re.sub(r'\W+', ' ', text.lower()).strip()


def main():
    task_entries = []
    for file in find_task_files():
        if file.lower().endswith('.json'):
            task_entries.extend(parse_json_file(file))
        elif file.lower().endswith('.md'):
            task_entries.extend(parse_md_file(file))

    groups = defaultdict(list)
    for desc, path, line in task_entries:
        key = normalize(desc)
        groups[key].append((desc, path, line))

    duplicates = {k: v for k, v in groups.items() if len(v) > 1}

    if not duplicates:
        print('No duplicate tasks found.')
    else:
        print('Duplicate tasks found:\n')
        for key, entries in duplicates.items():
            print(f"Task: '{entries[0][0]}'")
            for desc, path, line in entries:
                print(f"  - {path}:{line}")
            print()

if __name__ == '__main__':
    main() 
