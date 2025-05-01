import json
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Import new standard mailbox utilities
from dreamos.agents.utils.agent_utils import (
    MailboxMessagePriority,
    MailboxMessageType,
    create_mailbox_message,
    read_mailbox_message,
    write_mailbox_message,
)

# Assuming safe rewrite function exists, adjust import if needed
# from dreamos.memory.compaction_utils import _rewrite_memory_safely # No longer needed for sending


logger = logging.getLogger(__name__)

# Define standard mailbox subdirectories
INBOX_DIR_NAME = "inbox"
ARCHIVE_DIR_NAME = "archive"
OUTBOX_DIR_NAME = "outbox"  # Optional: For tracking sent items
FAILED_DIR_NAME = "failed"  # Optional: For handling errors


class MailboxError(Exception):
    """Custom exception for mailbox operations."""

    pass


class MailboxHandler:
    """
    Handles file-based mailbox operations for an agent using standardized JSON format.
    Provides methods to send messages/tasks to other agents' inboxes
    and potentially manage the agent's own inbox/archive.
    """

    def __init__(self, agent_id: str, mailboxes_base_dir: Path):
        """
        Initializes the handler for a specific agent.

        Args:
            agent_id: The ID of the agent this handler belongs to or acts on behalf of.
            mailboxes_base_dir: The root directory containing all agent mailboxes
                                  (e.g., runtime/agent_comms/agent_mailboxes).
        """
        if not mailboxes_base_dir.is_dir():
            raise MailboxError(
                f"Mailboxes base directory does not exist: {mailboxes_base_dir}"
            )

        self.agent_id = agent_id
        self.mailboxes_base_dir = mailboxes_base_dir
        self.agent_mailbox_dir = self.mailboxes_base_dir / self.agent_id
        self.inbox_path = self.agent_mailbox_dir / INBOX_DIR_NAME
        self.archive_path = self.agent_mailbox_dir / ARCHIVE_DIR_NAME

        # Ensure required directories for this agent exist
        try:
            self.inbox_path.mkdir(parents=True, exist_ok=True)
            self.archive_path.mkdir(parents=True, exist_ok=True)
            # Optionally create outbox/failed dirs if needed
        except OSError as e:
            raise MailboxError(
                f"Failed to create mailbox directories for agent {self.agent_id} under {self.agent_mailbox_dir}: {e}"
            )

    def _get_target_inbox(self, target_agent_id: str) -> Path:
        """Gets the inbox path for a target agent."""
        target_inbox = self.mailboxes_base_dir / target_agent_id / INBOX_DIR_NAME
        # Check if target mailbox exists? write_mailbox_message handles dir creation.
        return target_inbox

    def send(
        self,
        target_agent_id: str,
        message_type: str,
        payload: dict,
        filename_prefix: str = "msg",
        priority: MailboxMessagePriority = "MEDIUM",
    ) -> str | None:
        """
        Sends a message to another agent's inbox using the standard JSON format.

        Args:
            target_agent_id: The ID of the recipient agent.
            message_type: A string identifying the type of message (maps to standard 'type').
            payload: A dictionary containing the message content (maps to standard 'body').
            filename_prefix: Optional prefix for the message file (default: 'msg').
            priority: Optional message priority (default: 'MEDIUM').

        Returns:
            The full path of the created message file if successful, None otherwise.
        """
        target_inbox = self._get_target_inbox(target_agent_id)

        try:
            # Create the message using the standard utility
            # Map input args to standard schema fields
            message_data = create_mailbox_message(
                sender_agent_id=self.agent_id,
                recipient_agent_id=target_agent_id,
                subject=f"{message_type.capitalize()} from {self.agent_id}",  # Generate a basic subject
                message_type=message_type,  # Assuming input 'message_type' fits standard types
                body=payload,
                priority=priority,
            )

            # Write the message using the standard utility
            filepath = write_mailbox_message(
                message_data=message_data,
                recipient_inbox_path=str(target_inbox),  # Utility expects string path
                filename_prefix=filename_prefix,
            )
            logger.info(
                f"Sent message {Path(filepath).name} to agent {target_agent_id}'s inbox ({filepath})."
            )
            return filepath

        except (ValueError, IOError) as e:
            logger.error(
                f"Failed to create or write mailbox message to {target_agent_id}: {e}",
                exc_info=True,
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error sending message to {target_agent_id} at {target_inbox}: {e}",
                exc_info=True,
            )
            return None

    def get_messages(self, max_count: int | None = None) -> list[tuple[Path, dict]]:
        """Reads and validates standard JSON messages from the agent's own inbox."""
        messages = []
        try:
            # Look for standard .json files
            files = sorted(self.inbox_path.glob("*.json"), key=os.path.getmtime)
            count = 0
            for filepath in files:
                if max_count is not None and count >= max_count:
                    break

                # Use the standard utility to read and validate
                message_data = read_mailbox_message(
                    str(filepath)
                )  # Utility expects string path

                if message_data:
                    messages.append((filepath, message_data))
                    count += 1
                else:
                    # read_mailbox_message already logs warnings/errors
                    logger.debug(
                        f"Skipping invalid or unreadable message file: {filepath.name}"
                    )
                    # TODO: Consider moving invalid files to a 'failed' directory?

        except OSError as e:
            logger.error(f"Failed to list inbox directory {self.inbox_path}: {e}")
        return messages

    def archive_message(self, message_filepath: Path) -> bool:
        """Moves a processed message file (expected to be .json) from the inbox to the archive."""
        # TODO: Consider making internal file operations (glob, move) async if required
        if not message_filepath.is_file() or message_filepath.parent != self.inbox_path:
            logger.error(
                f"Cannot archive file '{message_filepath.name}': Not found in inbox {self.inbox_path}."
            )
            return False

        # Ensure the archive directory exists (should be created in __init__, but double-check)
        try:
            self.archive_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(
                f"Failed to ensure archive directory exists at {self.archive_path}: {e}"
            )
            return False

        target_archive_path = self.archive_path / message_filepath.name
        try:
            shutil.move(str(message_filepath), str(target_archive_path))
            logger.info(f"Archived message: {message_filepath.name}")
            return True
        except Exception as e:
            logger.error(
                f"Failed to archive message {message_filepath.name} to {self.archive_path}: {e}"
            )
            return False

    # Potential future methods:
    # - read_message(message_id_or_path)
    # - delete_message(message_id_or_path)
    # - handle_failed_message(...) # E.g., moving files identified as invalid by get_messages
