"""
Message Queue Processor

Background processor for handling cell phone message queue.
"""

import logging
import time
import threading
from .message_queue import MessageQueueManager

logger = logging.getLogger('message_processor')

class MessageProcessor:
    def __init__(self, process_interval: float = 1.0):
        self.queue_manager = MessageQueueManager()
        self.process_interval = process_interval
        self.running = False
        self.thread = None
        
    def start(self):
        """Start the message processor."""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._process_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info("Message processor started")
        
    def stop(self):
        """Stop the message processor."""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Message processor stopped")
        
    def _process_loop(self):
        """Main processing loop."""
        while self.running:
            try:
                # Process any pending messages
                self.queue_manager.process_queue()
                
                # Get queue status
                status = self.queue_manager.get_queue_status()
                if status["queue_size"] > 0:
                    logger.info(f"Queue status: {status}")
                    
            except Exception as e:
                logger.error(f"Error in message processing loop: {e}")
                
            # Wait before next processing cycle
            time.sleep(self.process_interval)
            
    def add_message(self, from_agent: str, to_agent: str, message: str, priority: int = 0) -> bool:
        """Add a message to the queue."""
        return self.queue_manager.add_message(from_agent, to_agent, message, priority)
        
    def get_status(self) -> dict:
        """Get current queue status."""
        return self.queue_manager.get_queue_status()
        
    def clear_queue(self):
        """Clear all pending messages."""
        self.queue_manager.clear_queue()

def main():
    processor = MessageProcessor()
    processor.start()
    
    try:
        # Example usage
        processor.add_message("Agent-1", "Agent-2", "Research task completed", priority=1)
        processor.add_message("Agent-3", "Agent-4", "Documentation progress update", priority=2)
        
        # Keep running for a while to process messages
        time.sleep(5)
        
    finally:
        processor.stop()

if __name__ == "__main__":
    main() 