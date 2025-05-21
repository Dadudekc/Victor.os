# Dream.OS Agent Lifecycle Library

The lifecycle library provides essential utilities for managing agent lifecycle and ensuring stable, reliable operation of autonomous agent loops in the Dream.OS system.

## Key Components

### 1. StableAutonomousLoop

The `StableAutonomousLoop` class implements the [Autonomous Loop Stability](../../../docs/knowledge/patterns/autonomous_loop_stability.md) pattern, providing a robust framework for creating autonomous agent loops that are resistant to common failure modes:

```python
from dreamos.skills.lifecycle import StableAutonomousLoop

class MyAgentLoop(StableAutonomousLoop):
    def __init__(self, agent_id):
        super().__init__(name=f"agent-{agent_id}-loop")
        self.agent_id = agent_id
        
    def _process_operations(self):
        # Custom implementation of core operations
        self.process_mailbox()
        self.process_tasks()
        
    # Override other methods as needed

# Usage
loop = MyAgentLoop(agent_id="agent-3")
loop.run()
```

### 2. DegradedOperationMode

The `DegradedOperationMode` context manager implements the [Degraded Operation Mode](../../../docs/knowledge/patterns/degraded_operation_mode.md) pattern, allowing agents to continue functioning in a limited capacity when normal operations are blocked or impaired:

```python
from dreamos.skills.lifecycle import DegradedOperationMode, AlternativeActions
from dreamos.skills.lifecycle.degraded_mode import ActionCategory

# Register a custom alternative action
def my_custom_action(context):
    # Implementation
    return True

AlternativeActions.register(
    AlternativeAction(
        name="my_custom_action",
        category=ActionCategory.PLANNING,
        action_fn=my_custom_action,
        prerequisites=["file_system"],
        description="Custom planning action"
    )
)

# Usage
with DegradedOperationMode(
    reason="File system error",
    available_resources=["file_system", "network"]
) as degraded:
    for action in degraded.get_alternative_actions():
        try:
            success = action.execute(context={"error": error})
            degraded.record_action_attempt(action, success)
        except Exception as e:
            logger.error(f"Failed to execute {action.name}: {e}")
```

### 3. CircuitBreaker

The `CircuitBreaker` class implements the Circuit Breaker pattern to protect operations that might fail, preventing cascading failures:

```python
from dreamos.skills.lifecycle import CircuitBreaker

# Usage
try:
    with CircuitBreaker("file_operation") as breaker:
        # Operation that might fail
        result = perform_risky_operation()
        
except RuntimeError as e:
    # Circuit is open, use alternative approach
    result = perform_alternative_operation()
```

### 4. LoopGuard

The `LoopGuard` context manager protects autonomous loops from common failure modes such as hangs, resource exhaustion, and unbounded growth:

```python
from dreamos.skills.lifecycle import LoopGuard

# Usage
with LoopGuard(
    timeout=60,
    memory_limit_mb=1000,
    on_timeout=handle_timeout_callback
) as guard:
    # Loop operations here
    while condition:
        # ...cycle operations...
        guard.reset_watchdog()  # Reset watchdog timer
        guard.log("Completed cycle", "INFO")
```

## Best Practices

1. **Extend StableAutonomousLoop**: For agent operational loops, extend the `StableAutonomousLoop` class rather than implementing loops from scratch.

2. **Use Circuit Breakers for External Operations**: Wrap all operations that interact with external systems (file system, network, etc.) in `CircuitBreaker` contexts.

3. **Implement Drift Detection**: Override `_detect_behavioral_drift()` and `_correct_drift()` methods in your `StableAutonomousLoop` subclass to detect and correct agent drift.

4. **Register Alternative Actions**: Register custom alternative actions for your agent's specific degraded operation capabilities.

5. **Maintain Clean State**: Clearly separate temporary cycle state from persistent state that should survive across cycles.

## Integration with Other Libraries

- **Error Recovery**: Works with `dreamos.skills.error_recovery` to handle and recover from errors.
- **Telemetry**: Reports agent status and metrics through the `dreamos.skills.telemetry` system.
- **Task Management**: Integrates with `dreamos.skills.tasks` for stable task processing.

## Example: Agent Operational Loop

```python
from dreamos.skills.lifecycle import StableAutonomousLoop, CircuitBreaker

class AgentOperationalLoop(StableAutonomousLoop):
    def __init__(self, agent_id):
        super().__init__(name=f"agent-{agent_id}")
        self.agent_id = agent_id
        self.mailbox_path = f"runtime/agent_comms/agent_mailboxes/{agent_id}/"
        
    def _process_operations(self):
        with CircuitBreaker("mailbox_processing"):
            self._process_mailbox()
            
        with CircuitBreaker("task_management"):
            self._process_tasks()
            
    def _process_mailbox(self):
        # Implementation
        self.register_action("process_mailbox")
        
    def _process_tasks(self):
        # Implementation
        self.register_action("process_tasks")
        
    def _detect_behavioral_drift(self):
        # Simple drift detection based on cycle timing
        if len(self.cycle_durations) >= 10:
            avg_duration = sum(self.cycle_durations) / len(self.cycle_durations)
            last_duration = self.cycle_durations[-1]
            
            if last_duration > avg_duration * 2:
                return {
                    "cycle_duration": {
                        "expected": avg_duration,
                        "actual": last_duration,
                        "deviation": last_duration / avg_duration
                    }
                }
        return None
```

## Contributing

When adding to this library:

1. Document all public APIs with docstrings
2. Include example usage in docstrings
3. Update test cases for new functionality
4. Keep classes focused on single responsibilities 