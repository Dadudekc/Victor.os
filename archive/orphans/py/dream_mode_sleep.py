#!/usr/bin/env python3
"""
DreamModeSleep.py

Main loop for launching the full automation stack:
- Launches ChatGPT Web Agent
- Launches Cursor Dispatcher (virtual desktop + keystroke injection)
- Launches Task Feedback Router

These agents together form a complete closed-loop workflow.
"""

import sys
from pathlib import Path

# --- Add parent directory to sys.path ---
# This allows absolute imports from directories like 'tools' at the root
SCRIPT_DIR = Path(__file__).resolve().parent
PARENT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PARENT_DIR))
# ---

import logging  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402

# --- Agent Imports ---
from agents import (  # noqa: E402
    chatgpt_web_agent,
    cursor_dispatcher,
    task_feedback_router,
)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s",
)
logger = logging.getLogger("dream_mode_sleep")

# --- Shutdown Event for All Threads ---
shutdown_event = threading.Event()


# --- Agent Launchers ---
def run_chatgpt_web_agent():
    logger.info("Attempting to start WebAgent loop...")
    try:
        chatgpt_web_agent.run_loop(shutdown_event)
    except Exception as e:
        logger.error(f"Web Agent crashed: {e}", exc_info=True)
    logger.info("WebAgent loop function finished.")


def run_cursor_dispatcher():
    logger.info("Attempting to start Dispatcher loop...")
    try:
        cursor_dispatcher.run_loop(shutdown_event)
    except Exception as e:
        logger.error(f"Cursor Dispatcher crashed: {e}", exc_info=True)
    logger.info("Dispatcher loop function finished.")


def run_task_feedback_router():
    logger.info("Attempting to start Router loop...")
    try:
        task_feedback_router.run_loop(shutdown_event)
    except Exception as e:
        logger.error(f"Feedback Router crashed: {e}", exc_info=True)
    logger.info("Router loop function finished.")


# --- Main ---
if __name__ == "__main__":
    logger.info("🔁 Dream Mode Initialization: Starting all agents...")

    threads = [
        threading.Thread(target=run_chatgpt_web_agent, name="WebAgent", daemon=True),
        threading.Thread(target=run_cursor_dispatcher, name="Dispatcher", daemon=True),
        threading.Thread(target=run_task_feedback_router, name="Router", daemon=True),
    ]

    for thread in threads:
        thread.start()

    try:
        while True:
            time.sleep(1)  # Idle while agents work
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested via keyboard.")
        shutdown_event.set()

    logger.info("🧹 Waiting for agents to shut down...")
    for thread in threads:
        thread.join()

    logger.info("✅ Dream Mode shutdown complete.")
