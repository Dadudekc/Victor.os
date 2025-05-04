import asyncio
import logging
import uuid
import collections
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from ..comms.project_board import ProjectBoardManager
from ..errors import ProjectBoardError, TaskNotFoundError
from .capability_handler import CapabilityHandler # To check capabilities

logger = logging.getLogger(__name__)

class TaskOperationsHandler:
    """Handles core task operations like getting, adding, updating, and checking dependencies."""

    def __init__(
        self,
        board_manager: ProjectBoardManager,
        capability_handler: CapabilityHandler,
        # agent_registry_handler: AgentRegistryHandler, # Needed for dependency check - PBM handles now?
        future_tasks_path: Path, # Needed for add_task
        future_tasks_lock_path: Path # Needed for add_task
    ):
        self.board_manager = board_manager
        self.capability_handler = capability_handler
        # self.agent_registry_handler = agent_registry_handler
        self.future_tasks_path = future_tasks_path
        self.future_tasks_lock_path = future_tasks_lock_path

        if not self.board_manager:
            logger.error("TaskOperationsHandler initialized without a ProjectBoardManager!")
        if not self.capability_handler:
             logger.error("TaskOperationsHandler initialized without a CapabilityHandler!")

    # --- Dependency Check Helper --- (Moved from TaskNexus)
    async def _check_dependencies_met(self, dependency_ids: List[str]) -> bool:
        """Checks if all dependency tasks are marked COMPLETED using ProjectBoardManager."""
        if not dependency_ids:
            return True
        if not self.board_manager:
            logger.error("Cannot check dependencies: ProjectBoardManager not available.")
            return False

        try:
            all_met = True
            for dep_id in dependency_ids:
                dep_task = await asyncio.to_thread(self.board_manager.get_task, dep_id)
                if not dep_task:
                    logger.warning(f"Dependency task {dep_id} not found on any board.")
                    all_met = False
                    break
                if dep_task.get("status", "").upper() != "COMPLETED":
                    logger.debug(f"Dependency task {dep_id} not COMPLETED (status: {dep_task.get('status')}).")
                    all_met = False
                    break

            if all_met:
                logger.debug(f"All dependencies met: {dependency_ids}")
            return all_met
        except Exception as e:
            logger.error(f"Error checking dependencies {dependency_ids}: {e}", exc_info=True)
            return False

    # --- Get Next Task --- (Moved from TaskNexus)
    async def get_next_task(self, agent_id: str, type_filter: Optional[str] = None) -> Optional[Dict]:
        """Claims and returns the next available task, checking capabilities and dependencies."""
        if not self.board_manager:
            logger.error("ProjectBoardManager not available, cannot get next task.")
            return None
        if not self.capability_handler:
             logger.warning("CapabilityHandler not available, cannot check capabilities.")
             # Proceed without capability check if handler missing?

        claimed_task_data = None
        try:
            ready_tasks = await asyncio.to_thread(self.board_manager.list_ready_queue_tasks, status="PENDING")
            if not ready_tasks:
                return None

            if type_filter:
                ready_tasks = [t for t in ready_tasks if t.get("task_type") == type_filter]
                if not ready_tasks: return None

            def get_priority(task):
                p = task.get("priority")
                if isinstance(p, int): return p
                if isinstance(p, str):
                    p_upper = p.upper()
                    if p_upper == "CRITICAL": return -100
                    if p_upper == "HIGH": return -50
                    if p_upper == "MEDIUM": return 0
                    if p_upper == "LOW": return 50
                return 999
            ready_tasks.sort(key=get_priority)

            agent_capabilities_set = None # Lazy load
            for task in ready_tasks:
                candidate_task_id = task.get("task_id")
                if not candidate_task_id: continue

                # Capability Check
                required_capabilities = task.get("required_capabilities")
                if required_capabilities and isinstance(required_capabilities, list) and self.capability_handler:
                    if agent_capabilities_set is None:
                        try:
                            agent_caps_list = await self.capability_handler.get_agent_capabilities(agent_id)
                            agent_capabilities_set = {cap.capability_id for cap in agent_caps_list if cap.is_active}
                        except Exception as e_caps:
                            logger.error(f"Failed to get capabilities for {agent_id}: {e_caps}. Skipping check.")
                            agent_capabilities_set = set()

                    if not set(required_capabilities).issubset(agent_capabilities_set):
                        logger.debug(f"Agent {agent_id} missing capabilities for {candidate_task_id}. Skipping.")
                        continue

                # Dependency Check
                dependencies = task.get("dependencies", [])
                if dependencies:
                    if not await self._check_dependencies_met(dependencies):
                        logger.debug(f"Dependencies not met for {candidate_task_id}. Skipping.")
                        continue

                # Attempt Claim
                logger.info(f"Agent {agent_id} attempting to claim task: {candidate_task_id}")
                try:
                    claim_successful = await asyncio.to_thread(
                        self.board_manager.claim_ready_task, candidate_task_id, agent_id
                    )
                    if claim_successful:
                        logger.info(f"Agent {agent_id} successfully claimed {candidate_task_id}.")
                        claimed_task_data = await asyncio.to_thread(
                            self.board_manager.get_task, candidate_task_id, board="working"
                        )
                        if not claimed_task_data:
                            logger.error(f"Claim success but failed to retrieve {candidate_task_id} from working board!")
                        break # Exit loop on successful claim
                    else:
                        logger.warning(f"Agent {agent_id} failed claim for {candidate_task_id} (likely claimed/lock timeout).")
                except (ProjectBoardError, TaskNotFoundError) as e_claim:
                    logger.warning(f"Claim failed for {candidate_task_id}: {e_claim}. Continuing search.")
                except Exception as e_unexp_claim:
                    logger.error(f"Unexpected error during claim for {candidate_task_id}: {e_unexp_claim}", exc_info=True)

            if not claimed_task_data:
                logger.debug(f"No claimable tasks found for agent {agent_id}.")

        except Exception as e_outer:
            logger.error(f"Error in get_next_task: {e_outer}", exc_info=True)

        return claimed_task_data

    # --- Add Task --- (Moved from TaskNexus, now simpler)
    async def add_task(self, task_dict: Dict) -> bool:
        """Adds a task to the future queue via ProjectBoardManager."""
        if not self.board_manager:
            logger.error("ProjectBoardManager not available, cannot add task.")
            return False

        task_dict.setdefault("status", "PENDING")
        if "task_id" not in task_dict and "id" not in task_dict:
            task_dict["task_id"] = f"task_{uuid.uuid4().hex[:8]}"
        task_id = task_dict.get("task_id", task_dict.get("id"))
        task_dict.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        task_dict["timestamp_updated"] = datetime.now(timezone.utc).isoformat()

        try:
            success = await asyncio.to_thread(self.board_manager.add_future_task, task_dict)
            if success:
                logger.info(f"Added task {task_id} to future queue via ProjectBoardManager.")
            else:
                 logger.warning(f"ProjectBoardManager failed to add task {task_id}.")
            return success
        except Exception as e:
            logger.error(f"Error adding task {task_id}: {e}", exc_info=True)
            return False

    # --- Update Task Status --- (Moved from TaskNexus, still needs careful review)
    async def update_task_status(
        self, task_id: str, status: str, agent_id: Optional[str] = None, notes: Optional[str] = None, **kwargs
    ) -> bool:
        """Updates a task's status and other fields on the working board via ProjectBoardManager."""
        if not self.board_manager:
            logger.error("ProjectBoardManager not available, cannot update task status.")
            return False

        updates = {
            "status": status,
            "timestamp_updated": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
        }
        if agent_id is not None:
            updates["assigned_agent"] = agent_id # PBM should handle claimed_by logic
        if notes is not None:
            # PBM expects full replacement, caller should handle appending if needed
            updates["notes"] = notes

        # Allow common extra fields to be passed through
        allowed_extra_updates = {
            "result_status", "started_at", "completed_at", "result_data",
            "error_message", "progress", "scoring"
        }
        for key, value in kwargs.items():
            if key in allowed_extra_updates:
                updates[key] = value
            else:
                logger.warning(f"Ignoring disallowed extra update field '{key}' in update_task_status.")

        try:
            log_msg = f"Delegating update for task {task_id} to status {status} via ProjectBoardManager."
            logger.info(log_msg)
            success = await asyncio.to_thread(
                self.board_manager.update_working_task, task_id, updates
            )
            if success:
                logger.info(f"ProjectBoardManager successfully updated task {task_id}.")
            else:
                logger.warning(f"ProjectBoardManager failed to update task {task_id} (task not found or write error).")
            return success
        # THIS IS THE BLOCK WITH THE ORIGINAL SYNTAX ERROR - ensure it's correct here
        except ProjectBoardError as e:
            logger.error(f"ProjectBoardError during task update delegation for {task_id}: {e}")
            return False
        except Exception as e_unexp: # Catch unexpected errors during delegation
            logger.error(f"Unexpected error during task update delegation for {task_id}: {e_unexp}", exc_info=True)
            return False
        # Removed the outer mis-indented except block from original TaskNexus

    # --- Get All Tasks / Stats --- (Moved from TaskNexus)
    async def get_all_tasks(self, board: str, status_filter: Optional[str] = None) -> List[Dict]:
        """Gets all tasks from a board via ProjectBoardManager."""
        if not self.board_manager:
            logger.error("ProjectBoardManager not available, cannot get tasks.")
            return []
        try:
            tasks = []
            if board == "working":
                tasks = await asyncio.to_thread(self.board_manager.list_working_queue_tasks, status=status_filter)
            elif board == "ready": # Assuming 'ready' queue is equivalent to 'future'
                tasks = await asyncio.to_thread(self.board_manager.list_ready_queue_tasks, status=status_filter)
            elif board == "completed":
                tasks = await asyncio.to_thread(self.board_manager.list_completed_queue_tasks, status=status_filter)
            else:
                logger.warning(f"Unsupported board '{board}' specified for get_all_tasks. Use 'working', 'ready', or 'completed'.")
                return []

            # PBM methods already handle filtering, so no extra filtering needed here.
            return tasks
        except Exception as e:
            logger.error(f"Error getting tasks from board '{board}': {e}", exc_info=True)
            return []

    async def stats(self) -> dict[str, collections.Counter]:
        """Return a Counter of task statuses for each board managed by PBM."""
        stats_data = {}
        if not self.board_manager:
            logger.error("ProjectBoardManager not available, cannot get stats.")
            return stats_data
        try:
            ready_tasks = await self.get_all_tasks(board="ready")
            working_tasks = await self.get_all_tasks(board="working")
            completed_tasks = await self.get_all_tasks(board="completed")

            stats_data["ready"] = collections.Counter(str(task.get("status", "UNKNOWN")).upper() for task in ready_tasks)
            stats_data["working"] = collections.Counter(str(task.get("status", "UNKNOWN")).upper() for task in working_tasks)
            stats_data["completed"] = collections.Counter(str(task.get("status", "UNKNOWN")).upper() for task in completed_tasks)
        except Exception as e:
            logger.error(f"Error generating task stats: {e}", exc_info=True)
        return stats_data 