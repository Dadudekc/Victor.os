import json
import logging
import threading
import time
from pathlib import Path
from _agent_coordination.utils.mailbox_utils import process_directory_loop

class EchoAgent:
    AGENT_NAME = "EchoAgent"

    def __init__(self, base_dir: str = "mailboxes"):
        # Setup mailbox directories
        self.root_dir = Path(base_dir) / self.AGENT_NAME
        self.inbox = self.root_dir / "inbox"
        self.processed = self.root_dir / "processed"
        self.error = self.root_dir / "error"
        # Initialize logger
        self.logger = logging.getLogger(self.AGENT_NAME)
        # Event to signal stop
        self._stop_event = threading.Event()

    def _process_mailbox_message(self, file_path: Path) -> bool:
        try:
            # Read and log message content
            content = json.loads(file_path.read_text(encoding="utf-8"))
            self.logger.info(f"[{self.AGENT_NAME}] Received message: {content}")
            return True
        except Exception as e:
            self.logger.error(f"[{self.AGENT_NAME}] Failed processing {file_path.name}: {e}", exc_info=True)
            return False

    def start_listening(self):
        # Start monitoring inbox directory
        self._stop_event.clear()
        process_directory_loop(
            watch_dir=self.inbox,
            process_func=self._process_mailbox_message,
            success_dir=self.processed,
            error_dir=self.error,
            stop_event=self._stop_event
        )

    def stop(self):
        # Signal the monitoring loop to stop
        self._stop_event.set()

if __name__ == '__main__':
    import sys
    # Accept optional base directory argument for mailboxes
    base_dir = sys.argv[1] if len(sys.argv) > 1 else 'mailboxes'
    agent = EchoAgent(base_dir=base_dir)
    try:
        agent.start_listening()
    except KeyboardInterrupt:
        agent.stop() 