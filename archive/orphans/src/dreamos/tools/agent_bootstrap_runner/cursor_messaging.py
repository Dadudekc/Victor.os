"""
Cursor-based messaging utilities for Dream.OS agents
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from dreamos.core.config import AppConfig
from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.utils.gui.injector import CursorInjector
from dreamos.utils.gui.retriever import ResponseRetriever

from .config import AgentConfig


class CursorAgentMessenger:
    """Handles Cursor-based messaging for agents."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(f"{config.agent_id}.messenger")
        self.app_config = AppConfig()
        self.agent_bus = AgentBus()

        # Initialize UI components
        self.injector = CursorInjector(
            agent_id=config.agent_id, coords_file=str(config.coords_file)
        )
        self.retriever = ResponseRetriever(
            agent_id=config.agent_id_for_retriever,
            coords_file=str(config.copy_coords_file),
        )

    async def send_message(self, message: str) -> bool:
        """
        Send a message to the agent via Cursor.

        Args:
            message: The message text to send

        Returns:
            bool: True if message was sent successfully
        """
        try:
            self.logger.info(
                f"Sending message to {self.config.agent_id}: {message[:50]}..."
            )
            return self.injector.inject(message)
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False

    async def get_response(self, timeout_sec: float = 30.0) -> Optional[str]:
        """
        Get a response from the agent via Cursor.

        Args:
            timeout_sec: Maximum time to wait for response

        Returns:
            str: The response text, or None if no response received
        """
        try:
            # Initial delay to allow agent to process
            await asyncio.sleep(5)

            start_time = datetime.now()
            while (datetime.now() - start_time).total_seconds() < timeout_sec:
                response = self.retriever.get_response()
                if response:
                    self.logger.info(
                        f"Got response from {self.config.agent_id}: {response[:50]}..."
                    )
                    return response
                await asyncio.sleep(2)

            self.logger.warning(
                f"No response from {self.config.agent_id} after {timeout_sec}s"
            )
            return None

        except Exception as e:
            self.logger.error(f"Failed to get response: {e}")
            return None

    async def send_and_get_response(
        self, message: str, timeout_sec: float = 30.0
    ) -> Optional[str]:
        """
        Send a message and wait for response.

        Args:
            message: The message to send
            timeout_sec: Maximum time to wait for response

        Returns:
            str: The response text, or None if no response received
        """
        if not await self.send_message(message):
            return None

        return await self.get_response(timeout_sec)


# For backward compatibility
async def publish_event(event: Dict[str, Any], config: AgentConfig) -> None:
    """Legacy function for publishing events - now uses CursorAgentMessenger"""
    messenger = CursorAgentMessenger(config)
    await messenger.send_message(json.dumps(event))
