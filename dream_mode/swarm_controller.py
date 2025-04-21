import os
import threading
import time
import logging
import subprocess
import argparse
from typing import Any, Dict, List

try:
    from dream_mode.azure_blob_channel import AzureBlobChannel
except ImportError:
    AzureBlobChannel = None
from dream_mode.local_blob_channel import LocalBlobChannel
from dream_mode.cursor_fleet_launcher import launch_cursor_instance, get_cursor_windows, assign_windows_to_monitors
from dream_mode.virtual_desktop_runner import VirtualDesktopController

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
    ):
        self.fleet_size = fleet_size
        # Initialize C2 channel (Azure or Local) for task/result exchange
        use_local = os.getenv("USE_LOCAL_BLOB", "0") == "1" or AzureBlobChannel is None or (
            not connection_string and not sas_token
        )
        if use_local:
            self.channel = LocalBlobChannel()
        else:
            self.channel = AzureBlobChannel(
                container_name=container_name,
                sas_token=sas_token,
                connection_string=connection_string,
            )
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
        # Dispatch initial tasks if provided
        if initial_tasks:
            for task in initial_tasks:
                logger.info(f"Dispatching initial task: {task}")
                self.channel.push_task(task)
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
            tasks = self.channel.pull_tasks()
            for task in tasks:
                logger.info(f"Worker received task: {task}")
                # Simulate work: echo back with a timestamp
                result = {"echo": task, "processed_at": time.time()}
                self.channel.push_result(result)
                logger.info(f"Worker pushed result: {result}")
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
        # Invoke lore compilation as a one-shot tool
        try:
            script = os.path.join(os.getcwd(), "_agent_coordination/tools/compile_lore.py")
            cmd = ["python", script, "--once", "--tasks", os.path.join(os.getcwd(), "runtime/task_list.json")]
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


if __name__ == "__main__":
    # CLI: allow specifying Azure connection or SAS token
    parser = argparse.ArgumentParser(description="Run SwarmController with Azure C2 channel")
    parser.add_argument("--connection-string", dest="connection_string", help="Azure storage connection string")
    parser.add_argument("--sas-token", dest="sas_token", help="Azure SAS token")
    parser.add_argument("--container-name", dest="container_name", default="dream-os-c2", help="Azure Blob container name")
    parser.add_argument("--fleet-size", dest="fleet_size", type=int, default=2, help="Number of Cursor agents in the swarm")
    args = parser.parse_args()

    # Resolve credentials: CLI flags or environment
    conn_str = args.connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    sas_tok = args.sas_token or os.getenv("AZURE_STORAGE_SAS_TOKEN")
    if not conn_str and not sas_tok:
        parser.error("Either --connection-string or --sas-token must be provided or set in environment variables.")

    controller = SwarmController(
        fleet_size=args.fleet_size,
        container_name=args.container_name,
        connection_string=conn_str,
        sas_token=sas_tok
    )
    # Default demo task if none provided
    initial_tasks = [{"id": "demo-1", "payload": "hello swarm"}]
    controller.start(initial_tasks=initial_tasks) 