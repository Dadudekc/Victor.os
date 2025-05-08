# Concurrency logic (workers, manager)
import asyncio # Changed to asyncio for all concurrency
import logging
# import queue # No longer using threading.Queue
# import threading # No longer using threading.Thread
from pathlib import Path
from typing import Any, Callable, List, Optional, Coroutine

logger = logging.getLogger(__name__)

# BotWorker is no longer a Thread, it's managed by asyncio tasks in MultibotManager
# Its run logic will be part of an async method in MultibotManager.

class MultibotManager:
    """Manages a pool of asyncio worker tasks for file processing."""

    # Type hint for scanner needs to be careful to avoid circular import
    # Using 'Any' or forward declaration if necessary (e.g., 'ProjectScanner')
    def __init__(
        self,
        scanner: Any, # Should be ProjectScanner instance, which has async _process_file
        num_workers: int = 4,
        status_callback: Optional[Callable[[Path, Optional[Any]], Coroutine[Any, Any, None]]] = None, # Callback can be async
    ):
        self.task_queue = asyncio.Queue() # Use asyncio.Queue
        self.results_list: List[Any] = []  # Store results here (ensure thread/task safety if accessed outside manager)
        self.scanner = scanner
        self.status_callback = status_callback
        self.num_workers = num_workers
        self.workers: List[asyncio.Task] = []
        self._stop_event = asyncio.Event() # For graceful shutdown if needed, though sentinel is primary

    async def _worker(self, worker_id: int):
        """Async worker task that processes files from the queue."""
        logger.info(f"Async worker {worker_id} started.")
        while True:
            file_path: Optional[Path] = None # Ensure defined for finally block
            try:
                file_path = await self.task_queue.get()
                if file_path is None:  # Sentinel value to stop
                    logger.info(f"Async worker {worker_id} received sentinel, stopping.")
                    break

                # Call the _process_file method on the scanner instance
                # ProjectScanner._process_file is now async def
                # result = await self.scanner._process_file(file_path)
                # Check if ProjectScanner has process_file_async as per previous refactor idea
                if hasattr(self.scanner, 'process_file_async'):
                    result = await self.scanner.process_file_async(file_path) 
                elif hasattr(self.scanner, '_process_file') and asyncio.iscoroutinefunction(self.scanner._process_file):
                    result = await self.scanner._process_file(file_path)
                else:
                    logger.error(f"Worker {worker_id}: Scanner has no suitable async process_file method for {file_path}")
                    result = None # Or raise an error

                if result is not None:
                    # If results_list is accessed by other coroutines, it needs a lock
                    # For now, assume it's managed safely or primarily appended to.
                    self.results_list.append(result)

                if self.status_callback:
                    try:
                        # If status_callback is async, await it
                        if asyncio.iscoroutinefunction(self.status_callback):
                            await self.status_callback(file_path, result)
                        else:
                            self.status_callback(file_path, result) # Call sync callback directly
                    except Exception as cb_err:
                        logger.error(
                            f"Error in status callback for {file_path} by worker {worker_id}: {cb_err}",
                            exc_info=True,
                        )

            except asyncio.CancelledError:
                logger.info(f"Async worker {worker_id} was cancelled.")
                break # Exit loop if task is cancelled
            except Exception as e:
                logger.error(f"Error in async worker {worker_id} processing task {file_path}: {e}", exc_info=True)
            finally:
                if file_path is not None:  # Don't call task_done on the sentinel
                    self.task_queue.task_done()
        logger.info(f"Async worker {worker_id} finished.")

    async def start_workers(self): # Changed to async
        """Starts the asyncio worker tasks."""
        if self.workers:  # Prevent starting multiple times
            logger.info("Workers already started.")
            return
        self._stop_event.clear() # Clear stop event if reusing manager
        self.workers = [
            asyncio.create_task(self._worker(i)) for i in range(self.num_workers)
        ]
        logger.info(f"Started {self.num_workers} async worker tasks.")

    async def add_task(self, file_path: Path): # Changed to async
        """Adds a file path task to the asyncio queue."""
        await self.task_queue.put(file_path)

    async def wait_for_completion(self): # Changed to async
        """Waits until all tasks in the asyncio queue have been processed."""
        await self.task_queue.join()
        logger.info("All tasks processed (async queue joined).")

    async def stop_workers(self): # Changed to async
        """Sends sentinel values to stop all worker tasks and waits for them."""
        if not self.workers:
            logger.info("No workers to stop.")
            return
            
        logger.info("Stopping async worker tasks...")
        for _ in self.workers:
            await self.task_queue.put(None) # Send sentinels
        
        # Wait for all worker tasks to complete
        try:
            await asyncio.gather(*self.workers, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error during worker shutdown (asyncio.gather): {e}")

        self.workers = []  # Clear worker list
        logger.info("Async worker tasks stopped.")

    def get_results(self) -> list:
        """Returns the list of results collected from workers.
        Note: If accessed concurrently while workers are active, ensure thread/task safety.
        Consider returning a copy or ensuring results_list is managed with a lock if needed.
        """
        return list(self.results_list) # Return a copy for safety
