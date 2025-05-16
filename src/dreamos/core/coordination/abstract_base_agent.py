"""
Base agent class for Dream.OS agents.
Provides core functionality and interfaces for all agents.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from dreamos.core.coordination.agent_bus import AgentBus, EventType

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all Dream.OS agents."""
    
    def __init__(self, agent_id: str, agent_bus: AgentBus):
        """
        Initialize the agent.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_bus: Agent bus for communication
        """
        self.agent_id = agent_id
        self.agent_bus = agent_bus
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the agent."""
        if self._running:
            return
            
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._send_heartbeats())
        
        # Announce agent start
        await self.agent_bus.publish(
            EventType.AGENT_STARTED.value,
            {
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        logger.info(f"{self.agent_id} started")
        
    async def stop(self):
        """Stop the agent."""
        if not self._running:
            return
            
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
                
        # Announce agent stop
        await self.agent_bus.publish(
            EventType.AGENT_STOPPED.value,
            {
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        logger.info(f"{self.agent_id} stopped")
        
    @abstractmethod
    async def process_message(self, message: Dict[str, Any]):
        """
        Process an incoming message.
        
        Args:
            message: Message to process
        """
        pass

    @abstractmethod
    async def execute_task(self, task_details: Dict[str, Any]):
        """
        Execute the given task.
        This is where task-specific logic, including potential LLM interactions, should reside.

        Args:
            task_details: A dictionary containing the details of the task to execute.
        """
        pass
        
    async def _send_heartbeats(self):
        """Send periodic heartbeats."""
        while self._running:
            try:
                await self.agent_bus.publish(
                    EventType.AGENT_HEARTBEAT.value,
                    {
                        "agent_id": self.agent_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
                await asyncio.sleep(5)  # Brief pause before retry 