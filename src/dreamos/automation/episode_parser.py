#!/usr/bin/env python3
"""
Episode Parser for Dream.OS
Validates and parses episode YAML files into structured task data.
"""

import yaml
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EpisodeParser:
    def __init__(self, yaml_path: str):
        self.yaml_path = Path(yaml_path)
        self.episode_data = None
        self.parsed_tasks = None

    def validate_structure(self) -> bool:
        """Validate the episode YAML structure."""
        required_sections = [
            'episode', 'objectives', 'milestones', 
            'task_board', 'guardian_directives',
            'self_regulation_hooks', 'agent_awareness',
            'digital_empathy', 'definition_of_done'
        ]
        
        try:
            with open(self.yaml_path, 'r', encoding='utf-8') as f:
                self.episode_data = yaml.safe_load(f)
            
            # Check required sections
            for section in required_sections:
                if section not in self.episode_data:
                    logger.error(f"Missing required section: {section}")
                    return False
                
            # Validate task board structure
            for task_id, task_data in self.episode_data['task_board'].items():
                required_fields = ['description', 'file', 'intent', 'owner', 'points', 'status']
                for field in required_fields:
                    if field not in task_data:
                        logger.error(f"Task {task_id} missing required field: {field}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating episode structure: {str(e)}")
            return False

    def parse_tasks(self) -> Dict[str, Any]:
        """Parse tasks into structured format."""
        if not self.episode_data:
            logger.error("No episode data loaded")
            return None

        parsed_tasks = {
            'episode_info': {
                'number': self.episode_data['episode']['number'],
                'codename': self.episode_data['episode']['codename'],
                'theme': self.episode_data['episode']['theme']
            },
            'tasks': []
        }

        for task_id, task_data in self.episode_data['task_board'].items():
            parsed_task = {
                'id': task_id,
                'description': task_data['description'],
                'file': task_data['file'],
                'intent': task_data['intent'],
                'owner': task_data['owner'],
                'points': task_data['points'],
                'status': task_data['status']
            }
            parsed_tasks['tasks'].append(parsed_task)

        self.parsed_tasks = parsed_tasks
        return parsed_tasks

    def save_parsed_tasks(self, output_path: str = None) -> bool:
        """Save parsed tasks to JSON file."""
        if not self.parsed_tasks:
            logger.error("No parsed tasks to save")
            return False

        if not output_path:
            output_path = self.yaml_path.parent / f"parsed_episode_{self.episode_data['episode']['number']}_tasks.json"

        try:
            with open(output_path, 'w') as f:
                json.dump(self.parsed_tasks, f, indent=2)
            logger.info(f"Saved parsed tasks to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving parsed tasks: {str(e)}")
            return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python episode_parser.py <episode_yaml_path>")
        sys.exit(1)

    yaml_path = sys.argv[1]
    parser = EpisodeParser(yaml_path)
    
    if parser.validate_structure():
        logger.info("Episode structure validation successful")
        if parser.parse_tasks():
            parser.save_parsed_tasks()
            logger.info("Episode parsing completed successfully")
        else:
            logger.error("Failed to parse tasks")
    else:
        logger.error("Episode structure validation failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 