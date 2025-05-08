# src/dreamos/tools/cursor_bridge/mock_cursor_bridge.py
import logging
import time
from typing import Optional, Any # Added Any

# Basic logger setup (replace with proper agent logging)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MockCursorBridge")

# --- Mock Components ---

class MockConfigInterface:
    """Mocks configuration retrieval."""
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        # Return dummy values
        if key == "cursor_bridge.injector.delay": return 0.1
        if key == "cursor_bridge.reader.timeout": return 5.0
        logger.info(f"[MockConfig] Getting config for: {key}")
        return default

class MockPromptInjector:
    """Mocks injecting prompts into Cursor UI."""
    def __init__(self, config: MockConfigInterface):
        self.config = config
        self.delay = self.config.get("cursor_bridge.injector.delay", 0.1)
        logger.info(f"[MockInjector] Initialized with delay: {self.delay}")

    def inject_prompt(self, prompt: str) -> bool:
        """Simulates injecting a prompt."""
        logger.info(f"[MockInjector] Attempting to inject prompt (length {len(prompt)})...")
        if not prompt:
            logger.error("[MockInjector] Cannot inject empty prompt.")
            return False
        try:
            # Simulate UI interaction delay
            time.sleep(self.delay)
            logger.info(f"[MockInjector] >>> '{prompt[:50]}...'") # Log truncated prompt
            logger.info("[MockInjector] Prompt injection simulation successful.")
            return True
        except Exception as e:
            logger.error(f"[MockInjector] Simulated injection failed: {e}", exc_info=True)
            return False

class MockResponseReader:
    """Mocks reading responses from Cursor UI (OCR/Clipboard)."""
    def __init__(self, config: MockConfigInterface):
        self.config = config
        self.timeout = self.config.get("cursor_bridge.reader.timeout", 5.0)
        logger.info(f"[MockReader] Initialized with timeout: {self.timeout}")

    def read_response(self) -> Optional[str]:
        """Simulates reading a response."""
        logger.info("[MockReader] Attempting to read response...")
        try:
            # Simulate waiting for response / OCR delay
            time.sleep(0.5) # Simulate base read time
            # Simulate potential variability or timeout wait
            # In a real scenario, this would involve polling UI or clipboard
            wait_time = min(self.timeout - 0.5, 1.0) # Simulate waiting up to 1s more
            time.sleep(wait_time)

            # Return a dummy response
            dummy_response = f"This is a simulated response received at {time.time()}."
            logger.info(f"[MockReader] <<< '{dummy_response[:50]}...'")
            logger.info("[MockReader] Response reading simulation successful.")
            return dummy_response
        except Exception as e:
            logger.error(f"[MockReader] Simulated reading failed: {e}", exc_info=True)
            return None

class MockLoopController:
    """Mocks the main bridge control loop."""
    def __init__(self, injector: MockPromptInjector, reader: MockResponseReader, config: MockConfigInterface):
        self.injector = injector
        self.reader = reader
        self.config = config # Potentially for loop-specific configs like max_retries
        self.max_retries = 3 # Example config
        logger.info("[MockController] Initialized.")

    def run_cycle(self, prompt: str) -> Optional[str]:
        """Simulates a single prompt->inject->read->response cycle."""
        logger.info(f"[MockController] Starting cycle for prompt: '{prompt[:50]}...'")
        inject_success = False
        for attempt in range(self.max_retries):
            logger.info(f"[MockController] Injection attempt {attempt + 1}/{self.max_retries}")
            inject_success = self.injector.inject_prompt(prompt)
            if inject_success:
                logger.info("[MockController] Injection succeeded.")
                break
            else:
                logger.warning("[MockController] Injection failed. Retrying after delay...")
                time.sleep(0.5) # Simulate retry delay
        
        if not inject_success:
            logger.error("[MockController] Injection failed after max retries. Aborting cycle.")
            return None

        # Simulate delay between injection and reading eligibility
        time.sleep(0.2)

        response = None
        for attempt in range(self.max_retries):
             logger.info(f"[MockController] Read attempt {attempt + 1}/{self.max_retries}")
             response = self.reader.read_response()
             if response is not None:
                 logger.info("[MockController] Read succeeded.")
                 break
             else:
                 logger.warning("[MockController] Read failed. Retrying after delay...")
                 time.sleep(0.5) # Simulate retry delay

        if response is None:
            logger.error("[MockController] Read failed after max retries.")
            return None

        logger.info(f"[MockController] Cycle completed successfully.")
        return response

# --- Factory/Setup ---
def create_mock_bridge():
    """Creates instances of the mock components."""
    config = MockConfigInterface()
    injector = MockPromptInjector(config)
    reader = MockResponseReader(config)
    controller = MockLoopController(injector, reader, config)
    return controller

# Example Usage (can be run directly for basic testing)
# if __name__ == "__main__":
#     print("--- Mock Cursor Bridge Test ---")
#     bridge_controller = create_mock_bridge()
#     test_prompt = "Explain the concept of asynchronous programming."
#     response = bridge_controller.run_cycle(test_prompt)
#     if response:
#         print("\n--- Cycle Result ---")
#         print(f"Prompt: {test_prompt}")
#         print(f"Response: {response}")
#     else:
#         print("\n--- Cycle Result ---")
#         print("Cycle failed to retrieve a response.")
#     print("--- End Test ---") 