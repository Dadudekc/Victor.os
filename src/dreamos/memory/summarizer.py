# TODO: [Refactor/Deprecate] This module provides placeholder summarization logic.
# It replaces old entries with a simple marker, not actual LLM summarization.
# Real summarization logic is likely in summarization_utils.py.
# Investigate merging relevant parts (like safe file rewrite logic) into
# summarization_utils.py and deleting this file, or renaming it to reflect
# its placeholder/archiving nature if kept separate.

import json
import logging
import os
import shutil  # Added for backup
import tempfile  # Added for safe writing
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

DEFAULT_KEEP_RECENT_N = 50
DEFAULT_MAX_AGE_DAYS = 7
DEFAULT_CREATE_BACKUP = True


def _generate_placeholder_summary(chunk: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generates a placeholder summary entry for a chunk of memory entries."""
    if not chunk:
        return None

    # Attempt to find start and end timestamps
    start_time = chunk[0].get("timestamp", "Unknown")
    end_time = chunk[-1].get("timestamp", "Unknown")
    entry_count = len(chunk)

    summary_content = (
        f"[Summary of {entry_count} entries from {start_time} to {end_time}]"
    )

    return {
        "type": "summary_chunk",
        "timestamp": end_time,  # Use end time for sorting purposes
        "start_time": start_time,
        "end_time": end_time,
        "entry_count": entry_count,
        "content": summary_content,
        "summarized_at": datetime.now(timezone.utc).isoformat(),
    }


def summarize_memory_file(
    file_path: str,
    keep_recent_n: int = DEFAULT_KEEP_RECENT_N,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    create_backup: bool = DEFAULT_CREATE_BACKUP,
) -> bool:
    """
    Summarizes old entries in an agent's JSON memory file safely.

    Reads a JSON file (expected to be a list of dicts), identifies entries
    older than max_age_days, keeps the keep_recent_n most recent entries raw,
    and replaces the rest with placeholder summary chunks.

    Args:
        file_path: Path to the JSON memory file.
        keep_recent_n: Number of most recent entries to keep raw.
        max_age_days: Entries older than this many days are candidates for summarization.
        create_backup: If True, creates a backup (.bak) of the original file.

    Returns:
        True if summarization was performed and file rewritten, False otherwise.

    Uses atomic write (write to temp file, then os.replace) for safety.
    """
    if not os.path.exists(file_path):
        logger.error(f"Memory file not found: {file_path}")
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            memory_entries: List[Dict[str, Any]] = json.load(f)
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from memory file: {file_path}")
        return False
    except Exception as e:
        logger.error(f"Error reading memory file {file_path}: {e}")
        return False

    if not isinstance(memory_entries, list):
        logger.error(
            f"Memory file format error: Expected a JSON list. Path: {file_path}"
        )
        return False

    if len(memory_entries) <= keep_recent_n:
        logger.info(
            f"Memory file {file_path} has {len(memory_entries)} entries, less than or equal to keep_recent_n ({keep_recent_n}). No summarization needed."
        )
        return False

    # --- Identify entries to summarize ---
    now = datetime.now(timezone.utc)
    age_threshold = now - timedelta(days=max_age_days)

    entries_to_process = []
    summarizable_entries = []
    raw_recent_entries = []

    try:
        parsed_entries = []
        for i, entry in enumerate(memory_entries):
            ts_str = entry.get("timestamp")
            if isinstance(ts_str, str):
                try:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    parsed_entries.append((dt, entry))
                except ValueError:
                    logger.warning(
                        f"Could not parse timestamp in entry {i} of {file_path}: {ts_str}"
                    )
                    parsed_entries.append(
                        (datetime.max.replace(tzinfo=timezone.utc), entry)
                    )
            else:
                logger.warning(f"Entry {i} in {file_path} missing timestamp.")
                parsed_entries.append(
                    (datetime.min.replace(tzinfo=timezone.utc), entry)
                )

        parsed_entries.sort(key=lambda x: x[0])
        entries_to_process = [entry for dt, entry in parsed_entries]

    except Exception as e:
        logger.error(
            f"Error processing or sorting entries by timestamp in {file_path}: {e}. Aborting summarization."
        )
        return False

    raw_recent_entries = entries_to_process[-keep_recent_n:]
    potentially_summarizable = entries_to_process[:-keep_recent_n]

    entries_kept_raw_not_recent = []
    for entry in potentially_summarizable:
        ts_str = entry.get("timestamp")
        entry_is_old = True
        if isinstance(ts_str, str):
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt >= age_threshold:
                    entry_is_old = False
            except ValueError:
                pass

        if entry_is_old:
            if entry.get("type") != "summary_chunk":
                summarizable_entries.append(entry)
        else:
            entries_kept_raw_not_recent.append(entry)

    if not summarizable_entries:
        logger.info(
            f"No entries older than {max_age_days} days found for summarization in {file_path}."
        )
        return False

    logger.info(
        f"Found {len(summarizable_entries)} entries eligible for summarization in {file_path}."
    )

    # --- Create summary entry ---
    summary_entry = _generate_placeholder_summary(summarizable_entries)

    # --- Combine and rewrite ---
    new_memory_entries = []
    if summary_entry:
        new_memory_entries.append(summary_entry)
    new_memory_entries.extend(entries_kept_raw_not_recent)
    new_memory_entries.extend(raw_recent_entries)

    temp_file = None
    try:
        if create_backup:
            backup_path = file_path + ".bak"
            try:
                shutil.copy2(file_path, backup_path)
                logger.info(f"Created backup: {backup_path}")
            except Exception as backup_err:
                logger.error(f"Failed to create backup for {file_path}: {backup_err}")

        file_dir = os.path.dirname(file_path)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False, dir=file_dir, suffix=".tmp"
        ) as tf:
            temp_file = tf.name
            json.dump(new_memory_entries, tf, indent=2)

        os.replace(temp_file, file_path)
        temp_file = None

        logger.info(
            f"Successfully summarized and safely rewrote memory file: {file_path}. New entry count: {len(new_memory_entries)}."
        )
        return True

    except Exception as e:
        logger.error(f"Error during safe write for {file_path}: {e}")
        return False
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                logger.info(f"Cleaned up temporary file: {temp_file}")
            except OSError as cleanup_err:
                logger.error(
                    f"Error cleaning up temporary file {temp_file}: {cleanup_err}"
                )
