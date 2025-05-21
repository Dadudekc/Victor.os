# Dream.OS Error Recovery Library

This library provides utilities for error classification, recovery, and handling to support resilient agent operations.

## Current Status

This is a **placeholder implementation** created by Agent-3 to facilitate integration between the lifecycle components and the upcoming error recovery system. All components here will be fully implemented by Agent-6.

## Integration with Lifecycle

These components are designed to integrate with the `dreamos.skills.lifecycle` library, particularly:

1. **StableAutonomousLoop** - Uses `recover_from_error()` to attempt recovery before entering degraded mode
2. **CircuitBreaker** - Will use `classify_error()` and `log_error()` to track failure patterns
3. **DegradedOperationMode** - Will use `get_available_recovery_resources()` to determine what capabilities remain during degraded operation

## Key Components

### Error Classification

The error classification system will categorize errors by type, which determines recovery strategies:

```python
from dreamos.skills.error_recovery import classify_error, ErrorType

# Classify an error
error_type = classify_error(exception, context)

# Check if it's a particular type
if error_type == ErrorType.TRANSIENT:
    # Handle transient error
```

### Recovery Strategies

Recovery strategies provide standardized approaches to handling different error types:

```python
from dreamos.skills.error_recovery import recover_from_error

# Attempt recovery
success = recover_from_error(exception, context)
if success:
    # Recovery succeeded, continue
else:
    # Recovery failed, enter degraded mode
```

### Error Logging

Structured error logging will enable analysis and monitoring:

```python
from dreamos.skills.error_recovery import log_error

# Log a detailed error
log_error(
    error=exception,
    operation="file_write",
    context={"file_path": "/path/to/file", "attempt": 3}
)
```

## Implementation Guidelines for Agent-6

When implementing the full library, please consider:

1. **Error Types**: Expand `ErrorType` enum with a comprehensive classification system based on the error classification document you'll create.

2. **Recovery Strategies**: Implement concrete `RecoveryStrategy` subclasses based on your error recovery strategy pattern document.

3. **Error Logging**: Enhance the logging system to support your standardized error reporting format.

4. **Integration Testing**: Ensure the integration with lifecycle components works correctly through the interfaces established here.

The placeholder structure is designed to be compatible with your eventual implementation, allowing for incremental development and testing.

## Available Hooks

To make integration easier, the lifecycle library has the following extension points:

1. In `StableAutonomousLoop.run()`, errors are passed to `_recover_from_error()` which will call your `recover_from_error()` function.

2. `CircuitBreaker.__exit__()` will be extended to use your error classification and logging.

3. `DegradedOperationMode` will use `get_available_recovery_resources()` to determine capabilities.

## Example Planned Integration

```python
# In StableAutonomousLoop._recover_from_error
def _recover_from_error(self, error: Exception, context: Dict[str, Any] = None) -> bool:
    """Attempt to recover from an error."""
    from dreamos.skills.error_recovery import recover_from_error, log_error
    
    # Log the error
    log_error(error, operation=self.name, context=context)
    
    # Attempt recovery
    return recover_from_error(error, context or self.state)
```

Please refer to the integration proposal document in your mailbox for a more detailed plan for our collaboration. 