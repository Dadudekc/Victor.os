import logging
import os
import time
from pathlib import Path

import pyautogui
import pyperclip

from dreamos.utils.dream_mode_utils.channel_loader import get_blob_channel

from ..config import AppConfig

# Logger for the Cursor worker
logger = logging.getLogger("CursorWorker")


def run(config: AppConfig, worker_id="worker-001"):
    """Simulated Cursor worker that pulls tasks and pushes results."""
    assets_dir = str(config.project_root / getattr(config.paths, "assets", "assets"))
    channel = get_blob_channel(config=config)
    logger.info(f"⚙️ CursorWorker {worker_id} online. Assets: {assets_dir}")

    def click_button(assets_dir: str, image_name, confidence=0.8, retry=3):
        """Locate and click a button by its image file."""
        image_path = os.path.join(assets_dir, image_name)
        for _ in range(retry):
            try:
                loc = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
            except Exception as e:
                logger.error(f"[{worker_id}] Error locating image {image_path}: {e}")
                return False
            if loc:
                pyautogui.click(loc)
                return True
            time.sleep(1)
        return False

    def wait_for_idle(assets_dir: str, image_name="spinner.png", timeout=60):
        """Wait for a UI spinner to disappear indicating completion."""
        start = time.time()
        image_path = os.path.join(assets_dir, image_name)
        while time.time() - start < timeout:
            try:
                not_busy = not pyautogui.locateOnScreen(image_path, confidence=0.8)
            except Exception as e:
                logger.error(f"[{worker_id}] Error locating image {image_path}: {e}")
                return True
            if not_busy:
                return True
            time.sleep(1)
        return False

    def process_task_ui(task, worker_id):
        """Automate Cursor IDE UI to handle a task."""
        task_id = task.get("id") or task.get("task_id")
        print(f"[{worker_id}] ▶️ UI automate task {task_id}")
        # Focus the Cursor IDE window if possible
        try:
            windows = pyautogui.getWindowsWithTitle("Cursor IDE")
            if windows:
                windows[0].activate()
        except Exception:
            pass
        # Type the task payload
        payload = task.get("payload") or task.get("content") or ""
        pyautogui.write(str(payload), interval=0.02)
        # Click the accept button
        if not click_button(assets_dir, "accept_button.png"):
            return {"id": task_id, "error": "accept_button_not_found"}
        # Wait for code generation to complete
        if not wait_for_idle(assets_dir):
            return {"id": task_id, "error": "generation_timeout"}
        # Extract generated code from the IDE via clipboard
        try:
            # Select all generated code and copy to clipboard
            pyautogui.hotkey("ctrl", "a")
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.5)
            result_content = pyperclip.paste()
        except Exception as _e:
            # Fallback if clipboard extraction fails
            result_content = f"Auto-generated content for {task_id}"
        return {"id": task_id, "content": result_content}

    while True:
        tasks = channel.pull_tasks()
        for task in tasks:
            # Automate Cursor UI for each task
            ui_result = process_task_ui(task, worker_id)
            channel.push_result(ui_result)
            print(f"[{worker_id}] pushed: {ui_result.get('id')}")
        time.sleep(1)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    try:
        from ..core.config import load_app_config

        config = load_app_config()
        if not config:
            raise ValueError(
                "Failed to load AppConfig for CursorWorker standalone run."
            )
    except Exception as e:
        logging.error(f"Cannot start CursorWorker standalone: {e}")
        exit(1)

    worker_id = sys.argv[1] if len(sys.argv) > 1 else "worker-001"
    run(config=config, worker_id=worker_id)
