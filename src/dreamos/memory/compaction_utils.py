# src/dreamos/memory/compaction_utils.py
import asyncio
import json
import logging
import os
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dreamos.core.errors import MemoryError as CoreMemoryError

logger = logging.getLogger(__name__)


# EDIT START: Change inheritance to CoreMemoryError
class CompactionError(CoreMemoryError):
    """Exception raised for errors during memory compaction."""

    pass


# EDIT END


def compact_segment_data(
    data: List[Dict[str, Any]], policy: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Applies a compaction policy to filter a list of memory segment entries.

    Currently supports:
    - 'time_based': Removes entries older than `max_age_days`.
    - 'keep_n': Keeps only the `keep_n` most recent entries.

    Assumes newer entries are appended later in the list for 'keep_n'.
    Entries with missing or unparseable timestamps are kept by default
    for 'time_based' compaction.

    Args:
        data: A list of dictionaries, where each dict is a memory entry.
              Must contain a parseable ISO 8601 'timestamp' key for time_based policy.
        policy: A dictionary defining the compaction policy.
                Required keys:
                - 'type': 'time_based' | 'keep_n'
                Optional keys:
                - 'max_age_days' (int, default 30): Used if type is 'time_based'.
                - 'keep_n' (int, default 500): Used if type is 'keep_n'.

    Returns:
        A new list containing the filtered (compacted) memory entries.

    Raises:
        ValueError/TypeError: Potentially during timestamp parsing if format is unexpected,
                              though these are currently caught and logged as warnings.
    """  # noqa: E501
    policy_type = policy.get("type", "time_based")
    logger.debug(f"Applying compaction policy '{policy_type}'...")

    if policy_type == "time_based":
        max_age_days = policy.get("max_age_days", 30)
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        compacted_data = []
        dropped_count = 0
        for entry in data:
            entry_ts_str = entry.get("timestamp")
            if entry_ts_str:
                try:
                    # Assuming ISO format timestamps, potentially with timezone
                    entry_ts = datetime.fromisoformat(
                        entry_ts_str.replace("Z", "+00:00")
                    )
                    # Make naive UTC for comparison if it's timezone-aware
                    if entry_ts.tzinfo:
                        entry_ts = entry_ts.astimezone(timezone.utc).replace(
                            tzinfo=None
                        )

                    if entry_ts >= cutoff_date:
                        compacted_data.append(entry)
                    else:
                        dropped_count += 1
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Could not parse timestamp '{entry_ts_str}' for compaction: {e}. Keeping entry."  # noqa: E501
                    )
                    compacted_data.append(entry)  # Keep if timestamp is bad
            else:
                logger.warning(
                    f"Entry missing 'timestamp' for time-based compaction. Keeping entry: {str(entry)[:100]}..."  # noqa: E501
                )
                compacted_data.append(entry)  # Keep if no timestamp
        logger.info(
            f"Time-based compaction: Kept {len(compacted_data)}, Dropped {dropped_count} (older than {max_age_days} days)"  # noqa: E501
        )
        return compacted_data

    elif policy_type == "keep_n":
        keep_n = policy.get("keep_n", 500)
        # Assumes newer entries are appended; keeps the last N
        if len(data) > keep_n:
            compacted_data = data[-keep_n:]
            dropped_count = len(data) - keep_n
            logger.info(
                f"Keep-N compaction: Kept {len(compacted_data)}, Dropped {dropped_count} (limit {keep_n})"  # noqa: E501
            )
            return compacted_data
        else:
            logger.info(
                f"Keep-N compaction: No change needed (Count {len(data)} <= Limit {keep_n})"  # noqa: E501
            )
            return data  # No change needed

    else:
        logger.warning(
            f"Unsupported compaction policy type: {policy_type}. No compaction applied."
        )
        return data


async def _rewrite_memory_safely(
    file_path: Path, data: List[Dict[str, Any]], is_compressed: bool
) -> bool:
    """Atomically writes data to a file using a temporary file and os.replace.

    Handles JSON serialization, including datetime objects, and optional
    zlib compression based on the `is_compressed` flag.

    Args:
        file_path: The target Path object for the final file.
        data: The list of dictionary entries to serialize and write.
        is_compressed: If True, applies zlib compression to the UTF-8 encoded JSON data.

    Returns:
        True if the write and atomic replacement were successful, False otherwise.
        Errors during write or replace are logged.
    """
    temp_path = file_path.with_suffix(file_path.suffix + f".{os.getpid()}.tmp")

    def _sync_rewrite():
        # Prepare data for JSON serialization (handle datetimes)
        def dt_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(
                f"Object of type {type(obj).__name__} is not JSON serializable"
            )

        json_data = json.dumps(data, indent=2, default=dt_serializer)

        if is_compressed:
            encoded_data = json_data.encode("utf-8")
            compressed_data = zlib.compress(encoded_data)
            with open(temp_path, "wb") as f:  # Write bytes
                f.write(compressed_data)
        else:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(json_data)

        os.replace(temp_path, file_path)
        # Removed temp_path.exists() check before os.remove as os.replace handles it.
        # The finally block will catch if temp_path still exists due to an error before os.replace.

    try:
        await asyncio.to_thread(_sync_rewrite)
        logger.debug(f"Safely rewrote memory file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to rewrite memory file {file_path}: {e}", exc_info=True)
        # Clean up temp file if save failed
        if await asyncio.to_thread(temp_path.exists):  # Check existence async
            try:
                await asyncio.to_thread(os.remove, temp_path)  # Remove async
            except OSError:
                logger.error(f"Failed to remove temporary save file: {temp_path}")
        return False
    # The finally block from the original was a bit confusing with os.replace.
    # If _sync_rewrite fails before os.replace, temp_path might exist.
    # If os.replace succeeds, temp_path is gone.
    # The except block above handles cleanup on failure.


async def compact_segment_file(file_path: Path, policy: Dict[str, Any]) -> bool:
    """Loads a memory segment file, applies compaction, and saves the result atomically.

    Reads a JSON segment file (plain or zlib compressed based on `.z` suffix),
    applies the specified compaction policy using `compact_segment_data`, and
    rewrites the file using `_rewrite_memory_safely` only if the data changed.

    Args:
        file_path: The Path object of the segment file to compact.
        policy: The compaction policy dictionary (passed to `compact_segment_data`).

    Returns:
        True if the process completed successfully (including cases where no
             compaction was needed). Currently returns via raising exceptions.

    Raises:
        CompactionError: If loading, parsing, processing (compact_segment_data),
                         or saving the file fails. Original exceptions (e.g.,
                         JSONDecodeError, IOError) may be chained.
        FileNotFoundError: If the input file does not exist.
    """
    logger.info(f"Starting compaction process for: {file_path}")

    exists = await asyncio.to_thread(file_path.exists)
    size = (await asyncio.to_thread(file_path.stat)).st_size if exists else 0

    if not exists or size == 0:
        logger.warning(f"Compaction skipped: File not found or empty - {file_path}")
        return True  # Nothing to compact

    is_compressed = file_path.suffix == ".z"
    original_data: Optional[List[Dict[str, Any]]] = None

    def _sync_read_and_parse():
        if is_compressed:
            with open(file_path, "rb") as f:
                compressed_data = f.read()
            json_str = zlib.decompress(compressed_data).decode("utf-8")
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                json_str = f.read()

        if not json_str.strip():
            logger.warning(
                f"Compaction skipped: File content is empty after potential decompression - {file_path}"  # noqa: E501
            )
            return None  # Special marker for empty content after read

        loaded_data = json.loads(json_str)
        if not isinstance(loaded_data, list):
            # EDIT START: Raise specific error
            # logger.error(f"Compaction failed: Expected a list in file {file_path}, found {type(loaded_data)}")  # noqa: E501
            # return False
            raise CompactionError(
                f"Expected a list in file {file_path}, found {type(loaded_data)}"
            )
            # EDIT END

    try:
        original_data = await asyncio.to_thread(_sync_read_and_parse)
        if original_data is None:  # Marker for empty content after read
            return True  # Treat as success

    except json.JSONDecodeError as e:
        # EDIT START: Raise specific error
        logger.error(
            f"Failed to parse segment file {file_path} for compaction: {e}",
            exc_info=True,
        )
        # return False
        raise CompactionError(f"Failed to parse JSON in {file_path}") from e
        # EDIT END
    except Exception as e:
        # EDIT START: Raise specific error
        logger.error(
            f"Failed to load segment file {file_path} for compaction: {e}",
            exc_info=True,
        )
        # return False
        raise CompactionError(f"Failed to load file {file_path}") from e
        # EDIT END

    # Check moved up for clarity (should be impossible if exceptions raised)
    # if original_data is None: return False

    try:
        # Apply compaction logic
        compacted_data = compact_segment_data(original_data, policy)

        # Save only if data changed
        if len(compacted_data) < len(original_data):
            logger.info(
                f"Data compacted for {file_path}. Original: {len(original_data)}, New: {len(compacted_data)}. Attempting rewrite."
            )
            # _rewrite_memory_safely is now async
            rewrite_success = await _rewrite_memory_safely(
                file_path, compacted_data, is_compressed
            )
            if not rewrite_success:
                # EDIT START: Raise specific error
                logger.error(f"Compaction failed during save for {file_path}")
                # return False
                raise CompactionError(f"Failed to rewrite compacted file {file_path}")
                # EDIT END
            return True
        else:
            logger.info(
                f"No data removed by compaction policy for {file_path}. No save needed."
            )
            return True
    except Exception as e:
        # Catch errors from compact_segment_data or other unexpected issues
        logger.error(
            f"Error during compaction processing for {file_path}: {e}", exc_info=True
        )
        raise CompactionError(
            f"Error during compaction data processing for {file_path}"
        ) from e

    # Check moved up for clarity (should be impossible if exceptions raised)
    # if original_data is None: return False

    try:
        # Apply compaction logic
        compacted_data = compact_segment_data(original_data, policy)

        # Save only if data changed
        if len(compacted_data) < len(original_data):
            logger.info(
                f"Data compacted for {file_path}. Original: {len(original_data)}, New: {len(compacted_data)}. Attempting rewrite."
            )
            # _rewrite_memory_safely is now async
            rewrite_success = await _rewrite_memory_safely(
                file_path, compacted_data, is_compressed
            )
            if not rewrite_success:
                # EDIT START: Raise specific error
                logger.error(f"Compaction failed during save for {file_path}")
                # return False
                raise CompactionError(f"Failed to rewrite compacted file {file_path}")
                # EDIT END
            return True
        else:
            logger.info(
                f"No data removed by compaction policy for {file_path}. No save needed."
            )
            return True
    except Exception as e:
        # Catch errors from compact_segment_data or other unexpected issues
        logger.error(
            f"Error during compaction processing for {file_path}: {e}", exc_info=True
        )
        raise CompactionError(
            f"Error during compaction data processing for {file_path}"
        ) from e
