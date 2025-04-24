#!/usr/bin/env python3
"""
Swarm Orchestrator v1
- Assigns tasks from remaining_tasks.json to agent mailboxes (mailbox_1.json, mailbox_2.json)
- Monitors result_N.json for task completions
- Moves completed tasks to complete/completed_tasks.json
"""
import json
import time
from pathlib import Path
from datetime import datetime
from _agent_coordination.tools.file_lock_manager import read_json, write_json

# Paths
ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / 'tasks'
REMAINING = TASKS_DIR / 'remaining_tasks.json'
COMPLETED_DIR = TASKS_DIR / 'complete'
COMPLETED = COMPLETED_DIR / 'completed_tasks.json'
MAILBOX_DIR = ROOT / 'shared_mailboxes'
AGENT_IDS = [1, 2]
MAILBOXS = {i: MAILBOX_DIR / f'mailbox_{i}.json' for i in AGENT_IDS}
RESULTS = {i: MAILBOX_DIR / f'result_{i}.json' for i in AGENT_IDS}

# Ensure completed tasks file exists
COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
if not COMPLETED.exists():
    COMPLETED.write_text('[]', encoding='utf-8')


def load_json(path: Path):
    try:
        data = read_json(path)
        return data if data else []
    except Exception:
        return []


def save_json(path: Path, data):
    try:
        write_json(path, data)
    except Exception as e:
        logger.error(f"Failed to write JSON at {path} with lock: {e}")


def log_to_mailboxes(message: str):
    """Append orchestrator log messages to all agent mailboxes."""
    timestamp = datetime.utcnow().isoformat()
    for mb_path in MAILBOXS.values():
        mb = load_json(mb_path)
        mb.setdefault('messages', []).append({
            'type': 'orchestrator_log',
            'timestamp': timestamp,
            'content': message
        })
        save_json(mb_path, mb)


def assign_tasks():
    remaining = load_json(REMAINING)
    if not remaining:
        return False
    # Round-robin assignment
    for idx, task in enumerate(remaining[:]):
        agent_id = AGENT_IDS[idx % len(AGENT_IDS)]
        mb = load_json(MAILBOXS[agent_id])
        mb.setdefault('messages', []).append(task)
        mb['assigned_agent_id'] = agent_id
        save_json(MAILBOXS[agent_id], mb)
        # Remove from remaining
        remaining.remove(task)
    save_json(REMAINING, remaining)
    return True


def collect_results():
    completed = load_json(COMPLETED)
    for agent_id, result_file in RESULTS.items():
        if not result_file.exists():
            continue
        res_list = load_json(result_file)
        for res in res_list:
            # Append to completed tasks
            completed.append(res)
        # clear result file
        save_json(result_file, [])
    save_json(COMPLETED, completed)


def main(poll_interval=5):
    log_to_mailboxes("Starting Swarm Orchestrator loop...")
    while True:
        # Assign tasks if any
        if assign_tasks():
            log_to_mailboxes("Assigned tasks to agents.")
        # Collect results
        collect_results()
        time.sleep(poll_interval)


if __name__ == '__main__':
    main() 