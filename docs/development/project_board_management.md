# Project Board Management

## Overview

The Project Board Management system provides a centralized interface for task management in Dream.OS, ensuring safe and reliable task tracking across the agent swarm.

## Core Components

### ProjectBoardManager

Located at `src/dreamos/coordination/project_board_manager.py`, this class provides a robust API for task management.

#### Key Features

1. **Task Board Operations**
   - Load and save task data
   - File locking for concurrent access
   - Atomic writes for data safety
   - Schema validation

2. **Task Management**
   - Task claiming and assignment
   - Status updates
   - Task creation
   - Task completion
   - Task archiving

3. **Concurrency Control**
   - File locking mechanism
   - Atomic write operations
   - Safe concurrent access

## API Reference

### Core Methods

1. **Task Board Operations**
   ```python
   load_boards()  # Load task data from JSON files
   save_boards()  # Save task data to JSON files
   ```

2. **Task Management**
   ```python
   get_task(task_id)  # Retrieve specific task
   list_future_tasks(status='unclaimed')  # List future tasks
   list_working_tasks(agent_id=None)  # List working tasks
   claim_task(task_id, agent_id)  # Claim task for agent
   update_task(task_id, updates)  # Update task details
   add_task(task_details, target_board='future')  # Add new task
   complete_task(task_id, summary, outputs)  # Mark task complete
   archive_task(task_id)  # Archive completed task
   ```

## Best Practices

1. **Task Creation**
   - Validate task data against schema
   - Include required fields
   - Document task dependencies

2. **Task Updates**
   - Use atomic operations
   - Maintain task history
   - Update status consistently

3. **Task Completion**
   - Provide completion summary
   - Include relevant outputs
   - Archive when appropriate

## Error Handling

1. **File Operations**
   - Handle I/O errors
   - Manage lock timeouts
   - Implement retry logic

2. **Validation**
   - Schema compliance
   - Data integrity
   - Required fields

3. **Concurrency**
   - Lock acquisition
   - Deadlock prevention
   - Timeout handling

## Related Documentation

- [Task Schema](../coordination/tasks/task-schema.json)
- [Agent Coordination](../coordination/README.md)
- [Development Guidelines](../development/guidelines.md) 