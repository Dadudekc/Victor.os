# Resilient Checkpoint System

## Overview

The Resilient Checkpoint System provides a robust checkpoint-based state management system for agents with:

- **Exponential backoff retry** for all file operations
- **Multiple fallback mechanisms** for reading/writing checkpoints
- **Comprehensive error handling** to prevent data corruption
- **Drift detection** to identify and recover from state inconsistencies
- **Automatic recovery** from transient errors

This document explains how the system works and provides guidelines for integrating it into agent operational loops.

## Architecture

The system consists of two primary components:

1. **ResilientCheckpointManager** (`src/dreamos/core/resilient_checkpoint_manager.py`) - Enhanced checkpoint manager with resilient IO operations
2. **resilient_io** (`src/dreamos/utils/resilient_io.py`) - Utilities for robust file operations

The ResilientCheckpointManager wraps the standard CheckpointManager with additional reliability features while maintaining the same interface, making it a drop-in replacement.

## Key Features

### 1. Resilient File Operations

All file operations use the resilient_io utilities, which provide:

- **Retry with exponential backoff** - Automatically retries operations on transient failures
- **Chunked reading/writing** - Handles large files more reliably
- **Atomic operations** - Prevents partial writes causing corruption
- **Multiple fallback methods** - If one method fails, another is tried

### 2. Enhanced Error Handling

The system includes comprehensive error handling:

- **Graceful degradation** - Falls back to standard checkpoint manager when resilient operations fail
- **Transaction logging** - Records operations for recovery purposes
- **Recovery checkpoints** - Automatically creates recovery points before risky operations

### 3. Drift Detection

The checkpoint manager can detect potential agent drift by:

- **Monitoring operational metrics** - Detects unusual patterns in task execution
- **Validating state consistency** - Ensures state matches expected patterns
- **Checking for corruption** - Identifies invalid or corrupted state files

### 4. Retention Policy

Checkpoints are managed according to a configurable retention policy:

- **Routine checkpoints** - Only the latest 3 are kept to save space
- **Recovery checkpoints** - Kept for 7 days for troubleshooting
- **Pre-operation checkpoints** - Kept until the operation completes successfully

## Integration Guide

### Basic Usage

To use the resilient checkpoint manager in your agent:

```python
# Import the resilient checkpoint manager
from dreamos.core.resilient_checkpoint_manager import ResilientCheckpointManager

# Initialize the manager with your agent ID
agent_id = "agent-3"  # Replace with your agent ID
checkpoint_manager = ResilientCheckpointManager(agent_id)

# Create a checkpoint
checkpoint_path = checkpoint_manager.create_checkpoint("routine")

# Restore from checkpoint
checkpoint_manager.restore_checkpoint(checkpoint_path)

# Get latest checkpoint
latest = checkpoint_manager.get_latest_checkpoint("routine")
```

### Checkpoint Types

The system supports different checkpoint types for various scenarios:

- **routine** - Regular checkpoints created during normal operation
- **pre_operation** - Created before potentially risky operations
- **recovery** - Created when errors or drift are detected

### Agent Loop Integration

For optimal integration into an agent's operational loop, use this pattern:

```python
# Initialize checkpoint manager
agent_id = "agent-3"  # Replace with your agent ID
checkpoint_manager = ResilientCheckpointManager(agent_id)

# Track operation time
session_start_time = time.time()
last_checkpoint_time = session_start_time

# Main loop
while True:  # Replace with actual loop condition
    try:
        # Normal agent operations
        process_mailbox()
        check_tasks()
        execute_current_task()
        
        # Regular checkpoint creation (every 30 minutes)
        current_time = time.time()
        if current_time - last_checkpoint_time >= 1800:  # 30 minutes
            checkpoint_manager.create_checkpoint("routine")
            last_checkpoint_time = current_time
            
        # Force state refresh after long uptime (2 hours)
        if current_time - session_start_time >= 7200:  # 2 hours
            recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
            # Optional: Perform controlled restart with state from checkpoint
            session_start_time = current_time
            
        # Check for drift
        if checkpoint_manager.detect_drift():
            logger.warning("Potential drift detected, creating recovery checkpoint")
            recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
            
            # Get latest checkpoint prior to drift
            latest = checkpoint_manager.get_latest_checkpoint("routine")
            if latest:
                logger.info(f"Restoring from latest routine checkpoint: {latest}")
                checkpoint_manager.restore_checkpoint(latest)
            
    except Exception as e:
        # Create recovery checkpoint on error
        recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
        logger.error(f"Error during operation: {str(e)}")
        logger.info(f"Recovery point created: {recovery_checkpoint}")
        # Continue loop or initiate recovery process
```

### Best Practices

1. **Create checkpoints at appropriate intervals**
   - Too frequent: Wastes resources
   - Too infrequent: Risk of data loss
   - Recommended: Every 15-30 minutes during active operation

2. **Create checkpoints before risky operations**
   ```python
   # Before a risky operation
   pre_op_checkpoint = checkpoint_manager.create_checkpoint("pre_operation")
   
   try:
       # Perform risky operation
       result = risky_operation()
       return result
   except Exception as e:
       # Something went wrong, restore from checkpoint
       logger.error(f"Operation failed: {str(e)}")
       checkpoint_manager.restore_checkpoint(pre_op_checkpoint)
       raise
   ```

3. **Monitor for drift**
   - Check for drift after operations that might cause state inconsistency
   - Restore from latest clean checkpoint when drift is detected

4. **Guard critical operations with recovery checkpoints**
   ```python
   # Create recovery checkpoint
   recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
   
   # Perform critical operation
   critical_operation()
   ```

## Testing and Validation

The checkpoint system includes comprehensive testing tools:

1. **Unit tests** - Located in `src/dreamos/core/test_resilient_checkpoint_manager.py`
2. **Integration testing** - Located in `src/dreamos/core/integrate_resilient_checkpoints.py`
3. **Validation tests** - Located in `src/dreamos/core/validate_checkpoint_resilience.py`

To validate the system before deployment:

```bash
# Run unit tests
python -m dreamos.core.test_resilient_checkpoint_manager

# Run integration test
python -m dreamos.core.integrate_resilient_checkpoints

# Run validation tests
python -m dreamos.core.validate_checkpoint_resilience
```

## Customization

The system can be customized for specific agent needs:

### Custom State Collection

Override the state collection methods to capture additional agent-specific state:

```python
class CustomCheckpointManager(ResilientCheckpointManager):
    def _get_custom_state(self):
        """Collect custom agent state."""
        return {
            "special_data": retrieve_special_data(),
            "additional_context": get_additional_context()
        }
        
    def _get_operational_context(self):
        """Override to include custom context."""
        context = super()._get_operational_context()
        context.update({
            "custom_fields": self._get_custom_state()
        })
        return context
```

### Enhanced Drift Detection

Implement agent-specific drift detection logic:

```python
class CustomCheckpointManager(ResilientCheckpointManager):
    def detect_drift(self):
        """Custom drift detection for specific agent."""
        # Check for standard drift
        standard_drift = super().detect_drift()
        
        # Add agent-specific drift detection
        custom_drift = self._detect_custom_drift()
        
        return standard_drift or custom_drift
        
    def _detect_custom_drift(self):
        """Implement agent-specific drift detection."""
        # Your custom detection logic here
        return False  # Replace with actual detection
```

## Troubleshooting

Common issues and solutions:

1. **Checkpoint creation fails**
   - Check file permissions
   - Verify disk space availability
   - Ensure agent_id is valid
   
2. **Restoration fails**
   - Check if the checkpoint file exists
   - Verify the checkpoint is not corrupted
   - Ensure the checkpoint belongs to the correct agent
   
3. **False drift detection**
   - Review the agent's operational patterns
   - Adjust drift detection sensitivity if needed
   - Check for environmental factors (resource contention, etc.)

4. **Recovery does not fix issues**
   - Try an earlier checkpoint
   - Check for issues outside the checkpoint scope
   - Consider a full agent reset as a last resort

## Implementation Status and Next Steps

The Resilient Checkpoint System is fully implemented and integrated with the following components:

- ✅ Core ResilientCheckpointManager
- ✅ Integration with resilient_io
- ✅ Comprehensive testing suite
- ✅ Validation framework

Next steps for the system:

1. **Performance optimization** - Further tune retry parameters and caching
2. **Enhanced drift metrics** - Develop more sophisticated drift detection algorithms
3. **Cross-agent consistency** - Ensure consistent state across related agents

## Conclusion

The Resilient Checkpoint System provides a robust foundation for agent state management, reducing the risk of drift and ensuring reliable recovery from errors and failures. By following the integration guidelines and best practices outlined in this document, agents can achieve significantly improved stability and reliability. 