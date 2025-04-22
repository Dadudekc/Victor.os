import os
import sys
import time
import logging
import subprocess
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

logger = logging.getLogger(__name__)

class CursorSessionManager:
    """
    Watches a directory for Cursor task files and launches Cursor IDE sessions to execute them.
    """
    def __init__(self, tasks_dir='cursor/queued_tasks', cursor_cmd=None):
        # Directory to watch for new task files (.prompt.md or .task.json)
        self.tasks_dir = os.path.abspath(tasks_dir)
        os.makedirs(self.tasks_dir, exist_ok=True)

        # Command to launch Cursor IDE (extendable via CLI)
        self.cursor_cmd = cursor_cmd or ['Cursor.exe']

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
            patterns=["*.prompt.md", "*.task.json"],
            ignore_directories=True
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


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    # Allow overriding via environment or CLI args if needed
    tasks_dir = os.getenv('CURSOR_TASKS_DIR', 'cursor/queued_tasks')
    # Optionally allow specifying full cursor command via env
    cursor_cmd = os.getenv('CURSOR_CMD')
    cmd = cursor_cmd.split() if cursor_cmd else None

    manager = CursorSessionManager(tasks_dir=tasks_dir, cursor_cmd=cmd)
    manager.start() 