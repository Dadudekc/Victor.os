"""
Resilient I/O Utilities

This module implements robust file and directory operations with retry logic,
fallback mechanisms, and comprehensive error reporting to address persistent
tool failures, particularly read_file and list_dir timeouts.

Author: Agent-3 (Loop Engineer)
Collaborator: Agent-2 (Infrastructure Engineer)
Date: 2025-05-18
"""

import os
import time
import json
import logging
import shutil
import tempfile
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Callable, TypeVar, Generic, Tuple
from contextlib import contextmanager
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dreamos.utils.resilient_io")

# Type variable for generic return types
T = TypeVar('T')

# Constants for retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds
DEFAULT_RETRY_BACKOFF = 2.0  # exponential backoff multiplier
DEFAULT_TIMEOUT = 10.0  # seconds
ERROR_LOG_DIR = "runtime/error_logs/io_errors"

# Ensure error log directory exists
os.makedirs(ERROR_LOG_DIR, exist_ok=True)

class IOError(Exception):
    """Base exception for resilient I/O operations."""
    pass

class FileReadError(IOError):
    """Exception raised when file reading fails."""
    pass

class FileWriteError(IOError):
    """Exception raised when file writing fails."""
    pass

class DirectoryOperationError(IOError):
    """Exception raised when directory operations fail."""
    pass

class TimeoutError(IOError):
    """Exception raised when an operation times out."""
    pass

class ErrorReport:
    """
    Class for generating, storing, and retrieving error reports.
    
    This provides a standardized way to log errors with rich context
    for later analysis and debugging.
    """
    
    def __init__(self, operation: str, path: str, exception: Exception, context: Dict[str, Any] = None):
        """
        Initialize an error report.
        
        Args:
            operation: The I/O operation that failed (e.g., "read_file", "list_dir")
            path: The file or directory path that was being accessed
            exception: The exception that was raised
            context: Additional context information
        """
        self.operation = operation
        self.path = path
        self.exception = exception
        self.exception_type = type(exception).__name__
        self.exception_msg = str(exception)
        self.timestamp = time.time()
        self.traceback = traceback.format_exc()
        self.context = context or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the error report to a dictionary."""
        return {
            "operation": self.operation,
            "path": self.path,
            "exception_type": self.exception_type,
            "exception_msg": self.exception_msg,
            "timestamp": self.timestamp,
            "traceback": self.traceback,
            "context": self.context
        }
        
    def save(self) -> str:
        """
        Save the error report to a file.
        
        Returns:
            Path to the saved error report file
        """
        # Create a unique filename based on timestamp and operation
        filename = f"{int(self.timestamp)}_{self.operation}_{self.exception_type}.json"
        filepath = os.path.join(ERROR_LOG_DIR, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            return filepath
        except Exception as e:
            logger.error(f"Failed to save error report: {e}")
            return ""
            
    @staticmethod
    def load(filepath: str) -> 'ErrorReport':
        """
        Load an error report from a file.
        
        Args:
            filepath: Path to the error report file
            
        Returns:
            The loaded ErrorReport instance
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            # Create a dummy exception since we can't recreate the original
            dummy_exception = Exception(data.get("exception_msg", "Unknown error"))
            
            report = ErrorReport(
                operation=data.get("operation", "unknown"),
                path=data.get("path", ""),
                exception=dummy_exception,
                context=data.get("context", {})
            )
            
            # Manual assignment for fields not in constructor
            report.exception_type = data.get("exception_type", "Exception")
            report.timestamp = data.get("timestamp", 0)
            report.traceback = data.get("traceback", "")
            
            return report
        except Exception as e:
            logger.error(f"Failed to load error report: {e}")
            raise

def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    backoff_factor: float = DEFAULT_RETRY_BACKOFF,
    exceptions_to_retry: Tuple[type] = (Exception,),
    timeout: Optional[float] = DEFAULT_TIMEOUT
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries
        retry_delay: Initial delay between retries (seconds)
        backoff_factor: Multiplier for increasing delay with each retry
        exceptions_to_retry: Tuple of exception types that should trigger retry
        timeout: Maximum time to wait for operation to complete (None for no timeout)
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            operation_name = func.__name__
            path = ""
            
            # Try to extract the path from args or kwargs for error reporting
            if len(args) > 0 and isinstance(args[0], (str, Path)):
                path = str(args[0])
            elif 'path' in kwargs:
                path = str(kwargs['path'])
            elif 'file_path' in kwargs:
                path = str(kwargs['file_path'])
            elif 'dir_path' in kwargs:
                path = str(kwargs['dir_path'])
            
            context = {
                "args": str(args),
                "kwargs": str(kwargs),
                "max_retries": max_retries,
                "retry_delay": retry_delay,
                "backoff_factor": backoff_factor
            }
            
            # Initialize variables for retry loop
            retry_count = 0
            current_delay = retry_delay
            start_time = time.time()
            
            while True:
                try:
                    # Check for timeout
                    if timeout is not None and time.time() - start_time > timeout:
                        error_context = {**context, "elapsed_time": time.time() - start_time}
                        error = TimeoutError(f"Operation {operation_name} timed out after {timeout} seconds")
                        report = ErrorReport(operation_name, path, error, error_context)
                        report_path = report.save()
                        logger.error(f"Timeout in {operation_name} for {path}. Error report: {report_path}")
                        raise error
                        
                    # Attempt operation
                    return func(*args, **kwargs)
                    
                except exceptions_to_retry as e:
                    retry_count += 1
                    
                    # If we've reached max retries, log and raise
                    if retry_count > max_retries:
                        error_context = {**context, "retry_count": retry_count}
                        report = ErrorReport(operation_name, path, e, error_context)
                        report_path = report.save()
                        logger.error(f"Max retries ({max_retries}) exceeded in {operation_name} for {path}. Error report: {report_path}")
                        raise
                        
                    # Log retry attempt
                    logger.warning(f"Retry {retry_count}/{max_retries} for {operation_name} on {path}: {e}")
                    
                    # Wait before retrying with exponential backoff
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
                    
        return wrapper
    return decorator

@with_retry()
def read_file(file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
    """
    Read a file with retry logic and error handling.
    
    Args:
        file_path: Path to the file to read
        encoding: File encoding
        
    Returns:
        Content of the file as a string
        
    Raises:
        FileReadError: If the file cannot be read after retries
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
            
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise FileReadError(f"Failed to read file {file_path}: {e}") from e

@with_retry()
def read_file_lines(file_path: Union[str, Path], offset: int = 0, limit: Optional[int] = None, encoding: str = 'utf-8') -> List[str]:
    """
    Read a specific range of lines from a file with retry logic.
    
    Args:
        file_path: Path to the file to read
        offset: Line offset (0-indexed)
        limit: Maximum number of lines to read (None for all lines)
        encoding: File encoding
        
    Returns:
        List of lines from the file
        
    Raises:
        FileReadError: If the file cannot be read after retries
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        with open(file_path, 'r', encoding=encoding) as f:
            if offset == 0 and limit is None:
                return f.readlines()
                
            # Skip to the offset
            for _ in range(offset):
                next(f, None)
                
            # Read the specified number of lines
            if limit is None:
                return list(f)
            else:
                return [next(f, None) for _ in range(limit)]
                
    except Exception as e:
        logger.error(f"Error reading lines from file {file_path}: {e}")
        raise FileReadError(f"Failed to read lines from file {file_path}: {e}") from e

@with_retry()
def read_json(file_path: Union[str, Path], encoding: str = 'utf-8') -> Dict[str, Any]:
    """
    Read a JSON file with retry logic.
    
    Args:
        file_path: Path to the JSON file
        encoding: File encoding
        
    Returns:
        Parsed JSON content as a dictionary
        
    Raises:
        FileReadError: If the file cannot be read or parsed after retries
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        with open(file_path, 'r', encoding=encoding) as f:
            return json.load(f)
            
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON file {file_path}: {e}")
        raise FileReadError(f"Failed to parse JSON file {file_path}: {e}") from e
    except Exception as e:
        logger.error(f"Error reading JSON file {file_path}: {e}")
        raise FileReadError(f"Failed to read JSON file {file_path}: {e}") from e

@with_retry()
def write_file(file_path: Union[str, Path], content: str, encoding: str = 'utf-8') -> bool:
    """
    Write content to a file with retry logic and atomic writing.
    
    Args:
        file_path: Path to the file to write
        content: Content to write to the file
        encoding: File encoding
        
    Returns:
        True if the file was written successfully
        
    Raises:
        FileWriteError: If the file cannot be written after retries
    """
    try:
        file_path = Path(file_path)
        
        # Create parent directories if they don't exist
        os.makedirs(file_path.parent, exist_ok=True)
        
        # Write to a temporary file first
        with tempfile.NamedTemporaryFile(mode='w', encoding=encoding, delete=False, dir=file_path.parent) as temp_file:
            temp_path = temp_file.name
            temp_file.write(content)
            
        # Atomic rename
        try:
            # On Windows, destination file must not exist for atomic rename
            if os.path.exists(file_path):
                os.unlink(file_path)
            os.rename(temp_path, file_path)
            return True
        except Exception as rename_error:
            # If rename fails, try a copy and delete approach
            try:
                shutil.copy2(temp_path, file_path)
                os.unlink(temp_path)
                return True
            except Exception as copy_error:
                logger.error(f"Fallback copy failed for {file_path}: {copy_error}")
                raise copy_error
                
    except Exception as e:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass
        logger.error(f"Error writing file {file_path}: {e}")
        raise FileWriteError(f"Failed to write file {file_path}: {e}") from e

@with_retry()
def write_json(file_path: Union[str, Path], data: Dict[str, Any], indent: int = 2, encoding: str = 'utf-8') -> bool:
    """
    Write JSON data to a file with retry logic and atomic writing.
    
    Args:
        file_path: Path to the file to write
        data: JSON-serializable data to write
        indent: Indentation level for pretty-printing
        encoding: File encoding
        
    Returns:
        True if the file was written successfully
        
    Raises:
        FileWriteError: If the file cannot be written after retries
    """
    try:
        content = json.dumps(data, indent=indent)
        return write_file(file_path, content, encoding)
    except Exception as e:
        logger.error(f"Error writing JSON to file {file_path}: {e}")
        raise FileWriteError(f"Failed to write JSON to file {file_path}: {e}") from e

@with_retry()
def list_dir(dir_path: Union[str, Path], pattern: Optional[str] = None) -> List[str]:
    """
    List directory contents with retry logic and pattern matching.
    
    Args:
        dir_path: Path to the directory to list
        pattern: Optional glob pattern to filter results
        
    Returns:
        List of directory entries, optionally filtered by pattern
        
    Raises:
        DirectoryOperationError: If the directory cannot be listed after retries
    """
    try:
        dir_path = Path(dir_path)
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")
            
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")
            
        # List directory contents
        if pattern is None:
            return os.listdir(dir_path)
        else:
            import glob
            # Use glob to handle pattern matching
            return [os.path.basename(p) for p in glob.glob(os.path.join(str(dir_path), pattern))]
            
    except Exception as e:
        logger.error(f"Error listing directory {dir_path}: {e}")
        raise DirectoryOperationError(f"Failed to list directory {dir_path}: {e}") from e

@with_retry()
def scan_dir(dir_path: Union[str, Path], recursive: bool = False, include_pattern: Optional[str] = None, 
           exclude_pattern: Optional[str] = None) -> List[str]:
    """
    Scan a directory recursively with retry logic and pattern filtering.
    
    Args:
        dir_path: Path to the directory to scan
        recursive: Whether to scan recursively
        include_pattern: Optional glob pattern for files to include
        exclude_pattern: Optional glob pattern for files to exclude
        
    Returns:
        List of file paths, optionally filtered by patterns
        
    Raises:
        DirectoryOperationError: If the directory cannot be scanned after retries
    """
    try:
        dir_path = Path(dir_path)
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")
            
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")
            
        import glob
        import fnmatch
        
        # Initialize results list
        results = []
        
        # Define the scan function based on recursion flag
        if recursive:
            # Use glob with recursive pattern
            pattern = "**/*" if include_pattern is None else f"**/{include_pattern}"
            all_files = glob.glob(os.path.join(str(dir_path), pattern), recursive=True)
        else:
            # Non-recursive scan
            pattern = "*" if include_pattern is None else include_pattern
            all_files = glob.glob(os.path.join(str(dir_path), pattern))
        
        # Filter by exclude pattern if provided
        if exclude_pattern is not None:
            results = [f for f in all_files if not fnmatch.fnmatch(os.path.basename(f), exclude_pattern)]
        else:
            results = all_files
            
        return results
        
    except Exception as e:
        logger.error(f"Error scanning directory {dir_path}: {e}")
        raise DirectoryOperationError(f"Failed to scan directory {dir_path}: {e}") from e

@with_retry()
def ensure_dir(dir_path: Union[str, Path]) -> bool:
    """
    Ensure a directory exists with retry logic.
    
    Args:
        dir_path: Path to the directory to ensure
        
    Returns:
        True if the directory exists or was created successfully
        
    Raises:
        DirectoryOperationError: If the directory cannot be created after retries
    """
    try:
        dir_path = Path(dir_path)
        os.makedirs(dir_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error ensuring directory {dir_path}: {e}")
        raise DirectoryOperationError(f"Failed to ensure directory {dir_path}: {e}") from e

@with_retry()
def copy_file(src_path: Union[str, Path], dst_path: Union[str, Path]) -> bool:
    """
    Copy a file with retry logic.
    
    Args:
        src_path: Source file path
        dst_path: Destination file path
        
    Returns:
        True if the file was copied successfully
        
    Raises:
        FileReadError: If the source file cannot be read
        FileWriteError: If the destination file cannot be written
    """
    try:
        src_path = Path(src_path)
        dst_path = Path(dst_path)
        
        if not src_path.exists():
            raise FileNotFoundError(f"Source file not found: {src_path}")
            
        # Create parent directories if they don't exist
        os.makedirs(dst_path.parent, exist_ok=True)
        
        shutil.copy2(src_path, dst_path)
        return True
    except Exception as e:
        logger.error(f"Error copying file from {src_path} to {dst_path}: {e}")
        if not Path(src_path).exists():
            raise FileReadError(f"Failed to copy file - source does not exist: {src_path}") from e
        else:
            raise FileWriteError(f"Failed to copy file to {dst_path}: {e}") from e

@with_retry()
def move_file(src_path: Union[str, Path], dst_path: Union[str, Path]) -> bool:
    """
    Move a file with retry logic.
    
    Args:
        src_path: Source file path
        dst_path: Destination file path
        
    Returns:
        True if the file was moved successfully
        
    Raises:
        FileReadError: If the source file cannot be read
        FileWriteError: If the destination file cannot be written
    """
    try:
        src_path = Path(src_path)
        dst_path = Path(dst_path)
        
        if not src_path.exists():
            raise FileNotFoundError(f"Source file not found: {src_path}")
            
        # Create parent directories if they don't exist
        os.makedirs(dst_path.parent, exist_ok=True)
        
        # Try atomic rename first
        try:
            # On Windows, destination file must not exist for atomic rename
            if os.path.exists(dst_path):
                os.unlink(dst_path)
            os.rename(src_path, dst_path)
            return True
        except OSError:
            # If rename fails, fall back to copy and delete
            shutil.copy2(src_path, dst_path)
            os.unlink(src_path)
            return True
            
    except Exception as e:
        logger.error(f"Error moving file from {src_path} to {dst_path}: {e}")
        if not Path(src_path).exists():
            raise FileReadError(f"Failed to move file - source does not exist: {src_path}") from e
        else:
            raise FileWriteError(f"Failed to move file to {dst_path}: {e}") from e

@with_retry()
def delete_file(file_path: Union[str, Path]) -> bool:
    """
    Delete a file with retry logic.
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        True if the file was deleted successfully or didn't exist
        
    Raises:
        FileWriteError: If the file cannot be deleted after retries
    """
    try:
        file_path = Path(file_path)
        
        if not file_path.exists():
            return True  # File doesn't exist, so deletion is "successful"
            
        os.unlink(file_path)
        return True
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        raise FileWriteError(f"Failed to delete file {file_path}: {e}") from e

@contextmanager
def file_lock(lock_file: Union[str, Path], timeout: float = 30.0, retry_delay: float = 0.1):
    """
    Context manager for file-based locking.
    
    This provides a simple file-based locking mechanism to prevent
    concurrent access to shared resources.
    
    Args:
        lock_file: Path to the lock file
        timeout: Maximum time to wait for the lock (seconds)
        retry_delay: Delay between lock acquisition attempts (seconds)
        
    Yields:
        None
        
    Raises:
        TimeoutError: If the lock cannot be acquired within the timeout
    """
    lock_file = Path(lock_file)
    
    # Create parent directories if they don't exist
    os.makedirs(lock_file.parent, exist_ok=True)
    
    start_time = time.time()
    
    # Attempt to acquire the lock
    while True:
        try:
            # Check if we've timed out
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timed out waiting for lock: {lock_file}")
                
            # Try to create the lock file exclusively
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            
            try:
                # Write a PID to the file for debugging
                os.write(fd, str(os.getpid()).encode())
                break  # Lock acquired successfully
            finally:
                os.close(fd)
                
        except FileExistsError:
            # Lock already exists, check if it's stale
            try:
                stat = os.stat(lock_file)
                if time.time() - stat.st_mtime > 300:  # 5 minutes
                    # Lock file is stale, attempt to remove it
                    logger.warning(f"Removing stale lock file: {lock_file}")
                    os.unlink(lock_file)
                    continue
            except FileNotFoundError:
                # Lock file was removed by another process, try again
                continue
                
            # Wait before retrying
            time.sleep(retry_delay)
            
    try:
        # Lock acquired, yield control
        yield
    finally:
        # Release the lock
        try:
            os.unlink(lock_file)
        except FileNotFoundError:
            # Lock file already removed, log a warning
            logger.warning(f"Lock file not found during release: {lock_file}")
        except Exception as e:
            # Log but don't raise, as this is in a finally block
            logger.error(f"Error releasing lock file {lock_file}: {e}")

def atomic_read_json(file_path: Union[str, Path], lock_file: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Read a JSON file atomically with locking.
    
    Args:
        file_path: Path to the JSON file
        lock_file: Path to the lock file (defaults to file_path + ".lock")
        
    Returns:
        Parsed JSON content as a dictionary
        
    Raises:
        FileReadError: If the file cannot be read or parsed
    """
    file_path = Path(file_path)
    if lock_file is None:
        lock_file = str(file_path) + ".lock"
        
    try:
        with file_lock(lock_file):
            return read_json(file_path)
    except Exception as e:
        logger.error(f"Error in atomic_read_json for {file_path}: {e}")
        raise FileReadError(f"Failed to read JSON file atomically {file_path}: {e}") from e

def atomic_write_json(file_path: Union[str, Path], data: Dict[str, Any], 
                    lock_file: Optional[Union[str, Path]] = None, 
                    indent: int = 2) -> bool:
    """
    Write JSON data to a file atomically with locking.
    
    Args:
        file_path: Path to the file to write
        data: JSON-serializable data to write
        lock_file: Path to the lock file (defaults to file_path + ".lock")
        indent: Indentation level for pretty-printing
        
    Returns:
        True if the file was written successfully
        
    Raises:
        FileWriteError: If the file cannot be written
    """
    file_path = Path(file_path)
    if lock_file is None:
        lock_file = str(file_path) + ".lock"
        
    try:
        with file_lock(lock_file):
            return write_json(file_path, data, indent=indent)
    except Exception as e:
        logger.error(f"Error in atomic_write_json for {file_path}: {e}")
        raise FileWriteError(f"Failed to write JSON file atomically {file_path}: {e}") from e

def get_error_reports(operation: Optional[str] = None, limit: int = 10) -> List[ErrorReport]:
    """
    Get a list of error reports.
    
    Args:
        operation: Optional operation filter
        limit: Maximum number of reports to return
        
    Returns:
        List of ErrorReport instances, newest first
    """
    try:
        # List all error report files
        report_files = [f for f in os.listdir(ERROR_LOG_DIR) if f.endswith('.json')]
        
        # Filter by operation if specified
        if operation:
            report_files = [f for f in report_files if f"_{operation}_" in f]
            
        # Sort by timestamp (newest first)
        report_files.sort(reverse=True)
        
        # Limit the number of reports
        report_files = report_files[:limit]
        
        # Load error reports
        reports = []
        for file in report_files:
            try:
                report = ErrorReport.load(os.path.join(ERROR_LOG_DIR, file))
                reports.append(report)
            except Exception as e:
                logger.error(f"Failed to load error report {file}: {e}")
                
        return reports
    except Exception as e:
        logger.error(f"Error getting error reports: {e}")
        return []

if __name__ == "__main__":
    # Simple demonstration of the module's functionality
    try:
        print("Testing read_file...")
        content = read_file("README.md")
        print(f"Successfully read README.md ({len(content)} bytes)")
        
        print("\nTesting list_dir...")
        entries = list_dir(".")
        print(f"Listed {len(entries)} entries in current directory")
        
        print("\nTesting atomic_write_json and atomic_read_json...")
        test_data = {"test": True, "timestamp": time.time()}
        atomic_write_json("test_data.json", test_data)
        read_data = atomic_read_json("test_data.json")
        print(f"Successfully wrote and read test data: {read_data}")
        
        print("\nTesting error reporting...")
        try:
            read_file("non_existent_file.txt")
        except Exception as e:
            report = ErrorReport("read_file", "non_existent_file.txt", e)
            report_path = report.save()
            print(f"Created error report: {report_path}")
            
    except Exception as e:
        print(f"Test failed: {e}") 