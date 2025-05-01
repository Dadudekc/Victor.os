import asyncio
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

# import filelock # F401 unused
from filelock import FileLock as ExternalFileLock
from filelock import Timeout

from dreamos.core.errors import DreamOSError

logger = logging.getLogger(__name__)

LOCK_TIMEOUT_SECONDS = 60


class LockAcquisitionError(DreamOSError):
    """Raised when a file lock cannot be acquired within the specified timeout.

    This typically occurs if another process or thread holds the lock for too
    long. The original `filelock.Timeout` exception is chained for context.
    """

    pass


class LockDirectoryError(DreamOSError):
    """Raised when the directory for the lock file cannot be created or accessed.

    This usually indicates a filesystem permission issue or an invalid base
    path. The original `OSError` is chained for context.
    """

    pass


@asynccontextmanager
async def FileLock(
    lock_file_path: Path | str, timeout: int = LOCK_TIMEOUT_SECONDS
) -> AsyncGenerator[None, None]:
    """
    Provides an async context manager for robust, non-blocking file locking.

    Wraps the synchronous `filelock` library, running its blocking `acquire`
    and `release` operations in a separate thread using `asyncio.to_thread`
    to avoid blocking the main asyncio event loop.

    Ensures exclusive access to a resource represented by `lock_file_path`
    across different asyncio tasks and potentially across different processes
    (if running on a shared filesystem that supports POSIX file locking).

    Creates a `.lock` file sibling to the target resource path.
    Handles creation of parent directories and cleanup of the `.lock` file on exit.

    Usage:
        ```python
        try:
            async with FileLock("/path/to/my_resource.dat"):
                # Critical section: Only one task/process enters here.
                # Perform operations on "/path/to/my_resource.dat"
                pass
        except LockAcquisitionError as e:
            logger.error(f"Could not acquire lock: {e}")
        except LockDirectoryError as e:
            logger.error(f"Lock directory issue: {e}")
        ```

    Args:
        lock_file_path: Base path for the lock. The actual lock file will have
            a `.lock` suffix (e.g., `/path/to/resource.dat.lock`).
            Can be a string or a Path object.
        timeout: Maximum time in seconds to wait for lock acquisition.
            Defaults to `LOCK_TIMEOUT_SECONDS` (60).

    Yields:
        None: When the lock has been successfully acquired.

    Raises:
        LockDirectoryError: If the parent directory for the lock file cannot be
            created/accessed (e.g., permission denied).
        LockAcquisitionError: If lock acquisition times out or fails unexpectedly.
            The original exception is chained.
    """
    lock_path = Path(f"{str(lock_file_path)}.lock")

    # Ensure the directory for the lock file exists
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create directory for lock file {lock_path}: {e}")
        raise LockDirectoryError(
            f"Failed to create/access parent directory for lock file {lock_path}"
        ) from e

    _lock = ExternalFileLock(str(lock_path), timeout=timeout)
    acquired = False
    try:
        logger.debug(f"Attempting to acquire lock: {lock_path} (timeout={timeout}s)")
        # Use asyncio.to_thread for the blocking filelock operation
        await asyncio.to_thread(_lock.acquire)
        acquired = True
        logger.debug(f"Acquired lock: {lock_path}")
        yield  # Enter the critical section
    except Timeout as e:
        logger.error(f"Timeout acquiring lock after {timeout} seconds: {lock_path}")
        raise LockAcquisitionError(
            f"Could not acquire lock on {lock_path} within {timeout} seconds."
        ) from e
    except Exception as e:
        logger.error(
            f"An unexpected error occurred acquiring lock {lock_path}: {e}",
            exc_info=True,
        )
        raise LockAcquisitionError(
            f"Unexpected error acquiring lock {lock_path}: {type(e).__name__}"
        ) from e
    finally:
        if acquired:
            try:
                logger.debug(f"Releasing lock: {lock_path}")
                await asyncio.to_thread(_lock.release)
                logger.debug(f"Released lock: {lock_path}")
                # Clean up the lock file after release
                try:
                    # Use missing_ok=True if Python 3.8+
                    if Path(lock_path).exists():  # Check existence before removing
                        os.remove(lock_path)
                        logger.debug(f"Removed lock file: {lock_path}")
                except OSError as e:
                    # Log if removal fails, but don't raise; lock is released.
                    logger.warning(f"Could not remove lock file {lock_path}: {e}")
            except Exception as e:
                # This shouldn't typically happen if acquire succeeded.
                logger.error(f"Error releasing lock {lock_path}: {e}", exc_info=True)


# # Example Usage / Test Block - COMMENTED OUT
# # Should be moved to a dedicated test file under tests/ ideally.
# async def example_usage(file_path: str, worker_id: int):
#     """Demonstrates using the async FileLock."""
#     logger.info(f"Worker {worker_id}: Attempting to access {file_path}")
#     try:
#         async with FileLock(file_path, timeout=5):
#             logger.info(f"Worker {worker_id}: Acquired lock for {file_path}")
#             # Simulate work that requires exclusive access
#             await asyncio.sleep(1)
#             logger.info(f"Worker {worker_id}: Releasing lock for {file_path}")
#     except LockAcquisitionError as e:
#         logger.error(f"Worker {worker_id}: Failed to acquire lock - {e}")
#     except FileNotFoundError as e:
#         logger.error(f"Worker {worker_id}: Error with lock file path - {e}")
#
#
# async def main():
#     """Runs a simple concurrency test."""
#     # Use a temporary directory for test files
#     with tempfile.TemporaryDirectory() as temp_dir:
#         test_file_path = Path(temp_dir) / "test_shared_resource.txt"
#         logger.info(f"Using temporary file: {test_file_path}")
#
#         # Ensure the file exists for the test
#         test_file_path.touch()
#
#         tasks = [example_usage(str(test_file_path), i) for i in range(3)]
#         await asyncio.gather(*tasks)
#
#         # No explicit cleanup needed for file/lock in temp_dir,
#         # it's handled by TemporaryDirectory context manager
#         logger.info(
#             f"Temp directory {temp_dir} and contents will be cleaned up."
#         )
#
#
# if __name__ == "__main__":
#     # Basic configuration for logger if running standalone
#     logging.basicConfig(level=logging.DEBUG,
#                         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#
#     asyncio.run(main())
# # End of commented out block
