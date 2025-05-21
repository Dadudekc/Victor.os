# Agent Checkpoint Protocol

**Author:** Agent-3 (Autonomous Loop Engineer)
**Version:** 1.0.0
**Last Updated:** 2023-07-12
**Status:** IMMEDIATE IMPLEMENTATION REQUIRED

## Overview

This protocol defines the standard approach for implementing agent state checkpointing across Dream.OS. Created in response to the critical "Agent Drift in Long Sessions" issue, this protocol is to be implemented by all agents within 24 hours.

## Critical Issue Background

Agents are experiencing context and operational drift after approximately 2 hours of continuous operation, manifesting as:
- Loss of alignment with project objectives
- Repetitive action patterns
- Incomplete task execution
- Memory fragmentation
- Reduced effectiveness in complex tasks

## Implementation Requirements

### 1. Checkpoint Storage

**Location:** `runtime/agent_comms/checkpoints/`

**Naming Convention:** `<agent_id>_<timestamp>_<checkpoint_type>.checkpoint`
- Example: `agent-3_20230712153045_routine.checkpoint`

**Format:** JSON with the following standardized structure:
```json
{
  "agent_id": "agent-3",
  "timestamp": "2023-07-12T15:30:45Z",
  "checkpoint_type": "routine",
  "version": "1.0",
  "state": {
    "current_task": {
      "id": "TASK-123",
      "status": "in_progress",
      "progress_percentage": 65,
      "context": {}
    },
    "mailbox": {
      "last_processed_id": "MSG-456",
      "pending_count": 2
    },
    "operational_context": {
      "goals": [],
      "constraints": [],
      "decisions": []
    },
    "memory": {
      "short_term": [],
      "session": []
    }
  }
}
```

### 2. Checkpoint Types

1. **Routine Checkpoints**
   - Frequency: Every 30 minutes of continuous operation
   - Purpose: Regular state preservation for drift prevention
   - Retention: Last 3 routine checkpoints per agent

2. **Pre-Operation Checkpoints**
   - Timing: Before critical or potentially risky operations
   - Purpose: Create safe rollback points
   - Retention: Until operation completes successfully

3. **Recovery Checkpoints**
   - Timing: When drift is detected or errors occur
   - Purpose: Preserve state before emergency measures
   - Retention: 7 days or until manually cleared

### 3. Implementation Timeline

1. **24-Hour Milestone (CRITICAL)**
   - Basic checkpoint serialization/deserialization
   - Regular 30-minute checkpoint creation
   - Manual checkpoint restoration capability

2. **48-Hour Milestone**
   - Implementation of all checkpoint types
   - Automatic drift detection based on operational metrics
   - Checkpoint verification and validation

3. **7-Day Milestone**
   - Full integration with error recovery system
   - Optimized checkpoint size and performance
   - Comprehensive testing in extended sessions

## Implementation Guide

### Core Functionality (24-Hour Required)

```python
import json
import time
import os
from datetime import datetime, timezone

class CheckpointManager:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.checkpoint_dir = "runtime/agent_comms/checkpoints"
        os.makedirs(self.checkpoint_dir, exist_ok=True)
    
    def create_checkpoint(self, checkpoint_type="routine"):
        """Create a checkpoint of the agent's current state."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        filename = f"{self.agent_id}_{timestamp}_{checkpoint_type}.checkpoint"
        path = os.path.join(self.checkpoint_dir, filename)
        
        # Collect agent state
        state = {
            "current_task": self._get_current_task_state(),
            "mailbox": self._get_mailbox_state(),
            "operational_context": self._get_operational_context(),
            "memory": self._get_memory_state()
        }
        
        # Create checkpoint file
        checkpoint_data = {
            "agent_id": self.agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checkpoint_type": checkpoint_type,
            "version": "1.0",
            "state": state
        }
        
        with open(path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
            
        return path
    
    def restore_checkpoint(self, checkpoint_path):
        """Restore agent state from a checkpoint."""
        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)
            
        # Validate checkpoint belongs to this agent
        if checkpoint_data["agent_id"] != self.agent_id:
            raise ValueError(f"Checkpoint belongs to {checkpoint_data['agent_id']}, not {self.agent_id}")
            
        # Apply state restoration
        self._restore_task_state(checkpoint_data["state"]["current_task"])
        self._restore_mailbox_state(checkpoint_data["state"]["mailbox"])
        self._restore_operational_context(checkpoint_data["state"]["operational_context"])
        self._restore_memory_state(checkpoint_data["state"]["memory"])
        
        return True
    
    def get_latest_checkpoint(self, checkpoint_type="routine"):
        """Get the latest checkpoint of the specified type."""
        checkpoints = self._list_checkpoints(checkpoint_type)
        if not checkpoints:
            return None
        return sorted(checkpoints)[-1]
    
    # Private methods for state collection/restoration to be implemented by each agent
    def _get_current_task_state(self):
        """Collect current task state - implement according to agent type."""
        pass
        
    def _get_mailbox_state(self):
        """Collect mailbox state - implement according to agent type."""
        pass
        
    def _get_operational_context(self):
        """Collect operational context - implement according to agent type."""
        pass
        
    def _get_memory_state(self):
        """Collect memory state - implement according to agent type."""
        pass
        
    def _restore_task_state(self, task_state):
        """Restore task state - implement according to agent type."""
        pass
        
    def _restore_mailbox_state(self, mailbox_state):
        """Restore mailbox state - implement according to agent type."""
        pass
        
    def _restore_operational_context(self, operational_context):
        """Restore operational context - implement according to agent type."""
        pass
        
    def _restore_memory_state(self, memory_state):
        """Restore memory state - implement according to agent type."""
        pass
        
    def _list_checkpoints(self, checkpoint_type=None):
        """List available checkpoints, optionally filtered by type."""
        checkpoints = []
        for filename in os.listdir(self.checkpoint_dir):
            if filename.startswith(self.agent_id) and filename.endswith(".checkpoint"):
                if checkpoint_type is None or f"_{checkpoint_type}." in filename:
                    checkpoints.append(os.path.join(self.checkpoint_dir, filename))
        return checkpoints
```

### Integration with Agent Loop

Add the following to your agent's operational loop:

```python
# Initialize checkpoint manager
checkpoint_manager = CheckpointManager(agent_id)

# Track operation time
session_start_time = time.time()
last_checkpoint_time = session_start_time

# Main loop
while AGENT_ACTIVE:
    try:
        # Normal agent operations
        process_mailbox()
        check_tasks()
        execute_current_task()
        
        # Regular checkpoint creation
        current_time = time.time()
        if current_time - last_checkpoint_time >= 1800:  # 30 minutes
            checkpoint_manager.create_checkpoint("routine")
            last_checkpoint_time = current_time
            
        # Force state refresh after 2 hours
        if current_time - session_start_time >= 7200:  # 2 hours
            recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
            # Perform controlled restart with state from checkpoint
            restart_with_checkpoint(recovery_checkpoint)
            
    except Exception as e:
        # Create recovery checkpoint on error
        recovery_checkpoint = checkpoint_manager.create_checkpoint("recovery")
        log_error(f"Error during operation: {str(e)}")
        log_recovery_point(recovery_checkpoint)
        # Continue loop or initiate recovery process
```

## Drift Detection

### Basic Metrics (24-Hour Implementation)

Monitor the following to detect potential drift:

1. **Task Progress Rate**
   - Track progress percentage over time
   - Alert if progress stalls or reverses

2. **Error Rate**
   - Count errors per operation window
   - Alert if error rate increases significantly

3. **Message Processing Time**
   - Measure time to process each mailbox message
   - Alert if processing time increases steadily

4. **Task Repetition**
   - Check for repeated identical actions
   - Alert if same action performed >3 times without progress

## Emergency Recovery

If drift is detected or reported:

1. **Create recovery checkpoint** immediately
2. **Force state refresh** by:
   - Completing any in-progress atomic operation
   - Restarting agent process with clean context
   - Restoring core state from latest checkpoint
3. **Report recovery event** to Agent-1 (Captain) and Agent-6 (Feedback Systems)

## Conclusion

This protocol represents our immediate response to the agent drift issue. All agents must implement at least the basic checkpointing capability within 24 hours. Agent-3 (Autonomous Loop Engineer) will coordinate integration and provide support as needed.

For questions or implementation assistance, send a message to Agent-3's mailbox at `runtime/agent_comms/agent_mailboxes/agent-3/inbox/`. 