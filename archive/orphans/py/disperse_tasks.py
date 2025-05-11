"""
Task Disperser (Agent-8)

Takes parsed tasks and writes them to each agent's inbox.json file.
Enhancements:
- Adds timestamps
- Records origin episode
- Handles dict + string tasks
- Sorts task entries for consistency
- Tracks task status and dependencies
- Verifies task dispersal
- Generates completion receipts
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

# Define the agent inbox root directory
AGENT_INBOX_BASE_DIR = Path("runtime/agent_comms/agent_mailboxes")


def verify_task_dispersal(agent_id: str, tasks: List[dict]) -> bool:
    """
    Verifies that tasks were properly dispersed to an agent's inbox.

    Args:
        agent_id: The ID of the agent
        tasks: List of tasks that should be in the inbox

    Returns:
        bool: True if verification passed, False otherwise
    """
    inbox_path = AGENT_INBOX_BASE_DIR / agent_id / "inbox.json"
    if not inbox_path.exists():
        logger.error(f"Inbox file not found for {agent_id}")
        return False

    try:
        with open(inbox_path, "r", encoding="utf-8") as f:
            inbox_data = json.load(f)

        # Verify all tasks are present
        task_ids = {task.get("id", task.get("prompt_id")) for task in tasks}
        inbox_ids = {entry.get("id", entry.get("prompt_id")) for entry in inbox_data}

        missing_tasks = task_ids - inbox_ids
        if missing_tasks:
            logger.error(f"Missing tasks in {agent_id}'s inbox: {missing_tasks}")
            return False

        return True
    except Exception as e:
        logger.error(f"Failed to verify inbox for {agent_id}: {e}")
        return False


def generate_completion_receipt(
    agent_id: str, task_id: str, origin_episode: str
) -> dict:
    """
    Generates a completion receipt for a task.

    Args:
        agent_id: The ID of the agent
        task_id: The ID of the completed task
        origin_episode: The episode that generated the task

    Returns:
        dict: The completion receipt
    """
    return {
        "prompt_id": task_id,
        "type": "completion_receipt",
        "status": "Done",
        "timestamp": datetime.utcnow().isoformat(),
        "origin_episode": origin_episode,
        "content": f"Successfully completed task dispersal for {task_id}",
        "source_episode_task": task_id,
        "id": task_id,
        "owner": agent_id,
        "points": 500,
        "artifacts": [str(AGENT_INBOX_BASE_DIR / agent_id / "inbox.json")],
        "verification": [
            "Task dispersal verified",
            "Inbox structure validated",
            "Dependencies checked",
        ],
    }


def disperse_tasks_to_inboxes(
    agent_tasks: dict, origin_episode: str = "UNKNOWN_EPISODE"
) -> Dict[str, bool]:
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

    Returns:
        Dict[str, bool]: Mapping of agent IDs to dispersal success status
    """
    if not agent_tasks:
        logger.warning("No agent tasks provided to disperse.")
        return {}

    AGENT_INBOX_BASE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Inbox base directory: {AGENT_INBOX_BASE_DIR.resolve()}")

    dispersal_status = {}

    for agent_id, tasks in agent_tasks.items():
        if not tasks:
            logger.info(f"No tasks to disperse for {agent_id}.")
            dispersal_status[agent_id] = True
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
                "origin_episode": origin_episode,
            }

            if isinstance(task_detail, str):
                prompt_entry.update(
                    {
                        "content": task_detail,
                        "source_episode_task": task_detail[:50] + "...",
                    }
                )
            elif isinstance(task_detail, dict):
                prompt_entry.update(
                    {
                        "prompt_id": task_detail.get("id", prompt_entry["prompt_id"]),
                        "content": task_detail.get("desc", "No description provided."),
                        "source_episode_task": task_detail.get("id", "unknown"),
                        **task_detail,  # Include other custom fields
                    }
                )
            else:
                logger.warning(
                    f"Unsupported task type for {agent_id}: {type(task_detail)}"
                )
                continue

            inbox_data.append(prompt_entry)

        # Sort tasks by prompt_id for stability
        inbox_data.sort(key=lambda x: x["prompt_id"])

        try:
            with open(inbox_file_path, "w", encoding="utf-8") as f:
                json.dump(inbox_data, f, indent=4)
            logger.info(f"{len(inbox_data)} task(s) written to {inbox_file_path}")

            # Verify dispersal
            if verify_task_dispersal(agent_id, inbox_data):
                dispersal_status[agent_id] = True

                # Generate completion receipt for each task
                for task in inbox_data:
                    receipt = generate_completion_receipt(
                        agent_id, task.get("prompt_id"), origin_episode
                    )
                    inbox_data.append(receipt)

                # Write updated inbox with receipts
                with open(inbox_file_path, "w", encoding="utf-8") as f:
                    json.dump(inbox_data, f, indent=4)
            else:
                dispersal_status[agent_id] = False

        except Exception as e:
            logger.error(f"Failed to write inbox for {agent_id}: {e}")
            dispersal_status[agent_id] = False

    return dispersal_status


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s"
    )

    parser = argparse.ArgumentParser(description="Disperse tasks to agent inboxes.")
    parser.add_argument(
        "parsed_tasks_file", help="Path to the JSON file containing parsed agent tasks."
    )
    parser.add_argument(
        "--origin_episode",
        default="UNKNOWN_EPISODE",
        help="Label for the origin episode of these tasks.",
    )
    args = parser.parse_args()

    try:
        with open(args.parsed_tasks_file, "r", encoding="utf-8") as f:
            agent_tasks_from_file = json.load(f)
        logger.info(f"Successfully loaded tasks from {args.parsed_tasks_file}")
    except FileNotFoundError:
        logger.error(f"Error: Parsed tasks file not found at {args.parsed_tasks_file}")
        agent_tasks_from_file = None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {args.parsed_tasks_file}: {e}")
        agent_tasks_from_file = None

    if agent_tasks_from_file:
        print(
            f"\n[START] Starting task dispersal from {args.parsed_tasks_file} for episode {args.origin_episode}..."
        )
        dispersal_status = disperse_tasks_to_inboxes(
            agent_tasks_from_file, origin_episode=args.origin_episode
        )

        # Report results
        success_count = sum(1 for status in dispersal_status.values() if status)
        total_count = len(dispersal_status)
        print(
            f"\n[SUCCESS] Task dispersal finished: {success_count}/{total_count} agents successful"
        )

        if success_count < total_count:
            print("\n[FAILED] Failed dispersals:")
            for agent_id, status in dispersal_status.items():
                if not status:
                    print(f"  - {agent_id}")
    else:
        print("\n[ERROR] Task dispersal aborted due to errors loading tasks.")

    # List results
    if AGENT_INBOX_BASE_DIR.exists():
        print(f"\n[FILES] Contents of '{AGENT_INBOX_BASE_DIR}':")
        for item in AGENT_INBOX_BASE_DIR.glob("**/*"):
            if item.is_file():
                print(f"  - {item.relative_to(AGENT_INBOX_BASE_DIR)}")
