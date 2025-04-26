"""
Command-line interface for adding Dreamscape episodes and updating memory.

This script allows adding new episodes (narrative + memory update) to the
Dreamscape chronicle from the command line, facilitating integration with
external agents or manual logging.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# --- Configuration ---
# Attempt to import config and core components from dreamscape_generator
# This requires the script to be run in an environment where dreamscape_generator
# is accessible (e.g., installed via pip install -e . or PYTHONPATH set).
try:
    # Assuming the script is run from the root or the package is installed
    from dreamscape_generator import config as project_config
    from dreamscape_generator.core.MemoryManager import MemoryManager
    from dreamscape_generator.utils import sanitize_filename, save_episode_file
except ImportError as e:
    print(f"Error: Failed to import dreamscape_generator components: {e}", file=sys.stderr)
    print("Please ensure dreamscape_generator is installed or PYTHONPATH is set correctly.", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(level=project_config.LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DreamscapeCLI")

# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(description="Add a new episode to the Dreamscape chronicle.")

    # Input source groups (mutually exclusive)
    narrative_group = parser.add_mutually_exclusive_group(required=True)
    narrative_group.add_argument("--narrative-file", help="Path to the file containing the narrative text.")
    narrative_group.add_argument("--narrative-stdin", action="store_true", help="Read narrative text from standard input.")

    update_group = parser.add_mutually_exclusive_group(required=True)
    update_group.add_argument("--update-file", help="Path to the JSON file containing the MEMORY_UPDATE block.")
    update_group.add_argument("--update-stdin", action="store_true", help="Read MEMORY_UPDATE JSON block from standard input.")

    # Optional arguments
    parser.add_argument("--title", help="Title for the episode (will be sanitized for filename).")
    parser.add_argument("--source", default="CLI Entry", help="Source description for the episode metadata (e.g., 'CursorAgent: Refactor').")
    parser.add_argument("--episode-dir", help=f"Override the default episode directory ({project_config.EPISODE_DIR}).")
    parser.add_argument("--memory-file", help=f"Override the default memory state file ({project_config.MEMORY_STATE_FILE}).")

    args = parser.parse_args()

    # --- Read Inputs ---
    narrative = ""
    update_data = None # This will hold the dictionary parsed from JSON

    try:
        if args.narrative_file:
            logger.info(f"Reading narrative from file: {args.narrative_file}")
            with open(args.narrative_file, 'r', encoding='utf-8') as f:
                narrative = f.read()
        elif args.narrative_stdin:
            logger.info("Reading narrative from stdin...")
            narrative = sys.stdin.read()
        narrative = narrative.strip()
        if not narrative:
            logger.error("Narrative input is empty. Aborting.")
            sys.exit(1)

        json_input_str = ""
        if args.update_file:
            logger.info(f"Reading memory update from file: {args.update_file}")
            with open(args.update_file, 'r', encoding='utf-8') as f:
                json_input_str = f.read()
        elif args.update_stdin:
            logger.info("Reading memory update from stdin...")
            json_input_str = sys.stdin.read() # Note: This assumes narrative was already read if both use stdin

        json_input_str = json_input_str.strip()
        if not json_input_str:
             logger.error("Memory update JSON input is empty. Aborting.")
             sys.exit(1)

        # Parse the JSON *after* reading both inputs if stdin is used for both
        update_data = json.loads(json_input_str)
        if not isinstance(update_data, dict) or "MEMORY_UPDATE" not in update_data:
             logger.error("Invalid JSON structure. Expected a dictionary with a 'MEMORY_UPDATE' key. Aborting.")
             sys.exit(1)
        memory_update_block = update_data.get("MEMORY_UPDATE")
        if not isinstance(memory_update_block, dict):
             logger.error("'MEMORY_UPDATE' value is not a dictionary. Aborting.")
             sys.exit(1)

    except FileNotFoundError as e:
        logger.error(f"Input file not found: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON input: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading inputs: {e}", exc_info=True)
        sys.exit(1)

    # --- Process and Save ---
    memory_file_path = args.memory_file or project_config.MEMORY_STATE_FILE
    episode_dir = args.episode_dir or project_config.EPISODE_DIR

    try:
        # 1. Update Memory State
        logger.info(f"Initializing MemoryManager with state file: {memory_file_path}")
        memory_manager = MemoryManager(state_file=memory_file_path)
        logger.info(f"Applying memory update from source: {args.source}...")
        memory_updated = memory_manager.update_state(memory_update_block)
        if memory_updated:
            logger.info("Memory state updated successfully.")
        else:
            logger.info("Memory update resulted in no changes to the state.")

        # 2. Prepare Episode Data
        timestamp_utc = datetime.now(timezone.utc)
        episode_title = args.title or narrative.split('\n', 1)[0][:50] # Default title from first line
        sanitized_title = sanitize_filename(episode_title)
        # Add timestamp to filename to ensure uniqueness if title isn't unique enough
        filename_timestamp = timestamp_utc.strftime('%Y%m%d_%H%M%S')
        episode_filename = f"{filename_timestamp}_{sanitized_title}.json"

        metadata = {
            "title": episode_title,
            "source": args.source,
            "timestamp_utc": timestamp_utc.isoformat(),
            "memory_updated": memory_updated,
            "memory_version_after_update": memory_manager.get_full_state().get("version") # Get version after potential update
        }

        # 3. Save Episode File
        saved_path = save_episode_file(
            episode_dir=episode_dir,
            episode_filename=episode_filename,
            narrative=narrative,
            update_dict=memory_update_block, # Save the update block itself within the episode
            metadata=metadata
        )

        if saved_path:
            print(f"Successfully added episode: {saved_path}")
            sys.exit(0)
        else:
            print("Failed to save episode file.", file=sys.stderr)
            sys.exit(1)

    except FileNotFoundError:
         logger.error(f"Memory state file not found at: {memory_file_path}. Cannot initialize MemoryManager.")
         print(f"Error: Memory state file not found at '{memory_file_path}'. Please ensure it exists or specify the correct path.", file=sys.stderr)
         sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during processing: {e}", exc_info=True)
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 
