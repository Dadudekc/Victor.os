"""
Task Disperser (Agent-8)

Takes parsed tasks and writes them to each agent's inbox.json file.
Enhancements:
- Adds timestamps
- Records origin episode
- Handles dict + string tasks
- Sorts task entries for consistency
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime
import argparse

logger = logging.getLogger(__name__)

# Define the agent inbox root directory
AGENT_INBOX_BASE_DIR = Path("runtime/agent_comms/agent_mailboxes")

def disperse_tasks_to_inboxes(agent_tasks: dict, origin_episode: str = "UNKNOWN_EPISODE"):
    """
    Writes tasks to the respective agent's inbox.json file.

    Args:
        agent_tasks: Dict[str, Union[List[str], List[dict]]]
            Example: {
                "Agent-7": [{"id": "YAML-PARSER-008", "desc": "..."}],
                "Agent-8": ["Write parsed tasks to inboxes."]
            }
        origin_episode: str
            Label indicating which episode generated these tasks.
    """
    if not agent_tasks:
        logger.warning("No agent tasks provided to disperse.")
        return

    AGENT_INBOX_BASE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Inbox base directory: {AGENT_INBOX_BASE_DIR.resolve()}")

    for agent_id, tasks in agent_tasks.items():
        if not tasks:
            logger.info(f"No tasks to disperse for {agent_id}.")
            continue

        agent_inbox_dir = AGENT_INBOX_BASE_DIR / agent_id
        agent_inbox_dir.mkdir(parents=True, exist_ok=True)
        inbox_file_path = agent_inbox_dir / "inbox.json"

        inbox_data = []
        for i, task_detail in enumerate(tasks):
            prompt_entry = {
                "prompt_id": f"{agent_id}_task_{i+1:03d}",
                "type": "instruction",
                "status": "new",
                "timestamp": datetime.utcnow().isoformat(),
                "origin_episode": origin_episode
            }

            if isinstance(task_detail, str):
                prompt_entry.update({
                    "content": task_detail,
                    "source_episode_task": task_detail[:50] + "..."
                })
            elif isinstance(task_detail, dict):
                prompt_entry.update({
                    "prompt_id": task_detail.get("id", prompt_entry["prompt_id"]),
                    "content": task_detail.get("desc", "No description provided."),
                    "source_episode_task": task_detail.get("id", "unknown"),
                    **task_detail  # Include other custom fields
                })
            else:
                logger.warning(f"Unsupported task type for {agent_id}: {type(task_detail)}")
                continue

            inbox_data.append(prompt_entry)

        # Sort tasks by prompt_id for stability
        inbox_data.sort(key=lambda x: x["prompt_id"])

        try:
            with open(inbox_file_path, 'w', encoding='utf-8') as f:
                json.dump(inbox_data, f, indent=4)
            logger.info(f"{len(inbox_data)} task(s) written to {inbox_file_path}")
        except Exception as e:
            logger.error(f"Failed to write inbox for {agent_id}: {e}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

    # Example usage
    sample_agent_tasks = {
        "Agent-1": [
            {"id": "TASK-A1-001", "desc": "Review monitoring logs.", "priority": "high"},
            {"id": "TASK-A1-002", "desc": "Summarize weekly activity.", "priority": "medium"}
        ],
        "Agent-7": [
            {"id": "YAML-PARSER-008", "desc": "Parse episode YAML for agent task lists."}
        ],
        "Agent-8": [
            "Disperse parsed tasks into inbox files using JSON format."
        ],
        "Agent-X": []
    }

    parser = argparse.ArgumentParser(description="Disperse tasks to agent inboxes.")
    parser.add_argument("parsed_tasks_file", help="Path to the JSON file containing parsed agent tasks.")
    parser.add_argument("--origin_episode", default="UNKNOWN_EPISODE", help="Label for the origin episode of these tasks.")
    args = parser.parse_args()

    try:
        with open(args.parsed_tasks_file, 'r', encoding='utf-8') as f:
            agent_tasks_from_file = json.load(f)
        logger.info(f"Successfully loaded tasks from {args.parsed_tasks_file}")
    except FileNotFoundError:
        logger.error(f"Error: Parsed tasks file not found at {args.parsed_tasks_file}")
        agent_tasks_from_file = None # Ensure it's defined for the print statement
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {args.parsed_tasks_file}: {e}")
        agent_tasks_from_file = None

    if agent_tasks_from_file:
        print(f"\n🔁 Starting task dispersal from {args.parsed_tasks_file} for episode {args.origin_episode}...")
        disperse_tasks_to_inboxes(agent_tasks_from_file, origin_episode=args.origin_episode)
        print("✅ Task dispersal finished.")
    else:
        print("\n❌ Task dispersal aborted due to errors loading tasks.")

    # Optional: List results
    if AGENT_INBOX_BASE_DIR.exists():
        print(f"\n📁 Contents of '{AGENT_INBOX_BASE_DIR}':")
        for item in AGENT_INBOX_BASE_DIR.glob("**/*"):
            if item.is_file():
                print(f"  - {item.relative_to(AGENT_INBOX_BASE_DIR)}")
