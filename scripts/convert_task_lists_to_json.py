#!/usr/bin/env python3
"""
Convert task list markdown files to JSON arrays.
Usage: scripts/convert_task_lists_to_json.py <input.md> [output.json]
"""
import sys
import os
import json


def parse_markdown_tasks(md_content):
    """Parse markdown list items into task dicts"""
    tasks = []
    for line in md_content.splitlines():
        line = line.strip()
        if line.startswith('- '):
            tasks.append({'description': line[2:].strip()})
    return tasks


def main():
    if len(sys.argv) < 2:
        print("Usage: convert_task_lists_to_json.py <input.md> [output.json]")
        sys.exit(1)
    infile = sys.argv[1]
    outfile = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(infile)[0] + '.json'

    with open(infile, 'r', encoding='utf-8') as f:
        md = f.read()
    tasks = parse_markdown_tasks(md)
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=2)
    print(f"Wrote {len(tasks)} tasks to {outfile}")


if __name__ == '__main__':
    main() 