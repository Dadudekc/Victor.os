# Async File Locking Utility (`src/dreamos/core/utils/file_locking.py`)

This module provides a robust, asynchronous context manager for file-based
locking, ensuring exclusive access to resources across potentially multiple
asynchronous tasks or processes.

## Purpose

When multiple parts of the system need to read/write to the same file (e.g.,
task lists, agent memory segments), it's crucial to prevent race conditions and
data corruption. This utility uses the `filelock` library to create `.lock`
files, guaranteeing that only one holder can operate on the target resource at a
time.

## Core Component

### `async with FileLock(lock_file_path: Path | str, timeout: int = 60)`

This is an asynchronous context manager.

- **Args:**
  - `lock_file_path` (Path | str): The _base_ path for the lock. The actual lock
    file created will have `.lock` appended (e.g., providing
    `runtime/tasks.json` results in a lock file `runtime/tasks.json.lock`).
  - `timeout` (int): The maximum time in seconds to wait to acquire the lock
    before raising an error. Defaults to 60 seconds.
- **Behavior:**
  - Ensures the directory for the `.lock` file exists.
  - Attempts to acquire the file lock using `filelock.FileLock`.
    - Uses `asyncio.to_thread` to run the blocking `filelock` operations without
      blocking the main asyncio event loop.
  - If successful, yields control, allowing the code within the `async with`
    block to execute with exclusive access.
  - If the timeout is reached before acquiring the lock, raises
    `LockAcquisitionError`.
  - If any other error occurs during acquisition (e.g., OS error, permissions),
    raises `LockAcquisitionError` or `LockDirectoryError`.
  - **Atomically releases the lock and removes the `.lock` file** when exiting
    the `async with` block (either normally or due to an exception).
- **Exceptions:**
  - `LockDirectoryError`: If the directory for the `.lock` file cannot be
    created/accessed.
  - `LockAcquisitionError`: If the lock cannot be acquired within the timeout or
    due to other errors during acquisition.

## Usage Example

```python
import asyncio
from pathlib import Path
from dreamos.core.utils.file_locking import FileLock, LockAcquisitionError

async def safe_write_to_file(filepath: Path, data: str):
    try:
        # The lock file will be filepath.lock
        async with FileLock(filepath, timeout=10):
            print(f"Acquired lock for {filepath}")
            # --- Critical section ---
            # Perform file read/write operations safely here
            current_content = ""
            if filepath.exists():
                current_content = filepath.read_text()
            new_content = current_content + data
            filepath.write_text(new_content)
            print(f"Safely wrote to {filepath}")
            # --- End critical section ---
        # Lock is automatically released here
        print(f"Lock released for {filepath}")

    except LockAcquisitionError as e:
        print(f"Error: Could not acquire lock for {filepath}: {e}")
    except Exception as e:
        print(f"An error occurred during file operation: {e}")

# Example call
# asyncio.run(safe_write_to_file(Path("runtime/shared_resource.txt"), "New data\n"))
```

## Notes

- This lock is primarily designed for coordinating tasks _within_ the Dream.OS
  application (different agents, services running async).
- While `filelock` _can_ provide inter-process locking on compatible
  filesystems, rely on this primarily for intra-application coordination unless
  inter-process safety is explicitly tested and confirmed for your environment.
- The timeout should be set appropriately based on expected file operation
  times.
