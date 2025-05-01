"""PromptExecutionMonitor monitors prompts, archives failures, and requeues them."""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Queue
from threading import Lock, Thread
from typing import Any, Dict, List, Optional

from dreamos.coordination.agent_bus import AgentBus, BaseEvent, EventType
from dreamos.core.coordination.event_payloads import (
    TaskCompletionPayload,
    TaskFailurePayload,
)
from dreamos.services.failed_prompt_archive import FailedPromptArchiveService

from ..core.coordination.base_agent import AgentState, TaskStatus

# TODO: Evaluate replacing threading with asyncio tasks for the monitor loop
# if the dispatcher and memory components are fully async-compatible.



logger = logging.getLogger(__name__)


class PromptExecutionMonitor:
    def __init__(
        self,
        memory,
        dispatcher,
        timeout_sec: int = 120,
        archive_service: Optional[FailedPromptArchiveService] = None,
    ):
        """Initialize the monitor with memory, dispatcher, and optional archive service."""
        self.memory = memory
        self.dispatcher = dispatcher
        self.timeout_sec = timeout_sec
        self.archive_service = archive_service or FailedPromptArchiveService()
        self.active_prompts: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="PromptMonitorThread"
        )
        self._monitor_thread.start()
        self.agent_bus = AgentBus()
        logger.info("PromptExecutionMonitor initialized and started.")

    def start_monitoring(self, prompt_id: str):
        """Begin monitoring a prompt execution."""
        if not prompt_id or not isinstance(prompt_id, str):
            logger.error(f"Invalid prompt_id provided for monitoring: {prompt_id}")
            return
        logger.info(f"🔍 Monitoring prompt {prompt_id}")
        with self._lock:
            self.active_prompts[prompt_id] = datetime.now(timezone.utc)

    def report_success(self, prompt_id: str, response: Optional[Dict[str, Any]] = None):
        """Handle successful completion of a prompt."""
        logger.info(f"✅ Prompt {prompt_id} completed successfully.")
        try:
            if hasattr(self.memory, "set"):
                data_to_store = response if response else {"status": "success"}
                self.memory.set(prompt_id, data_to_store, seg="interactions")
        except Exception as e:
            logger.error(
                f"Failed to store response for {prompt_id}: {e}", exc_info=True
            )
        with self._lock:
            self.active_prompts.pop(prompt_id, None)
        try:
            payload = TaskCompletionPayload(
                task_id=prompt_id,
                status=TaskStatus.COMPLETED,
                result=(
                    response
                    if response
                    else {"message": "Prompt completed successfully"}
                ),
            )
            evt = BaseEvent(
                event_type=EventType.TASK_COMPLETED,
                source_id="PromptExecutionMonitor",
                data=payload.__dict__,
            )
            asyncio.create_task(self.agent_bus.dispatch_event(evt))
            logger.debug(
                f"Dispatched {EventType.TASK_COMPLETED.name} event for prompt {prompt_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to dispatch {EventType.TASK_COMPLETED.name} event: {e}",
                exc_info=True,
            )

    def report_failure(
        self, prompt_id: str, reason: str, details: Optional[Dict[str, Any]] = None
    ):
        """Archive failure and requeue the prompt."""
        logger.warning(f"⚠️ Prompt {prompt_id} failed: {reason}")
        prompt_data = {}
        if hasattr(self.memory, "get"):
            prompt_data = self.memory.get(prompt_id, seg="interactions") or {}
        retry_count = prompt_data.get("retry_count", 0)
        existing = self.archive_service.get_by_prompt_id(prompt_id)
        if not existing:
            self.archive_service.log_failure(
                prompt_id, prompt_data, reason, retry_count
            )
            logger.info(f"📦 Archived failed prompt: {prompt_id} due to {reason}")
        else:
            logger.debug(f"Prompt {prompt_id} already archived; skipping duplicate log")
        with self._lock:
            self.active_prompts.pop(prompt_id, None)
        self.recover_and_requeue(prompt_id)
        try:
            payload = TaskFailurePayload(
                task_id=prompt_id,
                status=TaskStatus.FAILED,
                error=reason,
                details=details or {"failure_source": "PromptExecutionMonitor"},
                is_final=False,
            )
            evt = BaseEvent(
                event_type=EventType.TASK_FAILED,
                source_id="PromptExecutionMonitor",
                data=payload.__dict__,
            )
            asyncio.create_task(self.agent_bus.dispatch_event(evt))
            logger.debug(
                f"Dispatched {EventType.TASK_FAILED.name} event for prompt {prompt_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to dispatch {EventType.TASK_FAILED.name} event: {e}",
                exc_info=True,
            )
        try:
            out_dir = Path("runtime/logs")
            out_dir.mkdir(parents=True, exist_ok=True)
            log_path = out_dir / "prompt_failures.jsonl"
            entry = {
                "prompt_id": prompt_id,
                "reason": reason,
                "details": details,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            }
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write prompt failure log: {e}")

    def _monitor_loop(self):
        logger.info("Prompt monitor loop starting...")
        while True:
            try:
                time.sleep(10)
                now = datetime.now(timezone.utc)
                expired = []
                self._lock.acquire()
                try:
                    active_copy = list(self.active_prompts.items())
                finally:
                    self._lock.release()
                for pid, start_time in active_copy:
                    if (now - start_time).total_seconds() > self.timeout_sec:
                        logger.error(
                            f"🕒 Timeout: Prompt {pid} exceeded {self.timeout_sec}s"
                        )
                        self.report_failure(
                            pid,
                            "timeout",
                            {"timeout_duration_seconds": self.timeout_sec},
                        )
            except Exception as loop_e:
                logger.error(f"Error in monitor loop: {loop_e}", exc_info=True)
                time.sleep(30)

    def recover_and_requeue(self, prompt_id: str):
        """Fetch prompt data and requeue it for retry."""
        prompt_data = {}
        if hasattr(self.memory, "get"):
            try:
                prompt_data = self.memory.get(prompt_id, seg="interactions") or {}
            except Exception as mem_e:
                logger.error(
                    f"Failed to retrieve prompt data from memory for {prompt_id}: {mem_e}",
                    exc_info=True,
                )
                prompt_data = {"error": "Failed to retrieve original prompt data"}
        logger.info(f"🔁 Requeuing failed prompt {prompt_id}")
        try:
            if hasattr(self.dispatcher, "queue_prompt"):
                retry_count = prompt_data.get("retry_count", 0)
                prompt_data["retry_count"] = retry_count + 1
                self.dispatcher.queue_prompt(prompt_data, retry=True)
            else:
                logger.error(
                    f"Dispatcher has no 'queue_prompt' method. Cannot requeue {prompt_id}."
                )
        except Exception as e:
            logger.error(f"Failed to requeue prompt {prompt_id}: {e}", exc_info=True)
