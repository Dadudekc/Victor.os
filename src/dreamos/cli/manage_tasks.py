#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# src/dreamos/cli/manage_tasks.py <- MOVED FROM scripts/utils/
"""
CLI for interacting with Project Boards (future, working, completed).

Provides commands to view, claim, update, and add tasks using the
ProjectBoardManager abstraction layer for safe concurrent access.
"""

import datetime
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import click

# --- Setup Python Path ---
# Ensure the main 'src' directory is in the path to allow imports
# like 'from dreamos.core...'
SCRIPT_DIR = Path(__file__).resolve().parent
# Adjust path based on new location: src/dreamos/cli -> project root is 3 levels up
PROJECT_ROOT = SCRIPT_DIR.parents[2]
SRC_PARENT_DIR = PROJECT_ROOT / "src"  # Get the 'src' directory itself
if str(SRC_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_PARENT_DIR))
    # print(f"DEBUG: Added {SRC_PARENT_DIR} to sys.path") # Keep for debug if needed

# --- Core Imports ---
try:
    # Update import paths based on new location within src/dreamos/
    # Corrected import path per CONSOLIDATE-PBM-IMPL-001
    # from dreamos.core.comms.project_board import (
    from dreamos.coordination.project_board_manager import ProjectBoardManager

    # Import TaskStatus from correct location
    from dreamos.core.coordination.message_patterns import TaskStatus

    # Import Error from correct location
    from dreamos.core.errors import ProjectBoardError

    # Use core timestamp utility
    # from dreamos.utils.common_utils import get_utc_iso_timestamp
except ImportError as e:
    # Provide a more informative error if core components are missing
    sys.stderr.write(f"\nError: Failed to import core 'dreamos' components. \n")
    sys.stderr.write(
        f"Ensure the script is run from the project root or '{PROJECT_ROOT}' is structured correctly.\n"
    )
    sys.stderr.write(f"Import Error: {e}\n")
    sys.exit(1)

# --- Constants & Defaults ---
DEFAULT_BOARDS_BASE_DIR = PROJECT_ROOT / "runtime" / "agent_comms" / "project_boards"
WORKING_TASKS_FILENAME = "working_tasks.json"
COMPLETED_TASKS_FILENAME = "completed_tasks.json"
# FUTURE_TASKS_FILENAME = "future_tasks.json" # Deprecated
TASK_BACKLOG_FILENAME = "task_backlog.json"
TASK_READY_QUEUE_FILENAME = "task_ready_queue.json"


# --- Helper ---
def _now() -> str:
    """Returns the current UTC time as an ISO 8601 string."""
    # return get_utc_iso_timestamp()
    return (
        datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds")
        + "Z"
    )


# --- CLI Definition ---
@click.group()
@click.option(
    "--boards-dir",
    default=str(DEFAULT_BOARDS_BASE_DIR),
    help=f"Base directory for task boards (default: {DEFAULT_BOARDS_BASE_DIR})",
    type=click.Path(file_okay=False, dir_okay=True, exists=True, path_type=Path),
)
@click.pass_context
def cli(ctx, boards_dir):
    """Manage DreamOS Task Boards via the ProjectBoardManager."""
    ctx.ensure_object(dict)
    try:
        ctx.obj = ProjectBoardManager(boards_base_dir=boards_dir.resolve())
        # print(f"DEBUG: ProjectBoardManager initialized with {boards_dir.resolve()}") # Keep for debug if needed
    except Exception as e:
        click.echo(f"Error initializing ProjectBoardManager: {e}", err=True)
        sys.exit(1)


# --- Claim Command ---
@cli.command()
@click.argument("task_id")
@click.argument("agent_id")
@click.pass_obj
def claim(board_manager: ProjectBoardManager, task_id: str, agent_id: str):
    """Claim a task from the Task Ready Queue board by its ID."""
    try:
        # Assumes PBM has claim_ready_task method after REFACTOR-PBM-DUAL-QUEUE-001
        if board_manager.claim_ready_task(task_id, agent_id):
            click.echo(
                f"Task '{task_id}' claimed by '{agent_id}' from Ready Queue. Moved to working tasks."
            )
        else:
            # Error message handled within claim_ready_task, just echo generic failure
            click.echo(f"Failed to claim task '{task_id}'.", err=True)
            sys.exit(1)
    except ProjectBoardError as e:
        click.echo(f"Error claiming task: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)
        sys.exit(1)


# --- Update Command ---
@cli.command()
@click.argument("task_id")
@click.argument("agent_id")  # Require agent ID for attribution
@click.option("--status", help="New status for the task.")
@click.option("--note", help="Note to add/update for the task.")
@click.option(
    "--completion-summary", help="Completion summary (use with COMPLETED status)."
)
@click.option(
    "--add-output",
    multiple=True,
    help="Output file/resource path (can specify multiple).",
)
@click.pass_obj
def update(
    board_manager: ProjectBoardManager,
    task_id: str,
    agent_id: str,
    status: str | None,
    note: str | None,
    completion_summary: str | None,
    add_output: tuple[str],
):
    """Update status, notes, or add outputs for a task in the Working Tasks board."""
    updates = {"timestamp_updated": _now(), "last_updated_by": agent_id}
    needs_update = False

    if status:
        updates["status"] = status
        needs_update = True
    if note:
        updates["notes"] = note  # Overwrites previous notes if provided
        needs_update = True
    if completion_summary:
        updates["completion_summary"] = completion_summary
        needs_update = True
    if add_output:
        # Handle adding outputs - needs PBM method support
        # For now, we can store it in the 'outputs' field if it exists
        updates["outputs"] = list(add_output)  # Example: Store as a list
        needs_update = True

    if not needs_update:
        click.echo(
            "No update parameters provided (status, note, completion-summary, add-output)."
        )
        return

    try:
        if board_manager.update_working_task(task_id, updates):
            click.echo(f"Task '{task_id}' updated successfully by '{agent_id}'.")
        else:
            click.echo(
                f"Failed to update task '{task_id}'. Task may not exist in working board.",
                err=True,
            )
            sys.exit(1)
    except ProjectBoardError as e:
        click.echo(f"Error updating task: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)
        sys.exit(1)


# --- Complete Command ---
@cli.command()
@click.argument("task_id")
@click.argument("agent_id")  # Agent performing the completion
@click.option(
    "--final-status",
    default="COMPLETED",
    help="Final status (e.g., COMPLETED, FAILED).",
    show_default=True,
)
@click.option("--completion-summary", help="Final summary of the task outcome.")
@click.option("--note", help="Final notes to add/update.")
@click.option(
    "--add-output",
    multiple=True,
    help="Output file/resource path (can specify multiple).",
)
@click.pass_obj
def complete(
    board_manager: ProjectBoardManager,
    task_id: str,
    agent_id: str,
    final_status: str,
    completion_summary: str | None,
    note: str | None,
    add_output: tuple[str],
):
    """Mark a task as completed (or failed) and move it to the Completed board."""
    final_updates = {
        "status": final_status.upper(),
        # Changed timestamp_completed to timestamp_completed_utc for consistency
        "timestamp_completed_utc": _now(),
        "timestamp_updated": _now(),
        "completed_by": agent_id,
    }
    if completion_summary:
        final_updates["completion_summary"] = completion_summary
    if note:
        final_updates["notes"] = note
    if add_output:
        final_updates["outputs"] = list(add_output)

    try:
        if board_manager.move_task_to_completed(task_id, final_updates):
            click.echo(
                f"Task '{task_id}' moved to completed with status '{final_status}'."
            )
        else:
            click.echo(
                f"Failed to move task '{task_id}' to completed. Task may not exist in working board.",
                err=True,
            )
            sys.exit(1)
    except ProjectBoardError as e:
        click.echo(f"Error completing task: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)
        sys.exit(1)


# --- List Commands ---
# @cli.command('list-future') # Removed - Replaced by list-backlog / list-ready
# @click.option('--status', help='Filter by status (e.g., PENDING).')
# @click.pass_obj
# def list_future(board_manager: ProjectBoardManager, status: str | None):
#     """List tasks currently on the Future Tasks board."""
#     tasks = board_manager.list_future_tasks(status=status)
#     if tasks:
#         click.echo(json.dumps(tasks, indent=2))
#     else:
#         click.echo(f"No future tasks found{f' with status {status}' if status else ''}.")


@cli.command("list-backlog")
@click.option("--status", help="Filter by status (e.g., PENDING).")
@click.pass_obj
def list_backlog(board_manager: ProjectBoardManager, status: str | None):
    """List tasks currently on the Task Backlog board."""
    # Assumes PBM has list_backlog_tasks method after REFACTOR-PBM-DUAL-QUEUE-001
    tasks = board_manager.list_backlog_tasks(status=status)
    if tasks:
        click.echo(json.dumps(tasks, indent=2))
    else:
        click.echo(
            f"No backlog tasks found{f' with status {status}' if status else ''}."
        )


@cli.command("list-ready")
@click.option("--status", help="Filter by status (e.g., PENDING).")
@click.pass_obj
def list_ready(board_manager: ProjectBoardManager, status: str | None):
    """List tasks currently on the Task Ready Queue board."""
    # Assumes PBM has list_ready_queue_tasks method after REFACTOR-PBM-DUAL-QUEUE-001
    tasks = board_manager.list_ready_queue_tasks(status=status)
    if tasks:
        click.echo(json.dumps(tasks, indent=2))
    else:
        click.echo(
            f"No ready queue tasks found{f' with status {status}' if status else ''}."
        )


@cli.command("list-working")
@click.option("--agent-id", help="Filter by assigned agent ID.")
@click.pass_obj
def list_working(board_manager: ProjectBoardManager, agent_id: str | None):
    """List tasks currently on the Working Tasks board."""
    tasks = board_manager.list_working_tasks(agent_id=agent_id)
    if tasks:
        click.echo(json.dumps(tasks, indent=2))
    else:
        click.echo(
            f"No working tasks found{f' for agent {agent_id}' if agent_id else ''}."
        )


@cli.command("list-completed")
@click.option(
    "--limit",
    type=int,
    default=50,
    help="Limit number of tasks shown (most recent).",
    show_default=True,
)
@click.pass_obj
def list_completed(board_manager: ProjectBoardManager, limit: int):
    """List tasks currently on the Completed Tasks board."""
    # Assumes PBM has list_completed_tasks method after REFACTOR-PBM-DUAL-QUEUE-001
    try:
        tasks = board_manager.list_completed_tasks(limit=limit)
        if tasks:
            click.echo(json.dumps(tasks, indent=2))
        else:
            click.echo(f"No completed tasks found.")
    except ProjectBoardError as e:
        click.echo(f"Error listing completed tasks: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)
        sys.exit(1)


# --- Get Command ---
@cli.command()
@click.argument("task_id")
@click.pass_obj
def get(board_manager: ProjectBoardManager, task_id: str):
    """Get details for a specific task ID from any board."""
    task = board_manager.get_task(task_id)
    if task:
        click.echo(json.dumps(task, indent=2))
    else:
        click.echo(f"Task '{task_id}' not found on any board.", err=True)
        sys.exit(1)


# --- Add Command ---
@cli.command()
@click.argument("task_definition", type=click.File("r"))
@click.argument("agent_id")  # Agent responsible for adding
# @click.option('--board', default='future', type=click.Choice(['future', 'working']), help='Target board.', show_default=True) # Removed - always add to backlog
@click.pass_obj
def add(board_manager: ProjectBoardManager, task_definition, agent_id: str):
    """Add a new task from a JSON definition file to the Task Backlog."""
    try:
        new_task_data = json.load(task_definition)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON in task definition file: {e}", err=True)
        sys.exit(1)

    # Basic validation (ensure it's a dict, maybe check for 'description'?)
    if not isinstance(new_task_data, dict):
        click.echo("Error: Task definition file must contain a JSON object.", err=True)
        sys.exit(1)

    # Add metadata
    new_task_data["task_id"] = new_task_data.get(
        "task_id", board_manager._generate_task_id()
    )
    new_task_data["timestamp_created"] = _now()
    new_task_data["timestamp_updated"] = _now()
    new_task_data["created_by"] = agent_id
    # Set initial status for backlog
    new_task_data["status"] = new_task_data.get(
        "status", TaskStatus.PENDING.value
    )  # Default to PENDING for backlog
    # Remove logic for adding directly to working
    # if board == 'future':
    #      new_task_data['status'] = new_task_data.get('status', TaskStatus.PENDING.value) # Default to PENDING
    # else: # working board
    #      new_task_data['status'] = TaskStatus.ASSIGNED.value # Assume assigned if added directly to working
    #      new_task_data['assigned_agent_id'] = new_task_data.get('assigned_agent_id', 'UNKNOWN') # Assignee needed for working board

    try:
        # Assumes PBM has add_task_to_backlog method after REFACTOR-PBM-DUAL-QUEUE-001
        if board_manager.add_task_to_backlog(new_task_data):
            click.echo(
                f"Task '{new_task_data['task_id']}' added to backlog by '{agent_id}'."
            )
        else:
            click.echo("Failed to add task to backlog.", err=True)
            sys.exit(1)
    except ProjectBoardError as e:
        click.echo(f"Error adding task: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)
        sys.exit(1)


# --- Promote Command ---
@cli.command()
@click.argument("task_id")
# @click.option('--captain-id', required=True, help='ID of the Captain authorizing promotion.') # Add authorization later if needed
@click.pass_obj
def promote(board_manager: ProjectBoardManager, task_id: str):
    """Promote a task from the Task Backlog to the Task Ready Queue."""
    click.echo(
        f"[DEBUG] Attempting to promote task: {task_id}", err=True
    )  # DEBUG PRINT
    try:
        # Assumes PBM has promote_task_to_ready method after REFACTOR-PBM-DUAL-QUEUE-001
        click.echo(
            f"[DEBUG] Calling board_manager.promote_task_to_ready...", err=True
        )  # DEBUG PRINT
        if board_manager.promote_task_to_ready(task_id):
            click.echo(f"Task '{task_id}' promoted from Backlog to Ready Queue.")
        else:
            # This block should theoretically not be reached if PBM raises exceptions
            click.echo(
                f"[DEBUG] PBM returned False (unexpected).", err=True
            )  # DEBUG PRINT
            click.echo(
                f"Failed to promote task '{task_id}'. Task may not exist in backlog or promotion failed.",
                err=True,
            )
            sys.exit(1)
    except ProjectBoardError as e:
        click.echo(
            f"[DEBUG] Caught ProjectBoardError: {type(e).__name__}", err=True
        )  # DEBUG PRINT
        click.echo(f"Error promoting task: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(
            f"[DEBUG] Caught generic Exception: {type(e).__name__}", err=True
        )  # DEBUG PRINT
        click.echo(f"An unexpected error occurred: {e}", err=True)
        sys.exit(1)


# --- Entry Point ---
if __name__ == "__main__":
    # print(f"DEBUG: Running {__file__}") # Keep for debug if needed
    # print(f"DEBUG: Project Root: {PROJECT_ROOT}") # Keep for debug if needed
    # print(f"DEBUG: Sys Path: {sys.path}") # Keep for debug if needed
    cli()
