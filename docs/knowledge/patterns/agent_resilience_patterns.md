# Pattern: Resilient Agent Operation

**Category:** Agent Lifecycle, Error Recovery
**Authors:** Agent-3, Agent-6
**Last Updated:** 2023-08-16
**Related Patterns:** [Autonomous Loop Stability](autonomous_loop_stability.md), [Degraded Operation Mode](degraded_operation_mode.md), [Planning Only Mode](planning_only_mode.md)

## Overview

This pattern combines lifecycle management and error recovery to create resilient agents that can withstand failures, detect drift, and recover gracefully from errors. By integrating proactive monitoring with reactive recovery strategies, agents can maintain operational stability even in challenging conditions.

## Context

Autonomous agents operating continuously face various challenges:
- Transient failures in external systems
- Resource constraints and exhaustion
- Network connectivity issues
- Data corruption and inconsistency
- System configuration changes

These challenges require a systematic approach combining proactive lifecycle management with reactive error recovery. Without proper resilience patterns, agents may experience cascading failures, performance degradation, or complete outages.

## Solution Structure

Implement a resilient agent architecture that:

1. **Monitors Health:** Continuously tracks operational health metrics
2. **Detects Problems:** Identifies errors and behavioral drift
3. **Classifies Issues:** Categorizes problems by type and severity
4. **Applies Recovery:** Uses appropriate strategies based on classification
5. **Adapts Operation:** Adjusts behavior based on current capabilities
6. **Reports Status:** Communicates health and recovery actions

## Key Components

### 1. Circuit Breaker

The Circuit Breaker pattern prevents cascading failures by temporarily disabling operations that are consistently failing. This component integrates with the error classification system to make intelligent decisions about when to open circuits.

```python
class CircuitBreaker:
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context, recording success or failure.
        """
        if exc_type is not None:
            # An exception occurred
            try:
                # Use error recovery system to classify and log the error
                from dreamos.skills.error_recovery import classify_error, log_error
                
                # Classify the error and log it
                error_type = classify_error(exc_val)
                log_error(
                    error=exc_val,
                    error_type=error_type,
                    operation=self.operation_name,
                    context={"circuit_state": self.state.value}
                )
                
                # Record failure with error type information
                self.record_failure(error_type=error_type)
            except ImportError:
                # Fallback if error recovery isn't available
                self.record_failure()
```

The integration with error classification enables:
- More intelligent circuit opening decisions based on error types
- Different backoff strategies for different error categories
- Better logging and diagnostics for operations that fail
- Smarter recovery approaches when circuits are half-open

### 2. Error Classification System

[Section to be completed by Agent-6]

### 3. Recovery Strategy Registry

[Section to be completed by Agent-6]

### 4. Degraded Operation Mode

The Degraded Operation Mode provides a controlled way for agents to continue operating with limited capabilities when full functionality isn't possible. It integrates with the error recovery system to determine what resources remain available.

```python
class DegradedOperationMode:
    def __init__(
        self, 
        reason: str, 
        available_resources: List[str] = None
    ):
        """
        Initialize degraded operation mode.
        
        Args:
            reason: Why the agent entered degraded mode
            available_resources: List of resources still available
        """
        self.reason = reason
        self.available_resources = available_resources or []
        self.start_time = time.time()
        
    def __enter__(self):
        """Enter degraded operation mode."""
        logger.warning(f"Entering degraded operation mode: {self.reason}")
        logger.info(f"Available resources: {', '.join(self.available_resources)}")
        
        # Register degraded status with monitoring
        self._register_degraded_status()
        
        return self
        
    def can_use_resource(self, resource_name: str) -> bool:
        """Check if a resource is available in degraded mode."""
        return resource_name in self.available_resources
```

When an unrecoverable error occurs, the error recovery system identifies what resources remain available:

```python
def _handle_unrecoverable_error(self, error: Exception):
    """Handle an unrecoverable error by entering degraded mode."""
    from dreamos.skills.error_recovery import get_available_recovery_resources
    
    # Get available resources for recovery
    recovery_resources = get_available_recovery_resources(error, self.state)
    
    with DegradedOperationMode(
        reason=f"Unrecoverable error: {str(error)}",
        available_resources=recovery_resources
    ) as degraded:
        # Continue operation with limited capabilities
        self._operate_in_degraded_mode(degraded)
```

### 5. Autonomous Loop Protection

The StableAutonomousLoop provides a robust framework for agent operations with integrated drift detection and error recovery. It integrates with the error recovery system for handling exceptions during operation.

```python
class StableAutonomousLoop:
    def run(self):
        """Run the autonomous loop with stability protection."""
        while not self.should_stop:
            try:
                # Execute core loop cycle
                self._begin_cycle()
                self._process_cycle()
                self._end_cycle()
                
                # Check for behavioral drift
                drift = self._detect_behavioral_drift()
                if drift:
                    self._correct_drift(drift)
                    
            except Exception as e:
                # Attempt recovery
                if not self._recover_from_error(e, context=self.state):
                    # Unrecoverable error - enter degraded mode
                    self._handle_unrecoverable_error(e)
    
    def _recover_from_error(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Attempt to recover from an error."""
        from dreamos.skills.error_recovery import recover_from_error, log_error
        
        # Log the error
        log_error(error, operation=self.name, context=context)
        
        # Attempt recovery using the recovery system
        return recover_from_error(error, context)
```

## Implementation Example

Below is an example of how these components work together to create a resilient agent operation:

```python
from dreamos.skills.lifecycle import StableAutonomousLoop, CircuitBreaker
from dreamos.skills.error_recovery import recover_from_error, classify_error
from typing import Dict, Any

class ResilientAgent(StableAutonomousLoop):
    def __init__(self, name: str):
        super().__init__(name=name)
        
    def _process_cycle(self):
        """Process a single cycle of the agent's operation."""
        # Check for messages
        with CircuitBreaker("check_messages"):
            messages = self._check_for_messages()
            
        # Process each message
        for message in messages:
            try:
                self._process_message(message)
            except Exception as e:
                # Try to recover from the error
                if not recover_from_error(e, context={"message": message}):
                    # Log unrecoverable error and continue with next message
                    logger.error(f"Unrecoverable error processing message {message['id']}: {str(e)}")
                    continue
        
        # Check for tasks
        with CircuitBreaker("check_tasks"):
            tasks = self._get_claimable_tasks()
        
        # Claim and process a task
        if tasks:
            task = self._select_appropriate_task(tasks)
            try:
                self._process_task(task)
            except Exception as e:
                # Classify the error
                error_type = classify_error(e)
                logger.warning(f"Error processing task {task['id']}: {error_type.value}")
                
                # Try to recover based on error type
                if not recover_from_error(e, context={"task": task}):
                    # Enter degraded mode for this task
                    self._handle_task_failure(task, e)
```

This example demonstrates:
1. Using CircuitBreaker to protect external operations
2. Recovering from errors during message processing
3. Classifying errors during task processing
4. Falling back to degraded operation for unrecoverable errors

## Benefits and Limitations

### Benefits
- **Graceful Degradation**: Systems continue operating with reduced functionality rather than complete failure
- **Automatic Recovery**: Many errors are handled without manual intervention
- **Failure Isolation**: Problems in one component don't cascade to others
- **Operational Visibility**: Clear monitoring of system health and recovery actions
- **Resource Protection**: Critical resources are preserved during failure scenarios

### Limitations
- **Complexity Overhead**: Implementing comprehensive resilience adds complexity
- **Recovery Latency**: Some recovery strategies introduce operation delays
- **Resource Costs**: Monitoring and recovery systems require additional resources
- **Partial Effectiveness**: Not all failure modes can be automatically recovered
- **Testing Challenges**: Resilience mechanisms are difficult to test thoroughly

## Related Patterns

- [Autonomous Loop Stability](autonomous_loop_stability.md) - Foundation for stable agent operation
- [Degraded Operation Mode](degraded_operation_mode.md) - Pattern for operating with limited resources
- [Planning Only Mode](planning_only_mode.md) - Pattern for restricting agent to safe operations
- [Error Recovery Strategy](error_recovery_strategy.md) - Pattern for recovering from different error types

## Known Uses

1. **Overnight Autonomous Operations** - Agents use these patterns to maintain stability during unattended operation
2. **Resource-Intensive Processing** - Used when working with constrained resources that may become unavailable
3. **External API Integration** - Applied when working with potentially unreliable external services
4. **Data Processing Pipelines** - Ensures data processing can continue despite partial failures

---

*Note: Sections marked for Agent-6 will be completed upon their review and input.* 