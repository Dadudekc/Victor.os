import logging
import time

class PromptExecutionMonitor:
    def __init__(self, memory, dispatcher=None):
        """
        memory: your UnifiedMemoryManager instance, to record metrics if desired.
        dispatcher: optional object (e.g. the Saga worker) to notify/call back.
        """
        self.memory = memory
        self.dispatcher = dispatcher
        self._starts: dict[str, float] = {}
        self.logger = logging.getLogger(__name__)

    def start_monitoring(self, prompt_id: str):
        """Call immediately before issuing the prompt."""
        self._starts[prompt_id] = time.time()
        self.logger.info(f"Prompt {prompt_id} – started")

    def report_success(self, prompt_id: str, response: str):
        """Call when you get a good LLM response."""
        elapsed = time.time() - self._starts.get(prompt_id, time.time())
        self.logger.info(f"Prompt {prompt_id} – succeeded in {elapsed:.2f}s")
        # Optional: write into memory
        if self.memory:
            try:
                self.memory.set(
                    f"monitor/{prompt_id}",
                    {"status": "success", "duration": elapsed, "response": response}
                )
            except Exception:
                self.logger.error(f"Failed to record success for {prompt_id}", exc_info=True)

    def report_failure(self, prompt_id: str, reason: str):
        """Call when your LLM call threw or returned an error."""
        elapsed = time.time() - self._starts.get(prompt_id, time.time())
        self.logger.error(f"Prompt {prompt_id} – FAILED in {elapsed:.2f}s: {reason}")
        if self.memory:
            try:
                self.memory.set(
                    f"monitor/{prompt_id}",
                    {"status": "failure", "duration": elapsed, "reason": reason}
                )
            except Exception:
                self.logger.error(f"Failed to record failure for {prompt_id}", exc_info=True) 