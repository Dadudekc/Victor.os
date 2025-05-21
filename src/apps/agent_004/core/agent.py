"""
Agent-4: User Interaction Specialist
Primary interface between users and the Dream.OS system.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from dreamos.core.coordination.agent_bus import AgentBus, EventType
from dreamos.core.coordination.base_agent import BaseAgent
from .query_processor import QueryProcessor

logger = logging.getLogger(__name__)

class Agent4(BaseAgent):
    """User Interaction Specialist agent implementation."""
    
    def __init__(self, agent_id: str, agent_bus: AgentBus):
        """Initialize Agent-4.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_bus: Agent bus for communication
        """
        super().__init__(agent_id, agent_bus)
        self._message_queue = asyncio.Queue(maxsize=1000)
        self._active_tasks: Dict[str, Any] = {}
        self._user_contexts: Dict[str, Dict[str, Any]] = {}
        self.query_processor = QueryProcessor()
        
    async def start(self):
        """Start the agent and initialize all components."""
        await super().start()
        logger.info(f"{self.agent_id} starting up...")
        
        # Initialize message processing
        asyncio.create_task(self._process_messages())
        
        # Initialize user context management
        asyncio.create_task(self._manage_user_contexts())
        
        # Announce agent start
        await self.agent_bus.publish(
            EventType.AGENT_STARTED.value,
            {
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        logger.info(f"{self.agent_id} started successfully")
        
    async def _process_messages(self):
        """Process incoming messages from the message queue."""
        while self._running:
            try:
                message = await self._message_queue.get()
                await self._handle_message(message)
                self._message_queue.task_done()
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await self._handle_error(e)
                
    async def _handle_message(self, message: Dict[str, Any]):
        """Handle an incoming message.
        
        Args:
            message: The message to handle
        """
        try:
            # Extract message details
            msg_type = message.get("type")
            msg_data = message.get("data", {})
            user_id = msg_data.get("user_id")
            
            # Update user context
            if user_id:
                await self._update_user_context(user_id, msg_data)
            
            # Process message based on type
            if msg_type == "user_query":
                await self._handle_user_query(msg_data)
            elif msg_type == "system_notification":
                await self._handle_system_notification(msg_data)
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self._handle_error(e)
            
    async def _handle_user_query(self, query_data: Dict[str, Any]):
        """Handle a user query.
        
        Args:
            query_data: The query data to handle
        """
        try:
            # Extract query details
            user_id = query_data.get("user_id")
            query = query_data.get("query")
            
            # Process query
            response = await self.query_processor.process_query(query, user_id, self._user_contexts.get(user_id, {}))
            
            # Update user context
            if response["status"] == "success":
                self._update_user_context(user_id, {
                    "last_query": query,
                    "last_response": response,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                })
            
            # Send response
            await self._send_response(user_id, response)
            
        except Exception as e:
            logger.error(f"Error handling user query: {e}")
            await self._handle_error(e)
            
    async def _send_response(self, user_id: str, response: Dict[str, Any]):
        """Send a response to a user.
        
        Args:
            user_id: The ID of the user to send to
            response: The response to send
        """
        try:
            await self.agent_bus.publish(
                EventType.USER_RESPONSE.value,
                {
                    "user_id": user_id,
                    "response": response,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error sending response: {e}")
            await self._handle_error(e)
            
    async def _update_user_context(self, user_id: str, data: Dict[str, Any]):
        """Update the context for a user.
        
        Args:
            user_id: The ID of the user
            data: The data to update the context with
        """
        if user_id not in self._user_contexts:
            self._user_contexts[user_id] = {}
            
        self._user_contexts[user_id].update(data)
        
    async def _manage_user_contexts(self):
        """Manage user contexts, cleaning up old ones."""
        while self._running:
            try:
                # Clean up old contexts
                self.query_processor.cleanup_old_contexts()
                
                # Remove old user contexts
                current_time = datetime.now(timezone.utc)
                for user_id in list(self._user_contexts.keys()):
                    last_updated = datetime.fromisoformat(self._user_contexts[user_id].get("last_updated", "2000-01-01T00:00:00+00:00"))
                    if (current_time - last_updated).total_seconds() > 3600:  # 1 hour
                        del self._user_contexts[user_id]
                        
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Error managing user contexts: {e}")
                await self._handle_error(e)
                
    async def _handle_error(self, error: Exception):
        """Handle an error.
        
        Args:
            error: The error to handle
        """
        # Log error
        logger.error(f"Error occurred: {error}")
        
        # Notify other agents if necessary
        await self.agent_bus.publish(
            EventType.ERROR.value,
            {
                "agent_id": self.agent_id,
                "error": str(error),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
    async def stop(self):
        """Stop the agent and clean up resources."""
        self._running = False
        
        # Wait for message queue to empty
        await self._message_queue.join()
        
        # Clean up resources
        self._user_contexts.clear()
        self._active_tasks.clear()
        
        logger.info(f"{self.agent_id} stopped") 