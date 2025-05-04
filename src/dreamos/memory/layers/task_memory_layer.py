import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

# TODO: This class uses threading.Lock for thread safety.
# If used heavily within an async application, consider converting
# to use asyncio.Lock and making methods async for better event loop integration.

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define constants relative to project root (assumed structure: root/src/dreamos/...)
DEFAULT_MEMORY_FILE_REL = Path("runtime/memory/task_memory.json")


class TaskMemoryLayer:
    """
    Manages persistent storage and recall of task outcomes using a JSON file.
    Ensures basic thread safety for updates and auto-saves on modification.
    """

    def __init__(self, memory_file_rel: Optional[Path] = None):
        """
        Initializes the TaskMemoryLayer, loading existing memory or creating a new file.

        Args:
            memory_file_rel: Optional relative path to the memory file from project root.
                               Defaults to DEFAULT_MEMORY_FILE_REL.
        """  # noqa: E501
        # Determine project root dynamically
        # Assumes this file is at src/dreamos/memory/layers/task_memory_layer.py
        self.project_root = Path(__file__).resolve().parents[4]
        self.memory_file = self.project_root / (
            memory_file_rel or DEFAULT_MEMORY_FILE_REL
        )
        self._memory_data: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._load_memory()
        logger.info(f"TaskMemoryLayer initialized. Using file: {self.memory_file}")

    def _load_memory(self):
        """Loads memory data from the JSON file. Handles file not found and decode errors."""  # noqa: E501
        with self._lock:
            try:
                if self.memory_file.exists():
                    with open(self.memory_file, "r", encoding="utf-8") as f:
                        self._memory_data = json.load(f)
                    logger.debug(
                        f"Loaded {len(self._memory_data)} task records from {self.memory_file}"  # noqa: E501
                    )
                else:
                    logger.info(
                        f"Memory file not found at {self.memory_file}. Starting with empty memory."  # noqa: E501
                    )
                    self._memory_data = {}
            except json.JSONDecodeError:
                logger.error(
                    f"Failed to decode JSON from {self.memory_file}. Starting with empty memory.",  # noqa: E501
                    exc_info=True,
                )
                self._memory_data = {}
            except IOError as e:
                logger.error(
                    f"IO error loading memory file {self.memory_file}: {e}",
                    exc_info=True,
                )
                # Keep potentially partially loaded data or reset? Resetting is safer.
                self._memory_data = {}

    def _save_memory(self):
        """Saves the current memory data to the JSON file. Assumes lock is already held."""  # noqa: E501
        try:
            # Ensure the directory exists
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self._memory_data, f, indent=4)  # Use indent for readability
            logger.debug(f"Successfully saved memory to {self.memory_file}")
        except IOError as e:
            logger.error(
                f"IO error saving memory file {self.memory_file}: {e}", exc_info=True
            )
        except Exception as e:
            # Catch unexpected errors during save
            logger.error(
                f"Unexpected error saving memory file {self.memory_file}: {e}",
                exc_info=True,
            )

    def record_task_outcome(
        self, task_id: str, outcome: str, notes: Optional[str] = None
    ):
        """
        Records the outcome of a task and persists it immediately.

        Args:
            task_id: The unique identifier for the task.
            outcome: The result of the task (e.g., 'success', 'failure', 'cancelled').
            notes: Optional additional notes or details about the outcome.
        """
        if not task_id:
            logger.warning(
                "Attempted to record outcome for task with empty ID. Skipping."
            )
            return

        with self._lock:
            timestamp = time.time()
            task_record = {"outcome": outcome, "notes": notes, "timestamp": timestamp}
            self._memory_data[task_id] = task_record
            logger.info(f"Recorded outcome '{outcome}' for task_id: {task_id}")
            # Auto-save after modification
            self._save_memory()

    def recall_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Recalls the recorded outcome and details for a specific task.

        Args:
            task_id: The unique identifier for the task.

        Returns:
            A dictionary containing the task's recorded data (outcome, notes, timestamp),
            or None if the task_id is not found.
        """  # noqa: E501
        with self._lock:
            task_data = self._memory_data.get(task_id)
            if task_data:
                logger.debug(f"Recalled data for task_id: {task_id}")
                return (
                    task_data.copy()
                )  # Return a copy to prevent external modification
            else:
                logger.debug(f"No record found for task_id: {task_id}")
                return None


# Simple smoke test
if __name__ == "__main__":
    logger.info("--- Running TaskMemoryLayer Smoke Test ---")

    # Use a temporary file for the test
    test_file_path = Path("runtime/memory/task_memory_test.json")
    project_r = Path(__file__).resolve().parents[4]
    abs_test_file_path = project_r / test_file_path

    # Ensure clean start
    if abs_test_file_path.exists():
        abs_test_file_path.unlink()

    # 1. Initialize and record
    logger.info("1. Initializing layer 1 and recording task...")
    layer1 = TaskMemoryLayer(memory_file_rel=test_file_path)
    task_id_to_test = "smoke_task_001"
    outcome_to_test = "success"
    notes_to_test = "Task completed during smoke test."
    layer1.record_task_outcome(task_id_to_test, outcome_to_test, notes_to_test)
    logger.info(f"Recorded: {task_id_to_test} -> {outcome_to_test}")

    # 2. Initialize a second instance (simulates reload)
    logger.info("\n2. Initializing layer 2 (simulating reload)...")
    layer2 = TaskMemoryLayer(memory_file_rel=test_file_path)

    # 3. Recall the task
    logger.info(f"\n3. Recalling task {task_id_to_test} using layer 2...")
    recalled_data = layer2.recall_task(task_id_to_test)

    # 4. Verify
    logger.info("\n4. Verifying recalled data...")
    if recalled_data:
        print(f"  Recalled Data: {recalled_data}")
        assert (
            recalled_data.get("outcome") == outcome_to_test
        ), f"Outcome mismatch! Expected {outcome_to_test}, got {recalled_data.get('outcome')}"  # noqa: E501
        assert (
            recalled_data.get("notes") == notes_to_test
        ), f"Notes mismatch! Expected {notes_to_test}, got {recalled_data.get('notes')}"
        assert "timestamp" in recalled_data, "Timestamp missing!"
        logger.info("Verification PASSED!")
    else:
        logger.error("Verification FAILED! Task data not recalled.")

    # 5. Recall non-existent task
    logger.info("\n5. Recalling non-existent task...")
    non_existent_data = layer2.recall_task("non_existent_task_id")
    assert non_existent_data is None, "Recall of non-existent task should return None."
    logger.info("Recall of non-existent task PASSED.")

    # Cleanup
    logger.info("\n--- Smoke Test Complete. Cleaning up test file. ---")
    if abs_test_file_path.exists():
        abs_test_file_path.unlink()
