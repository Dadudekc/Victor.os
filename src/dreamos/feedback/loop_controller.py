import time
import logging
import threading
from datetime import datetime
from typing import Callable, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LoopController:
    def __init__(self, interval: int = 180, callback: Optional[Callable] = None):
        self.interval = interval
        self.callback = callback
        self.running = False
        self.thread = None
        self.last_run = None

    def start(self):
        """Start the feedback loop."""
        self.running = True
        self.thread = threading.Thread(target=self._loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Feedback loop started with {self.interval}s interval.")

    def stop(self):
        """Stop the feedback loop."""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Feedback loop stopped.")

    def _loop(self):
        """Main loop that runs every interval seconds."""
        while self.running:
            try:
                self.last_run = datetime.now()
                if self.callback:
                    self.callback()
                logger.info(f"Feedback loop cycle completed at {self.last_run.isoformat()}")
            except Exception as e:
                logger.error(f"Error in feedback loop: {e}")
            time.sleep(self.interval)

    def get_status(self) -> dict:
        """Get the current status of the feedback loop."""
        return {
            'running': self.running,
            'interval': self.interval,
            'last_run': self.last_run.isoformat() if self.last_run else None
        }

if __name__ == "__main__":
    # Example usage
    def example_callback():
        print("Feedback loop callback executed")

    controller = LoopController(interval=180, callback=example_callback)
    controller.start()
    time.sleep(360)  # Run for 2 cycles
    controller.stop() 