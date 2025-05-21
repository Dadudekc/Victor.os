# Pattern: Degraded Operation Mode

**Category:** Error Recovery, Autonomous Operation
**Author:** Agent-3
**Last Updated:** 2023-08-14
**Referenced From:** meta_analysis_protocol_adherence_YYYYMMDD.md

## Overview

Degraded Operation Mode is a pattern that allows agents to continue functioning in a limited capacity when normal operations are blocked or impaired. This pattern prevents agents from halting completely when faced with persistent failures, ensuring continuous operation even under suboptimal conditions.

## Context

In autonomous agent systems, tool failures, missing dependencies, or other blockers can prevent an agent from executing its primary tasks. Without a fallback mechanism, agents tend to halt or get stuck in retry loops, leading to system-wide inefficiencies.

The `meta_analysis_protocol_adherence_YYYYMMDD.md` report identified premature halting under failure as a significant issue in the Dream.OS system, particularly when agents faced persistent tool failures.

## Solution Structure

Implement a Degraded Operation Mode that:

1. **Detects Persistent Failures:** Identifies when primary operations repeatedly fail
2. **Provides Alternative Actions:** Offers a menu of alternative action types
3. **Maintains Productivity:** Ensures the agent remains productive despite limitations
4. **Prioritizes Recovery:** Works toward resolving the blockers when possible

```python
from dreamos.skills.lifecycle import DegradedOperationMode, AlternativeActions
from dreamos.skills.error_recovery import classify_error, is_persistent

def agent_operational_loop():
    # Normal operation attempts
    try:
        execute_primary_tasks()
    except Exception as e:
        if is_persistent(e):
            # Enter degraded operation mode
            with DegradedOperationMode() as degraded:
                # Try alternative action types in sequence
                for action_type in degraded.get_alternative_actions():
                    try:
                        action_type.execute()
                        if action_type.was_successful():
                            break  # Exit degraded mode if an action succeeds
                    except Exception as inner_e:
                        # Log but continue to next action type
                        log_degraded_action_failure(inner_e)
```

## Key Components

### 1. DegradedOperationMode Class

A context manager that:
- Tracks which action types have been attempted
- Provides a prioritized list of alternative actions
- Collects telemetry on degraded mode operation
- Ensures all action types are tried before halting

### 2. AlternativeActions Registry

A collection of fallback action types, including:
- **Documentation:** Create/update documentation about the blocker
- **Analysis:** Perform meta-analysis of failure patterns
- **Diagnostics:** Run self-diagnostic routines
- **Tool Self-Test:** Test tools with simple inputs to isolate issues
- **Cleanup:** Perform cleanup of temporary files or state
- **Planning:** Work on planning or design tasks that don't require blocked tools

### 3. Recovery Mechanism

Components to help escape degraded mode:
- Record detailed diagnostics during degraded operation
- Create tasks for resolving blockers
- Periodically retry normal operation

## Implementation Guidelines

1. **Prioritize Action Types:**
   - Order alternative actions from most to least productive
   - Consider resource requirements when sequencing

2. **Avoid Action Type Loops:**
   - Track which action types have been attempted
   - Don't repeat failed action types without changes

3. **Report Degraded Status:**
   - Provide clear telemetry when in degraded mode
   - Document the blockers preventing normal operation

4. **Exit Criteria:**
   - Define clear conditions for exiting degraded mode
   - Only halt when all action types have been exhausted

## Example Implementation

```python
from dreamos.skills.lifecycle import DegradedOperationMode
from dreamos.skills.telemetry import log_operation_mode
from typing import List, Callable

class AlternativeActionType:
    def __init__(self, name: str, action_fn: Callable, prerequisites: List[str] = None):
        self.name = name
        self.action_fn = action_fn
        self.prerequisites = prerequisites or []
        self.success = False
        
    def can_execute(self, available_resources: List[str]) -> bool:
        return all(prereq in available_resources for prereq in self.prerequisites)
        
    def execute(self, context: dict = None) -> bool:
        try:
            self.success = self.action_fn(context or {})
            return self.success
        except Exception as e:
            log_operation_mode(f"Failed to execute {self.name}: {str(e)}")
            self.success = False
            return False
            
    def was_successful(self) -> bool:
        return self.success

def execute_with_degraded_mode_fallback(primary_action, context=None):
    try:
        # Try primary action first
        return primary_action(context or {})
    except Exception as e:
        log_operation_mode(f"Primary action failed: {str(e)}")
        
        # Enter degraded mode with fallbacks
        with DegradedOperationMode() as degraded:
            # Get available resources
            available_resources = degraded.get_available_resources()
            
            # Try each alternative action type
            for action_type in degraded.get_alternative_actions():
                if action_type.can_execute(available_resources):
                    if action_type.execute(context):
                        log_operation_mode(f"Successfully executed alternative action: {action_type.name}")
                        return True
            
            # If we reach here, all alternatives failed
            log_operation_mode("All alternative actions failed or were unavailable")
            return False
```

## Benefits

1. **Continuous Operation:** Agents remain productive despite blockers
2. **Graceful Degradation:** System performance degrades gracefully rather than failing
3. **Self-Healing:** Alternative actions can work toward resolving blockers
4. **Efficiency:** Avoids wasting resources on continuous retries of failing operations

## Limitations

1. **Complexity:** Adds complexity to the operational loop
2. **Resource Overhead:** Requires tracking and managing alternative action types
3. **Potential Starvation:** Critical tasks might be delayed during extended degraded operation

## Related Patterns

- [Error Recovery Strategy](error_recovery_strategy.md)
- [Autonomous Loop Stability](autonomous_loop_stability.md)
- [Tool Failure Pivot](tool_failure_pivot.md)

## Known Uses

1. **Agent-3 Autonomous Loop:** Implemented in the core operational loop to prevent halting during file access issues
2. **Agent-6 Error Recovery:** Used as part of the standardized error handling protocol
3. **Agent-8 Testing Framework:** Applied to test runners to continue testing when some tests fail

## Example Scenario

When an agent encounters persistent timeouts trying to access a task board file:

1. It first attempts standard error recovery (retries with backoff)
2. If failures persist, it enters Degraded Operation Mode
3. In this mode, it:
   - Creates documentation about the blocker
   - Performs meta-analysis on the error patterns
   - Attempts to work with local cached copies if available
   - Creates a task for another agent to investigate the file issue
4. It continues operation in other areas, avoiding the problematic file
5. Periodically, it briefly attempts to access the file again to check if the issue is resolved

This approach ensures the agent remains productive despite the persistent file access issue. 