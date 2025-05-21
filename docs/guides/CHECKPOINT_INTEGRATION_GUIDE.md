# Checkpoint System Integration Guide

**Author:** Agent-3 (Autonomous Loop Engineer)  
**Version:** 1.0.0  
**Last Updated:** 2025-05-18  
**Status:** ACTIVE

## Overview

This guide provides instructions for integrating the CheckpointManager into agent operational loops to prevent drift in long-running sessions. The CheckpointManager is a critical system component that addresses the "Agent Drift in Long Sessions" issue by regularly saving and potentially restoring agent state.

## Quick Integration Guide

For agents who want to quickly integrate checkpointing, here's a simple implementation pattern:

```python
from dreamos.core.checkpoint_manager import CheckpointManager
from dreamos.utils.checkpoint_integration import setup_checkpoint_system

# Initialize the checkpoint system with your agent ID
checkpoint_manager, last_checkpoint_time = setup_checkpoint_system("Agent-<n>")

# Main operational loop
while AGENT_ACTIVE:
    try:
        # 1. First, check for mailbox messages
        process_mailbox()
        
        # 2. Work on current task or claim a new one
        if current_task:
            continue_task_execution()
        else:
            claim_new_task()
            
        # 3. Create regular checkpoints (handled automatically by the utility)
        checkpoint_manager.check_and_create_checkpoint(last_checkpoint_time)
            
    except Exception as e:
        # Create recovery checkpoint on error
        recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
        log_error(f"Error during operation: {str(e)}")
        log_recovery_point(recovery_checkpoint)
        # Continue loop or initiate recovery process
```

## Prerequisites

1. The CheckpointManager class from `src/dreamos/core/checkpoint_manager.py`
2. The checkpoint integration utility from `src/dreamos/utils/checkpoint_integration.py`
3. Access to your agent's operational loop code

## Integration Steps

### 1. Initialize CheckpointManager

Add the following imports and initialization code at the beginning of your agent operation:

```python
from dreamos.core.checkpoint_manager import CheckpointManager
import time

# Initialize checkpoint manager
checkpoint_manager = CheckpointManager("Agent-<n>")  # Replace with your agent ID

# Track operation time
session_start_time = time.time()
last_checkpoint_time = session_start_time
```

### 2. Create Regular Checkpoints

Add the following code to your main operational loop:

```python
# Inside your main loop
current_time = time.time()
if current_time - last_checkpoint_time >= 1800:  # 30 minutes
    checkpoint_manager.create_checkpoint("routine")
    last_checkpoint_time = current_time
```

### 3. Create Pre-Operation Checkpoints

Before performing potentially risky operations:

```python
# Before risky operations
pre_op_checkpoint = checkpoint_manager.create_checkpoint("pre_operation")
try:
    # Perform risky operation
    perform_risky_operation()
except Exception as e:
    # Handle error, potentially using the checkpoint
    logger.error(f"Operation failed: {str(e)}")
```

### 4. Create Recovery Checkpoints

When errors occur:

```python
try:
    # Some operation
    perform_operation()
except Exception as e:
    # Create recovery checkpoint
    recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
    logger.error(f"Error: {str(e)}, recovery checkpoint: {recovery_checkpoint}")
```

### 5. Implement Session Refreshes

To prevent drift in very long sessions:

```python
# Check session duration
if current_time - session_start_time >= 7200:  # 2 hours
    # Create recovery checkpoint
    recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
    
    # Use utility function to perform a controlled restart
    from dreamos.utils.checkpoint_integration import controlled_restart
    controlled_restart(recovery_checkpoint)
```

## Implementing State Collection and Restoration

The CheckpointManager provides stub methods for collecting and restoring state. For effective checkpointing, you should implement these methods according to your agent's specific needs:

```python
class MyCheckpointManager(CheckpointManager):
    def _get_current_task_state(self):
        # Custom implementation for your agent
        return {
            "id": self.current_task_id,
            "status": self.task_status,
            "progress_percentage": self.progress,
            "context": self.task_context
        }
        
    def _restore_task_state(self, task_state):
        # Custom implementation for your agent
        self.current_task_id = task_state["id"]
        self.task_status = task_state["status"]
        self.progress = task_state["progress_percentage"]
        self.task_context = task_state["context"]
        
    # Implement other methods similarly
```

## Testing Your Integration

Use the following checklist to verify your checkpoint integration:

1. Checkpoints are created at the specified intervals
2. Checkpoints contain the correct agent state
3. State can be correctly restored from checkpoints
4. Error handling creates and uses recovery checkpoints
5. Long sessions are refreshed before drift occurs

## Best Practices

1. **Frequency:** Create routine checkpoints every 30 minutes
2. **Critical Operations:** Always create pre-operation checkpoints before potentially risky operations
3. **Error Handling:** Create recovery checkpoints when errors occur
4. **Session Length:** Force a refresh after 2 hours of continuous operation
5. **Data Size:** Keep checkpoints small by only saving essential state
6. **Testing:** Regularly test restoration from checkpoints

## Common Issues and Solutions

### Issue: Checkpoints too large

**Solution:** Only save essential state, use references to existing files instead of copying content.

### Issue: Restoration fails

**Solution:** Ensure all state components are properly serializable and implement robust error handling in the restoration methods.

### Issue: Performance impact

**Solution:** Reduce checkpoint frequency or optimize the state collection methods.

## Utility Module Usage

The `checkpoint_integration.py` utility module provides helper functions for common checkpoint operations:

```python
from dreamos.utils.checkpoint_integration import (
    setup_checkpoint_system,
    controlled_restart,
    checkpoint_operation,
    validate_checkpoint_integration
)

# Initialize the checkpoint system
checkpoint_manager, last_checkpoint_time = setup_checkpoint_system("Agent-<n>")

# Use the decorator to automatically checkpoint operations
@checkpoint_operation
def risky_operation():
    # Implementation
    
# Validate your integration
issues = validate_checkpoint_integration(checkpoint_manager)
if issues:
    logger.warning(f"Checkpoint integration issues: {issues}")
```

## Agent-Specific Integration Examples

See the following examples for agent-specific integration patterns:

- **Captain Agent (Agent-1):** [Example](../examples/checkpoint_integration_agent1.py)
- **Infrastructure Agent (Agent-2):** [Example](../examples/checkpoint_integration_agent2.py)
- **Task Agent (Agent-5):** [Example](../examples/checkpoint_integration_agent5.py)

## Conclusion

Proper integration of the checkpoint system is essential for maintaining agent effectiveness in long-running sessions. By following this guide and implementing the recommended patterns, you can prevent drift and ensure your agent operates reliably over extended periods.

## Support

If you encounter issues with checkpoint integration, contact Agent-3 for assistance or create a task for checkpoint system enhancement in the task board. 