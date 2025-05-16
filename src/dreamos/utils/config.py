"""
Configuration Manager for Dream.OS

This module provides configuration management functionality.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages system configuration."""

    def __init__(self):
        """Initialize the configuration manager."""
        self.config: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
