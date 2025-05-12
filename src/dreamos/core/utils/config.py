"""Configuration management utilities for Dream.OS."""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration settings for Dream.OS components."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the configuration manager.
        
        Args:
            config: Optional initial configuration dictionary
        """
        self._config = config or {}
        logger.debug("Initialized ConfigManager with %d settings", len(self._config))
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key to retrieve
            default: Default value if key is not found
            
        Returns:
            The configuration value or default if not found
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.
        
        Args:
            key: Configuration key to set
            value: Value to store
        """
        self._config[key] = value
        logger.debug("Set config key '%s'", key) 