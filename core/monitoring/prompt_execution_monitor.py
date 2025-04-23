"""PromptExecutionMonitor monitors prompts, archives failures, and requeues them."""
import threading
import time
import logging
from datetime import datetime
from typing import Dict, Any

from core.services.failed_prompt_archive import FailedPromptArchiveService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class PromptExecutionMonitor:
    def __init__(self,
                 memory,
                 dispatcher,
                 timeout_sec: int = 120,
                 archive_service: FailedPromptArchiveService = None):
        """Initialize the monitor with memory, dispatcher, and optional archive service."""
        self.memory = memory
        self.dispatcher = dispatcher
        self.timeout_sec = timeout_sec
        self.archive_service = archive_service or FailedPromptArchiveService()
        self.active_prompts: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def start_monitoring(self, prompt_id: str):
        """Begin monitoring a prompt execution."""
        logger.info(f"🔍 Monitoring prompt {prompt_id}")
        with self._lock:
            self.active_prompts[prompt_id] = datetime.utcnow()

    def report_success(self, prompt_id: str, response: str):
        """Handle successful completion of a prompt."""
        logger.info(f"✅ Prompt {prompt_id} completed successfully.")
        try:
            if hasattr(self.memory, 'save_fragment'):
                self.memory.save_fragment(prompt_id, {"response": response})
        except Exception as e:
            logger.error(f"Failed to store response for {prompt_id}: {e}", exc_info=True)
        with self._lock:
            self.active_prompts.pop(prompt_id, None)

    def report_failure(self, prompt_id: str, reason: str):
        """Archive failure and requeue the prompt."""
        logger.warning(f"⚠️ Prompt {prompt_id} failed: {reason}")
        prompt_data = {}
        if hasattr(self.memory, 'load_fragment'):
            prompt_data = self.memory.load_fragment(prompt_id) or {}
        retry_count = prompt_data.get("retry_count", 0)
        # Prevent duplicate archiving
        existing = self.archive_service.get_by_prompt_id(prompt_id)
        if not existing:
            self.archive_service.log_failure(prompt_id, prompt_data, reason, retry_count)
            logger.info(f"📦 Archived failed prompt: {prompt_id} due to {reason}")
        else:
            logger.debug(f"Prompt {prompt_id} already archived; skipping duplicate log")
        self.recover_and_requeue(prompt_id)

    def _monitor_loop(self):
        """Background thread: check for prompt timeouts."""
        while True:
            time.sleep(10)
            now = datetime.utcnow()
            expired = []
            with self._lock:
                for pid, start_time in self.active_prompts.items():
                    if (now - start_time).total_seconds() > self.timeout_sec:
                        expired.append(pid)
            for pid in expired:
                logger.error(f"🕒 Timeout: Prompt {pid} exceeded {self.timeout_sec}s")
                self.report_failure(pid, "timeout")

    def recover_and_requeue(self, prompt_id: str):
        """Fetch prompt data and requeue it for retry."""
        prompt_data = {}
        if hasattr(self.memory, 'load_fragment'):
            prompt_data = self.memory.load_fragment(prompt_id) or {}
        # Always attempt to requeue failed prompt, even if prompt_data is empty
        logger.info(f"🔁 Requeuing failed prompt {prompt_id}")
        try:
            if hasattr(self.dispatcher, 'queue_prompt'):
                self.dispatcher.queue_prompt(prompt_data, retry=True)
        except Exception as e:
            logger.error(f"Failed to requeue prompt {prompt_id}: {e}", exc_info=True) 