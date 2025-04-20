import schedule
import time
import threading
import logging

# Use the re-exported functions from the src package
from dreamscape_generator.src import generate_episode, build_context

class AssistantWorker(threading.Thread):
    """A background thread that periodically generates episodes."""
    def __init__(self, interval_minutes=30, model="gpt-4o"):
        super().__init__(daemon=True) # Set as daemon so it exits when main thread exits
        self.interval_minutes = interval_minutes
        self.model = model
        self._stop_event = threading.Event() # Use an event for graceful stopping
        
        # Schedule the job
        schedule.every(self.interval_minutes).minutes.do(self.job)
        logging.info(f"AssistantWorker initialized. Job scheduled every {self.interval_minutes} minutes.")

    def job(self):
        """The actual task to be performed periodically."""
        if self._stop_event.is_set():
            logging.info("AssistantWorker stop event set, cancelling job run.")
            return schedule.CancelJob # Prevent rescheduling if stopped
            
        logging.info("Assistant auto-generation tick starting...")
        try:
            # Build context and generate episode using imported functions
            ctx = build_context()
            prompt = ctx["rendered_prompt"]
            logging.info(f"Assistant generating episode with model {self.model}...")
            # Run headless by default for background task
            generate_episode(prompt, self.model, headless=True)
            logging.info("Assistant auto-generation tick completed successfully.")
        except Exception as e:
            logging.error(f"Error during assistant auto-generation job: {e}", exc_info=True)

    def run(self):
        """The main loop for the thread, checking the schedule."""
        logging.info("AssistantWorker thread started.")
        while not self._stop_event.is_set():
            schedule.run_pending()
            # Sleep for a short interval before checking schedule again
            # Check stop event more frequently than the job interval
            time.sleep(min(self.interval_minutes * 60, 60)) # Sleep for up to 60s
        logging.info("AssistantWorker thread stopped.")

    def stop(self):
        """Signals the thread to stop gracefully."""
        logging.info("Stop signal received by AssistantWorker.")
        self._stop_event.set()
        # Optionally clear the schedule if desired upon stop
        # schedule.clear() 