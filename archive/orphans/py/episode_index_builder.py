"""
Episode Index Builder (Agent-3)

Builds and maintains a global index of all episodes in the Dream.OS project.
The index provides a flat manifest of all episodes with their key metadata,
making it easy to track project progress and history.
"""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class EpisodeIndexEntry:
    """Represents a single episode entry in the index."""

    episode_id: str
    codename: str
    title: str  # Overall refined objective
    theme: str
    north_star: str
    status: str  # Active, Completed, Planned
    artifacts: List[str]  # List of key artifacts/deliverables
    created_at: str
    updated_at: str
    objectives: List[str]
    definition_of_done: List[str]


class EpisodeIndexBuilder:
    """Builds and maintains the global episode index."""

    def __init__(self, episodes_dir: str = "episodes"):
        self.episodes_dir = Path(episodes_dir)
        self.index_file = self.episodes_dir / "EPISODE_INDEX.yaml"

    def _extract_artifacts(self, episode_data: Dict[str, Any]) -> List[str]:
        """Extract key artifacts from episode data."""
        artifacts = []

        # Extract from task board
        task_board = episode_data.get("task_board", {})
        for task_id, task_info in task_board.items():
            if isinstance(task_info, dict):
                desc = task_info.get("desc", "")
                if desc:
                    artifacts.append(f"{task_id}: {desc}")

        # Extract from milestones
        milestones = episode_data.get("milestones", [])
        for milestone in milestones:
            if isinstance(milestone, dict):
                desc = milestone.get("description", "")
                if desc:
                    artifacts.append(f"{milestone.get('id', 'Unknown')}: {desc}")

        return artifacts

    def _determine_status(self, episode_data: Dict[str, Any]) -> str:
        """Determine episode status based on task completion."""
        task_board = episode_data.get("task_board", {})
        if not task_board:
            return "Planned"

        total_tasks = len(task_board)
        completed_tasks = sum(
            1
            for task in task_board.values()
            if isinstance(task, dict) and task.get("status") == "Done"
        )

        if completed_tasks == 0:
            return "Planned"
        elif completed_tasks == total_tasks:
            return "Completed"
        else:
            return "Active"

    def _parse_episode_file(self, file_path: Path) -> Optional[EpisodeIndexEntry]:
        """Parse a single episode YAML file into an index entry."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                episode_data = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return None

        try:
            # Extract episode ID from filename (e.g., "episode-01.yaml" -> "01")
            episode_id = file_path.stem.split("-")[1]

            return EpisodeIndexEntry(
                episode_id=episode_id,
                codename=episode_data.get("codename", ""),
                title=episode_data.get("overall_refined_objective", ""),
                theme=episode_data.get("theme", ""),
                north_star=episode_data.get("north_star", ""),
                status=self._determine_status(episode_data),
                artifacts=self._extract_artifacts(episode_data),
                created_at=datetime.fromtimestamp(
                    file_path.stat().st_ctime
                ).isoformat(),
                updated_at=datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat(),
                objectives=episode_data.get("objectives", []),
                definition_of_done=episode_data.get("definition_of_done", []),
            )
        except Exception as e:
            logger.error(f"Error creating index entry for {file_path}: {e}")
            return None

    def build_index(self) -> bool:
        """Build or refresh the episode index."""
        try:
            # Find all episode YAML files
            episode_files = sorted(self.episodes_dir.glob("episode-*.yaml"))
            if not episode_files:
                logger.warning(f"No episode files found in {self.episodes_dir}")
                return False

            # Parse each episode file
            index_entries = []
            for file_path in episode_files:
                entry = self._parse_episode_file(file_path)
                if entry:
                    index_entries.append(asdict(entry))

            # Sort entries by episode ID
            index_entries.sort(key=lambda x: x["episode_id"])

            # Create the index structure
            index_data = {
                "last_updated": datetime.utcnow().isoformat(),
                "total_episodes": len(index_entries),
                "episodes": index_entries,
            }

            # Write the index file
            with open(self.index_file, "w", encoding="utf-8") as f:
                yaml.dump(index_data, f, sort_keys=False, allow_unicode=True)

            logger.info(
                f"Successfully built episode index with {len(index_entries)} entries"
            )
            return True

        except Exception as e:
            logger.error(f"Error building episode index: {e}")
            return False


def main():
    """CLI entry point for building the episode index."""
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s"
    )

    builder = EpisodeIndexBuilder()
    if builder.build_index():
        print("\n✅ Episode index built successfully!")
        print(f"📁 Index file: {builder.index_file}")
    else:
        print("\n❌ Failed to build episode index")


if __name__ == "__main__":
    main()
