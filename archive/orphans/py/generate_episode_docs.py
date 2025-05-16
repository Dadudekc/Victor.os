#!/usr/bin/env python3
"""
Episode Documentation Generator for Dream.OS
Converts episode YAML files to human-readable Markdown documentation.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EpisodeDocGenerator:
    def __init__(self, yaml_path: str):
        self.yaml_path = Path(yaml_path)
        self.episode_data = None
        self.output_dir = Path("docs/episodes")

    def load_episode(self) -> bool:
        """Load episode YAML file."""
        try:
            with open(self.yaml_path, "r", encoding="utf-8") as f:
                self.episode_data = yaml.safe_load(f)
            return True
        except Exception as e:
            logger.error(f"Error loading episode: {str(e)}")
            return False

    def generate_markdown(self) -> str:
        """Generate Markdown documentation from episode data."""
        if not self.episode_data:
            return ""

        md_lines = [
            f"# Episode {self.episode_data['episode']['number']}: {self.episode_data['episode']['codename']}",
            f"\n*Theme: {self.episode_data['episode']['theme']}*",
            "\n## Overview",
            f"\n{self.episode_data['episode']['north_star']}",
            "\n## Objectives",
        ]

        # Add objectives
        for obj in self.episode_data["objectives"]:
            md_lines.append(f"- {obj}")

        # Add milestones
        md_lines.extend(
            [
                "\n## Milestones",
                "| ID | Name | Description |",
                "|----|------|-------------|",
            ]
        )
        for milestone in self.episode_data["milestones"]:
            md_lines.append(
                f"| {milestone['id']} | {milestone['name']} | {milestone['description']} |"
            )

        # Add task board
        md_lines.extend(
            [
                "\n## Task Board",
                "| Task ID | Owner | Points | Status | Intent |",
                "|---------|-------|--------|--------|--------|",
            ]
        )
        for task_id, task in self.episode_data["task_board"].items():
            md_lines.append(
                f"| {task_id} | {task['owner']} | {task['points']} | {task['status']} | {task['intent']} |"
            )

        # Add guardian directives
        md_lines.extend(
            [
                "\n## Guardian Directives",
                "These core principles guide all autonomous operations:",
                "",
            ]
        )
        for directive in self.episode_data["guardian_directives"]:
            md_lines.append(f"- {directive}")

        # Add self-regulation hooks
        md_lines.extend(
            [
                "\n## Self-Regulation Hooks",
                "### Thresholds",
                "```yaml",
                yaml.dump(
                    self.episode_data["self_regulation_hooks"]["thresholds"],
                    default_flow_style=False,
                ),
                "```",
                "\n### Behaviors",
                "```yaml",
                yaml.dump(
                    self.episode_data["self_regulation_hooks"]["behaviors"],
                    default_flow_style=False,
                ),
                "```",
            ]
        )

        # Add agent awareness
        md_lines.extend(
            [
                "\n## Agent Awareness",
                "| Agent | Role | Purpose |",
                "|-------|------|---------|",
            ]
        )
        for agent, info in self.episode_data["agent_awareness"][
            "agent_prefixes"
        ].items():
            md_lines.append(
                f"| {agent} | {info} | {self.episode_data['agent_awareness']['config_file']} |"
            )

        # Add digital empathy
        md_lines.extend(
            [
                "\n## Digital Empathy",
                f"Log Directory: `{self.episode_data['digital_empathy']['log_dir']}`",
                "\n### Reflection Template",
                "```yaml",
                yaml.dump(
                    self.episode_data["digital_empathy"]["template"],
                    default_flow_style=False,
                ),
                "```",
            ]
        )

        # Add definition of done
        md_lines.extend(
            ["\n## Definition of Done", "The episode is complete when:", ""]
        )
        for item in self.episode_data["definition_of_done"]:
            md_lines.append(f"- {item}")

        # Add metadata
        md_lines.extend(
            [
                "\n---",
                f"\n*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
                f"*Next Episode Trigger: {self.episode_data['next_episode_trigger']}*",
            ]
        )

        return "\n".join(md_lines)

    def save_documentation(self) -> bool:
        """Save generated documentation to file."""
        if not self.episode_data:
            return False

        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = (
            self.output_dir / f"episode-{self.episode_data['episode']['number']}.md"
        )

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(self.generate_markdown())
            logger.info(f"Saved documentation to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving documentation: {str(e)}")
            return False


def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_episode_docs.py <episode_yaml_path>")
        sys.exit(1)

    yaml_path = sys.argv[1]
    generator = EpisodeDocGenerator(yaml_path)

    if generator.load_episode():
        if generator.save_documentation():
            logger.info("Documentation generation completed successfully")
        else:
            logger.error("Failed to save documentation")
    else:
        logger.error("Failed to load episode")
        sys.exit(1)


if __name__ == "__main__":
    main()
