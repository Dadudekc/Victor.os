'''
Episode Parser (Agent-7)

Reads episode YAML and extracts agent-specific task segments.
'''

import yaml
import logging
import argparse
import json
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class EpisodeMetadata:
    episode: str
    codename: str
    overall_refined_objective: str
    theme: str
    north_star: str
    objectives: List[str]
    definition_of_done: List[str]
    next_episode_trigger: str

@dataclass
class Task:
    id: str
    owner: str
    points: int
    status: str
    description: str = ""
    deps: List[str] = None

    def __post_init__(self):
        if self.deps is None:
            self.deps = []

def parse_episode_yaml(yaml_file_path: str) -> Dict[str, Any]:
    '''
    Parses the episode YAML file and returns a dictionary containing episode metadata
    and tasks per agent.

    Args:
        yaml_file_path: Path to the episode YAML file.

    Returns:
        A dictionary containing:
        - metadata: EpisodeMetadata object with episode details
        - tasks: Dictionary where keys are agent IDs and values are lists of Task objects
    '''
    logger.info(f"Parsing episode YAML: {yaml_file_path}")
    try:
        with open(yaml_file_path, 'r', encoding='utf-8') as f:
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
            episode=episode_data['episode'],
            codename=episode_data['codename'],
            overall_refined_objective=episode_data['overall_refined_objective'],
            theme=episode_data['theme'],
            north_star=episode_data['north_star'],
            objectives=episode_data['objectives'],
            definition_of_done=episode_data['definition_of_done'],
            next_episode_trigger=episode_data['next_episode_trigger']
        )
    except KeyError as e:
        logger.error(f"Missing required metadata field: {e}")
        return {}

    # Extract tasks
    agent_tasks = {}
    task_board = episode_data.get('task_board', {})
    if not task_board:
        logger.warning("Task board is empty or not found in the YAML file.")
        return {}

    # Map milestone descriptions to tasks
    milestone_map = {
        m['id']: m['description']
        for m in episode_data.get('milestones', [])
    }

    for task_id, task_details in task_board.items():
        owner = task_details.get('owner')
        if not owner:
            logger.warning(f"Task {task_id} has no owner assigned.")
            continue

        if owner not in agent_tasks:
            agent_tasks[owner] = []

        # Get task description from milestones if available
        description = milestone_map.get(task_id, task_details.get('desc', ''))

        task = Task(
            id=task_id,
            owner=owner,
            points=task_details.get('points', 0),
            status=task_details.get('status', 'Unknown'),
            description=description,
            deps=task_details.get('deps', [])
        )
        agent_tasks[owner].append(asdict(task))

    result = {
        'metadata': asdict(metadata),
        'tasks': agent_tasks,
        'parsed_at': datetime.utcnow().isoformat()
    }

    logger.info(f"Successfully parsed tasks for agents: {list(agent_tasks.keys())}")
    return result

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s:%(name)s:%(message)s')
    
    parser = argparse.ArgumentParser(description="Parse episode YAML to extract agent tasks.")
    parser.add_argument("yaml_file", help="Path to the episode YAML file.")
    parser.add_argument("--output_file", help="Path to save the parsed tasks JSON file.", 
                       default="episodes/parsed_episode_tasks.json")
    args = parser.parse_args()

    parsed_data = parse_episode_yaml(args.yaml_file)

    if parsed_data:
        print("\nSuccessfully parsed episode:")
        print(f"Episode: {parsed_data['metadata']['episode']} - {parsed_data['metadata']['codename']}")
        print("\nTasks by agent:")
        for agent, tasks in parsed_data['tasks'].items():
            print(f"\n  {agent}:")
            for task in tasks:
                print(f"    - {task['id']} ({task['status']}): {task['description']}")

        try:
            import os
            os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
            with open(args.output_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=2)
            logger.info(f"Successfully saved parsed data to {args.output_file}")
        except Exception as e:
            logger.error(f"Error saving parsed data to {args.output_file}: {e}")
    else:
        print("\nNo data parsed or an error occurred.") 