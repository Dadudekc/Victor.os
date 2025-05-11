"""Utility for syncing episode statuses by analyzing multiple sources."""

import logging
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Set

from .file_io import read_json_file, write_json_atomic

logger = logging.getLogger(__name__)


class EpisodeStatus(Enum):
    """Episode completion status indicators."""

    COMPLETE = "✅"  # All tasks done, logs show success
    IN_PROGRESS = "🟡"  # Some tasks active, no failures
    PENDING = "⏳"  # Not started or failed tasks


class EpisodeStatusSync:
    """Synchronizes episode statuses by analyzing multiple sources."""

    def __init__(self, base_path: Path):
        """Initialize with base path for all episode-related files.

        Args:
            base_path: Root path containing episodes, logs, and task board
        """
        self.base_path = Path(base_path)
        self.runtime_logs_path = self.base_path / "runtime" / "logs"
        self.episodes_path = self.base_path / "episodes"
        self.task_board_path = self.base_path / "task_board"

    def _get_episode_flag_files(self, episode_id: str) -> Set[Path]:
        """Find all .flag files for an episode.

        Args:
            episode_id: Episode identifier (e.g., "02")

        Returns:
            Set of Path objects for flag files
        """
        flag_files = set()
        for path in self.runtime_logs_path.rglob(f"*{episode_id}*.flag"):
            flag_files.add(path)
        return flag_files

    def _check_runtime_logs(self, episode_id: str) -> bool:
        """Check runtime logs for episode completion indicators.

        Args:
            episode_id: Episode identifier

        Returns:
            True if logs indicate successful completion
        """
        log_pattern = f"*{episode_id}*.log"
        success_indicators = {"completed", "success", "finished", "done"}

        for log_file in self.runtime_logs_path.rglob(log_pattern):
            try:
                content = log_file.read_text(encoding="utf-8").lower()
                if any(indicator in content for indicator in success_indicators):
                    return True
            except Exception as e:
                logger.warning(f"Error reading log file {log_file}: {e}")
        return False

    def _get_task_board_status(self, episode_id: str) -> Dict[str, str]:
        """Get task statuses from task board for an episode.

        Args:
            episode_id: Episode identifier

        Returns:
            Dict mapping task IDs to their status
        """
        task_board_file = self.task_board_path / f"episode_{episode_id}_tasks.json"
        if not task_board_file.exists():
            return {}

        try:
            tasks = read_json_file(task_board_file)
            if not tasks or not isinstance(tasks, dict):
                return {}

            return {
                task_id: task_data.get("status", "Unknown")
                for task_id, task_data in tasks.items()
            }
        except Exception as e:
            logger.error(f"Error reading task board for episode {episode_id}: {e}")
            return {}

    def _determine_episode_status(
        self,
        episode_id: str,
        task_statuses: Dict[str, str],
        has_flag_files: bool,
        has_success_logs: bool,
    ) -> EpisodeStatus:
        """Determine overall episode status based on all indicators.

        Args:
            episode_id: Episode identifier
            task_statuses: Dict of task IDs to their status
            has_flag_files: Whether episode has flag files
            has_success_logs: Whether logs indicate success

        Returns:
            EpisodeStatus enum value
        """
        if not task_statuses:
            return EpisodeStatus.PENDING

        # Check for any failed tasks
        if any(status.lower() == "failed" for status in task_statuses.values()):
            return EpisodeStatus.PENDING

        # Check if all tasks are done
        all_done = all(
            status.lower() in {"done", "completed", "success"}
            for status in task_statuses.values()
        )

        if all_done and (has_flag_files or has_success_logs):
            return EpisodeStatus.COMPLETE

        # Check if any tasks are active
        has_active = any(
            status.lower() in {"active", "in_progress", "running"}
            for status in task_statuses.values()
        )

        if has_active:
            return EpisodeStatus.IN_PROGRESS

        return EpisodeStatus.PENDING

    def sync_episode_status(self, episode_id: str) -> Optional[EpisodeStatus]:
        """Synchronize status for a specific episode.

        Args:
            episode_id: Episode identifier

        Returns:
            EpisodeStatus enum value or None if episode not found
        """
        # Get all status indicators
        flag_files = self._get_episode_flag_files(episode_id)
        has_success_logs = self._check_runtime_logs(episode_id)
        task_statuses = self._get_task_board_status(episode_id)

        # Determine overall status
        status = self._determine_episode_status(
            episode_id, task_statuses, bool(flag_files), has_success_logs
        )

        # Update episode metadata if it exists
        episode_file = self.episodes_path / f"episode-{episode_id}.yaml"
        if episode_file.exists():
            try:
                with open(episode_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Update status in content
                if "status:" in content:
                    content = content.replace(
                        f"status: {status.value}", f"status: {status.value}"
                    )
                else:
                    # Add status if not present
                    content += f"\nstatus: {status.value}\n"

                # Write back atomically
                write_json_atomic(episode_file, content)

            except Exception as e:
                logger.error(f"Error updating episode file {episode_file}: {e}")

        return status

    def sync_all_episodes(self) -> Dict[str, EpisodeStatus]:
        """Synchronize status for all episodes.

        Returns:
            Dict mapping episode IDs to their status
        """
        statuses = {}
        for episode_file in self.episodes_path.glob("episode-*.yaml"):
            try:
                episode_id = episode_file.stem.split("-")[1]
                status = self.sync_episode_status(episode_id)
                if status:
                    statuses[episode_id] = status
            except Exception as e:
                logger.error(f"Error processing episode file {episode_file}: {e}")

        return statuses
