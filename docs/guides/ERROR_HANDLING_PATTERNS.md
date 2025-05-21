# Error Handling Patterns Guide

## Overview

This guide outlines standardized error handling patterns for Dream.OS components, focusing on file operations, network requests, and other critical system components. Following these patterns will enhance system stability and improve recovery from transient failures.

## Core Principles

1. **Retry with Exponential Backoff** - Attempt operations multiple times with increasing delays
2. **Fallback Mechanisms** - Provide alternative approaches when primary methods fail
3. **Graceful Degradation** - Continue operation with reduced functionality rather than failing completely
4. **Comprehensive Logging** - Log details for monitoring, debugging, and analysis
5. **Recovery Checkpoints** - Create recovery points before potentially risky operations

## Standard Error Handling Patterns

### 1. File Operations

Use the `resilient_io` utilities for all file operations:

```python
from dreamos.utils.resilient_io import read_file, write_file, read_json, write_json, list_dir

# Reading files
try:
    content = read_file("path/to/file.txt")
except FileNotFoundError:
    # Handle missing file
    logger.warning("File not found, using default content")
    content = DEFAULT_CONTENT
except Exception as e:
    # Handle other errors
    logger.error(f"Error reading file: {str(e)}")
    # Consider fallback approach
    
# Writing files
try:
    success = write_file("path/to/file.txt", content)
    if not success:
        logger.error("Failed to write file")
except Exception as e:
    logger.error(f"Error writing file: {str(e)}")
    # Consider creating a backup or alternative storage
```

### 2. Custom Retry Logic

For operations not covered by resilient_io, use this pattern:

```python
from dreamos.utils.resilient_io import with_retry

# Retry a function call
result = with_retry(
    my_function, 
    *function_args,
    max_retries=5,
    operation_name="my_operation",
    path="operation_context"
)

# Or implement custom retry logic
max_retries = 5
for attempt in range(max_retries):
    try:
        # Attempt operation
        result = my_function(*args)
        break  # Success, exit the loop
    except TransientError as e:
        # Only retry on transient errors
        if attempt < max_retries - 1:
            delay = calculate_backoff(attempt)
            logger.warning(f"Attempt {attempt+1} failed: {str(e)}. Retrying in {delay}s")
            time.sleep(delay)
        else:
            logger.error(f"All {max_retries} attempts failed")
            # Handle the failure
            raise
    except Exception as e:
        # Don't retry on non-transient errors
        logger.error(f"Non-transient error: {str(e)}")
        raise
```

### 3. Transaction Logging

For critical operations, implement transaction logging:

```python
def perform_critical_operation(operation_type, context):
    # Log transaction start
    transaction_id = log_transaction_start(operation_type, context)
    
    try:
        # Perform the operation
        result = do_operation(context)
        
        # Log transaction success
        log_transaction_success(transaction_id, result)
        
        return result
        
    except Exception as e:
        # Log transaction failure
        log_transaction_failure(transaction_id, str(e))
        raise
```

### 4. Checkpointing

Create checkpoints before potentially risky operations:

```python
from dreamos.core.resilient_checkpoint_manager import ResilientCheckpointManager

# Initialize checkpoint manager
checkpoint_manager = ResilientCheckpointManager(agent_id)

# Before risky operation
checkpoint_path = checkpoint_manager.create_checkpoint("pre_operation")

try:
    # Perform risky operation
    result = risky_operation()
    return result
except Exception as e:
    # Something went wrong, restore from checkpoint
    logger.error(f"Operation failed: {str(e)}")
    logger.info(f"Restoring from checkpoint: {checkpoint_path}")
    checkpoint_manager.restore_checkpoint(checkpoint_path)
    # Consider retry or fallback
    raise
```

## Error Classification

Classify errors to determine appropriate handling:

1. **Transient Errors** - Temporary issues that may resolve on retry (timeouts, resource contention)
2. **Permanent Errors** - Issues that won't resolve with retries (file not found, permission denied)
3. **Fatal Errors** - Severe issues requiring immediate attention (data corruption, memory errors)

## Standardized Exception Hierarchy

```
BaseError
├── TransientError
│   ├── TimeoutError
│   ├── ResourceTemporarilyUnavailableError
│   └── NetworkTemporaryError
├── PermanentError
│   ├── ResourceNotFoundError
│   ├── PermissionError
│   └── ValidationError
└── FatalError
    ├── DataCorruptionError
    ├── SystemError
    └── UnrecoverableError
```

## Logging Best Practices

1. **Context** - Include operation context, file paths, timestamps
2. **Structured Format** - Use structured logging for better analysis
3. **Appropriate Levels** - Use correct severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
4. **Actionable** - Include enough information to diagnose and fix the issue

## Integration with Monitoring

Error logs should be integrated with monitoring systems to:

1. **Alert** on critical errors
2. **Track** error rates and patterns
3. **Analyze** common failure modes
4. **Trigger** automatic recovery procedures

## Example Implementation

For a complete example, see the implementation in:

1. `src/dreamos/utils/resilient_io.py` - Resilient file operations
2. `src/dreamos/core/resilient_checkpoint_manager.py` - Checkpoint system with error recovery
3. `src/dreamos/coordination/tasks/task_manager_stable.py` - Task management with transaction logging

## Adoption Checklist

- [ ] Replace direct file operations with resilient_io utilities
- [ ] Implement appropriate retry logic for other operations
- [ ] Add transaction logging for critical operations
- [ ] Create checkpoints before risky operations
- [ ] Follow standard exception hierarchy
- [ ] Use structured logging
- [ ] Test recovery procedures

By following these patterns, we can significantly improve the stability and reliability of the Dream.OS system. 