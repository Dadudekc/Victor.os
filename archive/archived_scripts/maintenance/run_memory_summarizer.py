#!/usr/bin/env python3
"""
Script to run the prototype memory summarization on a specified JSON file.

MOVED FROM: src/dreamos/tools/scripts/ by Agent 5 (2025-04-28)
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path to allow importing dreamos modules
# Assumes script is in PROJECT_ROOT/scripts/maintenance
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure the module path is correct for importing after moving the script
try:
    from src.dreamos.memory.summarization_utils import (
        DEFAULT_KEEP_RECENT_N,
        DEFAULT_MAX_AGE_DAYS,
        summarize_memory_file,
    )
except ImportError:
    logging.error(
        "Failed to import summarization tools. Ensure PYTHONPATH is set or script is run from project root."  # noqa: E501
    )
    # Fallback defaults if import fails, though script will likely fail later
    DEFAULT_KEEP_RECENT_N = 100
    DEFAULT_MAX_AGE_DAYS = 7

    def summarize_memory_file(*args, **kwargs):
        logging.error(
            "summarize_memory_file function not available due to import error."
        )
        return False


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run prototype memory summarization on a JSON file."
    )
    parser.add_argument(
        "file_path", help="Path to the agent memory JSON file to summarize."
    )
    parser.add_argument(
        "--keep-recent",
        type=int,
        default=DEFAULT_KEEP_RECENT_N,
        help=f"Number of recent entries to keep raw (default: {DEFAULT_KEEP_RECENT_N})",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=DEFAULT_MAX_AGE_DAYS,
        help=f"Summarize entries older than this many days (default: {DEFAULT_MAX_AGE_DAYS})",  # noqa: E501
    )

    args = parser.parse_args()

    target_file = Path(args.file_path)
    if not target_file.is_absolute():
        target_file = (
            PROJECT_ROOT / target_file
        )  # Assume relative to project root if not absolute

    if not target_file.exists():
        logging.error(f"Target memory file not found: {target_file}")
        sys.exit(1)

    logging.info(f"Starting memory summarization for: {target_file}")
    logging.info(f"Keeping recent entries: {args.keep_recent}")
    logging.info(f"Max age for summarization: {args.max_age_days} days")
    logging.warning("--- THIS IS A PROTOTYPE - IT WILL OVERWRITE THE FILE --- ")

    try:
        success = summarize_memory_file(
            file_path=target_file,
            keep_recent_n=args.keep_recent,
            max_age_days=args.max_age_days,
        )

        if success:
            logging.info("Memory summarization completed successfully.")
        else:
            logging.error("Memory summarization failed or was not needed.")
            sys.exit(1)

    except Exception as e:
        logging.error(
            f"An unexpected error occurred during summarization: {e}", exc_info=True
        )
        sys.exit(1)

    sys.exit(0)
