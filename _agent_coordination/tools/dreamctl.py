#!/usr/bin/env python3
import argparse
from dream_mode.config import load_config
import json
from pathlib import Path
import os
import subprocess


def status():
    """Show live agent health and task queues by reading the project board."""
    pb_path = Path.cwd() / "_agent_coordination" / "shared_mailboxes" / "project_board.json"
    try:
        data = json.loads(pb_path.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"[dreamctl] Error reading project board: {e}")
        return

    print("Agents status (project board):")
    agents = data.get("agents", [])
    for agent in agents:
        aid = agent.get("agent_id")
        status = agent.get("status")
        task = agent.get("current_task") or "<idle>"
        last = agent.get("last_seen")
        print(f" - {aid}: {status} (last_seen: {last}) -> {task}")

def pause():
    """Pause all agents in the swarm."""
    # Broadcast a pause directive to all agent mailboxes
    script = Path(__file__).parent / "broadcast_directive.py"
    try:
        subprocess.run(["python", str(script), "--content", "PAUSE_SWARM"], check=True)
        print("[dreamctl] Swarm paused.")
    except Exception as e:
        print(f"[dreamctl] Failed to pause swarm: {e}")

def resume():
    """Resume all paused agents in the swarm."""
    # Broadcast a resume directive to all agent mailboxes
    script = Path(__file__).parent / "broadcast_directive.py"
    try:
        subprocess.run(["python", str(script), "--content", "RESUME_SWARM"], check=True)
        print("[dreamctl] Swarm resumed.")
    except Exception as e:
        print(f"[dreamctl] Failed to resume swarm: {e}")

def claim(task_id):
    """Claim a task by its ID."""
    # Update runtime/task_list.json to claim the specified task
    task_file = Path.cwd() / "runtime" / "task_list.json"
    try:
        tasks = json.loads(task_file.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"[dreamctl] Error reading task list: {e}")
        return
    agent_id = os.getenv("AGENT_ID", "cli")
    claimed = False
    for t in tasks:
        if t.get("task_id") == task_id:
            t["status"] = "claimed"
            t["claimed_by"] = agent_id
            claimed = True
            break
    if not claimed:
        print(f"[dreamctl] Task {task_id} not found.")
        return
    try:
        task_file.write_text(json.dumps(tasks, indent=2), encoding='utf-8')
        print(f"[dreamctl] Task {task_id} claimed by {agent_id}.")
    except Exception as e:
        print(f"[dreamctl] Error writing task list: {e}")

def release(task_id):
    """Release a claimed task by its ID."""
    # Update runtime/task_list.json to release the specified task
    task_file = Path.cwd() / "runtime" / "task_list.json"
    try:
        tasks = json.loads(task_file.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"[dreamctl] Error reading task list: {e}")
        return
    released = False
    for t in tasks:
        if t.get("task_id") == task_id:
            t["status"] = "pending"
            t.pop("claimed_by", None)
            released = True
            break
    if not released:
        print(f"[dreamctl] Task {task_id} not found or not claimed.")
        return
    try:
        task_file.write_text(json.dumps(tasks, indent=2), encoding='utf-8')
        print(f"[dreamctl] Task {task_id} released.")
    except Exception as e:
        print(f"[dreamctl] Error writing task list: {e}")

def main():
    parser = argparse.ArgumentParser(prog="dreamctl", description="Dream.OS Swarm CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Show swarm status")
    subparsers_added = {"pause": subparsers.add_parser("pause", help="Pause the swarm"),
                        "resume": subparsers.add_parser("resume", help="Resume the swarm")}
    parser_claim = subparsers.add_parser("claim", help="Claim a task")
    parser_claim.add_argument("task_id", help="ID of the task to claim")
    parser_release = subparsers.add_parser("release", help="Release a claimed task")
    parser_release.add_argument("task_id", help="ID of the task to release")

    args = parser.parse_args()
    config = load_config()

    if args.command == "status":
        status()
    elif args.command == "pause":
        pause()
    elif args.command == "resume":
        resume()
    elif args.command == "claim":
        claim(args.task_id)
    elif args.command == "release":
        release(args.task_id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 
