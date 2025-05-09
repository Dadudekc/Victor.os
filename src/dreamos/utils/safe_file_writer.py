\"\"\"Provides a function for safe, atomic file writing.\"\"\"

import logging
import os
import uuid
from pathlib import Path

# Attempt to import filelock, assuming it's available as used elsewhere (e.g., PBM)
try:
    import filelock

    FILELOCK_AVAILABLE = True
except ImportError:
    filelock = None
    FILELOCK_AVAILABLE = False
    logging.warning(
        \"safe_file_writer: filelock library not found. \"
        \"File writing will not be fully concurrency-safe.\"
    )

logger = logging.getLogger(__name__)


class SafeWriteError(IOError):
    \"\"\"Custom exception raised for errors during the safe file writing process.

    This includes errors related to:
    - Invalid input parameters (path, content type).
    - Failure to acquire the file lock within the timeout period.
    - IOErrors during temporary file writing or final file replacement.
    - Unexpected exceptions during the write/rename process.
    \"\"\"

    pass


def safe_write_file(
    target_file: str | Path, content: str, lock_timeout: int = 10
) -> None:
    \"\"\"Writes string content to a target file atomically and with file locking.

    Ensures the target file is only replaced with new content upon success.
    Uses a temporary file and atomic `os.replace`.

    If `filelock` is available, acquires an exclusive lock (`.lock` file)
    before writing to prevent race conditions with other processes/agents
    using compatible locking.

    Steps:
    1. Validate input path and content type.
    2. Create parent directories if they don't exist.
    3. (If filelock available) Acquire exclusive lock (`.lock` file).
    4. Write content to a uniquely named temporary file in target directory.
    5. Atomically replace the original target file with the temporary file.
    6. Clean up the temporary file if the replacement fails.
    7. Release the lock (if acquired).

    Args:
        target_file: Final path of the file (string or Path object).
        content: The string content to write.
        lock_timeout: Max seconds to wait for file lock (default: 10).

    Raises:
        SafeWriteError: If any step fails (lock timeout, IO error,
            validation error, unexpected error). Original exception chained.
        TypeError: If `content` is not a string.
        ValueError: If `target_file` path resolution fails.
    \"\"\"
    if not isinstance(content, str):
        raise TypeError(\"Content must be a string.\")

    try:
        target_path = Path(target_file).resolve()
        # Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(f\"Invalid target_file path: {target_file}. Error: {e}\") from e

    lock_path = target_path.with_suffix(target_path.suffix + \".lock\")
    lock = None
    temp_file_path = None
    lock_acquired = False

    if FILELOCK_AVAILABLE and filelock:
        lock = filelock.FileLock(lock_path, timeout=lock_timeout)
    else:
        # No locking possible
        logger.warning(
            f\"Proceeding without file lock for {target_path} \"
            f\"due to missing library.\"
        )
        pass  # Continue without lock object

    try:
        # Acquire lock if possible
        if lock:
            logger.debug(f\"Acquiring lock for {target_path}...\")
            lock.acquire()
            lock_acquired = True
            logger.debug(f\"Lock acquired for {target_path}.\")

        # Create temporary file in the same directory
        temp_file_path = target_path.with_suffix(f\".tmp_{uuid.uuid4().hex}\")
        logger.debug(f\"Writing content to temporary file: {temp_file_path}\")

        # Write content to temporary file
        with open(temp_file_path, \"w\", encoding=\"utf-8\") as f_temp:
            f_temp.write(content)

        # Atomically replace the target file with the temporary file
        logger.debug(f\"Atomically replacing {target_path} with {temp_file_path}\")
        os.replace(temp_file_path, target_path)
        logger.info(f\"Successfully wrote content to {target_path}\")
        temp_file_path = None  # Indicate successful rename

    except filelock.Timeout as e:
        logger.error(f\"Timeout ({lock_timeout}s) acquiring lock for {target_path}.\")
        raise SafeWriteError(f\"Timeout acquiring lock for {target_path}\") from e
    except IOError as e:
        logger.error(
            f\"IOError during safe write to {target_path} \"
            f\"(temp: {temp_file_path}): {e}\"
        )
        raise SafeWriteError(f\"IOError during safe write to {target_path}\") from e
    except Exception as e:
        logger.error(
            f\"Unexpected error during safe write to {target_path} \"
            f\"(temp: {temp_file_path}): {e}\",
            exc_info=True,
        )
        raise SafeWriteError(
            f\"Unexpected error during safe write to {target_path}\"
        ) from e
    finally:
        # Release lock if acquired
        if lock_acquired and lock and lock.is_locked:
            try:
                lock.release()
                logger.debug(f\"Lock released for {target_path}.\")
            except Exception as e:
                # Log error but don\'t prevent cleanup
                logger.error(
                    f\"Failed to release lock for {target_path}: {e}\", exc_info=True
                )

        # Cleanup temp file if it still exists (i.e., rename failed)
        if temp_file_path and temp_file_path.exists():
            logger.warning(f\"Attempting to clean up temporary file: {temp_file_path}\")
            try:
                temp_file_path.unlink()
            except OSError as unlink_e:
                logger.error(
                    f\"Failed to remove temporary file {temp_file_path}: {unlink_e}\"
                ) 