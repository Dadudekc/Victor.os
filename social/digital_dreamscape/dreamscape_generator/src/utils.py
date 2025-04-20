"""
Utility functions for the Dreamscape Generator package.
"""

import os
import re
import json
import shutil
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Use a logger specific to utils, inheriting configuration from root?
# Or configure separately if needed.
logger = logging.getLogger(__name__) # Inherits level from root logger setup in main scripts

def sanitize_filename(text: str) -> str:
    """Removes characters unsafe for filenames and limits length."""
    if not isinstance(text, str): return "untitled"
    # Remove characters that are problematic for filenames
    text = re.sub(r'[\/*?:"<>|]', "", text)
    # Replace sequences of whitespace with a single underscore
    text = re.sub(r'\s+', '_', text)
    # Limit length to avoid issues with max path length
    max_len = 100
    if len(text) > max_len:
        # Try to cut at last underscore if one exists within the limit
        try:
            text = text[:max_len].rsplit('_', 1)[0]
        except IndexError:
            text = text[:max_len] # Cut directly if no underscore found
    return text.strip('_') or "untitled" # Ensure not empty

def save_episode_file(
    episode_dir: str,
    episode_filename: str,
    narrative: str,
    update_dict: Optional[Dict[str, Any]],
    metadata: Dict[str, Any]
) -> Optional[str]:
    """Saves the generated episode narrative and metadata to a JSON file.
    Backs up the existing file with a timestamp if it exists before overwriting.

    Args:
        episode_dir: The directory to save the episode file in.
        episode_filename: The base filename (e.g., 'sanitized_episode_title.json').
                           The .json extension will be added if missing.
        narrative: The generated story text.
        update_dict: The parsed experience update dictionary (MEMORY_UPDATE block), if any.
        metadata: Additional metadata (timestamp, source, title etc.).

    Returns:
        The full path to the saved episode file, or None if saving failed.
    """
    if not episode_filename.endswith('.json'):
        episode_filename += '.json'

    try:
        os.makedirs(episode_dir, exist_ok=True) # Ensure directory exists
    except OSError as e:
        logger.error(f"Failed to create episode directory '{episode_dir}': {e}", exc_info=True)
        return None

    target_filepath = os.path.join(episode_dir, episode_filename)
    logger.info(f"Preparing to save episode to: {target_filepath}")

    # --- Backup existing file ---
    if os.path.exists(target_filepath):
        try:
            timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
            # Ensure backup name doesn't clash if original already had .bak
            base, ext = os.path.splitext(episode_filename)
            backup_filename = f"{base}_{timestamp_str}.bak{ext}" # e.g., file_timestamp.bak.json
            backup_filepath = os.path.join(episode_dir, backup_filename)
            logger.info(f"Backing up existing episode file '{target_filepath}' to '{backup_filepath}'")
            shutil.move(target_filepath, backup_filepath)
        except (OSError, shutil.Error) as e:
            logger.error(f"Failed to back up existing episode file '{target_filepath}': {e}", exc_info=True)
            # Continue attempting to save the new file despite backup failure
            logger.warning(f"Proceeding to save {target_filepath} despite backup failure.")

    # --- Save new file ---
    episode_data = {
        "metadata": metadata,
        "narrative": narrative,
        "experience_update": update_dict # Store the MEMORY_UPDATE block itself
    }

    try:
        with open(target_filepath, 'w', encoding='utf-8') as f:
            json.dump(episode_data, f, indent=4, ensure_ascii=False)
        logger.info(f"Episode saved successfully to: {target_filepath}")
        return target_filepath
    except IOError as e:
        logger.error(f"Failed to write episode file '{target_filepath}': {e}", exc_info=True)
        return None
    except TypeError as e:
         logger.error(f"Failed to serialize episode data to JSON for '{target_filepath}': {e}", exc_info=True)
         logger.debug(f"Episode Data causing error: {episode_data}")
         return None

__all__ = ["sanitize_filename", "save_episode_file"] 