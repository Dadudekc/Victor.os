# task_feedback_router.py

import os
import json
import time
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("TaskFeedbackRouter")
logger.setLevel(logging.INFO)

# --- Path Setup ---
BASE_DIR = Path(__file__).parent
INBOX_ROOT = BASE_DIR / "inbox"
OUTBOX_ROOT = BASE_DIR / "outbox"
SENT_ROOT = BASE_DIR / "sent"
ARCHIVE_ROOT = BASE_DIR / "archive"
FAILED_ROOT = BASE_DIR / "failed"

# --- File Finding Logic ---
def find_task_file(agent_id: str, task_id: str) -> Path | None:
    search_dirs = [
        SENT_ROOT / agent_id,
        OUTBOX_ROOT / agent_id,
        ARCHIVE_ROOT / agent_id,
        FAILED_ROOT / agent_id,
    ]

    for d in search_dirs:
        if d.exists():
            for file in d.glob(f"{task_id}*.md"):
                return file
    return None

# --- Feedback Routing Logic ---
def route_feedback(agent_id: str, feedback: dict):
    task_id = feedback.get("task_id")
    signal = feedback.get("feedback")
    details = feedback.get("details", "")
    
    if not task_id or not signal:
        logger.warning(f"[{agent_id}] Missing required keys in feedback: {feedback}")
        return

    original_file = find_task_file(agent_id, task_id)
    if not original_file or not original_file.exists():
        logger.warning(f"[{agent_id}] Original file for task {task_id} not found.")
        return

    # Decide target dir based on feedback signal
    if signal == "APPROVED":
        target_dir = ARCHIVE_ROOT / agent_id
    elif signal == "REVISE":
        target_dir = OUTBOX_ROOT / agent_id
    elif signal == "REJECTED":
        target_dir = FAILED_ROOT / agent_id
    else:
        logger.warning(f"[{agent_id}] Unknown feedback signal: {signal}. Routing to 'failed/'.")
        target_dir = FAILED_ROOT / agent_id

    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / original_file.name

    # If REVISE, prepend feedback header to file
    if signal == "REVISE":
        try:
            with open(original_file, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Reformat feedback header generation slightly
            details_with_prefix = details.replace('\n', '\n# ')
            feedback_header = (
                f"# --- FEEDBACK ({signal}) ---\n"
                f"# {details_with_prefix}\n"
                f"# -------------------------\n\n"
            )

            updated_content = feedback_header + original_content
            with open(original_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
        except Exception as e:
            logger.error(f"[{agent_id}] Failed to prepend feedback: {e}", exc_info=True)

    try:
        shutil.move(str(original_file), str(target_path))
        logger.info(f"[{agent_id}] Routed task {task_id} → {signal.upper()} → {target_path}")
    except Exception as e:
        logger.error(f"[{agent_id}] Failed to move file: {e}", exc_info=True)

# --- Agent Main Loop ---
def run_loop(shutdown_event):
    logger.info("📬 Task Feedback Router started.")
    processed_timestamps = {}

    while not shutdown_event.is_set():
        for inbox_dir in INBOX_ROOT.glob("*"):
            if not inbox_dir.is_dir():
                continue

            agent_id = inbox_dir.name
            inbox_file = inbox_dir / "pending_responses.json"

            if not inbox_file.exists():
                continue

            try:
                with open(inbox_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    feedbacks = json.loads(content) if content.strip() else []
            except Exception as e:
                logger.error(f"[{agent_id}] Error reading inbox: {e}", exc_info=True)
                continue

            pending = []
            for feedback in feedbacks:
                ts = feedback.get("timestamp")
                if ts and ts in processed_timestamps.get(agent_id, set()):
                    pending.append(feedback)
                else:
                    route_feedback(agent_id, feedback)
                    processed_timestamps.setdefault(agent_id, set()).add(ts)

            try:
                with open(inbox_file, "w", encoding="utf-8") as f:
                    json.dump(pending, f, indent=2)
            except Exception as e:
                logger.error(f"[{agent_id}] Failed to update inbox file: {e}", exc_info=True)

        if shutdown_event.wait(5):
            break

    logger.info("📪 Task Feedback Router exiting.") 