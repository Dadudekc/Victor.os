"""CLI script for syncing episode statuses."""

import argparse
import logging
from pathlib import Path

from ..utils.episode_status_sync import EpisodeStatusSync


def setup_logging():
    """Configure logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main():
    """Main entry point for the episode status sync CLI."""
    parser = argparse.ArgumentParser(
        description="Sync episode statuses by analyzing runtime logs, task board, and flag files."
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=Path.cwd(),
        help="Base path containing episodes, logs, and task board (default: current directory)",
    )
    parser.add_argument(
        "--episode",
        type=str,
        help="Specific episode ID to sync (e.g., '02'). If not provided, syncs all episodes.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize sync utility
    sync = EpisodeStatusSync(args.base_path)

    if args.episode:
        # Sync single episode
        status = sync.sync_episode_status(args.episode)
        if status:
            print(f"Episode {args.episode}: {status.value}")
        else:
            print(f"Episode {args.episode} not found")
    else:
        # Sync all episodes
        statuses = sync.sync_all_episodes()
        if statuses:
            print("\nEpisode Status Summary:")
            print("-" * 30)
            for episode_id, status in sorted(statuses.items()):
                print(f"Episode {episode_id}: {status.value}")
        else:
            print("No episodes found to sync")


if __name__ == "__main__":
    main()
