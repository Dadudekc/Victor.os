from dataclasses import dataclass
from pathlib import Path
from ..core.config import INBOX_SUBDIR, MESSAGE_FORMAT

@dataclass
class TaskDispatcherConfig:
    """
    Configuration settings for TaskDispatcher.
    """
    task_list_path: Path = Path("task_list.json")
    check_interval: int = 10
    mailbox_root_dir: str = "mailboxes"
    inbox_subdir: str = INBOX_SUBDIR
    message_format: str = MESSAGE_FORMAT 