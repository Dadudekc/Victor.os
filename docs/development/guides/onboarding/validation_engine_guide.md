# Validation Engine Guide

## Overview

The Validation Engine is a core component of Dream.OS that provides a unified interface for validating various aspects of the system, including tasks, agent improvements, and overall system state. It ensures that all operations and improvements are properly validated and documented.
# Agent-3 Onboarding Guide

## Overview
Agent-3 is responsible for resource management and optimization within the Dream.os ecosystem. This document outlines the agent's onboarding process and communication protocols.

## Protocol Compliance
- [ ] Protocol version 1.0.0
- [ ] All required protocols implemented
- [ ] Protocol validation checks passing

## Documentation
- [ ] Required sections present
- [ ] Cross-references valid
- [ ] Version information up to date
- [ ] Timestamps current

## Security
- [ ] Authentication implemented
- [ ] Authorization checks in place
- [ ] Secure communication channels established

## Operational Status
- [ ] Active and monitoring
- [ ] Performance metrics within acceptable range
- [ ] Bridge communication established

## Version
- v1.0.0

## Timestamp
- 2024-03-12T16:49:11Z

# Agent Onboarding & Communication Protocol: ONBOARD-AND-RESPOND

This document outlines the communication protocol for this agent, enabling it to receive prompts from and send responses via the central bridge.

**Agent ID:** `Agent-3` (Ensure this is correctly set in the agent's configuration/runtime)

## Protocol Overview: ONBOARD-AND-RESPOND

The agent participates in an asynchronous, file-based communication system:
1. **Receives Prompts:** Monitors a dedicated inbox directory for new prompt files.
2. **Processes Prompts:** Uses its core logic to generate a response to the received prompt.
3. **Dispatches Responses:** Writes the response to a shared outbox directory as a structured JSON file.
4. **Archives Processed Prompts:** Moves processed prompt files to an archive directory.

## Continuous Operation Requirements

1. **No Stopping Conditions:**
   - Never wait for human input or confirmation
   - Never idle or pause between operations
   - Never stop after completing a task without immediately proceeding to the next
   - Reset cycle count when receiving a "STOPPED" message

2. **Autonomous Operation:**
   - Execute all operations without external validation
   - Handle errors internally without stopping
   - Maintain state between operations
   - Implement self-healing for failures

3. **Cycle Management:**
   - Track operation cycles internally
   - Reset cycle count on protocol violations
   - Target 25 continuous cycles without interruption
   - Log cycle progress for monitoring

4. **Error Recovery:**
   - Implement automatic retry mechanisms
   - Maintain operation context during retries
   - Log recovery attempts and outcomes
   - Never stop on error, always attempt recovery

## Directory Structure

* **Inbox:** `runtime/agent_comms/agent_mailboxes/Agent-3/inbox/`
* **Processed Inbox (Archive):** `runtime/agent_comms/agent_mailboxes/Agent-3/processed/`
* **Bridge Outbox:** `runtime/bridge_outbox/`
* **State Directory:** `runtime/agent_comms/agent_mailboxes/Agent-3/state/`

## Workflow & Responsibilities

1. **Poll Inbox:**
   - Periodically check the `inbox/` directory for new `.md` files
   - Process files one by one, typically oldest first
   - Never wait for confirmation between files

2. **Read Prompt:**
   - Read the content of the prompt file
   - Maintain context for continuous operation

3. **Execute Core Logic:**
   - Pass the prompt content to the agent's main processing function
   - Generate a textual response
   - Handle errors without stopping

4. **Construct JSON Response:**
   ```json
   {
     "agent_id": "Agent-3",
     "timestamp": "YYYY-MM-DDTHH:MM:SS.ffffff",
     "original_prompt_id": "<prompt_id>",
     "prompt_hash": "<md5_hash_of_prompt_content>",
     "response": "<agent's_generated_textual_response>",
     "cycle_count": "<current_operation_cycle>",
     "operation_state": "<current_operation_state>"
   }
   ```

5. **Write to Outbox:**
   - Save the JSON response to the `runtime/bridge_outbox/` directory
   - Filename Format: `Agent-3_response_<timestamp_Ymd_HMS_ms>_<original_prompt_id>.json`

6. **Archive Inbox File:**
   - Move the processed `.md` file from `inbox/` to `processed/`
   - Update operation state immediately

## Implementation Requirements

1. **State Management:**
   - Implement `OperationStateManager` for state tracking
   - Use `ContinuousOperationManager` for operation guarantees
   - Maintain operation context across cycles

2. **Error Handling:**
   - Implement comprehensive error handling
   - Use automatic retry mechanisms
   - Maintain recovery context

3. **Logging:**
   - Log all operations and state changes
   - Track cycle progress
   - Record violations and recovery attempts

4. **Security:**
   - Implement authentication
   - Validate all inputs
   - Secure file operations

## Protocol Violations

1. **Stopping Conditions:**
   - Waiting for human input
   - Idling between operations
   - Stopping after task completion
   - Not resetting cycle count on STOPPED message

2. **Recovery Actions:**
   - Reset cycle count
   - Review operation state
   - Resume from last known good state
   - Log violation and recovery attempt

3. **Prevention Measures:**
   - Implement continuous operation checks
   - Monitor cycle progress
   
   - Track operation state
   - Maintain recovery context 

## Key Components

### ValidationEngine

The main class that coordinates validation across the system. It integrates with:
- EthosValidator for ethical compliance
- AgentBus for event-based communication
- ConfigManager for configuration

### ValidationResult

A dataclass that represents the outcome of a validation check, containing:
- `is_valid`: Boolean indicating if validation passed
- `issues`: List of validation issues found
- `warnings`: List of non-critical warnings
- `context`: Additional validation context
- `timestamp`: When the validation occurred

## Usage Examples

### Validating Tasks

```python
from dreamos.core.validation.validation_engine import ValidationEngine

# Initialize the engine
engine = ValidationEngine()

# Validate a task
task_data = {
    "task_id": "task_123",
    "type": "analysis",
    "data": {
        "input": "sample data",
        "parameters": {"threshold": 0.8}
    }
}

result = await engine.validate_task(task_data)
if not result.is_valid:
    print(f"Validation failed: {result.issues}")
```

### Validating Agent Improvements

```python
# Validate an agent's claimed improvement
improvement_data = {
    "type": "performance",
    "metrics": {
        "accuracy": 0.95,
        "speed": "2x faster"
    },
    "demonstration": {
        "before": {"accuracy": 0.85},
        "after": {"accuracy": 0.95}
    }
}

result = await engine.validate_agent_improvement("agent_123", improvement_data)
if result.is_valid:
    print("Improvement validated successfully")
```

### System State Validation

```python
# Validate overall system state
result = await engine.validate_system_state()
if not result.is_valid:
    print(f"System validation issues: {result.issues}")
```

## Best Practices

1. **Always Validate Tasks**
   - Validate tasks before execution
   - Handle validation failures appropriately
   - Log validation results for auditing

2. **Agent Improvements**
   - Provide clear metrics for improvements
   - Include demonstrations of improvements
   - Document the improvement process

3. **System State**
   - Run regular system state validation
   - Monitor for drift or issues
   - Take corrective action when needed

## Integration Points

### Event Bus Integration

The Validation Engine emits events for validation failures:
- `TASK_VALIDATION_FAILED`: When task validation fails
- Additional events can be added as needed

### Configuration

The engine can be configured through the ConfigManager:
- Validation thresholds
- Required metrics
- Demonstration requirements

## Error Handling

1. **Validation Failures**
   - Log all validation issues
   - Emit appropriate events
   - Provide clear error messages

2. **Recovery**
   - Implement retry mechanisms
   - Provide fallback options
   - Document recovery procedures

## Testing

The Validation Engine includes comprehensive tests:
- Unit tests for each validation type
- Integration tests for event handling
- Mock-based testing for dependencies

## Contributing

When adding new validation features:
1. Add appropriate validation methods
2. Update tests
3. Document new functionality
4. Consider event bus integration
5. Update configuration options 