import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

# TODO: This class uses threading.Lock for thread safety.
# If used heavily within an async application, consider converting
# to use asyncio.Lock and making methods async for better event loop integration.

# Setup logging
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# )
logger = logging.getLogger(__name__)

# Define constants relative to project root (assumed structure: root/src/dreamos/...)
# FIXME: Project root calculation is fragile. Path should ideally come from AppConfig or be absolute.
DEFAULT_MEMORY_FILE_REL = Path("runtime/memory/task_memory.json")


class TaskMemoryLayer:
    """
    Manages persistent storage and recall of task outcomes using a JSON file.
    Ensures basic safety for concurrent async updates and auto-saves on modification.
    """

    def __init__(self, memory_file_rel: Optional[Path] = None):
        """
        Initializes the TaskMemoryLayer.
        Note: _load_memory is now async and not called from __init__.
        Call an explicit async_init() or rely on lazy loading by accessor methods.

        Args:
            memory_file_rel: Optional relative path to the memory file from project root.
                               Defaults to DEFAULT_MEMORY_FILE_REL.
        """  # noqa: E501
        # FIXME: Project root calculation here is fragile and assumes a fixed depth.
        # Consider passing an absolute path or an AppConfig instance.
        self.project_root = Path(__file__).resolve().parents[4]
        self.memory_file = self.project_root / (
            memory_file_rel or DEFAULT_MEMORY_FILE_REL
        )
        self._memory_data: Optional[Dict[str, Dict[str, Any]]] = None # Initialize as None, load lazily
        self._lock = asyncio.Lock() # Use asyncio.Lock
        # self._load_memory() # REMOVED: _load_memory is now async
        logger.info(f"TaskMemoryLayer initialized. Using file: {self.memory_file}")

    async def _ensure_loaded(self):
        """Ensures memory is loaded if it hasn't been already."""
        if self._memory_data is None:
            await self._load_memory()

    async def _load_memory(self):
        """Loads memory data from the JSON file. Handles file not found and decode errors. Async."""  # noqa: E501
        async with self._lock:
            if self._memory_data is not None: # Already loaded by another coroutine
                return
            try:
                if await asyncio.to_thread(self.memory_file.exists):
                    def _sync_load():
                        with open(self.memory_file, "r", encoding="utf-8") as f:
                            return json.load(f)
                    self._memory_data = await asyncio.to_thread(_sync_load)
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
                self._memory_data = {}

    async def _save_memory(self):
        """Saves the current memory data to the JSON file. Assumes lock is already held. Async."""  # noqa: E501
        if self._memory_data is None: # Should not happen if ensure_loaded was called by public methods
            logger.warning("_save_memory called but _memory_data is None. Skipping save.")
            return
        
        memory_data_copy = dict(self._memory_data) # Work with a copy for thread safety

        def _sync_save():
            # Ensure the directory exists
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(memory_data_copy, f, indent=4)

        try:
            await asyncio.to_thread(_sync_save)
            logger.debug(f"Successfully saved memory to {self.memory_file}")
        except IOError as e:
            logger.error(
                f"IO error saving memory file {self.memory_file}: {e}", exc_info=True
            )
        except Exception as e:
            logger.error(
                f"Unexpected error saving memory file {self.memory_file}: {e}",
                exc_info=True,
            )

    async def record_task_outcome(
        self, task_id: str, outcome: str, notes: Optional[str] = None
    ):
        """
        Records the outcome of a task and persists it immediately. Async.
        """
        if not task_id:
            logger.warning(
                "Attempted to record outcome for task with empty ID. Skipping."
            )
            return

        await self._ensure_loaded()
        async with self._lock:
            if self._memory_data is None: # Should be loaded by _ensure_loaded
                self._memory_data = {} # Initialize if somehow still None (defensive)
            
            timestamp = time.time() # time.time() is fine for a simple timestamp
            task_record = {"outcome": outcome, "notes": notes, "timestamp": timestamp}
            self._memory_data[task_id] = task_record
            logger.info(f"Recorded outcome '{outcome}' for task_id: {task_id}")
            await self._save_memory() # _save_memory is now async and called within lock

    async def recall_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Recalls the recorded outcome and details for a specific task. Async.
        """
        await self._ensure_loaded()
        # Reading can be done outside the main modification lock if just accessing dict,
        # but to ensure consistency with _ensure_loaded, we acquire it.
        # If _memory_data was guaranteed to be a thread/coroutine-safe dict, this might differ.
        async with self._lock:
            if self._memory_data is None: # Should be loaded by _ensure_loaded
                 return None # Should not happen
            
            task_data = self._memory_data.get(task_id)
            if task_data:
                logger.debug(f"Recalled data for task_id: {task_id}")
                return (
                    task_data.copy()
                ) 
            else:
                logger.debug(f"No record found for task_id: {task_id}")
                return None


# Simple smoke test - This needs to be adapted to run async methods
# if __name__ == "__main__":
#     logger.info("--- Running TaskMemoryLayer Smoke Test ---")
# ... (rest of smoke test would need asyncio.run and async def main_test())
