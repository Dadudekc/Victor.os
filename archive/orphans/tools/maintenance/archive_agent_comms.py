#!/usr/bin/env python3
"""
Utility to archive old agent communication (.msg) files.

Moves .msg files from runtime/agent_comms/ to runtime/agent_comms/archive/YYYY-MM-DD/
based on the date parsed from the filename (YYYYMMDD...). Files from the current
day are not archived.

MOVED FROM: src/dreamos/tools/dreamos_utils/ by Agent 5 (2025-04-28)
"""

import logging
from datetime import datetime
from pathlib import Path

from dreamos.utils import file_io

# --- Configuration ---
# Resolve paths relative to this script's new location
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[
    2
]  # Adjusted to reflect src/dreamos/tools/maintenance
COMMS_DIR = PROJECT_ROOT / "runtime" / "agent_comms"
ARCHIVE_BASE_DIR = COMMS_DIR / "archive"
FILENAME_DATE_FORMAT = "%Y%m%d"  # Expects YYYYMMDD at the start of the filename

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("CommsArchiver")


# --- Main Logic ---
def main():
    logger.info(f"Starting agent comms archival for directory: {COMMS_DIR}")
    today_str = datetime.now().strftime(FILENAME_DATE_FORMAT)
    archived_count = 0
    error_count = 0

    if not COMMS_DIR.is_dir():
        logger.error(f"Communications directory not found: {COMMS_DIR}. Exiting.")
        return

    # Ensure base archive directory exists
    if not file_io.ensure_directory(ARCHIVE_BASE_DIR):
        logger.error(
            f"Failed to create base archive directory {ARCHIVE_BASE_DIR} using file_io. Exiting."
        )
        return

    for item in COMMS_DIR.iterdir():
        # Process only .msg files directly in the comms dir
        # Skip the archive directory itself and mailbox directory
        if item.is_file() and item.suffix == ".msg" and item.parent == COMMS_DIR:
            filename = item.name
            logger.debug(f"Processing file: {filename}")

            # Extract date string (first 8 chars)
            if len(filename) < 8:
                logger.warning(f"Skipping file with too short name: {filename}")
                continue

            file_date_str = filename[:8]
            try:
                # Validate date format
                file_date = datetime.strptime(
                    file_date_str, FILENAME_DATE_FORMAT
                ).date()
                today_date = datetime.strptime(today_str, FILENAME_DATE_FORMAT).date()

                # Archive if file date is before today
                if file_date < today_date:
                    target_archive_dir = ARCHIVE_BASE_DIR / file_date.strftime(
                        "%Y-%m-%d"
                    )

                    logger.info(f"Archiving {filename} to {target_archive_dir}")

                    moved_path = file_io.move_file(
                        source_path=item,
                        destination_dir=target_archive_dir,
                    )

                    if moved_path:
                        archived_count += 1
                    else:
                        logger.error(
                            f"Failed to archive file {filename} to {target_archive_dir} using file_io."
                        )
                        error_count += 1
                else:
                    logger.debug(
                        f"File {filename} is from today or future. Skipping archive."
                    )

            except ValueError:
                logger.warning(
                    f"Skipping file with invalid date format prefix: {filename}"
                )
                continue
            except Exception as e:
                logger.error(
                    f"Unexpected error processing file {filename}: {e}", exc_info=True
                )
                error_count += 1
        elif item.name == ARCHIVE_BASE_DIR.name or item.name == "agent_mailboxes":
            logger.debug(f"Skipping known directory: {item.name}")
        elif item.is_file():
            logger.debug(f"Skipping non-.msg file: {item.name}")

    logger.info(
        f"Agent comms archival finished. Total Archived: {archived_count} file(s). Errors: {error_count}."  # noqa: E501
    )


if __name__ == "__main__":
    main()
