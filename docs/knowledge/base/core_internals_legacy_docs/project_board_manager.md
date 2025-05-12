# Project Board Manager (`src/dreamos/core/coordination/project_board_manager.py`)

**Status: MISSING FROM CODEBASE (as of YYYY-MM-DD HH:MM:SS UTC)**

## Overview

The Project Board Manager (PBM) is (was) intended as the central component responsible for managing the lifecycle of tasks within the Dream.OS system. It provides an interface for agents and other services to create, query, claim, update, and complete tasks.

## Core Responsibilities (Intended)

*   **Task Persistence:** Reading and writing task data to persistent storage, likely using structured files (e.g., JSON, JSONL) representing different task states (e.g., backlog/future, ready, working, completed).
*   **State Management:** Enforcing valid task state transitions (e.g., PENDING -> READY -> CLAIMED -> WORKING -> COMPLETED/FAILED).
*   **Concurrency Control:** Implementing file locking mechanisms to prevent race conditions when multiple agents access the task boards simultaneously.
*   **Schema Validation:** Validating task data against a defined JSON schema (`task-schema.json`) upon creation and update.
*   **API/CLI:** Providing programmatic access (likely via methods within the class) and potentially a command-line interface (`manage_tasks.py`) for manual task management.

## Current Issues

*   The module file is currently missing from its expected location.
*   This prevents all standard task management operations and causes failures in dependent components like the `manage_tasks.py` CLI.
*   Restoring or reimplementing the PBM is a critical priority.

## Related Components

*   `manage_tasks.py` (CLI frontend - Currently failing)
*   `src/dreamos/core/config.py` (Provides paths to task board files and schema)
*   `src/dreamos/core/errors.py` (Defines `ProjectBoardError`, `TaskNotFoundError`, etc.)
*   Agents that interact with tasks (Most agents) 