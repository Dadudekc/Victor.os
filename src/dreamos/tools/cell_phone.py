"""
Cell Phone Interface

Provides a simple interface for agents to send messages via cell phone.
"""

import logging
from typing import Optional
from .message_processor import MessageProcessor

logger = logging.getLogger('cell_phone')

class CellPhone:
    _instance: Optional['CellPhone'] = None
    _processor: Optional[MessageProcessor] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._processor = MessageProcessor()
            cls._processor.start()
        return cls._instance
    
    def send_message(self, from_agent: str, to_agent: str, message: str, priority: int = 0) -> bool:
        """Send a message via cell phone."""
        try:
            if not self._processor:
                logger.error("Message processor not initialized")
                return False
                
            success = self._processor.add_message(from_agent, to_agent, message, priority)
            if success:
                logger.info(f"Message queued from {from_agent} to {to_agent}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
            
    def get_status(self) -> dict:
        """Get current message queue status."""
        try:
            if not self._processor:
                return {"error": "Message processor not initialized"}
            return self._processor.get_status()
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {"error": str(e)}
            
    def clear_messages(self):
        """Clear all pending messages."""
        try:
            if self._processor:
                self._processor.clear_queue()
        except Exception as e:
            logger.error(f"Failed to clear messages: {e}")
            
    def shutdown(self):
        """Shutdown the cell phone interface."""
        try:
            if self._processor:
                self._processor.stop()
                self._processor = None
                self._instance = None
        except Exception as e:
            logger.error(f"Failed to shutdown: {e}")

def main():
    # Example usage
    phone = CellPhone()
    
    # Send some test messages
    phone.send_message("Agent-1", "Agent-2", "Research task completed", priority=1)
    phone.send_message("Agent-3", "Agent-4", "Documentation progress update", priority=2)
    
    # Get status
    status = phone.get_status()
    print(f"Cell phone status: {status}")
    
    # Cleanup
    phone.shutdown()

if __name__ == "__main__":
    main() 