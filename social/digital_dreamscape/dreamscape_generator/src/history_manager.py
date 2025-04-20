# Placeholder for HistoryManager logic
# Responsibilities:
# - Loading chat history from files (e.g., history/ directory)
# - Saving chat history (if applicable)
# - Querying/filtering history (e.g., find messages about 'asyncio')

import os
import logging
from typing import List, Optional

from dreamscape_generator import config as project_config

logger = logging.getLogger(__name__)
logger.setLevel(project_config.LOG_LEVEL)

class HistoryManager:
    """Manages access to chat history files."""
    def __init__(self, history_dir: str = project_config.HISTORY_DIR):
        self.history_dir = history_dir
        if not os.path.isdir(self.history_dir):
            logger.warning(f"History directory not found: {self.history_dir}. Creating it.")
            try:
                os.makedirs(self.history_dir)
            except OSError as e:
                logger.error(f"Failed to create history directory: {e}", exc_info=True)
                # Consider raising an error if the history dir is crucial and cannot be created
                raise

        logger.info(f"HistoryManager initialized for directory: {self.history_dir}")

    def find_history_files(self) -> List[str]:
        """Finds potential history files (e.g., .json, .txt, .md) in the history directory."""
        try:
            files = [f for f in os.listdir(self.history_dir)
                     if os.path.isfile(os.path.join(self.history_dir, f))
                     and f.lower().endswith(('.json', '.txt', '.md'))]
            logger.info(f"Found {len(files)} potential history files in {self.history_dir}.")
            # Sort files, potentially by modification time to find latest easily
            files.sort(key=lambda f: os.path.getmtime(os.path.join(self.history_dir, f)), reverse=True)
            return files
        except FileNotFoundError:
             logger.error(f"History directory not found when trying to list files: {self.history_dir}")
             return []
        except Exception as e:
            logger.error(f"Error listing history files in {self.history_dir}: {e}", exc_info=True)
            return []

    def get_recent_snippets(self, history_file: Optional[str] = None, query: Optional[str] = None, num_snippets: int = 10) -> str:
        """Loads snippets from a history file.

        Args:
            history_file: The specific history filename within the history_dir.
                          If None, attempts to use the most recently modified file.
            query: Optional search term to filter snippets (NOT IMPLEMENTED YET).
            num_snippets: The maximum number of recent lines/messages to return.

        Returns:
            A string containing the recent snippets, or an error/placeholder message.
        """
        if query:
            logger.warning("History query filtering is not yet implemented. Returning general snippets.")
            # TODO: Implement query-based filtering logic here.

        target_file = None
        if history_file:
            # Use the specified file if provided
            potential_path = os.path.join(self.history_dir, history_file)
            if os.path.isfile(potential_path):
                target_file = potential_path
            else:
                logger.error(f"Specified history file not found: {potential_path}")
                return f"[Error: History file '{history_file}' not found]"
        else:
            # Try to find the latest history file
            available_files = self.find_history_files()
            if available_files:
                target_file = os.path.join(self.history_dir, available_files[0]) # [0] is latest due to sort
                logger.info(f"No specific history file provided, using latest: {available_files[0]}")
            else:
                logger.warning("No history files found in directory. Cannot retrieve snippets.")
                return "[No history available]"

        # Read the last N lines from the target file
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                # Read all lines, then take the last N. Efficient for moderately sized files.
                # For very large files, a different approach might be needed.
                lines = f.readlines()
                start_index = max(0, len(lines) - num_snippets)
                snippets = [line.strip() for line in lines[start_index:]]
                logger.info(f"Read {len(snippets)} lines from '{os.path.basename(target_file)}'.")
                return "\n".join(snippets)
        except Exception as e:
            logger.error(f"Error reading snippets from history file {target_file}: {e}", exc_info=True)
            return f"[Error reading history file: {os.path.basename(target_file)}]"

    # Add other methods as needed, e.g.:
    # def load_full_history(self, filename: str) -> List[str]: ...
    # def save_history(self, filename: str, messages: List[str]): ...

__all__ = ["HistoryManager"] 