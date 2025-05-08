import json
import logging
import os
import re
import uuid
from pathlib import Path
from datetime import datetime, timezone

# --- Project Path Setup ---
# script_dir = os.path.dirname(__file__)  # social/
# project_root = os.path.abspath(os.path.join(script_dir, ".."))  # Go up one level
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)
# -------------------------

# --- Dependencies ---
from dreamforge.core.governance_memory_engine import log_event  # noqa: I001
from dreamos.core.comms.mailbox import (
    MAILBOXES_DIR_NAME,
    MailboxError,
    MailboxHandler,
)
from dreamos.core.config import AppConfig
from dreamos.utils.common_utils import get_utc_iso_timestamp

# FIXME: The source of AGENT_ID (recipient for tasks) needs to be clarified.
#        It was 'from social.constants import AGENT_ID'. This suggests a dependency
#        outside the dreamos structure or a mislocated constant. 
#        For now, define it as a placeholder that needs configuration.
RECIPIENT_AGENT_ID_FOR_FEEDBACK_TASKS = "PLACEHOLDER_CONFIGURE_ME" 

# --------------------

_SOURCE = "FeedbackProcessor"
_SOURCE_AGENT_ID = "FeedbackProcessorService" # Made more specific for a service

# --- Configuration ---
# Simple keyword matching for MVP
SUGGESTION_KEYWORDS = [
    "suggest",
    "recommend",
    "idea",
    "feature",
    "request",
    "improve",
    "add",
    "create",
]
BUG_KEYWORDS = ["bug", "error", "problem", "issue", "fix", "broken", "doesn't work"]

# AppConfig should be passed to a main function or class constructor, not loaded globally here.
# MAILBOXES_BASE will be derived from AppConfig when available.

# --- Initialize Mailbox Handler ---
# MailboxHandler (task_sender_mailbox) should be initialized in a class or main function
# that receives AppConfig.

def _extract_potential_suggestions(text: str) -> list[tuple[str, str]]:
    """Rudimentary extraction of sentences containing keywords."""
    suggestions = []
    if not text or not isinstance(text, str):
        return suggestions

    # Simple sentence splitting (improve later)
    sentences = re.split(r"[.!?\n]+\s*", text)

    for sentence in sentences:
        sentence_lower = sentence.lower()
        found_type = None
        for keyword in SUGGESTION_KEYWORDS:
            if keyword in sentence_lower:
                found_type = "suggestion"
                break
        if not found_type:
            for keyword in BUG_KEYWORDS:
                if keyword in sentence_lower:
                    found_type = "bug_report"
                    break

        if found_type and len(sentence.strip()) > 10:  # Avoid trivial matches
            suggestions.append((found_type, sentence.strip()))

    return suggestions


def _create_task_message(
    feedback_type: str, content: str, original_context: dict
) -> dict:
    """Formats an identified feedback item into a task message for the agent mailbox."""
    task_id = f"feedback_task_{uuid.uuid4()}"
    timestamp = get_utc_iso_timestamp()

    # Define task structure (adapt as needed)
    command = "process_feedback_item"  # New command for agent to handle
    details = {
        "feedback_id": task_id,
        "type": feedback_type,  # 'suggestion', 'bug_report'
        "original_text": content,
        "source_platform": original_context.get("platform"),
        "source_author": original_context.get("author"),
        "source_url": original_context.get("url"),
        "timestamp_received": original_context.get("timestamp"),
        "processing_notes": "Extracted automatically by FeedbackProcessor.",
    }

    message = {
        "message_id": task_id,
        "sender_agent_id": _SOURCE_AGENT_ID,
        "recipient_agent_id": RECIPIENT_AGENT_ID_FOR_FEEDBACK_TASKS, # Use defined placeholder
        "timestamp": timestamp,
        "type": "COMMAND",  # It's a command for the agent
        "command": command,
        "details": details,
    }
    return message


def process_feedback(feedback_items: list[dict]):
    """
    Parses a list of feedback items (mentions, comments), identifies potential
    suggestions or bugs using keywords, and creates task messages in the agent's inbox.

    Args:
        feedback_items: A list of dictionaries, where each dict represents a
                        feedback item (e.g., from scraping results). Expected keys
                        might include 'text', 'author', 'url', 'platform', 'timestamp'.
    """
    log_event("FEEDBACK_PROC_START", _SOURCE, {"item_count": len(feedback_items)})
    tasks_created = 0
    errors = 0

    if not isinstance(feedback_items, list):
        log_event(
            "FEEDBACK_PROC_ERROR",
            _SOURCE,
            {"error": "Invalid input: feedback_items is not a list"},
        )
        return

    for item in feedback_items:
        if not isinstance(item, dict) or "text" not in item:
            log_event(
                "FEEDBACK_PROC_WARN",
                _SOURCE,
                {"warning": "Skipping invalid feedback item", "item": item},
            )
            continue

        text_content = item.get("text")
        potential_matches = _extract_potential_suggestions(text_content)

        if potential_matches:
            log_event(
                "FEEDBACK_PROC_MATCH",
                _SOURCE,
                {
                    "matches_found": len(potential_matches),
                    "source_text_snippet": text_content[:100],
                },
            )
            for feedback_type, extracted_content in potential_matches:
                try:
                    task_message = _create_task_message(
                        feedback_type, extracted_content, item
                    )
                    # Send the task message using MailboxHandler
                    # Requires MailboxHandler to be initialized correctly and AGENT_INBOX path to be valid  # noqa: E501
                    filename_prefix = f"task_{feedback_type}"
                    if task_sender_mailbox: # task_sender_mailbox needs to be passed or initialized in context
                        success = task_sender_mailbox.send_message(
                            task_message,
                            recipient_agent_id=RECIPIENT_AGENT_ID_FOR_FEEDBACK_TASKS, # Use defined placeholder
                            filename_prefix=filename_prefix,
                        )
                        if success:
                            tasks_created += 1
                            log_event(
                                "FEEDBACK_PROC_TASK_CREATED",
                                _SOURCE,
                                {
                                    "task_id": task_message["message_id"],
                                    "type": feedback_type,
                                },
                            )
                        else:
                            errors += 1
                            log_event(
                                "FEEDBACK_PROC_ERROR",
                                _SOURCE,
                                {
                                    "error": "Failed to send task message via MailboxHandler",  # noqa: E501
                                    "task_details": task_message.get("details"),
                                },
                            )
                    else:
                        errors += 1
                        log_event(
                            "FEEDBACK_PROC_ERROR",
                            _SOURCE,
                            {
                                "error": "MailboxHandler not available for sending task message"  # noqa: E501
                            },
                        )

                except Exception as e:
                    errors += 1
                    log_event(
                        "FEEDBACK_PROC_ERROR",
                        _SOURCE,
                        {
                            "error": "Failed to create or send task message",
                            "details": str(e),
                            "original_item": item,
                        },
                    )

    log_event(
        "FEEDBACK_PROC_FINISH",
        _SOURCE,
        {
            "items_processed": len(feedback_items),
            "tasks_created": tasks_created,
            "errors": errors,
        },
    )


# --- Example Usage ---
if __name__ == "__main__":
    # EDIT START: Need datetime import here if fallback wasn't triggered earlier
    # This ensures the dummy data generation works even if core utils were imported successfully.  # noqa: E501
    # from datetime import datetime, timezone

    print("Testing Feedback Processor...")

    # Ensure dummy inbox exists for testing send
    if not os.path.exists(AGENT_INBOX):  # noqa: F821
        try:
            os.makedirs(AGENT_INBOX)  # noqa: F821
        except:  # noqa: E722
            print(f"Warning: Could not create dummy inbox {AGENT_INBOX}")  # noqa: F821

    dummy_feedback = [
        {
            "platform": "twitter",
            "author": "user123",
            "url": "http://twitter.com/user123/status/1",
            # EDIT START: Use core/fallback utility
            "timestamp": get_utc_iso_timestamp(),
            # EDIT END
            "text": "This is great! Maybe you could add a dark mode feature? I suggest it would be really popular.",  # noqa: E501
        },
        {
            "platform": "reddit",
            "author": "redditor456",
            "url": "http://reddit.com/r/some/comments/1",
            # EDIT START: Use core/fallback utility
            "timestamp": get_utc_iso_timestamp(),
            # EDIT END
            "text": "Found a problem. When I click the button, I get an error 500. This bug is quite annoying.",  # noqa: E501
        },
        {
            "platform": "twitter",
            "author": "anotherUser",
            "url": "http://twitter.com/anotherUser/status/2",
            # EDIT START: Use core/fallback utility
            "timestamp": get_utc_iso_timestamp(),
            # EDIT END
            "text": "Just posting my thoughts, no suggestions here.",
        },
        {
            "platform": "forum",
            "author": "helpfulPerson",
            "url": None,
            # EDIT START: Use core/fallback utility
            "timestamp": get_utc_iso_timestamp(),
            # EDIT END
            "text": "I have an idea for improvement. What if the dashboard automatically refreshed? Also, the login seems broken sometimes.",  # noqa: E501
        },
        {"platform": "discord", "text": None},  # Invalid item
    ]

    print(f"\nProcessing {len(dummy_feedback)} feedback items...")
    process_feedback(dummy_feedback)

    print("\nFeedback processing test finished.")
    print(
        f"Check the directory '{AGENT_INBOX}' for any generated task files (if not using dummy mailbox)."  # noqa: E501, F821
    )

    # Simple cleanup (optional)
    # Be careful if running tests multiple times rapidly
    # try:
    #     for f in os.listdir(AGENT_INBOX):
    #         if f.startswith("task_") and f.endswith(".json"):
    #             os.remove(os.path.join(AGENT_INBOX, f))
    #     print("Cleaned up dummy task files.")
    # except Exception as clean_e:
    #     print(f"Cleanup warning: {clean_e}")


class FeedbackProcessor:
    # Removed inbox, outbox, recipient_agent_id from __init__ as they were unused
    def __init__(self, mailbox_path: str = "feedback_mailbox.json"):
        self.mailbox_path = Path(mailbox_path)
        self.mailbox = self._load_mailbox()
