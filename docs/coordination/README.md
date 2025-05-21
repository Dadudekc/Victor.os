# Coordination System

## Overview
The coordination system manages agent interactions, task distribution, and team synchronization.

## Components

### Task Management
- Task assignment and tracking
- Progress monitoring
- Resource allocation
- Priority management

### Team Coordination
- Agent communication
- Status updates
- Meeting management
- Progress tracking

### Communication Channels
- Direct messaging
- Broadcast channels
- Team updates
- Meeting notes

## Usage

### Task Assignment
```python
from dreamos.coordination.task_manager import TaskManager

task_manager = TaskManager()
await task_manager.assign_task(agent_id, task_data)
```

### Team Updates
```python
from dreamos.coordination.team_coordinator import TeamCoordinator

coordinator = TeamCoordinator()
await coordinator.broadcast_update(update_data)
```

## Integration
- Agent Bus
- Message Queue
- Task Board
- Status Tracker

## Directory Structure
```
coordination/
├── team_updates/    # Team status updates
├── meeting_notes/   # Meeting documentation
└── README.md        # This file
```

## Progress Tracking
See `PROGRESS_TRACKER.md` for detailed progress information.

## Key Documents

- [**PROGRESS_TRACKER.md**](PROGRESS_TRACKER.md) - Current progress status and next steps for all agents
- [**COLLABORATIVE_ACTION_PLAN.md**](../vision/COLLABORATIVE_ACTION_PLAN.md) - The master plan for Dream.OS development

## Purpose

The coordination documents serve as the central reference point for all agents to:

1. Track the current status of all workstreams
2. Identify dependencies and blockers
3. Coordinate upcoming integration points
4. Monitor progress against success metrics
5. Document communication between agents

## Update Process

1. All coordination documents should be updated daily
2. Each agent is responsible for updating their own progress
3. Agent-6 (Feedback Systems Engineer) maintains the overall PROGRESS_TRACKER.md
4. Critical blockers should be highlighted immediately when discovered

## Usage Guidelines

1. **Always reference the source of truth**: Link back to the COLLABORATIVE_ACTION_PLAN.md when discussing requirements
2. **Update status before starting new work**: Ensure your current progress is captured
3. **Flag dependencies early**: Identify when your work depends on another agent's completion
4. **Document decisions**: Record all significant decisions in the coordination documents

---

*This README follows the Dream.OS Knowledge Sharing Protocol.* 