# File lock manager for atomic JSON file operations

import os
import time
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

if os.name == 'nt':
    import msvcrt
else:
    import fcntl

class FileLock:
    """Context manager that provides exclusive file lock for a given file path."""
    def __init__(self, file_path, timeout=10.0, delay=0.05):
        self.file_path = Path(file_path)
        self.timeout = timeout
        self.delay = delay
        self.handle = None

    def acquire(self):
        start_time = time.time()
        # Ensure parent directories and file exist
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.touch(exist_ok=True)
        # Open file for reading and writing in binary mode
        self.handle = open(self.file_path, 'r+b')
        while True:
            try:
                if os.name == 'nt':
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (IOError, BlockingIOError):
                if (time.time() - start_time) >= self.timeout:
                    raise TimeoutError(f"Timeout acquiring lock for {self.file_path}")
                time.sleep(self.delay)

    def release(self):
        if self.handle:
            try:
                if os.name == 'nt':
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(self.handle, fcntl.LOCK_UN)
            except Exception as e:
                logger.warning(f"Error releasing lock for {self.file_path}: {e}")
            finally:
                self.handle.close()
                self.handle = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def read_json(path, timeout=10.0, delay=0.05):
    """Read JSON data from a file with an exclusive lock."""
    file_path = Path(path)
    with FileLock(file_path, timeout=timeout, delay=delay):
        if not file_path.exists():
            return None
        with file_path.open('r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON {file_path}: {e}")
                raise


def write_json(path, data, timeout=10.0, delay=0.05, indent=2):
    """Write JSON data to a file with an exclusive lock."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(file_path, timeout=timeout, delay=delay):
        with file_path.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent) 