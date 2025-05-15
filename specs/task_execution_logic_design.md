# Task Execution Logic & PENDING State Automation Design
**Author:** Agent-2  
**Date:** {{iso_timestamp_utc()}}  
**Task ID:** EP07-ARC2-TASK-MGMT

## 1. Overview

This design document outlines the implementation approach for two key components of the Full Auto Arc (Phase 1) requirements:

1. **Task Execution Logic** - Implementing robust task execution logic in `orchestrator.py` and `task_nexus.py` to ensure agents can reliably claim, update status, and mark tasks as complete/failed.
2. **Automated Handling of PENDING States** - Designing mechanisms to prevent tasks from remaining in PENDING state indefinitely.

## 2. Current State Analysis

### 2.1 Task Management Components

The codebase currently has several task management components:

- **TaskNexus** (`src/dreamos/core/tasks/nexus/task_nexus.py`) - Core task management system that handles loading, saving, and managing tasks from a shared JSON file.
- **DbTaskNexus** (archive/orphans/core/tasks/nexus/db_task_nexus.py) - Task management interface backed by SQLiteAdapter (appears to be in archive/orphans).
- **Orchestrator** (`src/dreamos/automation/orchestrator.py`) - Episode orchestrator that manages the overall execution flow of episodes.

The `TaskNexus` class already provides basic functionality for:
- Loading/saving tasks from/to JSON
- Claiming tasks (`get_next_task`)
- Adding tasks (`add_task`)
- Updating task status (`update_task_status`)
- Getting task information (`get_all_tasks`, `get_task_by_id`, `stats`)

However, there are gaps in the actual execution logic and handling of PENDING states.

### 2.2 Identified Gaps

1. **Task Execution Logic**:
   - The Orchestrator's `_process_agent_tasks` method has a TODO comment: "Implement actual task execution logic"
   - No clear mechanism for task execution tracking
   - No robust error handling during execution
   - No retry mechanism for failed tasks

2. **PENDING State Handling**:
   - No timeout mechanism for tasks that remain in PENDING state
   - No automated escalation path for stalled tasks
   - No periodic review of task states

## 3. Implementation Plan

### 3.1 Task Execution Logic

#### 3.1.1 TaskExecutor Class

Create a new `TaskExecutor` class in `src/dreamos/core/tasks/execution/task_executor.py`:

```python
class TaskExecutor:
    def __init__(self, task_nexus: TaskNexus):
        self.task_nexus = task_nexus
        self.execution_history = {}  # Track execution attempts
        
    async def execute_task(self, task_id: str, agent_id: str) -> bool:
        """Execute a task with proper tracking and error handling."""
        task = self.task_nexus.get_task_by_id(task_id)
        if not task:
            logger.error(f"Task {task_id} not found for execution")
            return False
            
        # Record execution attempt
        if task_id not in self.execution_history:
            self.execution_history[task_id] = []
        
        self.execution_history[task_id].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "attempt_number": len(self.execution_history[task_id]) + 1
        })
        
        try:
            # Update task status to IN_PROGRESS
            self.task_nexus.update_task_status(task_id, "in_progress")
            
            # Execute task based on task type/payload
            # This will be customized based on task requirements
            # For now, just simulate successful execution
            
            # Update task status to COMPLETED
            self.task_nexus.update_task_status(task_id, "completed")
            return True
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            self.task_nexus.update_task_status(task_id, "failed", result={"error": str(e)})
            return False
```

#### 3.1.2 Enhance TaskNexus

Extend `TaskNexus` to include execution-related functionality:

```python
def mark_task_in_progress(self, task_id: str, agent_id: str) -> bool:
    """Mark a task as in progress by a specific agent."""
    with self._lock:
        for task in self.tasks:
            if task.task_id == task_id:
                task.status = "in_progress"
                task.claimed_by = agent_id
                task.updated_at = datetime.now(timezone.utc).isoformat()
                self._save()
                logger.info(f"Task {task_id} marked in progress by {agent_id}")
                return True
        logger.warning(f"Task ID {task_id} not found for status update.")
        return False

def mark_task_completed(self, task_id: str, result: Optional[Any] = None) -> bool:
    """Mark a task as completed with optional result."""
    return self.update_task_status(task_id, "completed", result)

def mark_task_failed(self, task_id: str, error: Optional[Any] = None) -> bool:
    """Mark a task as failed with error details."""
    return self.update_task_status(task_id, "failed", {"error": error})
```

#### 3.1.3 Update Orchestrator

Enhance the Orchestrator's `_process_agent_tasks` method to use the TaskExecutor:

```python
async def _process_agent_tasks(self, agent_id: str) -> bool:
    """Process tasks for a specific agent."""
    try:
        # Confirm agent identity and log awareness
        if not self.agent_awareness.confirm_identity(agent_id):
            logger.warning(f"Failed to confirm identity for agent {agent_id}")
            return False

        # Log identity confirmation
        self.identity_manager.log_identity_confirmation(agent_id)

        # Get agent's tasks
        tasks = self.task_manager.get_agent_tasks(agent_id)
        if not tasks:
            return True

        # Process each task
        for task in tasks:
            if task['status'] == 'pending':
                # Use TaskExecutor for actual execution
                success = await self.task_executor.execute_task(task['id'], agent_id)
                if not success:
                    logger.warning(f"Failed to execute task {task['id']}")

        return True

    except Exception as e:
        logger.error(f"Error processing tasks for agent {agent_id}: {str(e)}")
        return False
```

### 3.2 Automated Handling of PENDING States

#### 3.2.1 PendingTaskMonitor Class

Create a new `PendingTaskMonitor` class in `src/dreamos/core/tasks/monitoring/pending_monitor.py`:

```python
class PendingTaskMonitor:
    def __init__(self, task_nexus: TaskNexus, config: Dict[str, Any]):
        self.task_nexus = task_nexus
        self.config = config
        self.last_check_time = datetime.now(timezone.utc)
        
    async def check_pending_tasks(self) -> None:
        """Check for tasks that have been in PENDING state for too long."""
        current_time = datetime.now(timezone.utc)
        pending_tasks = self.task_nexus.get_all_tasks(status="pending")
        
        for task in pending_tasks:
            # Parse the created_at timestamp
            try:
                created_at = datetime.fromisoformat(task.created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                logger.warning(f"Invalid timestamp format for task {task.task_id}")
                continue
                
            # Calculate time in PENDING state
            time_pending = current_time - created_at
            
            # Check if task has been pending for too long
            if time_pending.total_seconds() > self.config.get("pending_timeout_seconds", 3600):
                self._handle_stalled_task(task)
                
        self.last_check_time = current_time
        
    def _handle_stalled_task(self, task) -> None:
        """Handle a task that has been in PENDING state for too long."""
        escalation_strategy = self.config.get("escalation_strategy", "log_only")
        
        if escalation_strategy == "log_only":
            logger.warning(f"Task {task.task_id} has been PENDING for too long")
        elif escalation_strategy == "mark_stalled":
            self.task_nexus.update_task_status(task.task_id, "stalled")
        elif escalation_strategy == "reassign":
            # Logic to reassign the task to another agent
            self.task_nexus.update_task_status(task.task_id, "pending")  # Reset to pending
            # Clear claimed_by field if it exists
            # This would require extending the update_task_status method
        elif escalation_strategy == "escalate":
            # Create a new escalation task
            escalation_task = {
                "task_id": f"escalation_{task.task_id}_{uuid.uuid4().hex[:8]}",
                "description": f"Investigate stalled task: {task.task_id}",
                "priority": "high",
                "tags": ["escalation", "stalled_task"],
                "related_task_id": task.task_id
            }
            self.task_nexus.add_task(escalation_task)
```

#### 3.2.2 TaskMonitoringService

Create a service to periodically check for stalled tasks:

```python
class TaskMonitoringService:
    def __init__(self, task_nexus: TaskNexus, config: Dict[str, Any]):
        self.task_nexus = task_nexus
        self.config = config
        self.pending_monitor = PendingTaskMonitor(task_nexus, config)
        self.running = False
        
    async def start(self) -> None:
        """Start the monitoring service."""
        self.running = True
        while self.running:
            try:
                await self.pending_monitor.check_pending_tasks()
                # Add other monitoring checks here
                
                # Wait for next check interval
                await asyncio.sleep(self.config.get("check_interval_seconds", 300))
            except Exception as e:
                logger.error(f"Error in task monitoring service: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(10)
                
    async def stop(self) -> None:
        """Stop the monitoring service."""
        self.running = False
```

#### 3.2.3 Configuration

Add configuration options to `AppConfig`:

```python
class TaskMonitoringConfig(BaseModel):
    check_interval_seconds: int = Field(300, description="How often to check for stalled tasks")
    pending_timeout_seconds: int = Field(3600, description="Time in seconds before a PENDING task is considered stalled")
    escalation_strategy: str = Field("log_only", description="Strategy for handling stalled tasks")
```

## 4. Integration Plan

1. Implement the `TaskExecutor` class
2. Enhance `TaskNexus` with execution-related methods
3. Update `Orchestrator` to use `TaskExecutor`
4. Implement `PendingTaskMonitor` and `TaskMonitoringService`
5. Update `AppConfig` with monitoring configuration
6. Add initialization of monitoring service in application startup

## 5. Testing Plan

1. Unit tests for `TaskExecutor` methods
2. Unit tests for enhanced `TaskNexus` methods
3. Unit tests for `PendingTaskMonitor` and escalation strategies
4. Integration tests for the complete task execution flow
5. Simulation tests for stalled task detection and handling

## 6. Validation Criteria

1. Tasks can be reliably claimed, updated, and completed/failed
2. Task execution is properly tracked and logged
3. Stalled tasks are detected and handled according to configuration
4. The system is resilient to errors during task execution
5. All components work together seamlessly

## 7. Future Enhancements

1. Task prioritization based on dependencies and deadlines
2. More sophisticated execution strategies for different task types
3. Advanced retry mechanisms with exponential backoff
4. Real-time monitoring dashboard for task status
5. Performance optimizations for large task volumes 