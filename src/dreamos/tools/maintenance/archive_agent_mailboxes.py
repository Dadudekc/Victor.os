#!/usr/bin/env python3
"""
Utility to recursively archive old agent mailbox (.msg) files.

Moves .msg files found within subdirectories of runtime/agent_comms/agent_mailboxes/
(e.g., Agent1/, Agent2/) to a corresponding archive structure within that agent's
directory (e.g., Agent1/archive/YYYY-MM-DD/).

Files from the current day are not archived.

MOVED FROM: src/dreamos/tools/dreamos_utils/ by Agent 5 (2025-04-28)
"""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

# --- Configuration ---
# Resolve paths relative to this script's new location
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]  # Assumes scripts/maintenance structure
MAILBOXES_BASE_DIR = PROJECT_ROOT / "runtime" / "agent_comms" / "agent_mailboxes"
ARCHIVE_SUBDIR_NAME = "archive"  # Archive directory name within each agent mailbox
FILENAME_DATE_FORMAT = "%Y%m%d"  # Expects YYYYMMDD at the start of the filename

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MailboxArchiver")


# --- Main Logic ---
def archive_mailbox(agent_mailbox_dir: Path):
    """Archives old .msg files within a specific agent mailbox directory."""
    logger.info(f"Processing mailbox: {agent_mailbox_dir.name}")
    today_str = datetime.now().strftime(FILENAME_DATE_FORMAT)
    archived_count = 0
    error_count = 0
    agent_archive_base = agent_mailbox_dir / ARCHIVE_SUBDIR_NAME

    # Ensure agent-specific base archive directory exists
    try:
        agent_archive_base.mkdir(exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create archive directory in {agent_mailbox_dir}: {e}")
        return 0, 1  # Return 0 archived, 1 error for this mailbox

    # Iterate directly within the agent's mailbox dir (e.g., Agent5/)
    # Do not iterate recursively into 'inbox' etc. by default, assume messages are flat for now
    # or adjust logic if messages are deeper (e.g., Agent5/inbox/*.msg)
    for item in agent_mailbox_dir.iterdir():
        # Process only .msg files directly in the agent mailbox dir
        # And skip the archive directory itself
        if (
            item.is_file()
            and item.suffix == ".msg"
            and item.parent == agent_mailbox_dir
        ):
            filename = item.name
            logger.debug(f"Processing file: {filename}")

            # Extract date string (first 8 chars)
            if len(filename) < 8:
                logger.warning(f"Skipping file with too short name: {filename}")
                continue

            file_date_str = filename[:8]
            try:
                file_date = datetime.strptime(
                    file_date_str, FILENAME_DATE_FORMAT
                ).date()
                today_date = datetime.strptime(today_str, FILENAME_DATE_FORMAT).date()

                if file_date < today_date:
                    target_archive_dir = agent_archive_base / file_date.strftime(
                        "%Y-%m-%d"
                    )
                    target_archive_path = target_archive_dir / filename

                    logger.info(f"Archiving {filename} to {target_archive_dir}")
                    try:
                        target_archive_dir.mkdir(exist_ok=True)
                        shutil.move(str(item), str(target_archive_path))
                        archived_count += 1
                    except OSError as e:
                        logger.error(f"Failed to move {filename} to archive: {e}")
                        error_count += 1
                    except Exception as e:
                        logger.error(
                            f"Unexpected error moving file {filename}: {e}",
                            exc_info=True,
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

    logger.info(
        f"Finished processing mailbox {agent_mailbox_dir.name}. Archived: {archived_count}, Errors: {error_count}."
    )
    return archived_count, error_count


def main():
    logger.info(
        f"Starting agent mailbox archival for base directory: {MAILBOXES_BASE_DIR}"
    )
    total_archived = 0
    total_errors = 0

    if not MAILBOXES_BASE_DIR.is_dir():
        logger.error(
            f"Mailboxes base directory not found: {MAILBOXES_BASE_DIR}. Exiting."
        )
        return

    # Iterate through potential agent directories
    for agent_dir in MAILBOXES_BASE_DIR.iterdir():
        # Process only directories (representing agents), skip files at this level
        if agent_dir.is_dir() and agent_dir.name != ARCHIVE_SUBDIR_NAME:
            archived, errors = archive_mailbox(agent_dir)
            total_archived += archived
            total_errors += errors

    logger.info(
        f"Agent mailbox archival finished. Total Archived: {total_archived} file(s). Total Errors: {total_errors}."
    )


if __name__ == "__main__":
    main()
