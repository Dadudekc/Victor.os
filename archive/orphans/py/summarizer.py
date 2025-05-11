"""Episode Summarizer: Generates dual-format episode outputs (markdown briefing and narrative JSON)."""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict

import yaml

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

DEFAULT_OUTPUT_DIR = Path("runtime/episode_outputs/")
DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_episode_yaml(episode_id: str) -> Dict:
    """Load episode data from the YAML file in episodes/."""
    yaml_path = Path(f"episodes/episode-{episode_id}.yaml")
    if not yaml_path.exists():
        raise FileNotFoundError(f"Episode YAML not found: {yaml_path}")
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    logging.info(f"Loaded YAML data: {data}")
    required_fields = [
        "title",
        "objectives",
        "task_board",
        "narrative",
        "themes",
        "milestones",
    ]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        logging.error(
            f"Missing required fields in {yaml_path}: {', '.join(missing_fields)}"
        )
        exit(1)
    return data


def generate_markdown_briefing(episode_data: Dict) -> str:
    """Generate a structured markdown briefing from episode data."""
    try:
        title = episode_data.get("title", "Unknown Episode")
        objective = episode_data.get("objectives", ["No objectives defined"])[0]
        tasks = episode_data.get("task_board", [])
        status = episode_data.get("status", "Unknown")

        md = f"# {title}\n\n"
        md += "## 🎯 Mission Objective\n"
        md += f"{objective}\n\n"
        md += "## 🧠 Assigned Tasks\n\n"
        md += "| ID | Description | Agent | Status |\n"
        md += "|----|-------------|-------|--------|\n"
        for task in tasks:
            task_id = task.get("id", "N/A")
            desc = task.get("description", "N/A")
            agent = task.get("assigned_to", "N/A")
            task_status = task.get("status", "PENDING")
            md += f"| {task_id} | {desc} | {agent} | {task_status} |\n"
        md += f"\n## 📦 Status: {status}\n"
        return md
    except KeyError as e:
        logging.error(f"KeyError in generate_markdown_briefing: {e}")
        raise
    except TypeError as e:
        logging.error(f"TypeError in generate_markdown_briefing: {e}")
        raise


def generate_lore_json(episode_data: Dict) -> Dict:
    """Generate a narrative-styled JSON blob for Dreamscape lore conversion."""
    try:
        title = episode_data.get("title", "Unknown Episode")
        narrative = episode_data.get("narrative", "No narrative provided.")
        themes = episode_data.get("themes", ["unknown"])
        milestones = episode_data.get("milestones", ["No milestones defined"])

        lore = {
            "title": title,
            "narrative": narrative,
            "themes": themes,
            "milestones": milestones,
        }
        return lore
    except KeyError as e:
        logging.error(f"KeyError in generate_lore_json: {e}")
        raise
    except TypeError as e:
        logging.error(f"TypeError in generate_lore_json: {e}")
        raise


def generate_devlog(episode_data):
    """Generate a devlog entry for the episode."""
    devlog_entry = f"# Devlog Entry for Episode {episode_data['episode_id']}\n\n"
    devlog_entry += f"## Overview\n{episode_data['overall_refined_objective']}\n\n"
    devlog_entry += "## Tasks\n"
    for task in episode_data["task_board"]:
        devlog_entry += f"- {task['name']} ({task['status']})\n"
    return devlog_entry


def write_episode_briefing(episode_number: int, summary_content: str):
    """Write the episode briefing markdown to the unified output directory."""
    output_path = DEFAULT_OUTPUT_DIR / f"EPISODE_{episode_number:02}_BRIEFING.md"
    logging.info(f"Writing markdown briefing to {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(summary_content)
    print(f"✅ Markdown briefing written to {output_path}")


def write_lore_json(episode_number: int, lore_data: Dict):
    """Write the narrative-styled JSON blob to the unified output directory."""
    output_path = DEFAULT_OUTPUT_DIR / f"episode_{episode_number:02}_lore.json"
    logging.info(f"Writing lore JSON to {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(lore_data, f, indent=2)
    print(f"✅ Lore JSON written to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate episode briefings and lore JSON."
    )
    parser.add_argument("--episode", required=True, help="Episode ID (e.g., '03')")
    parser.add_argument(
        "--output", help="Output directory (default: runtime/episode_outputs/)"
    )
    args = parser.parse_args()

    episode_id = args.episode
    output_dir = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        episode_data = load_episode_yaml(episode_id)
        md_briefing = generate_markdown_briefing(episode_data)
        lore_json = generate_lore_json(episode_data)
        devlog_entry = generate_devlog(episode_data)
        write_episode_briefing(episode_id, md_briefing)
        write_lore_json(episode_id, lore_json)
        devlog_path = DEFAULT_OUTPUT_DIR / f"EPISODE_{episode_id}_DEVLOG.md"
        with open(devlog_path, "w", encoding="utf-8") as f:
            f.write(devlog_entry)
        logging.info(f"Writing devlog entry to {devlog_path}")
        print(f"✅ Devlog entry written to {devlog_path}")
    except Exception as e:
        logging.error(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
