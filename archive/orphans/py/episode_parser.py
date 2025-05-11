"""
Episode Parser (Agent-7)

Reads episode YAML and extracts agent-specific task segments.
"""

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """Represents a single task in the episode."""

    id: str
    title: str
    assigned_to: str
    priority: str
    status: str
    details: Dict[str, Any]
    dependencies: List[str] = None


@dataclass
class Milestone:
    """Represents a milestone in the episode."""

    id: str
    title: str
    description: str
    tasks: List[Task]


@dataclass
class EpisodeMetadata:
    """Represents the metadata of an episode."""

    episode_id: str
    title: str
    status: str
    timestamp: str
    objectives: List[str]


def parse_episode_yaml(yaml_file_path: str) -> Dict[str, Any]:
    """
    Parses the episode YAML file and returns a dictionary containing episode metadata
    and tasks per agent.

    Args:
        yaml_file_path: Path to the episode YAML file.

    Returns:
        A dictionary containing:
        - metadata: EpisodeMetadata object with episode details
        - milestones: List of Milestone objects
        - tasks: Dictionary where keys are agent IDs and values are lists of Task objects
    """
    logger.info(f"Parsing episode YAML: {yaml_file_path}")
    try:
        with open(yaml_file_path, "r", encoding="utf-8") as f:
            episode_data = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Error: Episode YAML file not found at {yaml_file_path}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {yaml_file_path}: {e}")
        return {}

    # Extract metadata
    try:
        metadata = EpisodeMetadata(
            episode_id=episode_data["episode_id"],
            title=episode_data["title"],
            status=episode_data["status"],
            timestamp=episode_data["timestamp"],
            objectives=episode_data["objectives"],
        )
    except KeyError as e:
        logger.error(f"Missing required metadata field: {e}")
        return {}

    # Extract milestones and their tasks
    milestones = []
    agent_tasks = {}

    for milestone_data in episode_data.get("milestones", []):
        milestone_tasks = []

        for task_data in milestone_data.get("tasks", []):
            task = Task(
                id=task_data["id"],
                title=task_data["title"],
                assigned_to=task_data["assigned_to"],
                priority=task_data["priority"],
                status="PENDING",
                details=task_data["details"],
                dependencies=task_data.get("dependencies", []),
            )

            # Add to milestone tasks
            milestone_tasks.append(task)

            # Add to agent tasks
            if task.assigned_to not in agent_tasks:
                agent_tasks[task.assigned_to] = []
            agent_tasks[task.assigned_to].append(asdict(task))

        milestone = Milestone(
            id=milestone_data["id"],
            title=milestone_data["title"],
            description=milestone_data["description"],
            tasks=milestone_tasks,
        )
        milestones.append(asdict(milestone))

    result = {
        "metadata": asdict(metadata),
        "milestones": milestones,
        "tasks": agent_tasks,
        "dependencies": episode_data.get("dependencies", []),
        "success_criteria": episode_data.get("success_criteria", []),
        "rollout_plan": episode_data.get("rollout_plan", {}),
        "monitoring": episode_data.get("monitoring", {}),
        "parsed_at": datetime.utcnow().isoformat(),
    }

    logger.info(f"Successfully parsed tasks for agents: {list(agent_tasks.keys())}")
    return result


def validate_episode_structure(episode_data: Dict[str, Any]) -> bool:
    """
    Validates the structure of the parsed episode data.

    Args:
        episode_data: The parsed episode data dictionary.

    Returns:
        bool: True if the structure is valid, False otherwise.
    """
    required_fields = ["metadata", "milestones", "tasks"]
    if not all(field in episode_data for field in required_fields):
        logger.error("Missing required fields in episode data")
        return False

    # Validate metadata
    metadata = episode_data["metadata"]
    required_metadata = ["episode_id", "title", "status", "timestamp", "objectives"]
    if not all(field in metadata for field in required_metadata):
        logger.error("Missing required metadata fields")
        return False

    # Validate milestones
    for milestone in episode_data["milestones"]:
        required_milestone = ["id", "title", "description", "tasks"]
        if not all(field in milestone for field in required_milestone):
            logger.error(
                f"Missing required fields in milestone {milestone.get('id', 'Unknown')}"
            )
            return False

    # Validate tasks
    for agent, tasks in episode_data["tasks"].items():
        for task in tasks:
            required_task = [
                "id",
                "title",
                "assigned_to",
                "priority",
                "status",
                "details",
            ]
            if not all(field in task for field in required_task):
                logger.error(
                    f"Missing required fields in task {task.get('id', 'Unknown')}"
                )
                return False

    return True


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    )

    parser = argparse.ArgumentParser(
        description="Parse episode YAML to extract agent tasks."
    )
    parser.add_argument("yaml_file", help="Path to the episode YAML file.")
    parser.add_argument(
        "--output_file",
        help="Path to save the parsed tasks JSON file.",
        default="episodes/parsed_episode_tasks.json",
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate episode structure"
    )
    args = parser.parse_args()

    parsed_data = parse_episode_yaml(args.yaml_file)

    if parsed_data:
        if args.validate and not validate_episode_structure(parsed_data):
            logger.error("Episode structure validation failed")
            exit(1)

        print("\nSuccessfully parsed episode:")
        print(
            f"Episode: {parsed_data['metadata']['episode_id']} - {parsed_data['metadata']['title']}"
        )
        print("\nMilestones:")
        for milestone in parsed_data["milestones"]:
            print(f"\n  {milestone['title']}:")
            print(f"    {milestone['description']}")
            for task in milestone["tasks"]:
                print(f"      - {task['title']} (Assigned to: {task['assigned_to']})")

        print("\nTasks by agent:")
        for agent, tasks in parsed_data["tasks"].items():
            print(f"\n  {agent}:")
            for task in tasks:
                print(f"    - {task['title']} ({task['status']})")

        try:
            output_path = Path(args.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(parsed_data, f, indent=2)
            logger.info(f"Successfully saved parsed data to {args.output_file}")
        except Exception as e:
            logger.error(f"Error saving parsed data to {args.output_file}: {e}")
    else:
        print("\nNo data parsed or an error occurred.")
