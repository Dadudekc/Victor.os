#!/usr/bin/env python3
"""
Tool to update the current project in the project_board.json file.

Usage:
  set_project.py --project <name> [--board <project_board>]

This updates 'current_project' and the 'last_updated' timestamp.
"""
import argparse
import json
from pathlib import Path
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="Set the current project in the swarm project board.")
    parser.add_argument('--project', required=True, help='Name of the project to set.')
    parser.add_argument('--board', default='_agent_coordination/shared_mailboxes/project_board.json', help='Path to the project board JSON file.')
    args = parser.parse_args()

    board_path = Path(args.board)
    if not board_path.exists():
        print(f"Error: project board file not found: {board_path}")
        return

    data = json.loads(board_path.read_text(encoding='utf-8'))
    data['current_project'] = args.project
    data['last_updated'] = datetime.utcnow().isoformat() + 'Z'

    board_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    print(f"Set current_project to '{args.project}' in {board_path}.")

if __name__ == '__main__':
    main() 
