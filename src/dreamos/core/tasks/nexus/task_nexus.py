import asyncio
import collections
import datetime
import json
import logging
import os
import time
import uuid
from collections import Counter
from datetime import timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import filelock
from filelock import Timeout as LockAcquisitionError

# EDIT: Import relevant exceptions
from dreamos.core.errors import (
    BoardLockError,
    ProjectBoardError,
    TaskNotFoundError,
    TaskValidationError,
)

from ....config import AppConfig
from ...comms.project_board import ProjectBoardError, ProjectBoardManager
from .capability_registry import (
    DEFAULT_REGISTRY_PATH as DEFAULT_CAPABILITY_REGISTRY_PATH,
)
from .capability_registry import CapabilityRegistry

logger = logging.getLogger(__name__)


class TaskNexus:
    # Default paths (relative to project root) - will be overridden by config
    DEFAULT_FUTURE_TASKS_PATH = Path(
        "runtime/agent_comms/project_boards/future_tasks.json"
    )
    DEFAULT_WORKING_TASKS_PATH = Path(
        "runtime/agent_comms/project_boards/working_tasks.json"
    )
    DEFAULT_AGENT_REGISTRY_PATH = Path("runtime/agent_comms/agent_registry.json")
    DEFAULT_LOCK_TIMEOUT = 15  # Default lock timeout in seconds
    DEFAULT_HEARTBEAT_TTL = 60  # Default heartbeat TTL

    def __init__(self, config: AppConfig):
        self.config = config
        project_root = (
            Path(config.paths.project_root)
            if hasattr(config.paths, "project_root")
            else Path.cwd()
        )

        # --- Determine File Paths ---
        boards_base = Path(
            getattr(
                config.paths,
                "agent_comms_boards",
                project_root / "runtime/agent_comms/project_boards",
            )
        )
        self.future_tasks_path = Path(
            getattr(
                config.tasks,
                "future_tasks_file",
                boards_base / ProjectBoardManager.FUTURE_TASKS_FILENAME,
            )
        )
        self.working_tasks_path = Path(
            getattr(
                config.tasks,
                "working_tasks_file",
                boards_base / ProjectBoardManager.WORKING_TASKS_FILENAME,
            )
        )

        registry_base = Path(
            getattr(config.paths, "agent_comms", project_root / "runtime/agent_comms")
        )
        self.agent_registry_path = Path(
            getattr(
                config.tasks,
                "agent_registry_file",
                registry_base / "agent_registry.json",
            )
        )

        # EDIT START: Determine Capability Registry Path from config or default
        state_base = Path(
            getattr(config.paths, "runtime_state", project_root / "runtime/state")
        )  # Assuming a state path config
        self.capability_registry_path_str = str(
            getattr(
                config.tasks,
                "capability_registry_file",
                state_base / os.path.basename(DEFAULT_CAPABILITY_REGISTRY_PATH),
            )
        )
        logger.info(
            f"TaskNexus initialized using Capability Registry: {self.capability_registry_path_str}"
        )
        # EDIT END

        # --- Lock Files (Agent Registry Only Now) ---
        # Task board locks are handled by ProjectBoardManager
        self.agent_registry_lock_path = self.agent_registry_path.with_suffix(
            self.agent_registry_path.suffix + ".lock"
        )

        # --- Instantiate ProjectBoardManager ---
        try:
            self.board_manager = ProjectBoardManager(boards_base_dir=boards_base)
        except ProjectBoardError as e:
            logger.error(
                f"Failed to initialize ProjectBoardManager: {e}. Task board operations will likely fail.",
                exc_info=True,
            )
            # Depending on severity, might want to exit or disable functionality
            self.board_manager = None  # Ensure it's None if init fails

        # EDIT START: Instantiate CapabilityRegistry
        try:
            self.capability_registry = CapabilityRegistry(
                registry_path=self.capability_registry_path_str
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize CapabilityRegistry: {e}. Capability features will be unavailable.",
                exc_info=True,
            )
            self.capability_registry = None  # Ensure it's None if init fails
        # EDIT END

        # --- Other Config ---
        nexus_config = getattr(config.tasks, "nexus", None)
        self.lock_timeout = int(
            getattr(nexus_config, "lock_timeout_seconds", self.DEFAULT_LOCK_TIMEOUT)
        )
        self.heartbeat_ttl = int(
            getattr(nexus_config, "heartbeat_ttl_seconds", self.DEFAULT_HEARTBEAT_TTL)
        )

        self.agents: Dict[str, float] = {}

        logger.info(f"TaskNexus initialized.")
        logger.info(f"  Task Boards managed by ProjectBoardManager at: {boards_base}")
        logger.info(
            f"  Agent (Heartbeat) Registry: {self.agent_registry_path} (Lock: {self.agent_registry_lock_path})"
        )
        # EDIT START: Log Capability Registry path
        if self.capability_registry:
            logger.info(
                f"  Capability Registry: {self.capability_registry.registry_path} (Lock: {self.capability_registry.registry_lock_path})"
            )
        else:
            logger.warning("  Capability Registry: FAILED TO INITIALIZE.")
        # EDIT END
        logger.info(
            f"  Lock Timeout: {self.lock_timeout}s, Heartbeat TTL: {self.heartbeat_ttl}s"
        )

    # --- Private Async Load/Save Helpers (Agent Registry ONLY) ---
    async def _load_json_registry(
        self, file_path: Path, lock_path: Path
    ) -> Dict[str, float]:
        """Loads agent heartbeat registry asynchronously using its specific lock."""
        default_return = {}

        if not await asyncio.to_thread(file_path.exists):
            logger.warning(
                f"Registry file not found: {file_path}. Returning default: {default_return}"
            )
            return default_return

        try:
            async with filelock.FileLock(str(lock_path), timeout=self.lock_timeout):
                content = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
                if not content.strip():
                    logger.warning(
                        f"Registry file is empty: {file_path}. Returning default: {default_return}"
                    )
                    return default_return
                loaded_data = json.loads(content)
                if not isinstance(loaded_data, dict):
                    logger.error(
                        f"Registry file {file_path} did not contain a dictionary. Returning default."
                    )
                    return default_return
                return loaded_data
        except json.JSONDecodeError:
            logger.error(
                f"Failed to decode JSON from {file_path}. Returning default.",
                exc_info=True,
            )
            # TODO: Consider backing up corrupted file here?
            return default_return
        except LockAcquisitionError:
            logger.error(
                f"Timeout loading {file_path}: Could not acquire lock {lock_path} within {self.lock_timeout}s."
            )
            # Depending on use case, might raise or return default
            return default_return
        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {e}", exc_info=True)
            return default_return

    async def _save_json(self, file_path: Path, lock_path: Path, data: List | Dict):
        """Saves data to a JSON file using a file lock."""
        try:
            async with filelock.FileLock(str(lock_path), timeout=self.lock_timeout):
                # Ensure directory exists before writing
                await asyncio.to_thread(
                    file_path.parent.mkdir, parents=True, exist_ok=True
                )
                # Write atomically using asyncio.to_thread
                temp_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
                json_string = json.dumps(data, indent=2)
                await asyncio.to_thread(
                    temp_path.write_text, json_string, encoding="utf-8"
                )
                await asyncio.to_thread(os.replace, temp_path, file_path)
                logger.debug(f"Successfully saved data to {file_path}")
                return True
        except LockAcquisitionError:
            logger.error(
                f"Timeout saving {file_path}: Could not acquire lock {lock_path} within {self.lock_timeout}s."
            )
            return False
        except Exception as e:
            # Clean up temp file on error if it exists
            if await asyncio.to_thread(temp_path.exists):
                try:
                    await asyncio.to_thread(os.remove, temp_path)
                except OSError:
                    logger.error(
                        f"Failed to remove temporary save file {temp_path}",
                        exc_info=True,
                    )
            logger.error(f"Failed to save file {file_path}: {e}", exc_info=True)
            return False

    async def _load_agents(self) -> Dict[str, float]:
        """Loads agent heartbeat registry asynchronously."""
        # Type hint ensures load_json returns dict or empty dict
        agents_data: Dict = await self._load_json_registry(
            self.agent_registry_path, self.agent_registry_lock_path
        )
        # Ensure the loaded data is actually a dictionary
        if not isinstance(agents_data, dict):
            logger.warning(
                f"Agent registry file {self.agent_registry_path} contained invalid data type {type(agents_data)}. Resetting."
            )
            return {}
        return {k: float(v) for k, v in agents_data.items()}

    async def _save_agents(self) -> None:
        """Saves the current in-memory agent registry asynchronously."""
        # Assumes self.agents is the up-to-date dict to save
        await self._save_json(
            self.agent_registry_path, self.agent_registry_lock_path, self.agents
        )

    # --- Public Async Methods ---
    async def record_heartbeat(self, agent_name: str, timestamp: float = None) -> None:
        """
        Record or update the heartbeat timestamp for the given agent.
        """
        if timestamp is None:
            timestamp = time.time()
        try:
            # Use the specific agent registry lock
            async with filelock.FileLock(
                str(self.agent_registry_lock_path), timeout=self.lock_timeout
            ):
                # Reload agents to get latest state inside the lock
                self.agents = await self._load_agents()  # Load within lock
                self.agents[agent_name] = timestamp
                # Save within the same lock context
                await self._save_agents()
                logger.debug(f"Recorded heartbeat for {agent_name}")
        except LockAcquisitionError:
            logger.error(
                f"Timeout recording heartbeat for {agent_name}: Could not acquire lock {self.agent_registry_lock_path}."
            )
        except Exception as e:
            logger.error(
                f"Failed to record heartbeat for {agent_name}: {e}", exc_info=True
            )

    async def get_all_registered_agents(self) -> Dict[str, float]:
        """
        Return a dict of agent names to last heartbeat timestamps.
        Purges stale entries before returning.
        """
        active_agents = {}
        try:
            # Use the specific agent registry lock
            async with filelock.FileLock(
                str(self.agent_registry_lock_path), timeout=self.lock_timeout
            ):
                # Reload agents and purge stale entries inside the lock
                self.agents = await self._load_agents()  # Load within lock
                now = time.time()
                stale = [
                    a for a, ts in self.agents.items() if now - ts > self.heartbeat_ttl
                ]
                if stale:
                    logger.info(f"Purging {len(stale)} stale agent heartbeats: {stale}")
                    for a in stale:
                        self.agents.pop(a, None)  # Use pop for safety
                    # Save updated registry only if modified
                    await self._save_agents()
                active_agents = dict(self.agents)  # Return a copy
        except LockAcquisitionError:
            logger.error(
                f"Timeout getting registered agents: Could not acquire lock {self.agent_registry_lock_path}. Returning cached/empty."
            )
            # Return last known state or empty dict on timeout
            return dict(self.agents)  # May be stale
        except Exception as e:
            logger.error(f"Failed to get registered agents: {e}", exc_info=True)
            return {}  # Return empty on other errors
        return active_agents

    # --- Methods needing refactor for multi-board ---
    async def get_next_task(self, agent_id=None, type_filter=None):
        """
        Claim and return the next available task from the Ready Queue,
        considering priority and dependencies.
        Delegates the atomic move operation to ProjectBoardManager.
        """
        # REMOVED: Direct file manipulation logic.

        # TODO: Add dependency checking logic.

        if not self.board_manager:
            logger.error("ProjectBoardManager not initialized, cannot get next task.")
            return None

        if not agent_id:
            logger.warning("agent_id not provided to get_next_task. Cannot claim.")
            return None

        claimed_task_data = None

        try:
            # 1. Get potential tasks from the Ready Queue
            # Use PBM method to list pending tasks in the ready queue
            ready_tasks = await asyncio.to_thread(
                self.board_manager.list_ready_queue_tasks, status="PENDING"
            )

            if not ready_tasks:
                logger.debug("No PENDING tasks found in the ready queue.")
                return None

            # 2. Filter by type (if provided)
            if type_filter:
                ready_tasks = [
                    t for t in ready_tasks if t.get("task_type") == type_filter
                ]
                if not ready_tasks:
                    logger.debug(
                        f"No PENDING tasks found with type '{type_filter}' in ready queue."
                    )
                    return None

            # 3. Sort by Priority (assuming lower number is higher priority)
            # Handle missing or non-integer priorities gracefully
            def get_priority(task):
                p = task.get("priority")
                if isinstance(p, int):
                    return p
                # Basic mapping for string priorities (adjust as needed)
                if isinstance(p, str):
                    p_upper = p.upper()
                    if p_upper == "CRITICAL":
                        return -100
                    if p_upper == "HIGH":
                        return -50
                    if p_upper == "MEDIUM":
                        return 0
                    if p_upper == "LOW":
                        return 50
                return 999  # Default to lowest priority if unknown/missing

            ready_tasks.sort(key=get_priority)
            logger.debug(f"Sorted {len(ready_tasks)} ready tasks by priority.")

            # 4. Iterate through sorted tasks, check dependencies, and attempt claim
            agent_capabilities_set = None  # Lazy load agent capabilities

            for task in ready_tasks:
                candidate_task_id = task.get("task_id")
                if not candidate_task_id:
                    logger.warning(f"Skipping task with missing task_id: {task}")
                    continue

                # --- Capability Check (Existing logic) ---
                # (Keep existing capability check logic here...)
                required_capabilities = task.get("required_capabilities")
                if (
                    required_capabilities
                    and isinstance(required_capabilities, list)
                    and required_capabilities
                ):
                    if not self.capability_registry:
                        logger.warning(
                            f"Task {candidate_task_id} requires capabilities, but registry is unavailable. Skipping."
                        )
                        continue
                    if agent_capabilities_set is None:
                        try:
                            agent_caps_list = await self.get_agent_capabilities(
                                agent_id
                            )
                            agent_capabilities_set = {
                                cap.capability_id
                                for cap in agent_caps_list
                                if cap.is_active
                            }
                        except Exception as e_caps:
                            logger.error(
                                f"Failed to retrieve capabilities for agent {agent_id}: {e_caps}. Skipping capability check."
                            )
                            agent_capabilities_set = set()

                    if not set(required_capabilities).issubset(agent_capabilities_set):
                        logger.debug(
                            f"Agent {agent_id} missing capabilities for task {candidate_task_id}. Required: {required_capabilities}, Has: {agent_capabilities_set}. Skipping."
                        )
                        continue
                    else:
                        logger.debug(
                            f"Agent {agent_id} meets capability requirements for task {candidate_task_id}."
                        )
                # --- End Capability Check ---

                # --- Dependency Check ---
                dependencies = task.get("dependencies", [])
                if dependencies:
                    logger.debug(
                        f"Checking {len(dependencies)} dependencies for task {candidate_task_id}..."
                    )
                    dependencies_met = await self._check_dependencies_met(dependencies)
                    if not dependencies_met:
                        logger.debug(
                            f"Dependencies not met for task {candidate_task_id}. Skipping."
                        )
                        continue  # Skip to next task if dependencies not met
                    else:
                        logger.debug(f"Dependencies met for task {candidate_task_id}.")
                # -----------------------

                logger.info(
                    f"Agent {agent_id} attempting to claim highest priority available task: {candidate_task_id}"
                )
                # 5. Attempt atomic claim using the correct PBM method
                try:
                    claim_successful = await asyncio.to_thread(
                        self.board_manager.claim_ready_task, candidate_task_id, agent_id
                    )

                    if claim_successful:
                        logger.info(
                            f"Agent {agent_id} successfully claimed task {candidate_task_id} via ProjectBoardManager."
                        )
                        # Retrieve the claimed task data directly from PBM if possible, or re-read working
                        claimed_task_data = await asyncio.to_thread(
                            self.board_manager.get_task,
                            candidate_task_id,
                            board="working",
                        )
                        if not claimed_task_data:
                            logger.error(
                                f"Claim reported success, but task {candidate_task_id} could not be retrieved from working board!"
                            )
                        # Stop searching and return the claimed task
                        break  # <<< Exit loop once a task is claimed
                    else:
                        logger.warning(
                            f"Agent {agent_id} failed to claim task {candidate_task_id} (likely already claimed or lock timeout). Continuing search..."
                        )
                        # Continue to the next task in the priority list

                except (ProjectBoardError, TaskNotFoundError) as e_claim:
                    # Log expected errors during claim (e.g., not found because another agent claimed it first)
                    logger.warning(
                        f"Claim attempt failed for {candidate_task_id}: {e_claim}. Continuing search..."
                    )
                    continue  # Continue to the next task
                except Exception as e_unexp_claim:
                    logger.error(
                        f"Unexpected error during task claim for {candidate_task_id}: {e_unexp_claim}",
                        exc_info=True,
                    )
                    # Decide whether to stop or continue on unexpected errors
                    continue  # Continue for now

            # End of loop - if claimed_task_data is still None, no claimable task was found
            if not claimed_task_data:
                logger.debug(
                    f"No claimable tasks found for agent {agent_id} after checking {len(ready_tasks)} candidates."
                )

        except Exception as e_outer:
            logger.error(
                f"Error during get_next_task execution: {e_outer}", exc_info=True
            )
            claimed_task_data = None

        return claimed_task_data

    # --- Dependency Check Helper (Placeholder) ---
    async def _check_dependencies_met(self, dependency_ids: List[str]) -> bool:
        """Checks if all dependency tasks are marked COMPLETED."""
        if not dependency_ids:
            return True  # No dependencies means they are met

        if not self.board_manager:
            logger.error(
                "Cannot check dependencies: ProjectBoardManager not available."
            )
            return False  # Fail safe

        try:
            # Check status of each dependency
            for dep_id in dependency_ids:
                # Use PBM get_task which checks all relevant boards
                dep_task = await asyncio.to_thread(self.board_manager.get_task, dep_id)
                if not dep_task:
                    logger.warning(f"Dependency task {dep_id} not found on any board.")
                    return False  # Dependency not found
                # Only consider tasks explicitly COMPLETED
                if dep_task.get("status", "").upper() != "COMPLETED":
                    logger.debug(
                        f"Dependency task {dep_id} is not COMPLETED (status: {dep_task.get('status')})."
                    )
                    return False  # Dependency not met

            # If loop completes, all dependencies were found and COMPLETED
            logger.debug(f"All dependencies met: {dependency_ids}")
            return True
        except Exception as e:
            logger.error(
                f"Error checking dependencies {dependency_ids}: {e}", exc_info=True
            )
            return False  # Fail safe on error

    # --- End Dependency Check Helper ---

    async def add_task(self, task_dict):
        """
        Add a new task to the future tasks board with default status 'pending'.
        """
        task_dict.setdefault("status", "PENDING")  # Use PENDING consistently
        task_dict.setdefault(
            "created_at", datetime.now(timezone.utc).isoformat()
        )  # Add created timestamp
        task_dict.setdefault(
            "timestamp_updated", datetime.now(timezone.utc).isoformat()
        )
        # Ensure task_id exists
        if (
            "task_id" not in task_dict and "id" not in task_dict
        ):  # Check both common keys
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            task_dict["task_id"] = task_id
        else:
            task_id = task_dict.get(
                "task_id", task_dict.get("id")
            )  # Get existing ID for logging

        try:
            async with filelock.FileLock(
                self.future_tasks_lock_path, timeout=self.lock_timeout
            ):
                future_tasks = await self._load_json(
                    self.future_tasks_path, self.future_tasks_lock_path
                )
                if not isinstance(future_tasks, list):
                    logger.error(
                        f"Future tasks file {self.future_tasks_path} is not a list. Cannot add task."
                    )
                    return False  # Indicate failure
                future_tasks.append(task_dict)
                if await self._save_json(
                    self.future_tasks_path, self.future_tasks_lock_path, future_tasks
                ):
                    logger.info(
                        f"Added task {task_id} to {self.future_tasks_path.name}"
                    )
                    return True
                else:
                    logger.error(
                        f"Failed to save future tasks file after adding task {task_id}."
                    )
                    return False  # Save failed
        except LockAcquisitionError:
            logger.error(
                f"Timeout adding task {task_id}: Could not acquire lock {self.future_tasks_lock_path}."
            )
            return False
        except Exception as e:
            logger.error(
                f"Failed to add task {task_id} to {self.future_tasks_path.name}: {e}",
                exc_info=True,
            )
            return False

    async def update_task_status(
        self, task_id, status, agent_id=None, notes: Optional[str] = None, **kwargs
    ):
        """
        Update the status and notes of a task in the working_tasks board using ProjectBoardManager.
        Returns True on success, False otherwise.
        """
        if not self.board_manager:
            logger.error(
                "ProjectBoardManager not initialized, cannot update task status."
            )
            return False

        updates = {
            "status": status,
            "timestamp_updated": datetime.now(timezone.utc).isoformat(
                timespec="milliseconds"
            )
            + "Z",
        }
        if agent_id is not None:
            updates["assigned_agent"] = agent_id
        if notes is not None:
            # NOTE: Appending logic needs reconsideration. ProjectBoardManager expects a full
            # replacement value. The caller (Agent/Controller) should fetch existing notes
            # and construct the new combined notes if appending is desired.
            # For now, just pass the new notes directly.
            # existing_notes = task.get("notes", "")
            # updates["notes"] = f\"{existing_notes}\n---\n{notes}\" if existing_notes else notes
            updates["notes"] = notes

        # Include any other relevant kwargs allowed by the board manager's update method
        # (Need to align ProjectBoardManager.update_working_task if more fields are needed)
        allowed_extra_updates = {
            "result_status",
            "started_at",
            "completed_at",
            "result_data",
            "error_message",
            "progress",
            "scoring",
        }
        for key, value in kwargs.items():
            if key in allowed_extra_updates:
                updates[key] = value

        try:
            logger.info(
                f"Delegating update for task {task_id} to status {status} via ProjectBoardManager."
            )
            # Run the synchronous board manager method in a thread
            success = await asyncio.to_thread(
                self.board_manager.update_working_task, task_id, updates
            )
            if success:
                logger.info(f"ProjectBoardManager successfully updated task {task_id}.")
                return True
            else:
                logger.warning(
                    f"ProjectBoardManager failed to update task {task_id} (task not found or write error)."
                )
                return False
        except ProjectBoardError as e:
            logger.error(
                f"ProjectBoardError during task update delegation for {task_id}: {e}"
            )
            return False
        except Exception as e_unexp:
            logger.error(
                f"Unexpected error during task update delegation for {task_id}: {e_unexp}",
                exc_info=True,
            )
            return False

    async def get_all_tasks(
        self, board: str = "future", status_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Return all tasks from a specified board, optionally filtered by status.

        Args:
            board (str): Which board to load ('future', 'working', 'completed'). Defaults to 'future'.
            status_filter (Optional[str]): Status to filter by (e.g., 'PENDING', 'WORKING').
        """
        if board == "working":
            file_path = self.working_tasks_path
            lock_path = self.working_tasks_lock_path
        # elif board == 'completed': # Add if needed
        #     file_path = self.completed_tasks_path
        #     lock_path = self.completed_tasks_lock_path
        else:  # Default to future
            file_path = self.future_tasks_path
            lock_path = self.future_tasks_lock_path

        tasks = await self._load_json(file_path, lock_path)
        if not isinstance(tasks, list):
            logger.error(f"Task board file {file_path} did not contain a list.")
            return []

        if status_filter:
            # Case-insensitive status filter
            status_filter_upper = status_filter.upper()
            return [
                t
                for t in tasks
                if str(t.get("status", "")).upper() == status_filter_upper
            ]
        return tasks

    async def stats(self) -> dict[str, collections.Counter]:
        """Return a Counter of task statuses for each board."""
        stats_data = {}
        # Load latest tasks from each board
        future_tasks = await self.get_all_tasks(board="future")
        working_tasks = await self.get_all_tasks(board="working")
        # completed_tasks = await self.get_all_tasks(board='completed') # Add if completed board exists

        stats_data["future"] = Counter(
            str(task.get("status", "UNKNOWN")).upper() for task in future_tasks
        )
        stats_data["working"] = Counter(
            str(task.get("status", "UNKNOWN")).upper() for task in working_tasks
        )
        # stats_data['completed'] = Counter(task.get("status", "UNKNOWN")).upper() for task in completed_tasks)
        return stats_data

    async def reclaim_stale_tasks(
        self, stale_after: Optional[float] = None
    ) -> List[Dict]:
        """
        Scan for tasks in 'WORKING' state whose claiming agent heartbeat is older than stale_after seconds (or default TTL),
        reset them to 'PENDING', remove 'claimed_by', move them back to future_tasks, and return the list of reclaimed tasks.
        **NEEDS TESTING after multi-board refactor.**
        """
        if stale_after is None:
            stale_after = self.heartbeat_ttl  # Use default TTL if not specified

        reclaimed = []
        try:
            # Acquire all necessary locks
            # Nested async with ensures all locks are held or none are
            async with (
                filelock.FileLock(
                    self.agent_registry_lock_path, timeout=self.lock_timeout
                ),
                filelock.FileLock(
                    self.working_tasks_lock_path, timeout=self.lock_timeout
                ),
                filelock.FileLock(
                    self.future_tasks_lock_path, timeout=self.lock_timeout
                ),
            ):

                now = time.time()
                # Load state within locks
                agents = (
                    await self._load_agents()
                )  # Uses its own method which checks path
                working_tasks = await self._load_json(
                    self.working_tasks_path, self.working_tasks_lock_path
                )
                future_tasks = await self._load_json(
                    self.future_tasks_path, self.future_tasks_lock_path
                )

                if not isinstance(working_tasks, list) or not isinstance(
                    future_tasks, list
                ):
                    logger.error(
                        "Cannot reclaim stale tasks: One or both task board files are not lists."
                    )
                    return []

                tasks_to_move = []
                remaining_working_tasks = []

                for task in working_tasks:
                    # Check both WORKING and older CLAIMED status for robustness
                    if str(task.get("status", "")).upper() in ["WORKING", "CLAIMED"]:
                        agent = task.get(
                            "assigned_agent", task.get("claimed_by")
                        )  # Check both fields
                        last_hb = agents.get(agent)
                        if (
                            agent is None
                            or last_hb is None
                            or (now - last_hb) > stale_after
                        ):
                            task_id = task.get("task_id", task.get("id", "UNKNOWN"))
                            logger.warning(
                                f"Reclaiming stale task {task_id} claimed by {agent} (Last HB: {last_hb})"
                            )
                            # Mark task as pending and remove agent assignment
                            task["status"] = "PENDING"
                            task.pop("claimed_by", None)
                            task.pop("assigned_agent", None)
                            task["notes"] = (
                                f"(Reclaimed due to agent timeout at {datetime.now(timezone.utc).isoformat()}) "
                                + task.get("notes", "")
                            )
                            task["timestamp_updated"] = datetime.now(
                                timezone.utc
                            ).isoformat()
                            tasks_to_move.append(task)
                            reclaimed.append(task)  # Add to returned list
                        else:
                            remaining_working_tasks.append(task)  # Keep non-stale tasks
                    else:
                        remaining_working_tasks.append(
                            task
                        )  # Keep tasks with other statuses

                # Perform the move if any tasks were reclaimed
                if reclaimed:
                    future_tasks.extend(tasks_to_move)
                    # Save updated boards
                    save_working_ok = await self._save_json(
                        self.working_tasks_path,
                        self.working_tasks_lock_path,
                        remaining_working_tasks,
                    )
                    save_future_ok = await self._save_json(
                        self.future_tasks_path,
                        self.future_tasks_lock_path,
                        future_tasks,
                    )
                    if save_working_ok and save_future_ok:
                        logger.info(
                            f"Reclaimed and moved {len(reclaimed)} stale tasks back to future tasks."
                        )
                    else:
                        logger.critical(
                            f"CRITICAL: Failed to save one or both boards after reclaiming {len(reclaimed)} tasks! State may be inconsistent."
                        )
                        # Reclaimed list is still returned, but state is suspect
                else:
                    logger.debug("No stale tasks found to reclaim.")

        except LockAcquisitionError:
            logger.error(
                f"Timeout reclaiming stale tasks: Could not acquire all necessary locks."
            )
        except Exception as e:
            logger.error(f"Error reclaiming stale tasks: {e}", exc_info=True)

        return reclaimed

    # EDIT START: Add Capability Registry Passthrough Methods
    async def register_capability(self, capability: Any) -> bool:
        """Registers or updates a capability via the CapabilityRegistry."""
        if not self.capability_registry:
            logger.error(
                "CapabilityRegistry not initialized. Cannot register capability."
            )
            return False
        try:
            # Assuming CapabilityRegistry methods are synchronous for now
            return await asyncio.to_thread(
                self.capability_registry.register_capability, capability
            )
        except Exception as e:
            logger.error(
                f"Error calling capability_registry.register_capability: {e}",
                exc_info=True,
            )
            return False

    async def unregister_capability(self, agent_id: str, capability_id: str) -> bool:
        """Unregisters a capability via the CapabilityRegistry."""
        if not self.capability_registry:
            logger.error(
                "CapabilityRegistry not initialized. Cannot unregister capability."
            )
            return False
        try:
            return await asyncio.to_thread(
                self.capability_registry.unregister_capability, agent_id, capability_id
            )
        except Exception as e:
            logger.error(
                f"Error calling capability_registry.unregister_capability: {e}",
                exc_info=True,
            )
            return False

    async def get_capability(self, agent_id: str, capability_id: str) -> Optional[Any]:
        """Retrieves a specific capability via the CapabilityRegistry."""
        if not self.capability_registry:
            logger.error("CapabilityRegistry not initialized. Cannot get capability.")
            return None
        try:
            return await asyncio.to_thread(
                self.capability_registry.get_capability, agent_id, capability_id
            )
        except Exception as e:
            logger.error(
                f"Error calling capability_registry.get_capability: {e}", exc_info=True
            )
            return None

    async def get_agent_capabilities(self, agent_id: str) -> List[Any]:
        """Retrieves all capabilities for an agent via the CapabilityRegistry."""
        if not self.capability_registry:
            logger.error(
                "CapabilityRegistry not initialized. Cannot get agent capabilities."
            )
            return []
        try:
            return await asyncio.to_thread(
                self.capability_registry.get_agent_capabilities, agent_id
            )
        except Exception as e:
            logger.error(
                f"Error calling capability_registry.get_agent_capabilities: {e}",
                exc_info=True,
            )
            return []

    async def find_capabilities(self, query: Dict[str, Any]) -> List[Any]:
        """Finds capabilities matching criteria via the CapabilityRegistry."""
        if not self.capability_registry:
            logger.error(
                "CapabilityRegistry not initialized. Cannot find capabilities."
            )
            return []
        try:
            return await asyncio.to_thread(
                self.capability_registry.find_capabilities, query
            )
        except Exception as e:
            logger.error(
                f"Error calling capability_registry.find_capabilities: {e}",
                exc_info=True,
            )
            return []

    async def find_agents_for_capability(
        self, capability_id: str, require_active: bool = True
    ) -> List[str]:
        """Finds agent IDs that offer a specific capability via the CapabilityRegistry."""
        if not self.capability_registry:
            logger.error(
                "CapabilityRegistry not initialized. Cannot find agents for capability."
            )
            return []
        try:
            return await asyncio.to_thread(
                self.capability_registry.find_agents_for_capability,
                capability_id,
                require_active,
            )
        except Exception as e:
            logger.error(
                f"Error calling capability_registry.find_agents_for_capability: {e}",
                exc_info=True,
            )
            return []

    # EDIT START: Add wrapper for update_capability_status
    async def update_capability_status(
        self,
        agent_id: str,
        capability_id: str,
        is_active: Optional[bool] = None,
        last_verified_utc: Optional[str] = None,
    ) -> bool:
        """Updates capability status fields via the CapabilityRegistry."""
        if not self.capability_registry:
            logger.error(
                "CapabilityRegistry not initialized. Cannot update capability status."
            )
            return False
        try:
            return await asyncio.to_thread(
                self.capability_registry.update_capability_status,
                agent_id,
                capability_id,
                is_active=is_active,
                last_verified_utc=last_verified_utc,
            )
        except Exception as e:
            logger.error(
                f"Error calling capability_registry.update_capability_status: {e}",
                exc_info=True,
            )
            return False

    # EDIT END
