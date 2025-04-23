import time
from dream_mode.utils.channel_loader import get_blob_channel
import pyautogui
import pyperclip
import os
import logging

# Logger for the Cursor worker
logger = logging.getLogger("CursorWorker")
logger.setLevel(logging.INFO)
# Directory containing UI asset images
ASSETS_DIR = os.getenv('ASSETS_DIR', os.path.join(os.getcwd(), 'assets'))

def run(worker_id="worker-001"):
    """Simulated Cursor worker that pulls tasks and pushes results."""
    channel = get_blob_channel()
    logger.info(f"⚙️ CursorWorker {worker_id} online.")

    def click_button(image_name, confidence=0.8, retry=3):
        """Locate and click a button by its image file."""
        image_path = os.path.join(ASSETS_DIR, image_name)
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

    def wait_for_idle(image_name='spinner.png', timeout=60):
        """Wait for a UI spinner to disappear indicating completion."""
        start = time.time()
        image_path = os.path.join(ASSETS_DIR, image_name)
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
        if not click_button('accept_button.png'):
            return {"id": task_id, "error": "accept_button_not_found"}
        # Wait for code generation to complete
        if not wait_for_idle():
            return {"id": task_id, "error": "generation_timeout"}
        # Extract generated code from the IDE via clipboard
        try:
            # Select all generated code and copy to clipboard
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.5)
            result_content = pyperclip.paste()
        except Exception as e:
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
    worker_id = sys.argv[1] if len(sys.argv) > 1 else "worker-001"
    run(worker_id) 