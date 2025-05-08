"""
Defines the BaseDispatcher class for synchronous task processing.

FIXME: This dispatcher is synchronous and uses stdlib `queue.Queue`.
       If an asynchronous dispatcher is needed for integration with asyncio-based
       parts of the system, this will need to be refactored (e.g., use `asyncio.Queue`).
"""
import queue
import logging # Added for improved error handling
from abc import ABC, abstractmethod # Added for abstract method

logger = logging.getLogger(__name__) # Added logger

class BaseDispatcher(ABC): # Inherit from ABC
    """Base dispatcher that manages a task queue and processes tasks."""

    def __init__(self):
        self.is_running = False
        self.current_task = None
        self.task_queue = queue.Queue()

    def add_task(self, task):
        """Add a task to the queue."""
        self.task_queue.put(task)

    @abstractmethod
    def execute_task(self, task):
        """Executes a single task. Must be implemented by subclasses."""
        # raise NotImplementedError("Subclasses must implement execute_task")
        pass # Or raise NotImplementedError

    def run_dispatcher_loop(self):
        """Start processing tasks in the queue.
        
        Loops as long as is_running is True and tasks are available, 
        or waits for new tasks if queue is empty (blocking get).
        If intended as a continuously running service, ensure tasks are added
        by other threads/processes, or adapt loop for non-blocking checks if preferred.
        """
        self.is_running = True
        logger.info(f"{self.__class__.__name__} starting dispatcher loop.")
        while self.is_running:
            try:
                # Using a timeout allows the loop to check is_running periodically
                # even if the queue is empty, preventing a hard block if stop() is called.
                task = self.task_queue.get(timeout=1) 
            except queue.Empty:
                # Queue is empty, loop continues to check self.is_running
                continue 

            self.current_task = task
            logger.debug(f"Executing task: {task}")
            try:
                self.execute_task(task)
            except Exception as e:
                # Log the exception instead of silently passing
                logger.error(f"Error executing task {task}: {e}", exc_info=True)
            finally:
                self.current_task = None
                self.task_queue.task_done() # Signal that the task is done
        logger.info(f"{self.__class__.__name__} dispatcher loop stopped.")

    def stop(self):
        """Stop processing tasks after the current task completes."""
        logger.info(f"{self.__class__.__name__} stop requested.")
        self.is_running = False

    def get_status(self):
        """Return current status including running state, queue size, and current task."""  # noqa: E501
        return {
            "is_running": self.is_running,
            "queue_size": self.task_queue.qsize(),
            "current_task": self.current_task,
        }
