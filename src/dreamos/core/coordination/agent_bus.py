"""
Agent Bus for inter-agent communication.
Provides a pub/sub system for agent events and messages.
"""

import asyncio
import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Types of events that can be published."""
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"
    AGENT_HEARTBEAT = "agent.heartbeat"
    AGENT_RESPONSE = "agent.response"
    VOTE_INITIATED = "vote.initiated"
    AGENT_VOTE = "agent.vote"
    VOTE_COMPLETED = "vote.completed"
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    CURSOR_STATE = "system.cursor"
    CURSOR_STUCK = "system.cursor.stuck"

class BaseEvent(BaseModel):
    """Base event model."""
    event_type: str
    source_id: str
    data: Dict[str, Any] = Field(default_factory=dict)

class AgentBus:
    """Message bus for agent communication."""
    
    def __init__(self):
        """Initialize the agent bus."""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._running = False
        self._event_queue = asyncio.Queue()
        self._process_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start processing events."""
        if self._running:
            return
            
        self._running = True
        self._process_task = asyncio.create_task(self._process_events())
        logger.info("AgentBus started")
        
    async def stop(self):
        """Stop processing events."""
        if not self._running:
            return
            
        self._running = False
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
        logger.info("AgentBus stopped")
        
    async def publish(self, event_type: str, data: Dict[str, Any]):
        """
        Publish an event.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        await self._event_queue.put((event_type, data))
        
    async def subscribe(self, event_type: str, callback: Callable):
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Async callback function to handle the event
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to {event_type}")
        
    async def unsubscribe(self, event_type: str, callback: Callable):
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Callback function to remove
        """
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)
            logger.debug(f"Unsubscribed from {event_type}")
            
    async def _process_events(self):
        """Process events from the queue."""
        while self._running:
            try:
                event_type, data = await self._event_queue.get()
                
                if event_type in self._subscribers:
                    for callback in self._subscribers[event_type]:
                        try:
                            await callback(event_type, data)
                        except Exception as e:
                            logger.error(f"Error in event handler: {e}")
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                
        logger.info("Event processing stopped") 