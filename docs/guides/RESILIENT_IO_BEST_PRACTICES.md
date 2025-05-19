# Resilient I/O Best Practices Guide

## Overview

This guide provides best practices for using the `resilient_io` module to implement robust file and directory operations in Dream.OS applications. The module addresses persistent tool failures, including read_file and list_dir timeouts, with comprehensive retry logic, fallback mechanisms, and error reporting.

## Core Components

The `resilient_io` module offers these key components:

1. **Robust File Operations** - Read, write, and manage files with automatic retries
2. **Directory Management** - List, scan, and manipulate directories safely
3. **Error Reporting System** - Detailed error tracking and reporting
4. **File Locking** - Prevent concurrent access issues
5. **Atomic Operations** - Ensure data consistency during write operations

## Usage Patterns

### Basic File Operations

```python
from dreamos.utils.resilient_io import read_file, write_file, read_json, write_json

# Reading files
try:
    content = read_file("path/to/file.txt")
except FileReadError as e:
    # Handle file read errors with proper logging
    logger.error(f"Failed to read file: {str(e)}")
    # Implement fallback or recovery

# Writing files (automatically uses atomic write pattern)
try:
    success = write_file("path/to/file.txt", "File content")
    if not success:
        logger.warning("Write operation returned False")
except FileWriteError as e:
    logger.error(f"Failed to write file: {str(e)}")
    # Implement error recovery
```

### JSON Data Handling

```python
from dreamos.utils.resilient_io import read_json, write_json

# Reading JSON
try:
    data = read_json("config.json")
except FileReadError as e:
    logger.error(f"Failed to read JSON: {str(e)}")
    # Use default configuration
    data = DEFAULT_CONFIG

# Writing JSON (automatically handles atomic writes)
try:
    success = write_json("config.json", data)
except FileWriteError as e:
    logger.error(f"Failed to write JSON: {str(e)}")
    # Backup data or try alternative storage
```

### Directory Operations

```python
from dreamos.utils.resilient_io import list_dir, scan_dir, ensure_dir

# Listing directory contents
try:
    files = list_dir("./data")
except DirectoryOperationError as e:
    logger.error(f"Failed to list directory: {str(e)}")
    files = []

# Recursive directory scanning with patterns
try:
    python_files = scan_dir(
        "./src", 
        recursive=True, 
        include_pattern="*.py",
        exclude_pattern="__pycache__/*"
    )
except DirectoryOperationError as e:
    logger.error(f"Failed to scan directory: {str(e)}")
    python_files = []

# Ensuring directory exists
try:
    ensure_dir("./output/logs")
except DirectoryOperationError as e:
    logger.error(f"Failed to create directory structure: {str(e)}")
    # Use alternative location
```

### Atomic File Operations

```python
from dreamos.utils.resilient_io import atomic_read_json, atomic_write_json

# Atomic JSON operations with file locking
try:
    # Read with file lock to prevent concurrent access issues
    data = atomic_read_json("shared_config.json")
    
    # Modify data
    data["last_updated"] = time.time()
    
    # Write with file lock (all-or-nothing update)
    atomic_write_json("shared_config.json", data)
except (FileReadError, FileWriteError) as e:
    logger.error(f"Atomic file operation failed: {str(e)}")
```

### Custom Retry Behavior

```python
from dreamos.utils.resilient_io import with_retry

# Define custom function with retry decorator
@with_retry(
    max_retries=5,
    retry_delay=2.0,
    backoff_factor=1.5,
    exceptions_to_retry=(ConnectionError, TimeoutError),
    timeout=30.0
)
def fetch_remote_data(url):
    # Implementation...
    return data

# Function will automatically retry on specified exceptions
```

## Error Handling Guidelines

### 1. Use Specific Exception Types

Catch specific exceptions from the module:

```python
from dreamos.utils.resilient_io import (
    IOError, FileReadError, FileWriteError, 
    DirectoryOperationError, TimeoutError
)

try:
    # Operation that might fail
    content = read_file("important_data.txt")
except FileNotFoundError:
    # Handle missing file specifically
    logger.warning("File not found, creating with default content")
    write_file("important_data.txt", DEFAULT_CONTENT)
except FileReadError as e:
    # Handle other read errors
    logger.error(f"Error reading file: {str(e)}")
    # Implement appropriate recovery
```

### 2. Error Report Analysis

```python
from dreamos.utils.resilient_io import get_error_reports

# Get recent error reports for specific operation
read_file_errors = get_error_reports(operation="read_file", limit=5)

# Analyze error patterns
for report in read_file_errors:
    print(f"Operation: {report.operation}")
    print(f"Path: {report.path}")
    print(f"Exception: {report.exception_type} - {report.exception_msg}")
    print(f"Context: {report.context}")
```

### 3. Implement Graceful Degradation

```python
def process_data_files(file_list):
    results = []
    errors = []
    
    for file_path in file_list:
        try:
            # Try to process file
            data = read_json(file_path)
            result = process_data(data)
            results.append(result)
        except Exception as e:
            # Log error but continue with other files
            logger.error(f"Failed to process {file_path}: {str(e)}")
            errors.append((file_path, str(e)))
    
    # Report summary
    logger.info(f"Processed {len(results)} files successfully")
    if errors:
        logger.warning(f"Failed to process {len(errors)} files")
    
    return results, errors
```

## Performance Considerations

1. **Timeout Configuration**: Set appropriate timeouts based on file sizes and operation types
   ```python
   # Increase timeout for large files
   content = read_file("large_file.dat", timeout=60.0)
   ```

2. **Retry Limits**: Configure max_retries appropriately
   ```python
   # Fewer retries for non-critical operations
   files = list_dir("./temp", max_retries=2)
   
   # More retries for critical operations
   config = read_json("critical_config.json", max_retries=5)
   ```

3. **Resource Management**: Use context managers for file locks
   ```python
   from dreamos.utils.resilient_io import file_lock
   
   # Automatically releases lock when block exits
   with file_lock("resource.lock"):
       # Critical section
       pass
   ```

## Integration with Monitoring

Error reports generated by resilient_io are stored in `runtime/error_logs/io_errors/`. Implement regular analysis of these logs to:

1. Identify recurring issues
2. Detect performance bottlenecks
3. Guide system improvements

## Best Practices Checklist

- [ ] Replace all direct file operations with resilient_io equivalents
- [ ] Use specific exception types for targeted error handling
- [ ] Implement appropriate fallback mechanisms
- [ ] Configure retries based on operation criticality
- [ ] Ensure proper error logging and reporting
- [ ] Use atomic operations for critical data
- [ ] Regularly analyze error reports

## Example Implementation

For a comprehensive example of resilient I/O practices, see:

- `src/dreamos/agents/file_manager.py` - Agent utilizing resilient I/O
- `src/dreamos/core/checkpoint_manager.py` - Checkpoint system using atomic file operations
- `src/dreamos/utils/resilient_io.py` - The resilient I/O implementation

## Conclusion

By following these practices, you can significantly improve the reliability and fault tolerance of your Dream.OS components, ensuring robust performance even under adverse conditions. 