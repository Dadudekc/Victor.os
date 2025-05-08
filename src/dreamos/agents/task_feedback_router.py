# task_feedback_router.py
"""
Standalone Task Feedback Router Script.

This script monitors 'inbox' directories for various agents, reads feedback
messages (JSON format) from 'pending_responses.json' files within these inboxes.
Based on the feedback signal ('APPROVED', 'REVISE', 'REJECTED'), it locates
the original task markdown file and moves it to a corresponding state directory
(archive, outbox, failed). For 'REVISE' signals, it prepends feedback details
to the task file before moving.

FIXME: This is a standalone script relying on a local file-based polling system.
       - The directory structure (inbox, outbox, sent, archive, failed) is assumed
         to be relative to this script and might conflict/overlap with other state
         management (e.g., ProjectBoardManager, runtime/agent_comms mailboxes).
       - The read/process/write cycle for 'pending_responses.json' is not atomic
         and could lead to issues with concurrent access or script crashes.
       - The `processed_timestamps` cache is in-memory and lost on restart.
       - Consider integration with AgentBus for event-driven feedback handling if
         this is intended to be part of the broader agent system.
"""

import json
import logging
import shutil
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
        logger.warning(
            f"[{agent_id}] Unknown feedback signal: {signal}. Routing to 'failed/'."
        )
        target_dir = FAILED_ROOT / agent_id

    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / original_file.name

    # If REVISE, prepend feedback header to file
    if signal == "REVISE":
        try:
            with open(original_file, "r", encoding="utf-8") as f:
                original_content = f.read()

            # Reformat feedback header generation slightly
            details_with_prefix = details.replace("\n", "\n# ")
            feedback_header = (
                f"# --- FEEDBACK ({signal}) ---\n"
                f"# {details_with_prefix}\n"
                f"# -------------------------\n\n"
            )

            updated_content = feedback_header + original_content
            with open(original_file, "w", encoding="utf-8") as f:
                f.write(updated_content)
        except Exception as e:
            logger.error(f"[{agent_id}] Failed to prepend feedback: {e}", exc_info=True)

    try:
        shutil.move(str(original_file), str(target_path))
        logger.info(
            f"[{agent_id}] Routed task {task_id} → {signal.upper()} → {target_path}"
        )
    except Exception as e:
        logger.error(f"[{agent_id}] Failed to move file: {e}", exc_info=True)


# --- Agent Main Loop ---
def run_loop(shutdown_event):
    logger.info("📬 Task Feedback Router started.")
    # FIXME: processed_timestamps is an in-memory cache. If the script restarts,
    #        it might reprocess feedback unless pending_responses.json is accurately
    #        managed to only contain truly pending items.
    processed_timestamps = {}

    while not shutdown_event.is_set():
        for inbox_dir in INBOX_ROOT.glob("*"):
            if not inbox_dir.is_dir():
                continue

            agent_id = inbox_dir.name
            inbox_file = inbox_dir / "pending_responses.json"

            if not inbox_file.exists():
                continue
            
            # FIXME: The read-process-rewrite logic for inbox_file is not atomic.
            #        Concurrent modifications or crashes could lead to data loss or
            #         reprocessing. Consider file locking or a more robust queue.
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
                logger.error(
                    f"[{agent_id}] Failed to update inbox file: {e}", exc_info=True
                )

        if shutdown_event.wait(5):
            break

    logger.info("📪 Task Feedback Router exiting.")
