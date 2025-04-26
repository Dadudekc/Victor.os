# _agent_coordination/dispatchers/mailbox_service.py

import logging
from pathlib import Path
from typing import Any, Dict

from ..core.config import INBOX_SUBDIR, MESSAGE_FORMAT
from ..utils.mailbox_utils import dispatch_message_to_agent

logger = logging.getLogger("MailboxService")

class MailboxService:
    """
    Service to dispatch messages to agent mailboxes, using mailbox utilities.
    """
    def __init__(self, mailbox_root: Path, inbox_subdir: str = INBOX_SUBDIR, message_format: str = MESSAGE_FORMAT):
        self.mailbox_root = mailbox_root
        self.inbox_subdir = inbox_subdir
        self.message_format = message_format
        # Ensure mailbox root exists
        self.mailbox_root.mkdir(parents=True, exist_ok=True)

    def dispatch_message(self, target_agent: str, message_payload: Dict[str, Any]) -> bool:
        """
        Dispatches a message payload to the specified agent mailbox.
        """
        try:
            return dispatch_message_to_agent(
                mailbox_root=self.mailbox_root,
                target_agent=target_agent,
                message_payload=message_payload,
                inbox_subdir=self.inbox_subdir,
                message_format=self.message_format
            )
        except Exception as e:
            logger.error(f"MailboxService: error dispatching to {target_agent}: {e}", exc_info=True)
            return False 