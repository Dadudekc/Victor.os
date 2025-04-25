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
    except Exception:
        return tasks
    if not isinstance(data, list):
        return tasks
    for idx, task in enumerate(data, start=1):
        if isinstance(task, dict) and task.get('description'):
            desc = str(task['description']).strip()
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
    except Exception:
        pass
    return tasks


def find_task_files():
    """Discover all task_list files in the workspace, excluding the tasks output directory."""
    files = []
    for root, _, names in os.walk('.'):
        # skip the generated tasks directory
        parts = os.path.normpath(root).split(os.sep)
        if 'tasks' in parts:
            continue
        for name in names:
            if 'task_list' in name.lower() and (name.lower().endswith('.md') or name.lower().endswith('.json')):
                files.append(os.path.join(root, name))
    return files


def main():
    os.makedirs('tasks', exist_ok=True)
    for path in find_task_files():
        entries = []
        if path.lower().endswith('.json'):
            entries = parse_json_file(path)
        else:
            entries = parse_md_file(path)
        output = []
        for desc, file, line in entries:
            output.append({'description': desc, 'source': file, 'line': line})
        # preserve directory structure: use relative path under tasks
        rel = os.path.splitext(os.path.relpath(path, '.'))[0] + '.json'
        outpath = os.path.join('tasks', rel)
        # ensure parent directories exist
        os.makedirs(os.path.dirname(outpath), exist_ok=True)
        with open(outpath, 'w', encoding='utf-8') as outf:
            json.dump(output, outf, indent=2)
        print(f"Wrote {len(output)} tasks to {outpath}")


if __name__ == '__main__':
    main() 