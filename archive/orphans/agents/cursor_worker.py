"""
Cursor Worker: A simulated worker that processes tasks by automating the
Cursor IDE user interface using an OrchestratorBot.

This worker pulls tasks from a (currently placeholder) TaskChannel, performs
UI actions like typing, clicking image-based buttons, and clipboard operations,
and then pushes results back to the channel.

FIXME: The TaskChannel is a placeholder and needs to be replaced with a real
       task queuing/communication mechanism (e.g., AgentBus, ProjectBoardManager).
"""

import logging
import os
import time

# EDIT: Import OrchestratorBot and AppConfig
from ..core.bots.orchestrator_bot import OrchestratorBot
from ..core.config import AppConfig  # Added missing import

# from pathlib import Path # F401 Unused

# import pyautogui # EDIT: No longer needed directly
# import pyperclip # EDIT: No longer needed directly


# EDIT: Import channel abstraction (assuming it exists based on usage)
# This needs to be defined or imported correctly
# Example: from ..core.comms import TaskChannel
# Placeholder:
# FIXME: TaskChannel is a placeholder and needs to be replaced with a real
#        task queuing/communication mechanism (e.g., AgentBus, ProjectBoardManager).
class TaskChannel:
    def pull_tasks(self):
        # Placeholder implementation
        print("WARNING: Using placeholder TaskChannel.pull_tasks()")
        return []

    def push_result(self, result):
        # Placeholder implementation
        print(f"WARNING: Using placeholder TaskChannel.push_result(): {result}")
        pass


channel = TaskChannel()  # Placeholder instantiation

# Logger for the Cursor worker
logger = logging.getLogger("CursorWorker")

# EDIT: Define missing constant (copied from gui_interaction.py)
RESPONSE_CHECK_INTERVAL = 1  # Seconds between response checks
# TODO: Consider making UI element identifiers (image names, window titles)
#       configurable via AppConfig instead of being hardcoded strings.
#       Example: CURSOR_IDE_WINDOW_TITLE = "Cursor IDE"
#                ACCEPT_BUTTON_IMAGE = "accept_button.png"
#                SPINNER_IMAGE = "spinner.png"


def run(config: AppConfig, worker_id="worker-001"):
    """Simulated Cursor worker that pulls tasks and pushes results."""
    # EDIT: Instantiate the bot correctly
    bot = OrchestratorBot(config=config, agent_id=f"CursorWorker_{worker_id}")
    assets_dir = config.gui_assets_dir  # Assuming config has this attribute

    def click_button(assets_dir: str, image_name, confidence=0.8, retry=3):
        """Locate and click a button by its image file using the bot."""
        image_path = os.path.join(assets_dir, image_name)
        # EDIT: Rename unused loop var
        for _attempt in range(retry):
            loc_tuple = bot.locate_center_on_screen(image_path, confidence=confidence)
            if loc_tuple:
                # EDIT: Use bot.click
                if bot.click(x=loc_tuple[0], y=loc_tuple[1]):
                    logger.info(
                        f"[{worker_id}] Clicked {image_name} via bot at {loc_tuple}."
                    )
                    return True
                else:
                    logger.warning(
                        f"[{worker_id}] Bot click failed at {loc_tuple} for {image_name}. Retrying..."  # noqa: E501
                    )
            # else: # Location failed
            #    logger.debug(f"[{worker_id}] Image {image_name} not found on attempt {_attempt+1}/{retry}.")  # noqa: E501

            time.sleep(1)  # Wait before retrying
        logger.error(
            f"[{worker_id}] Failed to locate/click image {image_name} after {retry} retries."  # noqa: E501
        )
        return False

    def wait_for_idle(assets_dir: str, image_name="spinner.png", timeout=60):
        """Wait for a UI spinner to disappear indicating completion, using the bot."""
        start = time.time()
        image_path = os.path.join(assets_dir, image_name)
        while time.time() - start < timeout:
            try:
                # EDIT: Use bot.locate_on_screen
                # We want to check if the image is *not* found
                location = bot.locate_on_screen(image_path, confidence=0.8)
                not_busy = location is None  # True if spinner is not found
            except Exception as e:
                logger.error(
                    f"[{worker_id}] Error locating image {image_path} via bot: {e}",
                    exc_info=True,
                )
                # Consider returning False or raising on persistent error
                return False  # Exit loop on error
            if not_busy:
                logger.debug(
                    f"[{worker_id}] Idle state detected (image {image_name} not found)."
                )
                return True
            time.sleep(RESPONSE_CHECK_INTERVAL)  # Use constant
        logger.warning(
            f"[{worker_id}] Timeout waiting for idle state (image {image_name} persisted)."  # noqa: E501
        )
        return False

    def process_task_ui(task, worker_id):
        """Automate Cursor IDE UI to handle a task using the bot."""
        task_id = task.get("id") or task.get("task_id") or "unknown_task"
        logger.info(f"[{worker_id}] ▶️ UI automate task {task_id} using OrchestratorBot")

        # Focus the Cursor IDE window using the bot
        # EDIT: Use bot.activate_window
        # FIXME: Hardcoded window title "Cursor IDE" should be configurable.
        if not bot.activate_window("Cursor IDE"):
            logger.error(f"[{worker_id}] Failed to activate Cursor IDE window via bot.")
            # Decide if this is a fatal error for the task
            # return {"id": task_id, "error": "window_activation_failed"}
            # Continue for now, typing might still work if already focused

        # Type the task payload using the bot
        payload = task.get("payload") or task.get("content") or ""
        if not payload:
            logger.warning(
                f"[{worker_id}] No payload found for task {task_id}. Skipping typing."
            )
        elif not bot.typewrite(str(payload), interval=0.02):
            logger.error(
                f"[{worker_id}] Bot failed to type task payload for {task_id}."
            )
            return {"id": task_id, "error": "typing_failed"}

        # Click the accept button using the bot helper
        # FIXME: Hardcoded image name "accept_button.png" should be configurable.
        if not click_button(assets_dir, "accept_button.png"):
            logger.error(
                f"[{worker_id}] Failed find/click accept_button.png for task {task_id}."
            )
            return {"id": task_id, "error": "accept_button_not_found"}

        # Wait for code generation to complete using the bot helper
        # FIXME: Hardcoded image name "spinner.png" should be configurable.
        if not wait_for_idle(assets_dir, "spinner.png"):
            logger.warning(
                f"[{worker_id}] Timeout waiting for generation to complete for task {task_id}."  # noqa: E501
            )
            # Might not be fatal, attempt extraction anyway
            # return {"id": task_id, "error": "generation_timeout"}

        # Extract generated code from the IDE via clipboard using the bot
        result_content = None
        try:
            # Select all generated code and copy to clipboard using bot hotkeys
            # EDIT: Use bot.hotkey
            if not bot.hotkey("ctrl", "a"):
                raise RuntimeError("Failed to execute 'Ctrl+A' hotkey.")
            time.sleep(0.1)  # Short delay between hotkeys
            if not bot.hotkey("ctrl", "c"):
                raise RuntimeError("Failed to execute 'Ctrl+C' hotkey.")
            time.sleep(0.5)  # Allow time for clipboard update

            # EDIT: Use bot.get_clipboard_content
            result_content = bot.get_clipboard_content()
            if result_content is None:
                raise RuntimeError("Failed to get clipboard content via bot.")
            logger.info(
                f"[{worker_id}] Successfully extracted content ({len(result_content)} chars) for task {task_id} via clipboard."  # noqa: E501
            )

        except Exception as e:
            logger.error(
                f"[{worker_id}] Failed to extract result via clipboard for task {task_id}: {e}",  # noqa: E501
                exc_info=True,
            )
            # Fallback if clipboard extraction fails
            result_content = f"Error during content extraction for {task_id}: {e}"
            # Consider returning error status
            return {"id": task_id, "error": f"clipboard_extraction_failed: {e}"}

        return {"id": task_id, "status": "success", "content": result_content}

    while True:
        # EDIT: Use placeholder TaskChannel
        # FIXME: Replace placeholder channel.pull_tasks() with actual task source.
        tasks = channel.pull_tasks()
        if not tasks:
            logger.debug(f"[{worker_id}] No tasks found in channel. Sleeping.")
            time.sleep(5)  # Sleep longer if no tasks
            continue

        for task in tasks:
            # Automate Cursor UI for each task
            ui_result = process_task_ui(task, worker_id)

            # EDIT: Use placeholder TaskChannel
            # FIXME: Replace placeholder channel.push_result() with actual result sink.
            channel.push_result(ui_result)
            logger.info(
                f"[{worker_id}] Pushed result for task {ui_result.get('id')}: Status {ui_result.get('status', 'unknown')}"  # noqa: E501
            )

        time.sleep(RESPONSE_CHECK_INTERVAL)  # Use constant for loop sleep


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
