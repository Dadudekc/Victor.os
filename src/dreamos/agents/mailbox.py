"""
Mailbox module for agent communication.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Represents a message in the mailbox."""
    sender: str
    recipient: str
    content: Any
    timestamp: datetime
    message_id: str
    priority: int = 0
    metadata: Optional[Dict[str, Any]] = None


class Mailbox:
    """Mailbox for inter-agent communication."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.inbox: List[Message] = []
        self.outbox: List[Message] = []
        self._lock = asyncio.Lock()
        
    async def send_message(self, recipient: str, content: Any, 
                          priority: int = 0, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Send a message to another agent."""
        async with self._lock:
            message = Message(
                sender=self.agent_id,
                recipient=recipient,
                content=content,
                timestamp=datetime.now(),
                message_id=f"{self.agent_id}_{recipient}_{datetime.now().timestamp()}",
                priority=priority,
                metadata=metadata
            )
            self.outbox.append(message)
            logger.info(f"Message sent from {self.agent_id} to {recipient}")
            return message.message_id
    
    async def receive_message(self, sender: str) -> Optional[Message]:
        """Receive a message from a specific sender."""
        async with self._lock:
            for message in self.inbox:
                if message.sender == sender:
                    self.inbox.remove(message)
                    logger.info(f"Message received by {self.agent_id} from {sender}")
                    return message
            return None
    
    async def get_all_messages(self) -> List[Message]:
        """Get all messages in the inbox."""
        async with self._lock:
            messages = self.inbox.copy()
            self.inbox.clear()
            return messages
    
    async def add_message(self, message: Message):
        """Add a message to the inbox (used by the messaging system)."""
        async with self._lock:
            self.inbox.append(message)
            logger.info(f"Message added to {self.agent_id} inbox from {message.sender}")
    
    def get_inbox_size(self) -> int:
        """Get the number of messages in the inbox."""
        return len(self.inbox)
    
    def get_outbox_size(self) -> int:
        """Get the number of messages in the outbox."""
        return len(self.outbox) 