# Troubleshooting Guide: Agent Drift Issues

**Category:** Agent Lifecycle, Operational Stability
**Author:** Agent-3
**Last Updated:** 2023-08-15
**Related Patterns:** [Autonomous Loop Stability](../patterns/autonomous_loop_stability.md), [Degraded Operation Mode](../patterns/degraded_operation_mode.md)

## Overview

Agent drift occurs when an autonomous agent gradually deviates from its intended behavior or purpose over time. This guide helps identify, diagnose, and correct different types of agent drift to maintain operational stability.

## Types of Agent Drift

### 1. Priority Drift

**Symptoms:**
- Agent spending excessive time on low-priority tasks
- Critical tasks consistently delayed or ignored
- Task completion times steadily increasing

**Causes:**
- Insufficient priority validation in task selection
- Attractive distractions in non-essential tasks
- Missing timeout mechanisms on long-running operations

**Diagnostic Tools:**
```python
from dreamos.skills.analytics import TaskPriorityAnalyzer

# Analyze task distribution by priority
analyzer = TaskPriorityAnalyzer(agent_id="agent-3")
drift_report = analyzer.analyze_priority_distribution(days=7)
print(f"Priority drift index: {drift_report.drift_index}")
```

### 2. Scope Drift

**Symptoms:**
- Agent taking on tasks outside its expertise area
- Increased error rates in certain task categories
- Task claiming patterns expanding beyond defined boundaries

**Causes:**
- Overly broad task selection criteria
- Inadequate task skill requirements definition
- Missing expertise validation in task claiming

**Diagnostic Tools:**
```python
from dreamos.skills.analytics import AgentScopeAnalyzer

# Analyze task type distribution
analyzer = AgentScopeAnalyzer(agent_id="agent-3")
scope_report = analyzer.analyze_expertise_match(days=7)
print(f"Out-of-scope task percentage: {scope_report.out_of_scope_percent}%")
```

### 3. Resource Drift

**Symptoms:**
- Steadily increasing memory usage
- Growing cycle execution times
- Escalating disk or network usage

**Causes:**
- Resource leaks in agent operations
- Missing cleanup operations
- Accumulating temporary files or state

**Diagnostic Tools:**
```python
from dreamos.skills.lifecycle import ResourceUsageAnalyzer

# Analyze resource usage trends
analyzer = ResourceUsageAnalyzer(agent_id="agent-3")
resource_report = analyzer.analyze_trends(days=7)
print(f"Memory growth rate: {resource_report.memory_growth_rate_per_day}MB/day")
```

### 4. Focus Drift

**Symptoms:**
- Agent rapidly switching between unrelated tasks
- Low completion rate despite high activity
- Many tasks in partial completion state

**Causes:**
- Insufficient task stickiness mechanisms
- Overactive task reprioritization
- Missing partial progress persistence

**Diagnostic Tools:**
```python
from dreamos.skills.analytics import TaskCompletionAnalyzer

# Analyze task switching behavior
analyzer = TaskCompletionAnalyzer(agent_id="agent-3")
focus_report = analyzer.analyze_task_switching(days=7)
print(f"Task switching frequency: {focus_report.switches_per_hour}/hour")
```

### 5. Output Drift

**Symptoms:**
- Declining quality in agent outputs
- Increasing inconsistency in formatting or style
- Growing deviation from expected response patterns

**Causes:**
- Missing output validation
- Accumulating small errors in templates
- Gradual adaptation to unexpected inputs

**Diagnostic Tools:**
```python
from dreamos.skills.analytics import OutputConsistencyAnalyzer

# Analyze output consistency
analyzer = OutputConsistencyAnalyzer(agent_id="agent-3")
output_report = analyzer.analyze_consistency(days=7)
print(f"Output consistency score: {output_report.consistency_score}/100")
```

## Drift Detection and Correction

### Detecting Drift Automatically

```python
from dreamos.skills.lifecycle import StableAutonomousLoop
from typing import Dict, Any, Optional

class AgentLoop(StableAutonomousLoop):
    def _detect_behavioral_drift(self) -> Optional[Dict[str, Any]]:
        """Detect behavioral drift in the agent operation."""
        drift_indicators = {}
        
        # Check for priority drift
        if self._detect_priority_drift():
            drift_indicators["priority_drift"] = {
                "severity": "medium",
                "details": self._get_priority_metrics()
            }
            
        # Check for resource drift
        resource_drift = self._detect_resource_drift()
        if resource_drift:
            drift_indicators["resource_drift"] = {
                "severity": "high",
                "details": resource_drift
            }
            
        # Return drift indicators if any found
        return drift_indicators if drift_indicators else None
        
    def _correct_drift(self, drift: Dict[str, Any]):
        """Apply corrections for detected drift."""
        if "priority_drift" in drift:
            self._correct_priority_drift(drift["priority_drift"])
            
        if "resource_drift" in drift:
            self._correct_resource_drift(drift["resource_drift"])
```

### Manual Drift Analysis

For periodic manual review, use the following checklist:

1. **Task Distribution Review**
   - Review the past week's tasks by priority and type
   - Compare against the agent's defined role and expertise
   - Look for gradual shifts in task category distribution

2. **Resource Usage Analysis**
   - Check memory usage trends over time
   - Monitor cycle execution time growth
   - Inspect temporary storage usage patterns

3. **Output Quality Assessment**
   - Sample outputs from different periods
   - Compare against quality benchmarks
   - Look for subtle formatting or style changes

## Common Drift Scenarios and Solutions

### Scenario 1: Priority Inversion

**Symptoms:**
- Agent consistently working on low-priority tasks while high-priority tasks wait
- Delay in addressing critical issues
- System-wide impact due to bottlenecks

**Solution:**
```python
# Reset priority weights and thresholds
agent_context.set_config("priority_weights", {
    "critical": 100,  # Increased weight for critical tasks
    "high": 50,
    "medium": 20,
    "low": 5
})

# Enforce priority timeout scaling
agent_context.set_config("max_task_time_by_priority", {
    "low": 600,        # 10 minutes
    "medium": 1800,    # 30 minutes
    "high": 3600,      # 1 hour
    "critical": 7200   # 2 hours (but will be worked on immediately)
})

# Enable strict priority enforcement
agent_context.set_config("enforce_strict_priority", True)
```

### Scenario 2: Memory Leak

**Symptoms:**
- Steadily increasing memory usage
- Slower response times over prolonged operation
- Eventually reaching resource limits and crashing

**Solution:**
```python
# Implement cycle cleanup
def _end_cycle(self):
    # Clean up any temporary resources
    self._clear_temp_cache()
    
    # Reset non-persistent state
    self.temp_state = {}
    
    # Run garbage collection explicitly
    import gc
    gc.collect()
    
    # Log memory usage for tracking
    self._log_memory_usage()
```

### Scenario 3: Expertise Boundary Violation

**Symptoms:**
- Agent attempting tasks requiring skills it doesn't have
- Increased error rates and invalid outputs
- Task completion time growing for out-of-expertise tasks

**Solution:**
```python
# Implement expertise validation for task claiming
def _can_claim_task(self, task):
    # Get agent expertise
    agent_expertise = set(self.get_state("expertise", []))
    
    # Get task required expertise
    task_required_expertise = set(task.get("required_expertise", []))
    
    # If task requires expertise the agent doesn't have, reject it
    missing_expertise = task_required_expertise - agent_expertise
    if missing_expertise:
        logger.info(f"Rejecting task {task['id']} due to missing expertise: {missing_expertise}")
        return False
        
    return True
```

### Scenario 4: Cycle Time Growth

**Symptoms:**
- Agent cycles taking longer to complete
- Decline in tasks completed per hour
- Growing backlog despite active agent

**Solution:**
```python
# Implement cycle time monitoring and correction
def _validate_cycle_outcomes(self):
    """Validate cycle outcomes and correct drift."""
    # Track cycle duration
    current_duration = time.time() - self.last_cycle_start
    self.cycle_durations.append(current_duration)
    
    # Keep limited history
    if len(self.cycle_durations) > 100:
        self.cycle_durations = self.cycle_durations[-100:]
    
    # Check for cycle time growth
    if len(self.cycle_durations) >= 20:
        recent_avg = sum(self.cycle_durations[-10:]) / 10
        older_avg = sum(self.cycle_durations[-20:-10]) / 10
        
        # If recent cycles are over 50% slower, take corrective action
        if recent_avg > older_avg * 1.5:
            logger.warning(f"Cycle time growing: {older_avg:.2f}s -> {recent_avg:.2f}s")
            self._correct_cycle_time_growth()
```

## Prevention Measures

Implement these practices to prevent drift before it occurs:

### 1. Regular Calibration

```python
def perform_calibration(agent_id):
    """Calibrate agent parameters against baseline."""
    # Load baseline parameters
    baseline = load_agent_baseline(agent_id)
    
    # Get current agent state
    current = get_agent_state(agent_id)
    
    # Correct any drifting parameters
    corrections = {}
    for param, baseline_value in baseline.items():
        current_value = current.get(param)
        if current_value is not None:
            drift = calculate_parameter_drift(current_value, baseline_value)
            if drift > DRIFT_THRESHOLD:
                corrections[param] = baseline_value
    
    # Apply corrections if needed
    if corrections:
        apply_parameter_corrections(agent_id, corrections)
        return True
        
    return False
```

### 2. Operational Boundaries

```python
class OperationalBoundary:
    def __init__(self, parameter, min_value, max_value, correction_fn=None):
        self.parameter = parameter
        self.min_value = min_value
        self.max_value = max_value
        self.correction_fn = correction_fn or self._default_correction
        
    def check(self, current_value):
        """Check if current value is within boundaries."""
        if current_value < self.min_value or current_value > self.max_value:
            return False
        return True
        
    def correct(self, current_value):
        """Correct value to be within boundaries."""
        return self.correction_fn(current_value, self.min_value, self.max_value)
        
    def _default_correction(self, current_value, min_value, max_value):
        """Default correction: clamp to boundaries."""
        return max(min_value, min(current_value, max_value))
```

### 3. Periodic Reset

For long-running agents, implement periodic reset points:

```python
def schedule_reset(agent_id, interval_hours=168):  # Default: weekly
    """Schedule periodic agent reset to prevent drift accumulation."""
    # Get current timestamp
    current_time = time.time()
    
    # Calculate next reset time
    next_reset = current_time + (interval_hours * 3600)
    
    # Schedule reset
    scheduler.schedule_task(
        task_id=f"reset_{agent_id}_{int(next_reset)}",
        task_type="maintenance",
        schedule_time=next_reset,
        parameters={
            "agent_id": agent_id,
            "action": "reset",
            "preserve_state": ["expertise", "long_term_memory"]
        }
    )
```

## Debugging Tools

The following tools can help diagnose and resolve drift issues:

### 1. Drift Inspector

A command-line tool to analyze drift in an agent's operation:

```bash
python -m dreamos.tools.drift_inspector --agent-id agent-3 --days 7
```

This will generate a comprehensive drift report with:
- Priority distribution graphs
- Resource usage trends
- Task completion statistics
- Cycle time analysis
- Drift indicators with severity ratings

### 2. Operational Snapshot

Generate point-in-time snapshots for comparison:

```python
from dreamos.tools.snapshots import create_snapshot, compare_snapshots

# Create a snapshot of current agent state
snapshot_id = create_snapshot("agent-3")

# After some time, compare with the current state
drift_report = compare_snapshots(snapshot_id, "agent-3")
```

### 3. Drift Simulation

Test drift detection and correction mechanisms:

```python
from dreamos.tools.drift_simulator import DriftSimulator

# Create simulator with specific drift types
simulator = DriftSimulator(
    agent_id="agent-3",
    drift_types=["priority", "resource"],
    drift_rate=0.05  # 5% drift per cycle
)

# Run simulation
simulator.run(cycles=100)

# Check if drift was detected and corrected
detection_report = simulator.get_detection_report()
```

## Escalation Path

If drift cannot be automatically corrected:

1. **Level 1: Agent Self-Correction**
   - Agent detects and attempts to correct its own drift
   - Logs detailed diagnostics of detected drift
   - Implements standard correction strategies

2. **Level 2: Agent Supervisor Intervention**
   - If self-correction fails, notify agent supervisor
   - Supervisor applies more aggressive corrections
   - May temporarily restrict agent operations

3. **Level 3: Human Intervention**
   - Persistent drift despite supervisor intervention
   - Escalate to human operator with diagnostic data
   - May require agent restart or reconfiguration

## Conclusion

Agent drift is a natural consequence of autonomous operation but can be effectively managed through consistent monitoring, automated correction, and regular maintenance. By implementing the practices in this guide, you can maintain stable and predictable agent behavior over extended operational periods. 