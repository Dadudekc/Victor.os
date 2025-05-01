import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    from dreamos.core.config import AppConfig

logger = logging.getLogger(__name__)


class CursorSessionManager:
    """
    Watches a directory for Cursor task files and launches Cursor IDE sessions to execute them.
    """

    def __init__(self, tasks_dir="cursor/queued_tasks", cursor_cmd=None):
        # Directory to watch for new task files (.prompt.md or .task.json)
        self.tasks_dir = os.path.abspath(tasks_dir)
        os.makedirs(self.tasks_dir, exist_ok=True)

        # Command to launch Cursor IDE (extendable via CLI)
        self.cursor_cmd = cursor_cmd or ["Cursor.exe"]

    def on_created(self, event):
        """Called when a new task file appears."""
        file_path = event.src_path
        logger.info(f"New task detected: {file_path}")
        try:
            # Launch Cursor with the task file
            subprocess.Popen(self.cursor_cmd + [file_path])
            logger.info(f"Launched Cursor for task {file_path}")
        except Exception as e:
            logger.error(f"Failed to launch Cursor for {file_path}: {e}", exc_info=True)

    def start(self):
        """Starts watching the tasks directory."""
        event_handler = PatternMatchingEventHandler(
            patterns=["*.prompt.md", "*.task.json"], ignore_directories=True
        )
        event_handler.on_created = self.on_created

        observer = Observer()
        observer.schedule(event_handler, self.tasks_dir, recursive=False)
        observer.start()

        logger.info(f"CursorSessionManager is watching: {self.tasks_dir}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping CursorSessionManager...")
            observer.stop()
        observer.join()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )

    # EDIT START: Load AppConfig and get values from there
    # Allow overriding via environment or CLI args if needed
    # tasks_dir = os.getenv('CURSOR_TASKS_DIR', 'cursor/queued_tasks')
    # # Optionally allow specifying full cursor command via env
    # cursor_cmd = os.getenv('CURSOR_CMD')
    # cmd = cursor_cmd.split() if cursor_cmd else None

    tasks_dir = "cursor/queued_tasks"  # Default
    cmd = None  # Default

    try:
        from dreamos.core.config import load_app_config  # Assuming this exists

        config = load_app_config()
        if config:
            # Use paths relative to project root from config if available
            tasks_dir_path = getattr(config.paths, "cursor_tasks_dir", Path(tasks_dir))
            # Ensure tasks_dir is absolute path string for the manager
            tasks_dir = str(config.project_root / tasks_dir_path)
            cursor_config = getattr(config.tools, "cursor", None)
            if cursor_config and cursor_config.command:
                cmd = cursor_config.command.split()  # Split command string into list
            logger.info(f"Loaded config: Tasks Dir='{tasks_dir}', Cursor Cmd='{cmd}'")
        else:
            logger.warning("Failed to load AppConfig, using default paths/commands.")
            # Ensure default tasks_dir is relative to CWD if config fails
            tasks_dir = os.path.abspath(tasks_dir)

    except Exception as e:
        logger.error(
            f"Error loading AppConfig for CursorSessionManager: {e}. Using defaults.",
            exc_info=True,
        )
        # Ensure default tasks_dir is relative to CWD if config fails
        tasks_dir = os.path.abspath(tasks_dir)
    # EDIT END

    manager = CursorSessionManager(tasks_dir=tasks_dir, cursor_cmd=cmd)
    manager.start()
