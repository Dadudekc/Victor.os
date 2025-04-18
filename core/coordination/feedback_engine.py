from typing import Dict, Any
from datetime import datetime
import logging

# Setup logger for this module
logger = logging.getLogger(__name__)

class FeedbackEngine:
    """
    Processes and routes feedback from task executions.
    Integrates with memory systems and prompt refinement.
    (Currently implemented as an in-memory store)
    """
    
    def __init__(self, max_retries: int = 3):
        """
        Initializes the FeedbackEngine.

        Args:
            max_retries (int): Default maximum number of retries for a task.
        """
        self.feedback_history: Dict[str, list] = {} # task_id -> list of feedback entries
        self.retry_counts: Dict[str, int] = {}     # task_id -> count
        self.max_retries = max_retries
        logger.info(f"FeedbackEngine initialized with max_retries={max_retries}")
    
    def process_feedback(self, task_id: str, agent_id: str, feedback_data: Dict[str, Any]) -> bool:
        """
        Process feedback from task execution and store it.
        Updates retry count if feedback indicates failure.
        
        Args:
            task_id (str): Unique identifier for the task.
            agent_id (str): ID of the agent providing feedback.
            feedback_data (Dict[str, Any]): Execution feedback and metrics. 
                                           Should contain a 'success' boolean key.
            
        Returns:
            bool: True if feedback was processed successfully, False otherwise.
        """
        try:
            timestamp = datetime.now(datetime.timezone.utc).isoformat()
            log_entry = {
                "timestamp": timestamp,
                "agent_id": agent_id,
                "feedback": feedback_data
            }
            
            if task_id not in self.feedback_history:
                self.feedback_history[task_id] = []
            
            self.feedback_history[task_id].append(log_entry)
            logger.debug(f"Processed feedback for task '{task_id}' from agent '{agent_id}'.")
            
            # Track retry counts based on success flag
            if not feedback_data.get("success", True): # Default to success if key missing?
                current_retries = self.retry_counts.get(task_id, 0) + 1
                self.retry_counts[task_id] = current_retries
                logger.warning(f"Failure feedback received for task '{task_id}'. Retry count now {current_retries}.")
            else:
                 # Optionally reset retry count on success?
                 # if task_id in self.retry_counts:
                 #     del self.retry_counts[task_id]
                 pass
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing feedback for task {task_id}: {e}", exc_info=True)
            return False
    
    def get_retry_count(self, task_id: str) -> int:
        """Get the current number of recorded failures (retries) for a task."""
        return self.retry_counts.get(task_id, 0)
    
    def should_retry(self, task_id: str) -> bool:
        """Determine if a task should be retried based on failure count vs max_retries."""
        return self.get_retry_count(task_id) < self.max_retries
    
    def get_task_history(self, task_id: str) -> list:
        """Get the feedback history recorded for a specific task."""
        return self.feedback_history.get(task_id, [])

    def clear_task_state(self, task_id: str):
         """Removes history and retry counts for a specific task."""
         if task_id in self.feedback_history:
             del self.feedback_history[task_id]
             logger.info(f"Cleared feedback history for task '{task_id}'.")
         if task_id in self.retry_counts:
             del self.retry_counts[task_id]
             logger.info(f"Cleared retry count for task '{task_id}'.")

# Example Usage (can be run directly: python -m core.coordination.feedback_engine)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Running Feedback Engine example...")

    engine = FeedbackEngine(max_retries=2)
    task1 = "TASK-101"
    agent_a = "AgentA"
    agent_b = "AgentB"

    print(f"\nInitial state for {task1}: Should retry? {engine.should_retry(task1)}, Retries: {engine.get_retry_count(task1)}")

    print("\nProcessing first failure...")
    engine.process_feedback(task1, agent_a, {"success": False, "error": "Timeout"})
    print(f"State for {task1}: Should retry? {engine.should_retry(task1)}, Retries: {engine.get_retry_count(task1)}")

    print("\nProcessing second failure...")
    engine.process_feedback(task1, agent_a, {"success": False, "error": "Invalid Format"})
    print(f"State for {task1}: Should retry? {engine.should_retry(task1)}, Retries: {engine.get_retry_count(task1)}")

    print("\nProcessing success (should not increment retry count)...")
    engine.process_feedback(task1, agent_b, {"success": True, "result": "Data processed"})
    print(f"State for {task1}: Should retry? {engine.should_retry(task1)}, Retries: {engine.get_retry_count(task1)}") # Retries remain 2

    print("\nProcessing third failure (max retries reached)...")
    engine.process_feedback(task1, agent_a, {"success": False, "error": "Crashed"})
    print(f"State for {task1}: Should retry? {engine.should_retry(task1)}, Retries: {engine.get_retry_count(task1)}") # Should be False, Retries 3

    print("\nGetting task history...")
    history = engine.get_task_history(task1)
    import json
    print(json.dumps(history, indent=2))

    print("\nClearing task state...")
    engine.clear_task_state(task1)
    print(f"State for {task1}: Should retry? {engine.should_retry(task1)}, Retries: {engine.get_retry_count(task1)}")
    print(f"History for {task1}: {engine.get_task_history(task1)}")

    logger.info("Feedback Engine example finished.") 