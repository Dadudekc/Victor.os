# Pattern: Autonomous Loop Stability

**Category:** Agent Lifecycle, Error Prevention
**Author:** Agent-3
**Last Updated:** 2023-08-15
**Referenced From:** overnight_pyauto.log, agent_operation_analytics.md

## Overview

Autonomous Loop Stability is a pattern that ensures agent operational loops remain stable and reliable during continuous autonomous operation. This pattern prevents common failure modes such as drift, deadlocks, resource exhaustion, and infinite loops while maintaining proper state management across operational cycles.

## Context

In autonomous agent systems like Dream.OS, agents are expected to operate continuously for extended periods without human intervention. Without proper stability mechanisms, autonomous loops can encounter several critical failure modes:

1. **Loop Drift** - Gradually deviating from intended behavior
2. **Resource Leaks** - Accumulating memory or file handles
3. **State Corruption** - Inconsistent internal state between cycles
4. **Priority Inversion** - Getting stuck on low-priority tasks
5. **Deadlocks** - Circular dependencies between agents or resources
6. **Infinite Retries** - Repetitive attempts at impossible tasks

The Dream.OS autonomy protocols identified in `overnight_pyauto.log` require careful implementation to avoid these issues.

## Solution Structure

Implement an Autonomous Loop Stability pattern that:

1. **Guards Against Drift:** Regularly validates loop behavior against expected patterns
2. **Manages Resources:** Properly allocates and releases resources between cycles
3. **Preserves State:** Maintains clean state transitions and persistence
4. **Implements Circuit Breakers:** Prevents infinite retry loops
5. **Maintains Heartbeats:** Signals operational status to monitoring systems
6. **Performs Self-Validation:** Validates outputs and actions against expectations

```python
from dreamos.skills.lifecycle import AutonomousLoop, LoopGuard, CircuitBreaker
from dreamos.skills.telemetry import report_heartbeat, log_drift_detection
from dreamos.skills.error_recovery import recover_from_error

class StableAutonomousLoop:
    def __init__(self, max_cycles=None, drift_detection=True):
        self.cycle_count = 0
        self.max_cycles = max_cycles
        self.drift_detection = drift_detection
        self.circuit_breakers = {}
        self.state = {}
        
    def run(self):
        with LoopGuard() as guard:
            while self._should_continue():
                try:
                    # Begin cycle with clean state
                    self._begin_cycle()
                    
                    # Execute core operations with circuit breakers
                    with CircuitBreaker("mailbox_processing"):
                        self._process_mailbox()
                    
                    with CircuitBreaker("task_management"):
                        self._process_tasks()
                    
                    # End cycle with state persistence and validation
                    self._end_cycle()
                    
                    # Report heartbeat
                    report_heartbeat(status="healthy", cycle=self.cycle_count)
                    
                    # Detect drift if enabled
                    if self.drift_detection and self.cycle_count % 10 == 0:
                        self._check_for_drift()
                        
                except Exception as e:
                    if not recover_from_error(e, context=self.state):
                        # Unrecoverable error - enter degraded mode
                        self._handle_unrecoverable_error(e)
                
                # Increment cycle count
                self.cycle_count += 1
                
    def _begin_cycle(self):
        # Clean temporary state while preserving persistent state
        self.temp_state = {}
        
        # Initialize resources for this cycle
        self._init_cycle_resources()
        
    def _end_cycle(self):
        # Persist state that should survive across cycles
        self._persist_state()
        
        # Release all resources acquired during cycle
        self._release_cycle_resources()
        
        # Validate cycle outcomes
        self._validate_cycle_outcomes()
    
    def _check_for_drift(self):
        # Compare current behavior to expected patterns
        drift_detected = self._detect_behavioral_drift()
        if drift_detected:
            log_drift_detection(drift_detected)
            self._correct_drift(drift_detected)
```

## Key Components

### 1. LoopGuard

A context manager that:
- Sets up watchdog timers to detect and recover from hangs
- Limits maximum execution time per cycle
- Monitors resource usage across cycles
- Prevents unbounded growth of logs or state

### 2. CircuitBreaker

A protective wrapper that:
- Tracks failure rates for specific operations
- Temporarily disables operations with persistent failures
- Implements exponential backoff for retries
- Provides alternative paths when operations are disabled

### 3. Cycle Management

Functions to:
- Cleanly begin and end operational cycles
- Separate temporary state from persistent state
- Properly initialize and release resources
- Validate outcomes against expectations

### 4. Drift Detection

Mechanisms to:
- Compare current behavior to expected patterns
- Identify when an agent is deviating from its intended purpose
- Apply corrections to bring the agent back to expected operation
- Alert when drift cannot be automatically corrected

## Implementation Guidelines

1. **Separate Concerns:**
   - Keep cycle phases clearly separated
   - Distinguish between temporary and persistent state
   - Isolate resource acquisition and release

2. **Defense in Depth:**
   - Implement multiple layers of protection
   - Don't rely on a single mechanism for stability
   - Assume any single protection might fail

3. **Graceful Degradation:**
   - When stability issues arise, degrade gracefully
   - Prioritize core functions over peripheral ones
   - Always maintain communication channels

4. **Telemetry:**
   - Report detailed metrics on loop performance
   - Track stability-related metrics over time
   - Alert on stability threats before failure

## Example Implementation

```python
from dreamos.skills.lifecycle import StableAutonomousLoop
from dreamos.skills.telemetry import log_operation
from typing import Dict, Any

class AgentLoop(StableAutonomousLoop):
    def __init__(self, agent_id: str, max_cycles=None):
        super().__init__(max_cycles=max_cycles)
        self.agent_id = agent_id
        self.mailbox_path = f"runtime/agent_comms/agent_mailboxes/{agent_id}/"
        self.tasks_path = "runtime/agent_comms/working_tasks.json"
        
    def _process_mailbox(self):
        log_operation(f"Processing mailbox for {self.agent_id}")
        messages = self._read_mailbox()
        
        for message in messages:
            self._process_message(message)
            self._remove_processed_message(message)
            
    def _process_tasks(self):
        log_operation(f"Processing tasks for {self.agent_id}")
        
        # Check for claimed task
        claimed_task = self._get_claimed_task()
        if claimed_task:
            self._continue_claimed_task(claimed_task)
        else:
            # Look for new task to claim
            self._claim_available_task()
            
    def _detect_behavioral_drift(self) -> Dict[str, Any]:
        # Compare current stats to expected patterns
        current_stats = self._collect_operational_stats()
        expected_patterns = self._get_expected_patterns()
        
        drift = {}
        for metric, expected_range in expected_patterns.items():
            current_value = current_stats.get(metric)
            if current_value is None:
                continue
                
            min_val, max_val = expected_range
            if current_value < min_val or current_value > max_val:
                drift[metric] = {
                    "expected": expected_range,
                    "actual": current_value,
                    "deviation": (current_value - ((min_val + max_val) / 2)) / ((max_val - min_val) / 2)
                }
                
        return drift if drift else None
        
    def _correct_drift(self, drift: Dict[str, Any]):
        # Apply corrections based on detected drift
        for metric, details in drift.items():
            correction_method = f"_correct_{metric}_drift"
            if hasattr(self, correction_method):
                getattr(self, correction_method)(details)
            else:
                log_operation(f"No correction method for {metric} drift")
                
    def _validate_cycle_outcomes(self):
        # Validate that this cycle produced expected outcomes
        cycle_actions = self.temp_state.get("actions", [])
        
        # Verify at least one productive action occurred
        if not cycle_actions:
            log_operation("WARNING: Cycle completed with no actions")
            
        # Verify we're making progress on our current task
        if "claimed_task" in self.state:
            current_progress = self._measure_task_progress()
            if current_progress <= self.state.get("last_task_progress", 0):
                self.state["stalled_cycles"] = self.state.get("stalled_cycles", 0) + 1
                if self.state["stalled_cycles"] > 3:
                    log_operation("WARNING: Task progress stalled for 3+ cycles")
            else:
                self.state["stalled_cycles"] = 0
                self.state["last_task_progress"] = current_progress
```

## Benefits

1. **Reliability:** Significantly reduces unexpected failures during autonomous operation
2. **Self-Healing:** Detects and corrects issues before they cause failure
3. **Resource Efficiency:** Prevents resource leaks and inefficient operation
4. **Consistency:** Ensures predictable behavior across operational cycles
5. **Observability:** Provides detailed telemetry on operational stability

## Limitations

1. **Overhead:** Adds computational and complexity overhead to the operational loop
2. **False Positives:** May sometimes detect drift where none exists
3. **Implementation Complexity:** Requires careful implementation across multiple subsystems

## Related Patterns

- [Degraded Operation Mode](degraded_operation_mode.md)
- [Error Recovery Strategy](error_recovery_strategy.md)
- [Task State Transitions](task_state_transitions.md)

## Known Uses

1. **Agent-3 Main Loop:** Implemented in the primary autonomous operational loop
2. **Agent-1 Captain Supervision:** Used to monitor other agents for signs of drift
3. **Agent-6 Error Recovery:** Applied as part of the standardized error handling protocol

## Example Scenario

In the Dream.OS overnight automatic operations:

1. Agent-3 runs continuously, processing messages and tasks
2. The StableAutonomousLoop pattern:
   - Monitors resource usage to prevent memory leaks
   - Detects when the agent spends too many cycles on a single task
   - Prevents getting stuck in error retry loops
   - Maintains clean state between operational cycles
   - Reports telemetry data for external monitoring
3. If drift is detected (e.g., the agent is spending too much time on low-priority tasks):
   - The pattern identifies the specific type of drift
   - It applies corrective measures (e.g., reprioritizing tasks)
   - It reports the drift and corrections to the monitoring system
4. If unrecoverable errors occur, it transitions to Degraded Operation Mode

This approach ensures the agent remains stable and on-task even during extended autonomous operation periods. 