import os
import threading
import time
import logging
import subprocess
import argparse
from typing import Any, Dict, List
from pathlib import Path
import json
from datetime import datetime  # for heartbeat timestamp

# Azure C2 channel logic commented out - using LocalBlobChannel only
AzureBlobChannel = None
from dream_mode.local_blob_channel import LocalBlobChannel
from dream_mode.cursor_fleet_launcher import launch_cursor_instance, get_cursor_windows, assign_windows_to_monitors
from dream_mode.virtual_desktop_runner import VirtualDesktopController
from dream_mode.task_nexus.task_nexus import TaskNexus
from core.hooks.stats_logger import StatsLoggingHook
from core.chat_engine.feedback_engine_v2 import FeedbackEngineV2

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s")

class SwarmController:
    """
    Controls a fleet of Cursor agents using AzureBlobChannel for task/result exchange.
    """
    def __init__(
        self,
        fleet_size: int = 3,
        container_name: str = "dream-os-c2",
        sas_token: str = None,
        connection_string: str = None,
        stats_interval: int = None,
    ):
        self.fleet_size = fleet_size
        # Determine stats interval (CLI args override env)
        if stats_interval is None:
            stats_interval = int(os.getenv("STATS_INTERVAL", "60"))
        # Initialize TaskNexus for central task management
        self.nexus = TaskNexus(task_file="runtime/task_list.json")
        # Stats logging hook for monitoring task metrics
        self.stats_hook = StatsLoggingHook(self.nexus)
        # Start periodic stats auto-logging
        self._start_stats_autologger(interval=stats_interval)
        # Initialize C2 channel for results (Local only)
        self.channel = LocalBlobChannel()
        # Verify connectivity to Azure Blob channel
        if not self.channel.healthcheck():
            logger.error("AzureBlobChannel healthcheck failed, aborting SwarmController initialization.")
            raise RuntimeError("Channel healthcheck failed")
        self.workers: List[threading.Thread] = []
        self._stop_event = threading.Event()

    def start(self, initial_tasks: List[Dict] = None):
        """
        Launch GUI and headless agents and start routing loop.
        """
        logger.info(f"Starting SwarmController with {self.fleet_size} agents...")
        # 0. Spawn ChatGPT WebAgent producer thread
        try:
            from dream_mode.agents.chatgpt_web_agent import run_loop as chat_run_loop
            logger.info("Starting ChatGPTWebAgent producer thread...")
            chat_thread = threading.Thread(
                target=chat_run_loop,
                args=(self._stop_event,),
                name="ChatGPTWebAgent",
                daemon=True
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
            t = threading.Thread(target=self._worker_loop, name=f"Worker-{i+1}", daemon=True)
            t.start()
            self.workers.append(t)

        # 4. Start routing loop in main thread
        self._route_loop()

    def _worker_loop(self):
        """
        Worker thread: pull tasks, simulate processing, push results.
        """
        # Use VirtualDesktopController for headless launching if needed
        try:
            vdc = VirtualDesktopController()
            vdc.launch_cursor_headless(cursor_exe_path=os.getenv("CURSOR_PATH", "Cursor.exe"))
        except Exception:
            logger.info("Proceeding without headless setup")

        while not self._stop_event.is_set():
            # Record heartbeat for this worker agent
            try:
                self.nexus.record_heartbeat(threading.current_thread().name)
            except Exception as e:
                logger.warning(f"Failed to record heartbeat for {threading.current_thread().name}: {e}")
            # Claim the next pending task from TaskNexus
            task = self.nexus.get_next_task(agent_id=threading.current_thread().name)
            if task:
                logger.info(f"Worker received task: {task}")
                # Simulate work: echo back with a timestamp
                result = {"echo": task, "processed_at": time.time()}
                self.channel.push_result(result)
                logger.info(f"Worker pushed result: {result}")
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
                results = self.channel.pull_results()
                for res in results:
                    self._handle_result(res)
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
        # FeedbackEngineV2 analysis for archived failures
        try:
            fe = FeedbackEngineV2()
            analyses = fe.analyze_failures()
            # Save analysis per result id
            feedback_dir = os.path.join("dream_logs", "feedback")
            os.makedirs(feedback_dir, exist_ok=True)
            output_file = os.path.join(feedback_dir, f"failure_analysis_{result.get('id','unknown')}.json")
            fe.save_analysis(analyses, output_file=output_file)
            logger.info(f"🔍 Feedback analysis saved for result: {result.get('id')}")
        except Exception as e:
            logger.error(f"Failed to run feedback analysis for result {result.get('id')}: {e}", exc_info=True)
        # Persist modified_files and log_tail into runtime/task_list.json for lore compilation
        try:
            task_list_path = Path('runtime/task_list.json')
            tasks_data = json.loads(task_list_path.read_text(encoding='utf-8'))
            for t in tasks_data:
                if t.get('id') == result.get('id'):
                    payload = t.setdefault('payload', {})
                    # modified_files from result metadata
                    payload['modified_files'] = result.get('modified_files', [])
                    # log_tail from result stdout
                    stdout = result.get('stdout', '')
                    if isinstance(stdout, str):
                        lines = stdout.strip().splitlines()
                        payload['log_tail'] = '\n'.join(lines[-10:])
            task_list_path.write_text(json.dumps(tasks_data, indent=2), encoding='utf-8')
        except Exception:
            pass
        # Invoke lore compilation as a one-shot tool
        try:
            # Auto-generate Devlog lore for the swarm
            script = os.path.join(os.getcwd(), "_agent_coordination/tools/compile_lore.py")
            cmd = [
                "python", script,
                "--style", "devlog",
                "--translation", os.path.join(os.getcwd(), "dream_logs/config/dream_translation.yaml"),
                "--tasks", os.path.join(os.getcwd(), "runtime/task_list.json")
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
        thread = threading.Thread(target=self._stats_loop, args=(interval,), daemon=True, name="StatsAutoLogger")
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

if __name__ == "__main__":
    # CLI: allow specifying Azure connection or SAS token
    parser = argparse.ArgumentParser(description="Run SwarmController with Azure C2 channel")
    parser.add_argument("--connection-string", dest="connection_string", help="Azure storage connection string")
    parser.add_argument("--sas-token", dest="sas_token", help="Azure SAS token")
    parser.add_argument("--container-name", dest="container_name", default="dream-os-c2", help="Azure Blob container name")
    parser.add_argument("--fleet-size", dest="fleet_size", type=int, default=2, help="Number of Cursor agents in the swarm")
    parser.add_argument("--stats-interval", dest="stats_interval", type=int, help="Seconds between automatic stats snapshots (overrides STATS_INTERVAL env)")
    args = parser.parse_args()

    # Resolve credentials: CLI flags or environment
    conn_str = args.connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    sas_tok = args.sas_token or os.getenv("AZURE_STORAGE_SAS_TOKEN")
    # Allow local mode fallback without Azure credentials
    use_local = os.getenv("USE_LOCAL_BLOB", "0") == "1"
    if not use_local and not conn_str and not sas_tok:
        parser.error("Either --connection-string or --sas-token must be provided or set in environment variables (or enable USE_LOCAL_BLOB=1 for local mode).")

    controller = SwarmController(
        fleet_size=args.fleet_size,
        container_name=args.container_name,
        connection_string=conn_str,
        sas_token=sas_tok,
        stats_interval=args.stats_interval
    )
    # Default demo task if none provided
    initial_tasks = [{"id": "demo-1", "payload": "hello swarm"}]
    controller.start(initial_tasks=initial_tasks) 