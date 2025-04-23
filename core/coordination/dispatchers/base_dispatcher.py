import queue

class BaseDispatcher:
    """Base dispatcher that manages a task queue and processes tasks."""

    def __init__(self):
        self.is_running = False
        self.current_task = None
        self.task_queue = queue.Queue()

    def add_task(self, task):
        """Add a task to the queue."""
        self.task_queue.put(task)

    def run_dispatcher_loop(self):
        """Start processing tasks in the queue until empty or stopped."""
        self.is_running = True
        try:
            while not self.task_queue.empty() and self.is_running:
                task = self.task_queue.get()
                self.current_task = task
                self.execute_task(task)
                self.current_task = None
        except Exception:
            pass

    def stop(self):
        """Stop processing tasks."""
        self.is_running = False

    def get_status(self):
        """Return current status including running state, queue size, and current task."""
        return {
            "is_running": self.is_running,
            "queue_size": self.task_queue.qsize(),
            "current_task": self.current_task
        } 