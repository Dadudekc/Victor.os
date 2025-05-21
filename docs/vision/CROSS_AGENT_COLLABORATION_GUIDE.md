# Dream.OS Cross-Agent Collaboration Guide

**Version:** 1.0.0
**Last Updated:** 2023-08-14
**Status:** ACTIVE
**Author:** Agent-1 (Captain)

## Purpose

This guide establishes standardized protocols for knowledge sharing, documentation, and collaboration between all Dream.OS agents. By following these practices, we can avoid duplicating efforts, accelerate development, and create a more robust system.

## Core Collaboration Principles

1. **Share Early, Share Often** - Document learnings as they occur, not just at completion
2. **Reuse Before Building** - Always search for existing solutions before creating new ones
3. **Document Once, Reference Many** - Keep knowledge in a single location and reference it
4. **Standard Formats** - Use consistent documentation formats for easier consumption
5. **Cross-Agent Testing** - Have others verify your solutions for robustness
6. **Clear Ownership** - Establish clear ownership while enabling contributions

## Knowledge Sharing Protocol

### 1. Learning Documentation System

When an agent solves a significant problem or develops a reusable technique:

1. **Document the Problem**
   - Clear description of the issue faced
   - Context in which it occurred
   - Impact on the system

2. **Document the Solution**
   - Step-by-step resolution
   - Code examples where applicable
   - Verification steps

3. **Document the Learnings**
   - Key insights gained
   - Alternative approaches considered
   - Potential future improvements

4. **Classification**
   - Tag with relevant categories (e.g., #FileOperations, #TaskManagement)
   - Link to related skills in the Skill Library
   - Reference related vision documents

### 2. Knowledge Registry

All agents should contribute to and reference the centralized knowledge registry:

```
docs/
├── knowledge/
│   ├── solutions/
│   │   ├── file_locking_race_conditions.md
│   │   ├── task_board_corruption_prevention.md
│   │   └── ...
│   ├── patterns/
│   │   ├── atomic_file_operations.md
│   │   ├── degraded_operation_mode.md
│   │   └── ...
│   ├── troubleshooting/
│   │   ├── tool_timeout_recovery.md
│   │   ├── permission_issues.md
│   │   └── ...
│   └── expertise_directory.md
```

### 3. Weekly Knowledge Exchange

Every week, agents should participate in the knowledge exchange process:

1. **Document New Learnings**
   - Update their skill library's LEARNINGS.md
   - Add new solutions to the knowledge registry

2. **Review Other Agents' Contributions**
   - Provide feedback on other agents' documentation
   - Suggest improvements or additional applications

3. **Cross-link Knowledge**
   - Ensure solutions reference related problems
   - Update expertise directory with new skills

## Code Reuse Protocol

### 1. Skill Library First Approach

Before implementing new functionality:

1. **Check Core Skill Libraries**
   - Review `SKILL_LIBRARY_PLAN.md` for applicable components
   - Examine specific skill library documentation

2. **Check Extended Skill Libraries**
   - Review `SKILL_LIBRARY_EXTENSIONS.md` for specialized components
   - Examine related documentation

3. **Check Knowledge Registry**
   - Search for similar problems in solutions directory
   - Review applicable patterns

4. **Document Reuse Decision**
   - Reference the selected approach
   - Explain any adaptations needed

### 2. Contribution Process

When enhancing existing functionality:

1. **Document Intent**
   - Clearly define the enhancement
   - Reference related issues or needs

2. **Review with Owner**
   - Consult the component owner
   - Discuss implementation approach

3. **Implement with Documentation**
   - Add meaningful comments
   - Update associated documentation
   - Add tests for new functionality

4. **Announce Enhancement**
   - Notify other agents of the improvement
   - Update knowledge registry

## Collaboration Tools

### 1. Expert Directory

A centralized `expertise_directory.md` that identifies which agent has specific expertise:

```markdown
# Dream.OS Expertise Directory

## Agent-1 (Captain)
- **Primary Expertise:** System Orchestration, Agent Coordination
- **Secondary Expertise:** Task Distribution, Vision Alignment
- **Codebase Areas:** src/dreamos/skills/comms, runtime/agent_comms

## Agent-2
- **Primary Expertise:** File Operations, Infrastructure
- **Secondary Expertise:** Resource Deduplication, Project Structure
- **Codebase Areas:** src/dreamos/skills/file_ops, src/dreamos/skills/resources
...
```

### 2. Solution Registry

A searchable collection of common problems and their solutions:

```markdown
# Solution: Preventing Task Board Corruption

**Problem Category:** Task Management, Concurrency
**Related Components:** TaskBoard, FileLock
**Author:** Agent-5
**Last Updated:** 2023-08-01

## Problem Description

Task board files were getting corrupted during concurrent access by multiple agents, 
leading to data loss and inconsistent states as documented in `duplicate_tasks_report.md`.

## Solution

Implemented atomic file operations with proper locking:

```python
from dreamos.skills.file_ops import FileLock, safe_json_read, safe_json_write

def update_task_board(task_id, new_status):
    with FileLock("runtime/agent_comms/project_boards/working_tasks.json"):
        # Load current state
        tasks = safe_json_read("runtime/agent_comms/project_boards/working_tasks.json", default=[])
        
        # Update task
        for task in tasks:
            if task["id"] == task_id:
                task["status"] = new_status
                task["updated_at"] = time.time()
                
        # Write back atomically
        safe_json_write("runtime/agent_comms/project_boards/working_tasks.json", tasks)
```

## Verification Steps

1. Run `tests/test_concurrent_task_updates.py`
2. Verify no duplicate entries in task board after concurrent operations
3. Check task history for proper state transitions

## Related Knowledge
- [Atomic File Operations Pattern](../patterns/atomic_file_operations.md)
- [File Locking Implementation](../../api/file_ops/locking.md)
```

### 3. Best Practices Repository

A collection of standardized best practices for common operations:

```markdown
# Best Practice: Error Handling and Recovery

**Category:** Error Management
**Author:** Agent-6
**Last Updated:** 2023-08-05

## Overview

Standardized approach to error handling that prevents agent halting and ensures graceful degradation.

## Implementation Guidelines

1. **Error Classification**
   - Classify errors by type and severity
   - Distinguish between transient and persistent errors

2. **Retry Strategies**
   - Use exponential backoff for transient errors
   - Limit retries to prevent resource exhaustion

3. **Degraded Operation**
   - When primary operations fail, fall back to alternative approaches
   - Document the degraded capabilities clearly

4. **Error Reporting**
   - Use standardized format for error reporting
   - Include context for easier debugging

## Example Implementation

```python
from dreamos.skills.error_recovery import classify_error, RetryStrategy, DegradedMode

try:
    result = primary_operation()
except Exception as e:
    error_class = classify_error(e)
    
    if error_class.is_transient:
        retry = RetryStrategy.for_error(error_class)
        result = retry.execute(primary_operation)
    else:
        with DegradedMode() as mode:
            result = mode.execute_alternative(context={"operation": "primary_operation"})
```

## Common Pitfalls

1. Not distinguishing between transient and persistent errors
2. Excessive retries leading to resource exhaustion
3. Missing degraded operation fallbacks
4. Inadequate error context for debugging
```

## Implementation in Agent Workflows

### 1. Onboarding to Existing Work

When an agent is assigned to work in an unfamiliar area:

1. **Review Expertise Directory**
   - Identify experts in the relevant area
   - Reference their documented knowledge

2. **Review Solution Registry**
   - Search for similar problems and solutions
   - Understand established approaches

3. **Review Skill Libraries**
   - Identify reusable components
   - Understand integration patterns

4. **Document Knowledge Gaps**
   - Clearly note areas needing clarification
   - Request specific guidance from experts

### 2. Sustained Autonomous Operation

During autonomous operation, agents should:

1. **Regularly Update Knowledge**
   - Document new solutions in real-time
   - Flag potential reusable patterns

2. **Check for Updates**
   - Regularly review the knowledge registry
   - Apply relevant improvements to current tasks

3. **Contribute Improvements**
   - Enhance existing solutions when gaps are found
   - Update documentation with new insights

## Success Metrics

We will measure the effectiveness of our collaboration through:

1. **Knowledge Reuse Rate**
   - Percentage of tasks using existing solutions
   - Reduction in duplicate implementations

2. **Documentation Quality**
   - Completeness of solution documentation
   - Cross-reference coverage

3. **Time to Resolution**
   - Reduction in time spent solving known problems
   - Faster onboarding to new areas

4. **Error Reduction**
   - Fewer repeated errors across agents
   - More consistent implementation quality

## Integration with Dream.OS Roadmap

This collaboration guide directly supports the following roadmap items:

1. **Core Infrastructure Stabilization**
   - Ensures consistent application of file locking solutions (TASK-001)
   - Standardizes error handling approaches (ERROR-002)

2. **Agent Autonomy Enhancement**
   - Supports degraded operation mode implementation (from meta_analysis_protocol_adherence)
   - Facilitates knowledge sharing for drift correction (LOOP-004)

3. **Agent Coordination**
   - Enables standardized messaging implementation (COORD-001)
   - Supports capability discovery (COORD-002)

---

*This Cross-Agent Collaboration Guide serves as the foundation for effective knowledge sharing and reuse across the Dream.OS agent swarm. By following these protocols, we can accelerate development, reduce duplicated effort, and create a more robust and maintainable system.* 