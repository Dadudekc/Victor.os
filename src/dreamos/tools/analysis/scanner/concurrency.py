# Concurrency logic (workers, manager) 
import threading
import queue
import logging
from pathlib import Path
from typing import List, Optional, Callable, Any # Added Any for result type

logger = logging.getLogger(__name__)

class BotWorker(threading.Thread):
    """
    A background worker that pulls file tasks from a queue,
    processes them, and appends results to results_list.
    """
    # Type hint for scanner needs to be careful to avoid circular import
    # Using 'Any' or forward declaration if necessary
    def __init__(self, task_queue: queue.Queue, results_list: list, scanner: Any, status_callback: Optional[Callable[[Path, Optional[Any]], None]] = None):
        super().__init__()
        self.task_queue = task_queue
        self.results_list = results_list
        self.scanner = scanner # Instance of the main ProjectScanner
        self.status_callback = status_callback
        self.daemon = True
        self.start()

    def run(self):
        while True:
            try:
                file_path: Optional[Path] = self.task_queue.get()
                if file_path is None: # Sentinel value to stop
                    break
                
                # Call the _process_file method on the scanner instance
                # This method is defined in ProjectScanner (main.py)
                result = self.scanner._process_file(file_path)
                
                if result is not None:
                    self.results_list.append(result)
                    
                if self.status_callback:
                    try:
                        self.status_callback(file_path, result)
                    except Exception as cb_err:
                        logger.error(f"Error in status callback for {file_path}: {cb_err}", exc_info=True)
                        
            except Exception as e:
                # Log error but keep the worker alive
                logger.error(f"Error in BotWorker processing task: {e}", exc_info=True)
            finally:
                if file_path is not None: # Don't call task_done on the sentinel
                    self.task_queue.task_done()

class MultibotManager:
    """Manages a pool of BotWorker threads."""
    def __init__(self, scanner: Any, num_workers: int = 4, status_callback: Optional[Callable[[Path, Optional[Any]], None]] = None):
        self.task_queue = queue.Queue()
        self.results_list = [] # Store results here
        self.scanner = scanner
        self.status_callback = status_callback
        self.num_workers = num_workers
        self.workers: List[BotWorker] = []

    def start_workers(self):
        """Starts the worker threads."""
        if self.workers: # Prevent starting multiple times
             return
        self.workers = [
            BotWorker(self.task_queue, self.results_list, self.scanner, self.status_callback)
            for _ in range(self.num_workers)
        ]
        logger.info(f"Started {self.num_workers} worker threads.")

    def add_task(self, file_path: Path):
        """Adds a file path task to the queue."""
        self.task_queue.put(file_path)

    def wait_for_completion(self):
        """Blocks until all tasks in the queue have been processed."""
        self.task_queue.join()
        logger.info("All tasks processed.")

    def stop_workers(self):
        """Sends sentinel values to stop all worker threads."""
        logger.info("Stopping worker threads...")
        for _ in self.workers:
            self.task_queue.put(None)
        # Optionally wait for threads to finish
        for worker in self.workers:
            worker.join(timeout=5) # Add a timeout
        self.workers = [] # Clear worker list
        logger.info("Worker threads stopped.")

    def get_results(self) -> list:
         """Returns the list of results collected from workers."""
         return self.results_list 