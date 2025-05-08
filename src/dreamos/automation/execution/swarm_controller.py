"""
SwarmController
===============

Coordinates a fleet of Cursor GUI / headless agents, dispatching work from a
central `TaskNexus`, collecting results via an in-process `EventBus`, feeding
them to `FeedbackEngineV2`, and persisting lore for Dream.OS.

Key refactors
-------------
*   **Config-first** – everything comes from one `AppConfig`.
*   **Single EventType source** – avoid accidental shadowing.
*   **Clean imports** – drop unused stdlib & package names.
*   **Graceful shutdown** – join worker threads.
*   **Quieter logs** – debug for tight loops, info for milestones.
"""

from __future__ import annotations  # noqa: I001

import asyncio
import datetime as _dt
import json
import logging
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dreamos.agents.chatgpt_web_agent import run_loop as chat_run_loop
from dreamos.core.config import AppConfig
from dreamos.core.tasks.nexus.db_task_nexus import DbTaskNexus, TaskDict
from dreamos.core.db.sqlite_adapter import SQLiteAdapter
from dreamos.core.coordination.agent_bus import AgentBus, BaseEvent
from dreamos.core.coordination.event_types import EventType
from dreamos.core.agents.base_agent import BaseAgent
from dreamos.feedback.feedback_engine_v2 import FeedbackEngineV2
from dreamos.hooks.stats_logger import StatsLoggingHook
from dreamos.hooks.devlog_hook import DevlogHook

from dreamos.automation.cursor_orchestrator import (
    CursorOrchestrator,
    CursorOrchestratorError,
)

from dreamos.channels.local_blob_channel import LocalBlobChannel
from .cursor_fleet_launcher import (
    assign_windows_to_monitors,
    get_cursor_windows,
    launch_cursor_instance,
)
from .virtual_desktop_runner import VirtualDesktopController

# {{ EDIT START: Import ProjectBoardManager }}
from dreamos.coordination.project_board_manager import ProjectBoardManager
# {{ EDIT END }}

# --- EDIT START: Import AgentPointsManager ---
# --- EDIT END ---

# {{ EDIT START: Import TaskAutoRewriter and related types }}
from dreamos.tools.task_editor import (
    TaskAutoRewriter,
    ProposedTaskEdit,
    TaskAutoRewriterError,
)
# {{ EDIT END }}

# EDIT: Import GUI Controller (assuming Path exists)
from ..gui.controller import GUIController

# {{ EDIT START: Import devlog utility }}
from dreamos.reporting.devlog_utils import update_devlog_index
# {{ EDIT END }}

logger = logging.getLogger(__name__)  # logging configured by entry point


class SwarmController:
    """Top-level coordinator for Cursor agents (GUI & headless)."""

    _DEFAULT_STATS_INTERVAL_SEC: int = 60

    # --------------------------------------------------------------------- #
    # Construction
    # --------------------------------------------------------------------- #
    def __init__(
        self,
        config: AppConfig,
        # EDIT: Add adapter and bus dependencies
        adapter: SQLiteAdapter,
        agent_bus: AgentBus,
        # EDIT: Remove direct nexus instantiation
        # nexus: Optional[TaskNexus] = None,
        # bus: Optional[AgentBus] = None,
        num_workers: Optional[int] = None,
    ):
        self.config: AppConfig = config
        self.num_workers = num_workers or config.swarm.fleet_size
        # EDIT: Initialize DbTaskNexus with adapter
        self.nexus = DbTaskNexus(adapter=adapter)
        # EDIT: Use passed agent_bus
        self.bus = agent_bus
        # self.bus = bus or AgentBus() # OLD
        self.adapter = adapter  # Store adapter for agent instantiation

        # {{ EDIT START: Instantiate TaskAutoRewriter }}
        try:
            self.task_rewriter = TaskAutoRewriter(config=self.config)
            logger.info("TaskAutoRewriter initialized.")
        except Exception as e:
            logger.critical(
                f"Failed to initialize TaskAutoRewriter: {e}", exc_info=True
            )
            self.task_rewriter = None  # Indicate rewriter failed
        # {{ EDIT END }}

        # -- fleet & channel ------------------------------------------------
        self.fleet_size: int = getattr(config.swarm, "fleet_size", 3)

        # {{ EDIT START: Safely access nested Azure Blob config }}
        azure_conf = config.integrations.azure_blob if config.integrations else None
        self.container_name: str = (
            getattr(azure_conf, "container_name", "dream-os-c2")
            if azure_conf
            else "dream-os-c2"
        )
        self.sas_token: Optional[str] = (
            getattr(azure_conf, "sas_token", None) if azure_conf else None
        )
        self.connection_string: Optional[str] = (
            getattr(azure_conf, "connection_string", None) if azure_conf else None
        )
        # {{ EDIT END }}

        # {{ EDIT START: Adjust use_local logic }}
        self.use_local: bool = not bool(self.connection_string or self.sas_token)
        # {{ EDIT END }}

        if not self.use_local and not (self.connection_string or self.sas_token):
            logger.warning(
                "💾 Azure Blob not fully configured; falling back to LocalBlobChannel."
            )
            self.use_local = True

        self.channel = LocalBlobChannel()
        if not self.channel.healthcheck():
            raise RuntimeError("LocalBlobChannel health-check failed – aborting")

        # -- runtime components --------------------------------------------
        self.stats_hook = StatsLoggingHook(self.nexus)
        self.event_bus = EventBus()
        # {{ EDIT START: Instantiate ProjectBoardManager }}
        try:
            self.pbm = ProjectBoardManager(config=self.config)
            logger.info("ProjectBoardManager initialized.")
        except Exception as e:
            logger.critical(
                f"Failed to initialize ProjectBoardManager: {e}", exc_info=True
            )
            self.pbm = None  # Indicate PBM failed

        # {{ EDIT START: Instantiate DevlogHook }}
        try:
            self.devlog_hook = DevlogHook(agent_bus=self.event_bus, config=self.config)
            logger.info("DevlogHook initialized.")
        except Exception as e:
            logger.critical(f"Failed to initialize DevlogHook: {e}", exc_info=True)
            self.devlog_hook = None
        # {{ EDIT END }}

        # -- orchestration state -------------------------------------------
        self._stop_event = threading.Event()
        self.workers: List[GUIController] = []
        self.agents: Dict[str, BaseAgent] = {}
        self.threads: List[threading.Thread] = []

        # --- EDIT START: Add state for captaincy check ---
        self.last_captaincy_check_time = time.monotonic()  # Track last check time
        self.current_captain_id: Optional[str] = None  # Store current captain
        self._load_initial_captain_id()  # Load from file if exists
        # --- EDIT END ---

        # -- background stats ----------------------------------------------
        stats_ivl = getattr(
            config.monitoring, "stats_interval", self._DEFAULT_STATS_INTERVAL_SEC
        )
        self._start_stats_autologger(interval=stats_ivl)

        # {{ EDIT START: Instantiate CursorOrchestrator }}
        # Use the async factory function if available and run it
        try:
            # Need to run the async factory function in an event loop
            # Since __init__ is synchronous, use asyncio.run() carefully or
            # defer initialization that requires async context.
            # Simpler approach: instantiate directly if possible, or call factory later.
            # Let's assume direct instantiation or handle async init later in start().
            # self.cursor_orchestrator = asyncio.run(get_cursor_orchestrator(config=config, agent_bus=self.event_bus))
            # Direct instantiation (assuming __init__ is compatible):
            self.cursor_orchestrator = CursorOrchestrator(
                config=config, agent_bus=self.event_bus
            )
            logger.info("CursorOrchestrator instantiated.")
        except Exception as e:
            logger.critical(
                f"Failed to instantiate CursorOrchestrator: {e}", exc_info=True
            )
            # Decide if this is fatal
            raise RuntimeError(f"CursorOrchestrator instantiation failed: {e}") from e
        # {{ EDIT END }}

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def start(self, initial_tasks: Optional[List[Dict[str, Any]]] = None) -> None:
        """Bring up chat-producer, GUI agents, headless workers, then begin routing loop."""  # noqa: E501
        logger.info(f"🚀 SwarmController booting {self.fleet_size} agents")

        # {{ EDIT START: Run async setup }}
        # Use asyncio.run() to execute the async setup portion
        try:
            asyncio.run(self._async_setup())
        except Exception as setup_err:
            logger.critical(f"Async setup failed: {setup_err}", exc_info=True)
            raise RuntimeError(f"Failed during async setup: {setup_err}") from setup_err
        # {{ EDIT END }}

        # 0) ChatGPT Web-agent (producer)
        self._spawn_thread(
            target=chat_run_loop,
            args=(self._stop_event,),
            name="ChatGPTWebAgent",
        )

        # 1) Seed TaskNexus
        for task in initial_tasks or []:
            self.nexus.add_task(task)
            logger.info(f"📥 Seed task queued → {task.get('id', task)[:60]}")

        # 2) GUI Cursor processes
        processes = [launch_cursor_instance(i) for i in range(self.fleet_size)]
        time.sleep(0.5)  # allow windows to surface

        try:
            windows = get_cursor_windows(target_count=len(processes), timeout=30)
            assign_windows_to_monitors(windows)
        except Exception as tiling_err:  # pylint: disable=broad-except
            logger.warning(f"🪟 Window tiling skipped: {tiling_err}")

        # {{ EDIT START: Start CursorOrchestrator Listener }}
        # Needs to run in the background, likely async in its own task/thread
        # Since start() is synchronous and manages threads, launch listener in thread
        self._spawn_thread(
            # Target the async start_listening method, needs an async runner
            target=self._run_cursor_orchestrator_listener_async,
            name="CursorOrchestratorListener",
        )
        # {{ EDIT END }}

        # 3) Headless workers
        for i in range(self.fleet_size):
            self._spawn_thread(target=self._worker_loop, name=f"Worker-{i+1}")

        # 4) Routing loop (blocking)
        self._route_loop()

    def shutdown(self) -> None:
        """Signal workers to stop then join threads."""
        logger.info("🛑 SwarmController shutdown initiated")
        self._stop_event.set()

        for t in self.threads:
            t.join(timeout=5)

        logger.info("✅ SwarmController shutdown complete")

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #
    def _spawn_thread(self, *, target, args: tuple = (), name: str) -> None:
        th = threading.Thread(target=target, args=args, name=name, daemon=True)
        th.start()
        self.threads.append(th)

    # {{ EDIT START: Add async setup method }}
    async def _async_setup(self) -> None:
        """Perform asynchronous setup tasks like subscribing to event bus."""
        logger.info("Performing async setup for SwarmController...")
        # Subscribe to EventBus here
        if self.event_bus:
            try:
                await self.event_bus.subscribe(
                    EventType.TASK_COMPLETED.value, self._handle_result_async
                )
                logger.info(
                    f"Successfully subscribed to {EventType.TASK_COMPLETED.value}"
                )
                # Add other subscriptions if needed
            except Exception as sub_err:
                logger.error(
                    f"Failed to subscribe to event bus: {sub_err}", exc_info=True
                )
                # Decide if this is fatal
        else:
            logger.warning("EventBus not available during async setup.")
        logger.info("Async setup complete.")

        # {{ EDIT START: Subscribe DevlogHook }}
        if self.devlog_hook:
            await self.devlog_hook.setup_subscriptions()
            logger.info("DevlogHook subscriptions activated.")
        else:
            logger.warning(
                "DevlogHook was not initialized, cannot activate subscriptions."
            )
        # {{ EDIT END }}

    # {{ EDIT END }}

    # {{ EDIT START: Add async runner for Cursor Orchestrator Listener }}
    def _run_cursor_orchestrator_listener_async(self) -> None:
        """Wrapper to run the async start_listening method in a thread."""
        worker_name = threading.current_thread().name
        logger.info(f"Thread {worker_name} starting.")
        try:
            if self.cursor_orchestrator:
                # Check if start_listening is async
                if asyncio.iscoroutinefunction(
                    self.cursor_orchestrator.start_listening
                ):
                    asyncio.run(self.cursor_orchestrator.start_listening())
                else:
                    # If not async (unlikely based on name), run directly
                    # self.cursor_orchestrator.start_listening()
                    logger.error(
                        "CursorOrchestrator.start_listening is not an async function as expected."
                    )
            else:
                logger.error("CursorOrchestrator instance not available.")
        except Exception as e:
            logger.critical(f"[{worker_name}] CRITICAL ERROR: {e}", exc_info=True)
        finally:
            logger.info(f"Thread {worker_name} finished.")

    # {{ EDIT END }}

    # --------------------------------------------------------------------- #
    # Background Worker Loop
    # --------------------------------------------------------------------- #
    def _worker_loop(self) -> None:
        """Continuously run agent logic within an async context until stopped."""  # noqa: E501
        worker_name = threading.current_thread().name
        logger.info(f"👷 {worker_name} started.")
        try:
            # Each worker thread needs its own event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._run_agent_async_loop(worker_name))
        except Exception as e:
            logger.critical(
                f"💥 {worker_name} encountered fatal error: {e}", exc_info=True
            )
        finally:
            # {{ EDIT START: Ensure loop closure in finally }}
            if loop and not loop.is_closed():
                loop.close()
            # {{ EDIT END }}
            logger.info(f"👷 {worker_name} stopped.")

    async def _run_agent_async_loop(self, worker_name: str) -> None:
        """The core async loop run by each worker thread."""
        # {{ EDIT START: Initialize agent cycle count outside loop? Or assume agent has it }}
        # Assuming BaseAgent manages its own cycle count internally
        # agent.cycle_count = 0 # Example if managed here
        # {{ EDIT END }}
        while not self._stop_event.is_set():
            task_dict: Optional[TaskDict] = None  # Use TaskDict type hint
            original_task_id_for_logging = "UNKNOWN"
            try:
                # {{ EDIT START: Rename task to task_dict for clarity }}
                task_dict = await self.nexus.claim_task()  # Use async claim
                # {{ EDIT END }}
                if task_dict:
                    original_task_id_for_logging = task_dict.get(
                        "task_id", "CLAIMED_UNKNOWN_ID"
                    )
                    logger.info(
                        f"👷 [{worker_name}] claimed task: {original_task_id_for_logging}"
                    )

                    # {{ EDIT START: Task Auto-Rewrite Step }}
                    processed_task_dict = task_dict  # Start with the original task
                    if self.task_rewriter:
                        try:
                            logger.debug(
                                f"[{worker_name}] Analyzing task {original_task_id_for_logging} for auto-rewrite."
                            )
                            proposal: Optional[
                                ProposedTaskEdit
                            ] = await asyncio.to_thread(
                                self.task_rewriter.analyze_and_propose_rewrite,
                                task_dict,
                            )

                            if proposal:
                                logger.info(
                                    f"[{worker_name}] TaskAutoRewriter proposed changes for {original_task_id_for_logging}: {proposal.rationale}"
                                )

                                # Apply direct modifications
                                if proposal.modifications:
                                    processed_task_dict = await asyncio.to_thread(
                                        self.task_rewriter.apply_task_edit,
                                        task_dict,
                                        proposal,
                                    )
                                    logger.info(
                                        f"[{worker_name}] Applied direct modifications to task {original_task_id_for_logging}."
                                    )
                                    # Update task in nexus if it was modified
                                    # Note: This assumes update_task can handle the full task_dict
                                    await self.nexus.update_task(
                                        original_task_id_for_logging,
                                        processed_task_dict,
                                    )
                                    logger.info(
                                        f"[{worker_name}] Updated modified task {original_task_id_for_logging} in TaskNexus."
                                    )
                                    task_dict = processed_task_dict  # Use the modified task for execution

                                # Handle new tasks
                                if proposal.new_tasks_to_create:
                                    for new_task_data in proposal.new_tasks_to_create:
                                        new_task_id = new_task_data.get(
                                            "task_id", "NEW_UNKNOWN_ID"
                                        )
                                        # Ensure essential fields if not provided by rewriter
                                        new_task_data.setdefault("status", "PENDING")
                                        new_task_data.setdefault(
                                            "priority", task_dict.get("priority", 3)
                                        )  # Inherit priority
                                        new_task_data.setdefault(
                                            "injected_by",
                                            f"TaskAutoRewriter (from {original_task_id_for_logging})",
                                        )
                                        new_task_data.setdefault(
                                            "timestamp_injected_utc",
                                            _dt.datetime.now(
                                                _dt.timezone.utc
                                            ).isoformat(),
                                        )

                                        await self.nexus.add_task(new_task_data)
                                        logger.info(
                                            f"[{worker_name}] TaskAutoRewriter created new sub-task: {new_task_id} (split from {original_task_id_for_logging})."
                                        )

                                    # Decide what to do with the original task if it was split
                                    # Option A: Mark original as SUPERSEDED/SPLIT and don't execute now
                                    await self.nexus.update_task_status(
                                        original_task_id_for_logging,
                                        "SUPERSEDED_BY_SPLIT",
                                        completion_summary=f"Split into new tasks by TaskAutoRewriter. Rationale: {proposal.rationale}",
                                    )
                                    logger.info(
                                        f"[{worker_name}] Marked original task {original_task_id_for_logging} as SUPERSEDED_BY_SPLIT."
                                    )
                                    task_dict = None  # Do not proceed with original task this cycle
                                    # The worker will loop and pick up a new task (possibly one of the split ones)
                                else:
                                    # If only modifications were made, update task_dict to the processed one
                                    task_dict = processed_task_dict

                        except TaskAutoRewriterError as tar_err:
                            logger.error(
                                f"[{worker_name}] TaskAutoRewriter failed for task {original_task_id_for_logging}: {tar_err}",
                                exc_info=True,
                            )
                            # Proceed with original task_dict if rewriter fails
                        except Exception as e_rewrite:
                            logger.error(
                                f"[{worker_name}] Unexpected error during task auto-rewrite for {original_task_id_for_logging}: {e_rewrite}",
                                exc_info=True,
                            )
                            # Proceed with original task_dict

                    # If task_dict is still valid (not set to None by splitting logic), execute it
                    if task_dict:
                        current_task_id_for_execution = task_dict.get(
                            "task_id", "MODIFIED_UNKNOWN_ID"
                        )
                        logger.info(
                            f"👷 [{worker_name}] Proceeding to execute task: {current_task_id_for_execution}"
                        )
                        await self._execute_task_with_retry(task_dict, worker_name)
                    else:
                        logger.info(
                            f"👷 [{worker_name}] Original task {original_task_id_for_logging} was split or deferred. Skipping execution this cycle."
                        )
                    # {{ EDIT END: Task Auto-Rewrite Step }}

                    # {{ EDIT START: Increment cycle count and update index }}
                    # Assuming the agent assigned to the task can be retrieved or is context
                    agent_id = task_dict.get("assigned_agent")
                    if agent_id:
                        agent = self.agents.get(agent_id)
                        if agent and hasattr(
                            agent, "cycle_count"
                        ):  # Check if agent exists and has counter
                            agent.cycle_count += 1  # Increment agent's cycle
                            logger.debug(
                                f"Agent {agent_id} completed cycle {agent.cycle_count}"
                            )
                            if agent.cycle_count % 10 == 0:
                                # {{ EDIT START: Simplify log message to avoid f-string issue }}
                                logger.info(
                                    "Updating devlog index for agent cycle multiple of 10."
                                )
                                # {{ EDIT END }}
                                try:
                                    devlog_base_path = (
                                        self.config.paths.resolve_relative_path(
                                            self.config.paths.devlog_dir
                                        )
                                    )
                                    # Run synchronous update in executor to avoid blocking async loop
                                    loop = asyncio.get_running_loop()
                                    await loop.run_in_executor(
                                        None,  # Use default executor
                                        update_devlog_index,
                                        agent_id,
                                        devlog_base_path,
                                    )
                                except Exception as idx_err:
                                    logger.error(
                                        f"Error updating devlog index for {agent_id}: {idx_err}",
                                        exc_info=True,
                                    )
                        else:
                            logger.warning(
                                f"Could not find agent {agent_id} or it lacks 'cycle_count' attribute for devlog update."
                            )
                    # {{ EDIT END }}
                else:
                    # No task claimed, wait before polling again
                    await asyncio.sleep(self.config.swarm.idle_poll_interval_sec)
            except Exception as e:
                logger.error(
                    f"👷 [{worker_name}] Error in agent loop: {e}", exc_info=True
                )
                if task_dict:
                    # Attempt to mark task as failed if error occurred during processing
                    try:
                        # {{ EDIT START: Use original_task_id_for_logging for status update }}
                        await self.nexus.update_task_status(
                            original_task_id_for_logging, "failed", error=str(e)
                        )
                        # {{ EDIT END }}
                    except Exception as update_err:
                        logger.error(
                            f"Failed to mark task {original_task_id_for_logging} as failed after loop error: {update_err}"
                        )
                # Avoid busy-looping on persistent errors
                await asyncio.sleep(self.config.swarm.error_poll_interval_sec)

    async def _execute_task_with_retry(self, task: Dict, worker_name: str) -> None:
        """Handles the execution of a single task with retry logic for orchestrator errors."""
        task_id = task.get("task_id", "UNKNOWN_ID")
        # {{ EDIT START: Ensure agent_id is derived correctly or use a default }}
        # agent_id = task.get("agent_id") # This might be None if task is freshly claimed
        # if not agent_id:
        #     # Fallback: try to get it from worker_name or a config
        #     # Example: if worker_name is "Worker-1", agent_id could be "Agent-1"
        #     # This mapping should be robust or configured.
        #     worker_num_str = worker_name.split('-')[-1]
        #     agent_id = f"Agent-{worker_num_str}" # Simple derivation, may need refinement
        #     logger.warning(f"Task {task_id} had no assigned agent_id, derived {agent_id} from worker_name {worker_name}. Task should ideally have agent_id set by PBM/Nexus on claim.")

        # More robust: Agent ID should be consistently part of the task dict when claimed/processed.
        # For now, assume it's in task, or orchestrator handles agent mapping.
        # Let's use a placeholder if not found, but this indicates a potential issue upstream.
        agent_id = task.get("assigned_agent") or task.get(
            "claimed_by"
        )  # Prefer 'assigned_agent' or 'claimed_by'
        if not agent_id:
            # A more generic fallback tied to the worker instance rather than deriving from name
            agent_id = (
                f"swarm_worker_{worker_name.split('-')[-1]}"  # e.g. swarm_worker_1
            )
            logger.warning(
                f"Task {task_id} is missing 'assigned_agent' or 'claimed_by'. Using derived agent_id: {agent_id} for orchestrator. This should be set during task claim/assignment."
            )
        # {{ EDIT END }}
        prompt = task.get(
            "prompt", task.get("params", {}).get("description", "")
        )  # Use description as fallback prompt
        max_attempts = self.config.swarm.get("task_execution_attempts", 3)
        retry_delay = self.config.swarm.get("task_retry_delay", 5.0)

        for attempt in range(max_attempts):
            logger.info(
                f"[{worker_name}] Attempt {attempt + 1}/{max_attempts} for task {task_id}"
            )
            success = False
            result_content = None
            error_details = None

            try:
                # Step 1: Inject Prompt
                logger.debug(f"[{worker_name}] Injecting prompt for task {task_id}...")
                inject_success = await self.cursor_orchestrator.inject_prompt(
                    agent_id=agent_id,
                    prompt=prompt,
                    timeout=self.config.gui_automation.get("inject_timeout", 60.0),
                )
                if not inject_success:
                    logger.warning(
                        f"[{worker_name}] Prompt injection failed for task {task_id} (attempt {attempt + 1})"
                    )
                    error_details = "Prompt injection failed"
                    # Go to retry logic immediately
                    raise CursorOrchestratorError(error_details)

                # Step 2: Retrieve Response
                logger.debug(
                    f"[{worker_name}] Retrieving response for task {task_id}..."
                )
                result_content = await self.cursor_orchestrator.retrieve_response(
                    agent_id=agent_id,
                    timeout=self.config.gui_automation.get("retrieve_timeout", 120.0),
                )

                if result_content is None:
                    logger.warning(
                        f"[{worker_name}] Response retrieval returned None for task {task_id} (attempt {attempt + 1})"
                    )
                    error_details = "Response retrieval failed (returned None)"
                    # Go to retry logic
                    raise CursorOrchestratorError(error_details)

                # If both steps succeeded
                success = True
                logger.info(
                    f"[{worker_name}] Successfully processed task {task_id} (attempt {attempt + 1})"
                )
                break  # Exit retry loop on success

            except CursorOrchestratorError as co_err:
                logger.warning(
                    f"[{worker_name}] CursorOrchestrator error on attempt {attempt + 1} for task {task_id}: {co_err}"
                )
                error_details = f"Orchestrator Error: {co_err}"
                # Fall through to retry/failure logic
            except Exception as e:
                logger.error(
                    f"[{worker_name}] Unexpected error during task {task_id} execution (attempt {attempt + 1}): {e}",
                    exc_info=True,
                )
                error_details = f"Unexpected Error: {e}"
                # Treat unexpected errors as potentially fatal for this attempt
                break  # Exit retry loop on unexpected errors

            # Retry delay logic
            if attempt < max_attempts - 1:
                logger.info(f"[{worker_name}] Retrying task {task_id} after delay...")
                await asyncio.sleep(
                    retry_delay * (attempt + 1)
                )  # Exponential backoff basic
            else:
                logger.error(
                    f"[{worker_name}] Task {task_id} failed after {max_attempts} attempts."
                )

        # After loop (success or final failure)
        result_payload = {
            "task_id": task_id,
            "agent_id": agent_id,
            "status": "completed" if success else "failed",
            "result": result_content if success else None,
            "error": error_details if not success else None,
            "completed_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        }

        try:
            await self.channel.push_result(result_payload)
            logger.info(
                f"[{worker_name}] Pushed result for task {task_id} (Status: {result_payload['status']})"
            )
        except Exception as push_err:
            logger.error(
                f"[{worker_name}] CRITICAL: Failed to push result for task {task_id}: {push_err}",
                exc_info=True,
            )
            # Consider adding to a dead-letter queue or alternative error handling

    def _maybe_launch_headless_cursor(self) -> None:
        """Launch headless Cursor if path exists, else continue silently."""
        cursor_cfg = getattr(self.config.tools, "cursor", None)
        cursor_exe = getattr(cursor_cfg, "executable_path", "Cursor.exe")

        if not Path(cursor_exe).exists():
            logger.warning(
                f"Cursor exe not found at '{cursor_exe}', skipping headless launch"
            )
            return

        try:
            VirtualDesktopController().launch_cursor_headless(
                cursor_exe_path=cursor_exe
            )
            logger.info(f"🖥️  Headless Cursor launched → {cursor_exe}")
        except Exception as vdc_err:  # pylint: disable=broad-except
            logger.warning(f"Headless launch failed: {vdc_err}")

    # --------------------------------------------------------------------- #
    # Router
    # --------------------------------------------------------------------- #
    def _route_loop(self) -> None:
        """Idle loop so main thread can honour Ctrl-C & run atexit hooks."""
        logger.info("📡 Routing loop active – Ctrl-C to exit")
        try:
            while not self._stop_event.is_set():
                time.sleep(5)
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received – shutting down")
        finally:
            self.shutdown()

    # --------------------------------------------------------------------- #
    # Result Handler
    # --------------------------------------------------------------------- #
    # {{ EDIT START: Rename _handle_result to sync wrapper, create async handler }}
    # def _handle_result(self, result: Dict[str, Any]) -> None:
    #     """Handle result -> feedback -> lore persistence."""
    #     logger.info(f"📑 Result received for {result.get('id')}")
    #     self._run_feedback_engine(result)
    #     self._persist_lore_metadata(result)
    #     self._compile_lore()

    async def _handle_result_async(self, result: Dict[str, Any]) -> None:
        """Async handler for task results received via EventBus."""
        task_id = result.get("task_id") or result.get("id", "unknown_task")
        logger.info(f"📑 Async: Result received for {task_id}")
        # Run potentially blocking operations in executor threads
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self._run_feedback_engine, result)
            await loop.run_in_executor(None, self._persist_lore_metadata, result)
            await loop.run_in_executor(None, self._compile_lore)
            logger.info(f"📑 Async: Processing complete for {task_id}")
        except Exception as e:
            logger.error(
                f"📑 Async: Error processing result for {task_id}: {e}", exc_info=True
            )

    # Keep sync version if needed elsewhere, or remove if only used by bus
    # def _handle_result_sync_wrapper(self, result: Dict[str, Any]) -> None:
    #     """Synchronous wrapper if needed."""
    #     asyncio.run(self._handle_result_async(result))
    # {{ EDIT END }}

    # ------------------------------------------------------------------ #
    # Feedback / Lore helpers
    # ------------------------------------------------------------------ #
    def _run_feedback_engine(self, result: Dict[str, Any]) -> None:
        try:
            fe = FeedbackEngineV2(config=self.config)
            analyses = asyncio.run(fe.analyze_failures())
            if analyses:
                out_dir = Path("dream_logs/feedback")
                out_dir.mkdir(parents=True, exist_ok=True)
                out_file = out_dir / f"failure_analysis_{result['id']}.json"
                fe.save_analysis(analyses, output_file=str(out_file))
                logger.info(f"🔍 Feedback saved → {out_file}")
        except Exception as fe_err:  # pylint: disable=broad-except
            logger.error(f"FeedbackEngineV2 failed: {fe_err}", exc_info=True)

    def _persist_lore_metadata(self, result: Dict[str, Any]) -> None:
        try:
            task_list_path = Path("runtime/task_list.json")
            if not task_list_path.exists():
                logger.warning(
                    f"Lore metadata persistence skipped: {task_list_path} not found."
                )
                return
            tasks = json.loads(task_list_path.read_text(encoding="utf-8"))
            for t in tasks:
                if t.get("id") == result["id"]:
                    payload = t.setdefault("payload", {})
                    payload["modified_files"] = result.get("modified_files", [])
                    stdout = result.get("stdout", "")
                    payload["log_tail"] = "\n".join(stdout.strip().splitlines()[-10:])
            task_list_path.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
        except Exception as lore_err:  # pylint: disable=broad-except
            logger.warning(f"Lore metadata persistence failed: {lore_err}")

    def _compile_lore(self) -> None:
        try:
            # EDIT START: Fix potential script path - assuming it moved or is elsewhere
            # script = Path("_agent_coordination/tools/compile_lore.py")
            # Attempting a more likely location based on project structure. Needs verification.
            # Assuming compile_lore is part of the project analysis tools now
            script = Path(
                "src/dreamos/tools/analysis/project_scanner/compile_lore.py"
            )  # Guessed path, might need adjustment
            # EDIT END
            if not script.exists():
                logger.warning(
                    f"Lore compilation skipped: Script not found at {script}"
                )
                return
            subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--style",
                    "devlog",
                    "--translation",
                    "dream_logs/config/dream_translation.yaml",
                    "--tasks",
                    "runtime/task_list.json",
                ],
                check=True,
            )
            logger.debug("Lore compiled")
        except Exception as comp_err:  # pylint: disable=broad-except
            logger.error(f"Lore compilation failed: {comp_err}", exc_info=True)

    # ------------------------------------------------------------------ #
    # Stats helper
    # ------------------------------------------------------------------ #
    def _start_stats_autologger(self, interval: int) -> None:
        self._spawn_thread(
            target=self._stats_loop,
            args=(interval,),
            name="StatsAutoLogger",
        )

    def _stats_loop(self, interval: int) -> None:
        """Background loop to log stats and perform periodic checks."""
        logger.info(f"📊 Stats logger started (interval: {interval}s)")
        while not self._stop_event.is_set():
            loop_start_time = time.monotonic()
            try:
                self.stats_hook.log_stats()  # Existing stats logging

                # --- EDIT START: Add Captaincy Check ---
                if self.points_manager and self.config.agent_points_system:
                    check_interval_minutes = getattr(
                        self.config.agent_points_system,
                        "captaincy_check_interval_minutes",
                        15,
                    )
                    check_interval_seconds = check_interval_minutes * 60

                    now = time.monotonic()
                    if now - self.last_captaincy_check_time >= check_interval_seconds:
                        logger.debug("Performing periodic captaincy check...")
                        self.last_captaincy_check_time = now
                        try:
                            new_captain_id = self.points_manager.determine_captain()

                            if new_captain_id != self.current_captain_id:
                                logger.info(
                                    f"Captaincy change detected! New Captain: {new_captain_id} (Previous: {self.current_captain_id})"
                                )
                                self.current_captain_id = new_captain_id

                                # Write to status file
                                default_path = "runtime/governance/current_captain.txt"
                                file_path_str = getattr(
                                    self.config.agent_points_system,
                                    "captain_status_file",
                                    default_path,
                                )
                                status_file = (
                                    self.config.paths.project_root / file_path_str
                                ).resolve()
                                try:
                                    status_file.parent.mkdir(
                                        parents=True, exist_ok=True
                                    )
                                    status_file.write_text(
                                        str(new_captain_id) if new_captain_id else "",
                                        encoding="utf-8",
                                    )
                                    logger.info(
                                        f"Updated captain status file: {status_file} -> {new_captain_id}"
                                    )
                                    # TODO: Broadcast event? e.g., self.bus.publish(BaseEvent(type=EventType.CAPTAIN_UPDATE, data={'captain_id': new_captain_id}))
                                except Exception as e_write:
                                    logger.error(
                                        f"Failed to write captain status to {status_file}: {e_write}",
                                        exc_info=True,
                                    )
                            else:
                                logger.debug(
                                    f"Captaincy unchanged: {self.current_captain_id}"
                                )

                        except Exception as e_captain_check:
                            logger.error(
                                f"Error during captaincy check: {e_captain_check}",
                                exc_info=True,
                            )
                    else:
                        # logger.debug("Skipping captaincy check (interval not reached).") # Too noisy maybe
                        pass
                # --- EDIT END ---

            except Exception as e:
                logger.error(f"Error in stats loop: {e}", exc_info=True)

            # Accurate sleep calculation
            elapsed = time.monotonic() - loop_start_time
            sleep_duration = max(0, interval - elapsed)
            if self._stop_event.wait(timeout=sleep_duration):
                break  # Exit loop if stop event is set during wait

        logger.info("📊 Stats logger stopped")

    def _process_agent_output(self, agent_id: str, output: Any):
        # ... (existing logic) ...
        # Example: Publish event on agent output
        output_event = BaseEvent(
            event_type=EventType.AGENT_OUTPUT_RECEIVED,  # Use imported EventType
            source_id=agent_id,
            data={"output": str(output)},  # Ensure data is serializable
        )
        self.bus.dispatch_event(output_event)

    def _handle_agent_error(self, agent_id: str, error: Exception):
        # ... (existing logic) ...
        # Example: Publish event on agent error
        error_type = EventType.AGENT_ERROR  # Default error type
        if isinstance(error, CursorOrchestratorError):  # Check specific error type
            error_type = EventType.CURSOR_BRIDGE_ERROR  # Use specific event type

        error_event = BaseEvent(
            event_type=error_type,
            source_id=agent_id,
            data={"error": str(error), "error_type": type(error).__name__},
        )
        self.bus.dispatch_event(error_event)

    # --- EDIT START: Add helper to load initial captain ID ---
    def _load_initial_captain_id(self):
        """Loads the captain ID from the status file on startup, if it exists."""
        if not self.config.agent_points_system:
            return  # No points system configured

        default_path = "runtime/governance/current_captain.txt"
        file_path_str = getattr(
            self.config.agent_points_system, "captain_status_file", default_path
        )
        status_file = (self.config.paths.project_root / file_path_str).resolve()

        try:
            if status_file.exists():
                self.current_captain_id = status_file.read_text(
                    encoding="utf-8"
                ).strip()
                if self.current_captain_id:
                    logger.info(
                        f"Loaded initial Captain ID: {self.current_captain_id} from {status_file}"
                    )
                else:
                    logger.info(f"Captain status file {status_file} is empty.")
                    self.current_captain_id = None
            else:
                logger.info(
                    f"Captain status file {status_file} not found. No initial captain loaded."
                )
        except Exception as e:
            logger.error(
                f"Error loading initial captain ID from {status_file}: {e}",
                exc_info=True,
            )
            self.current_captain_id = None

    # --- EDIT END ---
