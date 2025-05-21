"""
Message Bus implementation for Dream.OS inter-agent communication.
"""

from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import logging
from pathlib import Path
import json
import uuid
from queue import Queue
from threading import Lock, Thread
import time

class MessageBus:
    """
    Message bus for inter-agent communication in Dream.OS.
    """
    
    def __init__(
        self,
        state_dir: Optional[Path] = None,
        log_level: int = logging.INFO
    ):
        """
        Initialize the message bus.
        
        Args:
            state_dir: Directory to store message state (optional)
            log_level: Logging level for the bus
        """
        self.state_dir = state_dir or Path("runtime/communication")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger("dreamos.message_bus")
        self.logger.setLevel(log_level)
        
        # Message queues for each agent
        self.queues: Dict[str, Queue] = {}
        self.queue_lock = Lock()
        
        # Message handlers
        self.handlers: Dict[str, List[Callable]] = {}
        self.handler_lock = Lock()
        
        # Message history
        self.message_history: Dict[str, Dict[str, Any]] = {}
        self.history_lock = Lock()
        
        # Load message history
        self._load_history()
        
        # Start message processing thread
        self.running = True
        self.processor = Thread(target=self._process_messages, daemon=True)
        self.processor.start()
        
        self.logger.info("Message Bus initialized")
    
    def register_agent(self, agent_id: str) -> None:
        """
        Register an agent with the message bus.
        
        Args:
            agent_id: ID of agent to register
        """
        with self.queue_lock:
            if agent_id not in self.queues:
                self.queues[agent_id] = Queue()
                self.logger.info(f"Registered agent {agent_id}")
    
    def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent from the message bus.
        
        Args:
            agent_id: ID of agent to unregister
        """
        with self.queue_lock:
            if agent_id in self.queues:
                del self.queues[agent_id]
                self.logger.info(f"Unregistered agent {agent_id}")
    
    def subscribe(self, message_type: str, handler: Callable) -> None:
        """
        Subscribe to messages of a specific type.
        
        Args:
            message_type: Type of messages to subscribe to
            handler: Function to call when message received
        """
        with self.handler_lock:
            if message_type not in self.handlers:
                self.handlers[message_type] = []
            self.handlers[message_type].append(handler)
            self.logger.info(f"Subscribed to messages of type {message_type}")
    
    def unsubscribe(self, message_type: str, handler: Callable) -> None:
        """
        Unsubscribe from messages of a specific type.
        
        Args:
            message_type: Type of messages to unsubscribe from
            handler: Handler to remove
        """
        with self.handler_lock:
            if message_type in self.handlers:
                self.handlers[message_type].remove(handler)
                self.logger.info(f"Unsubscribed from messages of type {message_type}")
    
    def publish(
        self,
        message_type: str,
        content: Dict[str, Any],
        sender: str,
        recipients: Optional[List[str]] = None
    ) -> str:
        """
        Publish a message to the bus.
        
        Args:
            message_type: Type of message
            content: Message content
            sender: ID of sending agent
            recipients: List of recipient agent IDs (None for broadcast)
            
        Returns:
            Message ID
        """
        message_id = str(uuid.uuid4())
        
        message = {
            "id": message_id,
            "type": message_type,
            "content": content,
            "sender": sender,
            "recipients": recipients,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store in history
        with self.history_lock:
            self.message_history[message_id] = message
            self._save_history()
        
        # Queue message for recipients
        with self.queue_lock:
            if recipients:
                for recipient in recipients:
                    if recipient in self.queues:
                        self.queues[recipient].put(message)
            else:
                # Broadcast to all agents except sender
                for agent_id, queue in self.queues.items():
                    if agent_id != sender:
                        queue.put(message)
        
        # Call handlers
        with self.handler_lock:
            handlers = self.handlers.get(message_type, [])
            for handler in handlers:
                try:
                    handler(message)
                except Exception as e:
                    self.logger.error(f"Error in message handler: {str(e)}")
        
        self.logger.info(f"Published message {message_id} of type {message_type}")
        return message_id
    
    def get_messages(
        self,
        agent_id: str,
        timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get messages for an agent.
        
        Args:
            agent_id: ID of agent to get messages for
            timeout: Timeout in seconds (None for no timeout)
            
        Returns:
            Next message, or None if timeout
        """
        with self.queue_lock:
            queue = self.queues.get(agent_id)
            if not queue:
                return None
            
            try:
                return queue.get(timeout=timeout)
            except:
                return None
    
    def get_message_history(
        self,
        message_type: Optional[str] = None,
        sender: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get message history with optional filters.
        
        Args:
            message_type: Filter by message type
            sender: Filter by sender
            start_time: Filter by start time
            end_time: Filter by end time
            
        Returns:
            List of matching messages
        """
        with self.history_lock:
            messages = list(self.message_history.values())
            
            if message_type:
                messages = [m for m in messages if m["type"] == message_type]
            
            if sender:
                messages = [m for m in messages if m["sender"] == sender]
            
            if start_time:
                messages = [m for m in messages if datetime.fromisoformat(m["timestamp"]) >= start_time]
            
            if end_time:
                messages = [m for m in messages if datetime.fromisoformat(m["timestamp"]) <= end_time]
            
            return messages
    
    def _process_messages(self) -> None:
        """
        Background thread to process messages.
        """
        while self.running:
            time.sleep(0.1)  # Prevent busy waiting
    
    def shutdown(self) -> None:
        """
        Shutdown the message bus.
        """
        self.running = False
        if self.processor.is_alive():
            self.processor.join()
        self.logger.info("Message Bus shut down")
    
    def _save_history(self) -> None:
        """
        Save message history to disk.
        """
        history_file = self.state_dir / "message_history.json"
        with open(history_file, "w") as f:
            json.dump(self.message_history, f, indent=2)
    
    def _load_history(self) -> None:
        """
        Load message history from disk.
        """
        history_file = self.state_dir / "message_history.json"
        if history_file.exists():
            with open(history_file, "r") as f:
                self.message_history = json.load(f) 