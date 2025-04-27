#!/usr/bin/env python3
"""
CLI tool to generate Dreamscape Chronicle from logs.
"""
import argparse
import json

def generate_chronicle(logs_path: str, output_path: str):
    """
    Read events from a JSON logs file and write a markdown chronicle.
    Each event should have 'agent_id', 'task_id', and 'outcome'.
    """
    with open(logs_path, 'r') as f:
        events = json.load(f)

    lines = ['# Dreamscape Chronicle']
    for evt in events:
        agent_id = evt.get('agent_id', 'unknown')
        task_id = evt.get('task_id', 'unknown')
        outcome = evt.get('outcome', 'unknown')
        lines.append(f"## Task {task_id} by {agent_id} - {outcome}\n")

    with open(output_path, 'w') as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description='Generate Dreamscape Chronicle from logs')
    parser.add_argument('--logs', required=True, help='Path to JSON logs file')
    parser.add_argument('--output', default='Dreamscape_Chronicle.md', help='Output Markdown file')
    args = parser.parse_args()
    generate_chronicle(args.logs, args.output)


if __name__ == '__main__':
    main() 
