"""
Standardized messaging system for Dream.OS agents.

Implements the inbox/outbox directory structure and message handling as documented in
docs/agent_system/agent_directory_structure.md
"""

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dreamos.core.coordination.agent_bus import AgentBus, BaseEvent

from .config import AgentConfig

logger = logging.getLogger(__name__)


class MessageFormat:
    """Standard message format for agent communications."""

    def __init__(
        self,
        message_id: str,
        sender_agent_id: str,
        recipient_agent_id: str,
        subject: str,
        message_type: str,
        body: Union[str, Dict],
        priority: str = "MEDIUM",
        metadata: Optional[Dict] = None,
    ):
        self.message_id = message_id
        self.sender_agent_id = sender_agent_id
        self.recipient_agent_id = recipient_agent_id
        self.timestamp_utc = datetime.now(timezone.utc).isoformat()
        self.subject = subject
        self.message_type = message_type
        self.body = body
        self.priority = priority
        self.metadata = metadata or {}

    def to_dict(self) -> Dict:
        """Convert message to dictionary format."""
        return {
            "message_id": self.message_id,
            "sender_agent_id": self.sender_agent_id,
            "recipient_agent_id": self.recipient_agent_id,
            "timestamp_utc": self.timestamp_utc,
            "subject": self.subject,
            "type": self.message_type,
            "body": self.body,
            "priority": self.priority,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "MessageFormat":
        """Create message from dictionary."""
        return cls(
            message_id=data["message_id"],
            sender_agent_id=data["sender_agent_id"],
            recipient_agent_id=data["recipient_agent_id"],
            subject=data["subject"],
            message_type=data["type"],
            body=data["body"],
            priority=data.get("priority", "MEDIUM"),
            metadata=data.get("metadata", {}),
        )


async def publish_event(
    bus: AgentBus,
    logger: logging.Logger,
    agent_id: str,
    event_type: str,
    data: Dict[str, Any],
):
    """Fire structured event on AgentBus."""
    evt = BaseEvent(
        event_type=f"dreamos.{agent_id.lower()}.{event_type}",
        source_id=agent_id,
        data=data,
    )
    try:
        await bus.publish(evt.event_type, evt)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(f"Event publish fail {evt.event_type}: {exc}")


def archive_inbox(logger: logging.Logger, config: AgentConfig) -> bool:
    """
    Move processed inbox JSON to archive with epoch suffix.

    Args:
        logger: Logger instance
        config: Agent configuration

    Returns:
        bool: True if archive was successful
    """
    if not config.inbox_file.exists():
        return False
    try:
        dest = (
            config.archive_dir
            / f"inbox.{int(datetime.now(timezone.utc).timestamp())}.json"
        )
        config.inbox_file.rename(dest)
        logger.debug(f"Archived inbox to {dest}")
        return True
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Failed archiving inbox: {e}")
        return False


def load_inbox(logger: logging.Logger, config: AgentConfig) -> List[Dict[str, Any]]:
    """
    Return list with messages from inbox.json.

    Args:
        logger: Logger instance
        config: Agent configuration

    Returns:
        List of message dictionaries
    """
    if not config.inbox_file.exists():
        return []
    try:
        with config.inbox_file.open(encoding="utf-8") as fh:
            data = json.load(fh)
            # Handle both single object and list formats
            if isinstance(data, dict):
                logger.info(
                    f"Loaded inbox message {data.get('prompt_id') or data.get('id')}"
                )
                return [data]
            elif isinstance(data, list):
                if data:
                    logger.info(f"Loaded {len(data)} inbox messages")
                return data
            else:
                logger.warning(f"Unexpected inbox format: {type(data)}")
                return []
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Inbox read error: {e}")
        return []


def read_input_file(logger: logging.Logger, config: AgentConfig) -> Optional[str]:
    """
    Read content from task.txt if it exists.

    Args:
        logger: Logger instance
        config: Agent configuration

    Returns:
        str: Content of task.txt or None if file doesn't exist or is empty
    """
    if not config.input_file.exists():
        return None
    try:
        txt = config.input_file.read_text(encoding="utf-8").strip()
        return txt if txt else None
    except Exception as e:
        logger.error(f"Error reading input file: {e}")
        return None


def create_seed_inbox(
    logger: logging.Logger, config: "AgentConfig", custom_prompt: Optional[str] = None
) -> bool:
    """
    Create a seed inbox message if inbox is empty.

    Args:
        logger: Logger instance
        config: Agent configuration
        custom_prompt: Optional custom prompt text

    Returns:
        bool: True if seed message was created
    """
    # Ensure inbox directory exists
    config.inbox_dir.mkdir(parents=True, exist_ok=True)

    # Check if inbox is empty
    if list(config.inbox_dir.glob("*.json")):
        return False

    # Create seed message
    seed_message = MessageFormat(
        message_id=f"SEED-{config.agent_id}",
        sender_agent_id="System",
        recipient_agent_id=config.agent_id,
        subject=f"{config.agent_id} Activation",
        message_type="INSTRUCTION",
        body=custom_prompt
        or (
            f"# {config.agent_id} Activation\n\n"
            f"I am {config.agent_id}. Systems nominal; awaiting directives.\n\n"
            f"## Immediate Actions Required:\n\n"
            f"1. Read the INBOX_LOOP_PROTOCOL\n"
            f"2. Begin continuous operation\n\n"
            f"## Your Role: {config.charter}\n\n"
            f"Traits: {config.traits}"
        ),
    )

    # Write seed message to inbox
    try:
        message_path = (
            config.inbox_dir / f"seed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with message_path.open("w", encoding="utf-8") as f:
            json.dump(seed_message.to_dict(), f, indent=2)
        logger.info(f"Created seed message in inbox: {message_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create seed message: {e}")
        return False


def process_message(config: "AgentConfig", message_path: Path) -> bool:
    """
    Process a message by moving it to the processed directory.

    Args:
        config: Agent configuration
        message_path: Path to the message file

    Returns:
        bool: True if message was processed successfully
    """
    try:
        # Ensure processed directory exists
        config.processed_dir.mkdir(parents=True, exist_ok=True)

        # Move message to processed directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        processed_path = config.processed_dir / f"{timestamp}_{message_path.name}"
        message_path.rename(processed_path)
        return True
    except Exception as e:
        logger.error(f"Failed to process message {message_path}: {e}")
        return False


def send_message(
    sender_config: "AgentConfig",
    recipient_id: str,
    subject: str,
    message_type: str,
    body: Union[str, Dict],
    priority: str = "MEDIUM",
    metadata: Optional[Dict] = None,
) -> bool:
    """
    Send a message to another agent's inbox.

    Args:
        sender_config: Sender's agent configuration
        recipient_id: Recipient agent ID
        subject: Message subject
        message_type: Type of message
        body: Message content
        priority: Message priority
        metadata: Optional metadata

    Returns:
        bool: True if message was sent successfully
    """
    try:
        # Construct recipient's inbox path
        recipient_inbox = sender_config.base_runtime.parent / recipient_id / "inbox"
        recipient_inbox.mkdir(parents=True, exist_ok=True)

        # Create message
        message = MessageFormat(
            message_id=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{sender_config.agent_id}_{recipient_id}",
            sender_agent_id=sender_config.agent_id,
            recipient_agent_id=recipient_id,
            subject=subject,
            message_type=message_type,
            body=body,
            priority=priority,
            metadata=metadata,
        )

        # Write message to recipient's inbox
        message_path = recipient_inbox / f"{message.message_id}.json"
        with message_path.open("w", encoding="utf-8") as f:
            json.dump(message.to_dict(), f, indent=2)

        logger.info(f"Sent message {message.message_id} to {recipient_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send message to {recipient_id}: {e}")
        return False


def update_inbox_with_prompt(
    logger: logging.Logger, config: AgentConfig, custom_prompt: str
) -> bool:
    """
    Update existing inbox with a custom prompt.

    Args:
        logger: Logger instance
        config: Agent configuration
        custom_prompt: Custom prompt text

    Returns:
        bool: True if inbox was updated
    """
    success = False

    # Update legacy inbox.json if it exists
    if config.inbox_file.exists():
        try:
            with config.inbox_file.open("r", encoding="utf-8") as fh:
                inbox_data = json.load(fh)

            # Update the prompt (handle both single object and list formats)
            if isinstance(inbox_data, dict):
                inbox_data["prompt"] = custom_prompt
                inbox_data["timestamp"] = datetime.now(timezone.utc).isoformat()
            elif isinstance(inbox_data, list) and inbox_data:
                inbox_data[0]["prompt"] = custom_prompt
                inbox_data[0]["timestamp"] = datetime.now(timezone.utc).isoformat()

            with config.inbox_file.open("w", encoding="utf-8") as fh:
                json.dump(inbox_data, fh, indent=2)
            logger.info(
                f"Updated existing inbox with custom prompt @ {config.inbox_file}"
            )
            success = True
        except Exception as e:
            logger.error(f"Error updating inbox with custom prompt: {e}")

    # Create a new file in the inbox directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prompt_file = config.inbox_dir / f"custom_prompt_{timestamp}.md"

    try:
        prompt_file.write_text(custom_prompt)
        logger.info(f"Created custom prompt file in inbox: {prompt_file}")
        success = True
    except Exception as e:
        logger.error(f"Failed to create custom prompt file: {e}")

    return success


def list_inbox_files(logger: logging.Logger, config: AgentConfig) -> List[Path]:
    """
    List all markdown files in the inbox directory.

    Args:
        logger: Logger instance
        config: Agent configuration

    Returns:
        List of Path objects for inbox files
    """
    try:
        if not config.inbox_dir.exists():
            config.inbox_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created inbox directory: {config.inbox_dir}")
            return []

        files = list(config.inbox_dir.glob("*.md"))
        files.sort(key=lambda x: x.stat().st_mtime)  # Sort by creation time

        if files:
            logger.info(f"Found {len(files)} message files in inbox")

        return files
    except Exception as e:
        logger.error(f"Error listing inbox files: {e}")
        return []


def archive_inbox_file(
    logger: logging.Logger, config: AgentConfig, file_path: Path
) -> bool:
    """
    Archive a processed inbox file.

    Args:
        logger: Logger instance
        config: Agent configuration
        file_path: Path to the file to archive

    Returns:
        bool: True if archiving was successful
    """
    try:
        if not config.processed_dir.exists():
            config.processed_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created processed directory: {config.processed_dir}")

        dest_path = config.processed_dir / file_path.name
        shutil.move(str(file_path), str(dest_path))
        logger.info(f"Archived {file_path.name} to processed directory")
        return True
    except Exception as e:
        logger.error(f"Error archiving inbox file {file_path.name}: {e}")
        return False


def update_agent_state(
    logger: logging.Logger,
    config: AgentConfig,
    cycle_count: int,
    current_task: str = None,
) -> bool:
    """
    Update the agent's state file.

    Args:
        logger: Logger instance
        config: Agent configuration
        cycle_count: Current cycle count
        current_task: Current task description

    Returns:
        bool: True if state update was successful
    """
    try:
        if not config.state_dir.exists():
            config.state_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created state directory: {config.state_dir}")

        # Load existing state if it exists
        state = {}
        if config.state_file.exists():
            try:
                state = json.loads(config.state_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Error loading state file: {e}")

        # Update state
        state["cycle_count"] = cycle_count
        state["last_active"] = datetime.now(timezone.utc).isoformat()
        if current_task:
            state["current_task"] = current_task

        # Write state file
        with config.state_file.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        logger.debug(f"Updated state file: cycle={cycle_count}, task={current_task}")
        return True
    except Exception as e:
        logger.error(f"Error updating state file: {e}")
        return False
