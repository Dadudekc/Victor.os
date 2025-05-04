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
import importlib
import json
import logging
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dreamos._agent_coordination.tools.event_bus import EventBus
from dreamos._agent_coordination.tools.event_type import EventType
from dreamos.agents.chatgpt_web_agent import run_loop as chat_run_loop
from dreamos.core.config import AppConfig
from dreamos.core.tasks.nexus.task_nexus import TaskNexus
from dreamos.feedback.feedback_engine_v2 import FeedbackEngineV2
from dreamos.hooks.stats_logger import StatsLoggingHook

from dreamos.automation.cursor_orchestrator import CursorOrchestrator

from ...channels.local_blob_channel import LocalBlobChannel
from .cursor_fleet_launcher import (
    assign_windows_to_monitors,
    get_cursor_windows,
    launch_cursor_instance,
)
from .virtual_desktop_runner import VirtualDesktopController

logger = logging.getLogger(__name__)  # logging configured by entry point


class SwarmController:
    """Top-level coordinator for Cursor agents (GUI & headless)."""

    _DEFAULT_STATS_INTERVAL_SEC: int = 60

    # --------------------------------------------------------------------- #
    # Construction
    # --------------------------------------------------------------------- #
    def __init__(self, config: AppConfig) -> None:
        self.config: AppConfig = config

        # -- fleet & channel ------------------------------------------------
        self.fleet_size: int = getattr(config.swarm, "fleet_size", 3)

        azure_conf = getattr(config.integrations, "azure_blob", None)
        self.container_name: str = getattr(azure_conf, "container_name", "dream-os-c2")
        self.sas_token: Optional[str] = getattr(azure_conf, "sas_token", None)
        self.connection_string: Optional[str] = getattr(
            azure_conf, "connection_string", None
        )
        self.use_local: bool = getattr(config.memory_channel, "use_local_blob", False)

        if not self.use_local and not (self.connection_string or self.sas_token):
            logger.warning(
                "💾 Azure Blob not fully configured; falling back to LocalBlobChannel."
            )
            self.use_local = True

        self.channel = LocalBlobChannel()
        if not self.channel.healthcheck():
            raise RuntimeError("LocalBlobChannel health-check failed – aborting")

        # -- runtime components --------------------------------------------
        self.nexus = TaskNexus(config=self.config, task_file="runtime/task_list.json")
        self.stats_hook = StatsLoggingHook(self.nexus)
        self.event_bus = EventBus()
        self.event_bus.subscribe(EventType.TASK_COMPLETED.value, self._handle_result)

        # -- orchestration state -------------------------------------------
        self._stop_event = threading.Event()
        self.workers: List[threading.Thread] = []

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

        for t in self.workers:
            t.join(timeout=5)

        logger.info("✅ SwarmController shutdown complete")

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #
    def _spawn_thread(self, *, target, args: tuple = (), name: str) -> None:
        th = threading.Thread(target=target, args=args, name=name, daemon=True)
        th.start()
        self.workers.append(th)

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

    # .........................................
    # Worker
    # .........................................
    def _worker_loop(self) -> None:
        """Instantiate and run a dedicated agent instance (e.g., Agent2)."""
        worker_name = threading.current_thread().name
        logger.info(f"Worker thread {worker_name} starting.")

        try:
            # Run the async part of the worker loop
            asyncio.run(self._run_agent_async(worker_name))
        except Exception as e:
            logger.critical(
                f"[{worker_name}] CRITICAL ASYNC RUNNER ERROR: {e}", exc_info=True
            )
        finally:
            logger.info(f"Worker thread {worker_name} finished.")

    async def _run_agent_async(self, worker_name: str) -> None:
        """Asynchronous part of the worker loop: instantiate and run agent."""
        # Attempt to launch headless Cursor in a virtual desktop
        # self._maybe_launch_headless_cursor() # Keep this if needed for the agent

        # --- Agent Instantiation ---
        agent_instance = None
        agent_config_found = False
        try:
            # Iterate through configured activations
            for activation_conf in self.config.swarm.active_agents:
                # Check if the worker_name matches the pattern
                if re.fullmatch(activation_conf.worker_id_pattern, worker_name):
                    agent_config_found = True
                    logger.info(
                        f"[{worker_name}] Matched activation config: {activation_conf.agent_module}.{activation_conf.agent_class}"  # noqa: E501
                    )

                    # Dynamically import the module
                    try:
                        module_path = activation_conf.agent_module
                        module = importlib.import_module(module_path)
                    except ImportError as e:
                        logger.critical(
                            f"[{worker_name}] Failed to import agent module {module_path}: {e}"  # noqa: E501
                        )
                        return  # Cannot proceed

                    # Get the class from the module
                    try:
                        AgentClass = getattr(module, activation_conf.agent_class)
                    except AttributeError:
                        logger.critical(
                            f"[{worker_name}] Agent class {activation_conf.agent_class} not found in module {module_path}."  # noqa: E501
                        )
                        return  # Cannot proceed

                    # Prepare arguments for instantiation (common args)
                    # Specific agents might need more/different args - requires more complex config or introspection  # noqa: E501
                    agent_id = (
                        activation_conf.agent_id_override
                        or f"{activation_conf.agent_class}_{worker_name}"
                    )
                    agent_args = {
                        "agent_id": agent_id,
                        "config": self.config,
                        "agent_bus": self.event_bus,
                        # Conditionally add PBM if the agent expects it (best effort)
                        # A better approach might involve dependency injection or capability checks  # noqa: E501
                    }
                    if (
                        hasattr(AgentClass, "__init__")
                        and "pbm" in AgentClass.__init__.__code__.co_varnames
                    ):
                        if not self.nexus or not self.nexus.board_manager:
                            logger.error(
                                f"[{worker_name}] Agent {AgentClass.__name__} requires PBM, but it's not available in TaskNexus."  # noqa: E501
                            )
                            # Decide how to handle: skip agent, raise error?
                            # For now, skip instantiation if PBM is required but missing.  # noqa: E501
                            return
                        agent_args["pbm"] = self.nexus.board_manager

                    # Instantiate the agent
                    logger.info(
                        f"[{worker_name}] Instantiating {AgentClass.__name__} with ID {agent_id}..."  # noqa: E501
                    )
                    agent_instance = AgentClass(**agent_args)
                    logger.info(
                        f"[{worker_name}] Successfully instantiated {agent_id}."
                    )
                    break  # Stop after finding the first matching config

            if not agent_config_found:
                logger.warning(
                    f"[{worker_name}] No activation config found for this worker. Skipping agent instantiation."  # noqa: E501
                )
                return

        except Exception as e:
            logger.critical(
                f"[{worker_name}] CRITICAL ERROR instantiating agent: {e}",
                exc_info=True,
            )
            return  # Cannot proceed without an agent instance

        # --- Run Agent's Autonomous Loop ---
        if not agent_instance:
            logger.error(
                f"[{worker_name}] Agent instance not created. Cannot run loop."
            )
            return

        logger.info(
            f"[{worker_name}] Starting agent {agent_instance.agent_id}'s autonomous loop..."  # noqa: E501
        )
        agent_task = None
        try:
            # Create a task for the agent's loop - asyncio.run provides the loop
            if not hasattr(
                agent_instance, "run_autonomous_loop"
            ) or not asyncio.iscoroutinefunction(agent_instance.run_autonomous_loop):
                logger.error(
                    f"[{worker_name}] Agent {agent_instance.agent_id} does not have a valid async 'run_autonomous_loop' method."  # noqa: E501
                )
                return
            agent_task = asyncio.create_task(agent_instance.run_autonomous_loop())

            # Monitor the stop event and cancel the agent task if needed
            while not self._stop_event.is_set():
                if agent_task.done():
                    logger.info(
                        f"[{worker_name}] Agent {agent_instance.agent_id} loop task finished unexpectedly."  # noqa: E501
                    )
                    # Check for exceptions
                    exc = agent_task.exception()
                    if exc:
                        logger.error(
                            f"[{worker_name}] Agent loop task finished with error: {exc}",  # noqa: E501
                            exc_info=exc,
                        )
                    break  # Exit worker loop if agent loop finishes

                # Yield control while checking stop event periodically
                try:
                    # wait_for ensures sleep doesn't block cancellation indefinitely
                    await asyncio.wait_for(asyncio.sleep(1), timeout=1.1)
                except asyncio.TimeoutError:
                    pass  # Expected if sleep completes

            # If stop event is set, cancel the agent task gracefully
            if self._stop_event.is_set():
                if agent_task and not agent_task.done():
                    logger.info(
                        f"[{worker_name}] Stop event set. Cancelling agent {agent_instance.agent_id} loop..."  # noqa: E501
                    )
                    agent_task.cancel()
                    try:
                        # Wait briefly for cancellation to propagate
                        await asyncio.wait_for(agent_task, timeout=5.0)
                    except asyncio.CancelledError:
                        logger.info(
                            f"[{worker_name}] Agent {agent_instance.agent_id} loop successfully cancelled."  # noqa: E501
                        )
                    except asyncio.TimeoutError:
                        logger.warning(
                            f"[{worker_name}] Timeout waiting for agent {agent_instance.agent_id} loop cancellation."  # noqa: E501
                        )
                    except Exception as e:
                        logger.error(
                            f"[{worker_name}] Error during agent task cancellation/cleanup: {e}",  # noqa: E501
                            exc_info=True,
                        )

        except Exception as e:
            logger.exception(f"[{worker_name}] Unhandled error running agent loop: {e}")
        finally:
            logger.debug(f"[{worker_name}] Agent async runner finishing.")

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
    def _handle_result(self, result: Dict[str, Any]) -> None:
        """Handle result → feedback → lore persistence."""
        logger.info(f"📑 Result received for {result.get('id')}")
        self._run_feedback_engine(result)
        self._persist_lore_metadata(result)
        self._compile_lore()

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
            script = Path("_agent_coordination/tools/compile_lore.py")
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
        while not self._stop_event.is_set():
            try:
                self.stats_hook.log_snapshot()
                print(f"📊 Stats @ {_dt.datetime.utcnow().isoformat()}Z")
            except Exception as stats_err:  # pylint: disable=broad-except
                logger.error(f"Stats logging failed: {stats_err}", exc_info=True)
            time.sleep(interval)
