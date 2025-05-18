"""
Configuration Manager for Dream.OS

This module provides configuration management functionality.
"""

from typing import Any, Dict

# Global instance
_config_instance = None

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
        # Support dot notation (e.g., "social.twitter.username")
        if "." in key:
            parts = key.split(".")
            current = self.config
            for part in parts[:-1]:
                if part not in current or not isinstance(current[part], dict):
                    return default
                current = current[part]
            return current.get(parts[-1], default)
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        # Support dot notation (e.g., "social.twitter.username")
        if "." in key:
            parts = key.split(".")
            current = self.config
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            self.config[key] = value

def get_config() -> ConfigManager:
    """Get the global configuration manager instance.
    
    Returns:
        The global ConfigManager instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance
