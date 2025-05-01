import asyncio
import logging
import os
import platform
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from _agent_coordination.tools.event_bus import EventBus
from _agent_coordination.tools.event_type import EventType

from dreamos.agents.chatgpt_web_agent import run_loop as chat_run_loop

# EDIT START: Import AppConfig
from dreamos.core.config import AppConfig
from dreamos.core.tasks.nexus.task_nexus import TaskNexus
from dreamos.feedback.feedback_engine_v2 import FeedbackEngineV2
from dreamos.hooks.stats_logger import StatsLoggingHook

from ...channels.local_blob_channel import LocalBlobChannel
from ...core.coordination.agent_bus import AgentBus, BaseEvent, EventType
from ...core.coordination.base_agent import BaseAgent, TaskStatus
from .cursor_fleet_launcher import (
    assign_windows_to_monitors,
    get_cursor_windows,
    launch_cursor_instance,
)
from .virtual_desktop_runner import VirtualDesktopController

# EDIT END


logger = logging.getLogger(__name__)
# Remove basicConfig - should be configured by application entry point
# logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s")


class SwarmController:
    """
    Controls a fleet of Cursor agents using LocalBlobChannel for task/result exchange.
    """

    # EDIT START: Remove static helper methods for config resolution
    # @staticmethod
    # def _resolve_config_args(fleet_size, container_name, sas_token, connection_string, stats_interval):
    #     ...
    # @staticmethod
    # def _resolve_config(connection_string: Optional[str], sas_token: Optional[str], container_name: str) -> Tuple[Optional[str], Optional[str], str, bool]:
    #     ...
    # @staticmethod
    # def _resolve_stats_interval(stats_interval: Optional[int]) -> int:
    #     ...
    # EDIT END

    # EDIT START: Modify __init__ to accept AppConfig and use it
    def __init__(
        self,
        config: AppConfig,  # Accept AppConfig
        # Remove old args that now come from config
        # fleet_size: int = 3,
        # container_name: str = "dream-os-c2",
        # sas_token: str = None,
        # connection_string: str = None,
        # stats_interval: int = None,
    ):
        self.config = config  # Store config

        # Resolve all configuration from AppConfig object
        self.fleet_size = getattr(config.swarm, "fleet_size", 3)
        azure_conf = getattr(config.integrations, "azure_blob", None)
        self.container_name = (
            getattr(azure_conf, "container_name", "dream-os-c2")
            if azure_conf
            else "dream-os-c2"
        )
        self.sas_token = getattr(azure_conf, "sas_token", None) if azure_conf else None
        self.connection_string = (
            getattr(azure_conf, "connection_string", None) if azure_conf else None
        )
        stats_interval = getattr(config.monitoring, "stats_interval", 60)

        # Determine Azure connection mode (local vs cloud)
        self.use_local = getattr(config.memory_channel, "use_local_blob", False)
        # _, _, _, self.use_local = self._resolve_config(
        #     self.connection_string, self.sas_token, self.container_name
        # )
        if not self.use_local and not self.connection_string and not self.sas_token:
            logger.warning(
                "Azure connection string/SAS token not found in config and not using local blobs. Channel operations might fail."
            )
            # Consider raising an error if cloud storage is expected but unconfigured
            # raise RuntimeError("Azure Blob Storage required but not configured (connection_string/sas_token missing)")

        # Initialize TaskNexus for central task management
        self.nexus = TaskNexus(
            config=self.config, task_file="runtime/task_list.json"
        )  # Pass config to Nexus
        # Stats logging hook for monitoring task metrics
        self.stats_hook = StatsLoggingHook(self.nexus)
        # Start periodic stats auto-logging
        self._start_stats_autologger(interval=stats_interval)
        # Initialize EventBus for pub/sub events
        self.event_bus = EventBus()
        # Subscribe to task results from workers
        self.event_bus.subscribe(EventType.TASK_COMPLETED.value, self._handle_result)
        # Initialize C2 channel for results (Local only)
        # TODO: Channel initialization might need AppConfig too?
        self.channel = LocalBlobChannel()
        # Verify connectivity to LocalBlobChannel
        if not self.channel.healthcheck():
            logger.error(
                "LocalBlobChannel healthcheck failed, aborting SwarmController initialization."
            )
            raise RuntimeError("Channel healthcheck failed")
        self.workers: List[threading.Thread] = []
        self._stop_event = threading.Event()

    # EDIT END

    def start(self, initial_tasks: List[Dict] = None):
        """
        Launch GUI and headless agents and start routing loop.
        """
        logger.info(f"Starting SwarmController with {self.fleet_size} agents...")
        # 0. Spawn ChatGPT WebAgent producer thread
        try:
            logger.info("Starting ChatGPTWebAgent producer thread...")
            chat_thread = threading.Thread(
                target=chat_run_loop,
                args=(self._stop_event,),
                name="ChatGPTWebAgent",
                daemon=True,
            )
            chat_thread.start()
            self.workers.append(chat_thread)
        except ImportError as e:
            logger.warning(f"ChatGPTWebAgent integration failed: {e}")
        # Dispatch initial tasks into TaskNexus if provided
        if initial_tasks:
            for task in initial_tasks:
                logger.info(f"Dispatching initial task to TaskNexus: {task}")
                self.nexus.add_task(task)
        # 1. Launch GUI instances
        logger.info("Launching GUI Cursor instances...")
        processes = []
        for i in range(self.fleet_size):
            proc = launch_cursor_instance(i)
            processes.append(proc)
            time.sleep(0.5)
        # 2. Tile windows
        try:
            windows = get_cursor_windows(target_count=len(processes), timeout=30)
            assign_windows_to_monitors(windows)
        except Exception as e:
            logger.warning(f"Window tiling skipped: {e}")

        # 3. Start headless dispatcher threads
        logger.info("Starting headless dispatcher workers...")
        for i in range(self.fleet_size):
            t = threading.Thread(
                target=self._worker_loop, name=f"Worker-{i+1}", daemon=True
            )
            t.start()
            self.workers.append(t)

        # 4. Start routing loop in main thread
        self._route_loop()

    def _worker_loop(self):
        """
        Worker thread: pull tasks, simulate processing, push results.
        """
        # EDIT START: Get CURSOR_PATH from config
        # Use VirtualDesktopController for headless launching if needed
        try:
            vdc = VirtualDesktopController()
            # cursor_exe_path=os.getenv("CURSOR_PATH", "Cursor.exe") # REMOVE os.getenv
            # Access the config object passed during __init__
            cursor_config = getattr(self.config.tools, "cursor", None)
            cursor_exe_path = (
                getattr(cursor_config, "executable_path", "Cursor.exe")
                if cursor_config
                else "Cursor.exe"
            )

            # Ensure the path is valid before launching
            if not Path(cursor_exe_path).exists():
                logger.warning(
                    f"Cursor executable path from config not found: {cursor_exe_path}. Attempting default 'Cursor.exe'."
                )
                cursor_exe_path = "Cursor.exe"  # Fallback, though might still fail

            vdc.launch_cursor_headless(cursor_exe_path=cursor_exe_path)
            logger.info(f"Launched headless cursor using path: {cursor_exe_path}")
        except Exception as e_launch:
            logger.warning(
                f"Proceeding without headless setup due to error: {e_launch}"
            )
        # EDIT END

        while not self._stop_event.is_set():
            # Record heartbeat for this worker agent
            try:
                self.nexus.record_heartbeat(threading.current_thread().name)
            except Exception as e:
                logger.warning(
                    f"Failed to record heartbeat for {threading.current_thread().name}: {e}"
                )
            # Claim the next pending task from TaskNexus
            task = self.nexus.get_next_task(agent_id=threading.current_thread().name)
            if task:
                logger.info(f"Worker received task: {task}")
                # Simulate work: echo back with a timestamp
                result = {
                    "task_id": task.get("id"),
                    "agent_id": threading.current_thread().name,
                    "echo": task,
                    "processed_at": time.time(),
                }
                # Publish result event to EventBus instead of blob channel
                self.event_bus.publish(
                    EventType.TASK_COMPLETED.value, result, ack_required=False
                )
                logger.info(f"Worker published result via EventBus: {result}")
                # Mark task as completed in TaskNexus
                self.nexus.update_task_status(task.get("id"), "completed")
                # Log stats snapshot after task completion
                try:
                    self.stats_hook.log_snapshot()
                except Exception as se:
                    logger.error(f"Failed to log stats snapshot: {se}", exc_info=True)
            else:
                time.sleep(2)

    def _route_loop(self):
        """
        Main loop: monitor results and handle them.
        """
        logger.info("Entering routing loop...")
        try:
            while not self._stop_event.is_set():
                # Deprecated: channel.poll disabled in favor of EventBus
                # results = self.channel.pull_results()
                # for res in results:
                #     self._handle_result(res)
                time.sleep(5)
        except KeyboardInterrupt:
            logger.info("SwarmController interrupted, shutting down...")
        finally:
            self.shutdown()

    def _handle_result(self, result: Dict[Any, Any]):
        """
        Handle an incoming result from an agent.
        """
        logger.info(f"SwarmController received result: {result}")
        # EDIT START: Pass AppConfig to FeedbackEngineV2
        # FeedbackEngineV2 analysis for archived failures
        try:
            # fe = FeedbackEngineV2()
            fe = FeedbackEngineV2(config=self.config)  # Pass config
            # {{ EDIT START: Run async function in event loop }}
            # TODO: FeedbackEngineV2.analyze_failures is now async! -> DONE
            # This needs to be run in an event loop or adapted.
            # For now, logging a warning. Needs further refactoring if async analysis is required here.
            # analyses = fe.analyze_failures()
            # logger.warning("FeedbackEngineV2 analysis skipped in _handle_result (needs async handling).")
            # analyses = [] # Placeholder
            try:
                # Run analyze_failures in a new event loop (safer if _handle_result is sync)
                analyses = asyncio.run(
                    fe.analyze_failures()
                )  # This blocks until analyze_failures completes
                logger.debug(f"Feedback analysis returned {len(analyses)} items.")
            except RuntimeError as rt_e:
                # This might happen if _handle_result is *already* running in an event loop
                # Although asyncio.run() is supposed to handle this, provide a fallback log
                logger.warning(
                    f"RuntimeError running async analyze_failures (may be nested loops?): {rt_e}. Skipping analysis."
                )
                analyses = []  # Placeholder
            except Exception as async_e:
                logger.error(
                    f"Error running async analyze_failures: {async_e}", exc_info=True
                )
                analyses = []  # Placeholder
            # {{ EDIT END }}
            # Save analysis per result id
            feedback_dir = os.path.join("dream_logs", "feedback")
            os.makedirs(feedback_dir, exist_ok=True)
            output_file = os.path.join(
                feedback_dir, f"failure_analysis_{result.get('id','unknown')}.json"
            )
            # Ensure save_analysis can handle an empty list
            if analyses:
                fe.save_analysis(analyses, output_file=output_file)
                logger.info(
                    f"🔍 Feedback analysis saved for result: {result.get('id')}"
                )
            else:
                logger.info(
                    f"No feedback analysis data generated or analysis skipped for result: {result.get('id')}"
                )
        except Exception as e:
            logger.error(
                f"Failed to run feedback analysis for result {result.get('id')}: {e}",
                exc_info=True,
            )
        # EDIT END
        # Persist modified_files and log_tail into runtime/task_list.json for lore compilation
        try:
            task_list_path = Path("runtime/task_list.json")
            tasks_data = json.loads(task_list_path.read_text(encoding="utf-8"))
            for t in tasks_data:
                if t.get("id") == result.get("id"):
                    payload = t.setdefault("payload", {})
                    # modified_files from result metadata
                    payload["modified_files"] = result.get("modified_files", [])
                    # log_tail from result stdout
                    stdout = result.get("stdout", "")
                    if isinstance(stdout, str):
                        lines = stdout.strip().splitlines()
                        payload["log_tail"] = "\n".join(lines[-10:])
            task_list_path.write_text(
                json.dumps(tasks_data, indent=2), encoding="utf-8"
            )
        except Exception:
            pass
        # Invoke lore compilation as a one-shot tool
        try:
            # Auto-generate Devlog lore for the swarm
            script = os.path.join(
                os.getcwd(), "_agent_coordination/tools/compile_lore.py"
            )
            cmd = [
                "python",
                script,
                "--style",
                "devlog",
                "--translation",
                os.path.join(os.getcwd(), "dream_logs/config/dream_translation.yaml"),
                "--tasks",
                os.path.join(os.getcwd(), "runtime/task_list.json"),
            ]
            subprocess.run(cmd, check=True)
            logger.info("Lore compiled successfully.")
        except Exception as e:
            logger.error(f"Failed to compile lore: {e}", exc_info=True)

    def shutdown(self):
        """
        Signal all workers to stop.
        """
        logger.info("Shutting down SwarmController...")
        self._stop_event.set()

    def _start_stats_autologger(self, interval: int = 60) -> None:
        """Launch a background thread to log stats periodically."""
        thread = threading.Thread(
            target=self._stats_loop,
            args=(interval,),
            daemon=True,
            name="StatsAutoLogger",
        )
        thread.start()

    def _stats_loop(self, interval: int) -> None:
        """Background loop that logs stats until stop event is set."""
        while not self._stop_event.is_set():
            try:
                self.stats_hook.log_snapshot()
                # Console heartbeat for manual monitoring
                print(f"📊 Stats snapshot at {datetime.utcnow().isoformat()} UTC")
            except Exception as e:
                logger.error(f"Auto stats logging failed: {e}", exc_info=True)
            time.sleep(interval)


# ... existing code ...
