"""Defines the abstract base class for all LLM Bridge Adapters."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class BaseAdapter(ABC):
    """
    Abstract Base Class for LLM Bridge Adapters.

    Defines the common interface required for interacting with different
    LLM services or models through a unified bridge.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the adapter with optional configuration.

        Args:
            config (Optional[Dict[str, Any]]): Configuration dictionary 
                                                specific to the adapter 
                                                (e.g., API keys, model names).
        """
        self.config = config or {}
        self._validate_config()
        logger.info(f"Initialized {self.__class__.__name__}")

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the unique name identifier for this adapter."""
        pass

    def _validate_config(self):
        """
        Optional method for subclasses to validate their specific configuration.
        Called during initialization. Should raise ValueError on issues.
        """
        pass # Default implementation does nothing

    @abstractmethod
    async def send_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Sends a message to the underlying LLM or service.

        Args:
            message (str): The primary message content to send.
            context (Optional[Dict[str, Any]]): Additional context like conversation history,
                                                 system prompts, or parameters.

        Returns:
            str: A unique identifier for the interaction or conversation turn, 
                 if applicable (e.g., message ID, thread ID). Returns an empty
                 string if not applicable.

        Raises:
            AdapterError: If communication with the service fails.
        """
        pass

    @abstractmethod
    async def get_response(self, interaction_id: str) -> Dict[str, Any]:
        """
        Retrieves the response associated with a previous interaction.

        This might involve polling, waiting for a webhook, or querying 
        based on the interaction_id returned by send_message.

        Args:
            interaction_id (str): The identifier returned by a previous 
                                  `send_message` call.

        Returns:
            Dict[str, Any]: A dictionary containing the response details, 
                            typically including keys like 'content', 'status', 
                            'timestamp', 'metadata'. The structure should be 
                            standardized across adapters where possible.

        Raises:
            AdapterError: If retrieving the response fails or times out.
            ValueError: If the interaction_id is invalid.
        """
        pass

    async def close(self):
        """
        Optional method to clean up resources (e.g., close connections).
        Default implementation does nothing.
        """
        logger.info(f"Closing {self.__class__.__name__}")
        pass # Default does nothing

    # --- Helper Methods (Optional) ---

    def get_config_value(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """Helper to safely retrieve a value from the config."""
        return self.config.get(key, default)


class AdapterError(Exception):
    """Custom exception for errors originating from an adapter."""
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception

    def __str__(self):
        if self.original_exception:
            return f"{super().__str__()} (Original: {self.original_exception})"
        return super().__str__() 
