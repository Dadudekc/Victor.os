# cursor_dispatcher.py
"""
Standalone Cursor Dispatcher Script.

This script loads tasks from a local JSON queue file (`task_queue.json`),
renders them using a Jinja2 template, and injects the resulting prompts as
keystrokes into a headlessly launched Cursor application. It uses a
VirtualDesktopController for managing the Cursor instance and keystroke injection.

FIXME: This is a standalone script and not integrated with the main DreamOS
       AgentBus or ProjectBoardManager. Task sourcing and status tracking are local.
       Consider integration if it needs to be part of the broader agent swarm.
FIXME: Lacks a feedback mechanism for actual task success/failure within Cursor.
"""

import json
import logging
import os
import time
from pathlib import Path

from utils.prompt_renderer import PromptRenderer

from .virtual_desktop_runner import VirtualDesktopController

# Logger Setup
logger = logging.getLogger("CursorDispatcher")
# FIXME: Module-level basicConfig can interfere; configure logging at app entry point.
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
# )

# File/Path Constants
AGENT_DIR = Path(__file__).parent
BASE_DIR = AGENT_DIR.parent
QUEUE_FILE = BASE_DIR / "task_queue.json"
TEMPLATE_DIR = BASE_DIR.parent.parent / "templates"

# Initialize Prompt Renderer
try:
    prompt_renderer = PromptRenderer(TEMPLATE_DIR)
except FileNotFoundError:
    logger.error(
        f"Template directory not found at {TEMPLATE_DIR}. Cannot initialize PromptRenderer."  # noqa: E501
    )
    prompt_renderer = None

# --- Prompt Template ---
# PROMPT_TEMPLATE = """..."""


# --- Dispatcher Core ---
def render_task_prompt(task: dict) -> str | None:
    if not prompt_renderer:
        logger.error("PromptRenderer not initialized. Cannot render task prompt.")
        return None

    # FIXME: Hardcoded template name "chatgpt_task_prompt.j2". Consider making configurable.
    rendered = prompt_renderer.render("chatgpt_task_prompt.j2", {"task": task})
    if rendered is None:
        logger.error(
            f"Failed to render template 'chatgpt_task_prompt.j2' for task {task.get('task_id')}"  # noqa: E501
        )
    return rendered


def load_queue() -> list:
    if not QUEUE_FILE.exists():
        logger.warning(f"No task queue found at {QUEUE_FILE}. Creating empty.")
        QUEUE_FILE.write_text("[]", encoding="utf-8")
        return []
    try:
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Failed to load task queue from {QUEUE_FILE}: {e}", exc_info=True)
        return []


def save_queue(queue: list):
    try:
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(queue, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save queue to {QUEUE_FILE}: {e}", exc_info=True)


def dispatch_tasks(vdc: VirtualDesktopController):
    queue = load_queue()
    modified = False

    for task in queue:
        if task.get("status") != "pending":
            continue

        try:
            logger.info(f"Dispatching task: {task['task_id']}")
            rendered = render_task_prompt(task)

            if rendered is None:
                logger.error(
                    f"Skipping task {task['task_id']} due to rendering failure."
                )
                continue

            logger.debug(f"Rendered prompt:\n{rendered[:150]}...")

            vdc.inject_keystrokes(rendered)
            task["status"] = "injected"
            modified = True
            time.sleep(1.5)  # Small gap between injections
        except Exception as e:
            logger.error(f"Failed to inject task {task['task_id']}: {e}", exc_info=True)

    if modified:
        save_queue(queue)


# --- Entry Point ---
def run_loop(shutdown_event):
    if not prompt_renderer:
        logger.critical("PromptRenderer failed to initialize. Dispatcher cannot run.")
        return

    logger.info("🚀 Cursor Dispatcher started.")

    # FIXME: Cursor path detection relies on a list of common paths.
    #        A configuration option for `cursor_path` would be more robust.
    if os.name == "nt":
        cursor_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Cursor\Cursor.exe"),
            r"C:\Program Files\Cursor\Cursor.exe",
        ]
    else:
        cursor_paths = [
            "/usr/bin/cursor",
            "/opt/Cursor/cursor",
            os.path.expanduser("~/Applications/Cursor.AppImage"),
        ]
    cursor_path = next((p for p in cursor_paths if os.path.exists(p)), None)

    if not cursor_path:
        logger.error("Cursor executable not found. Please set path manually.")
        return

    vdc = VirtualDesktopController()
    try:
        logger.info(f"Launching Cursor headlessly from: {cursor_path}")
        vdc.launch_cursor_headless(cursor_exe_path=cursor_path)

        while not shutdown_event.is_set():
            dispatch_tasks(vdc)
            if shutdown_event.wait(5):
                break
    except Exception as e:
        logger.error(f"Dispatcher loop error: {e}", exc_info=True)
    finally:
        logger.info("Shutting down virtual desktop...")
        vdc.teardown()
        logger.info("Cursor Dispatcher stopped.")


# Optional manual run for testing
if __name__ == "__main__":
    import threading

    shutdown_event = threading.Event()
    try:
        run_loop(shutdown_event)
    except KeyboardInterrupt:
        shutdown_event.set()
