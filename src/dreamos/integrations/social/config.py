"""
Configuration for social media integrations.
"""

import os
from typing import Any, Dict, Optional

class SocialConfig:
    """
    Simple configuration class for social media integrations.
    """
    
    def __init__(self):
        """Initialize with default values."""
        self.config = {
            "social": {
                "linkedin": {},
                "twitter": {},
                "facebook": {},
                "instagram": {},
                "reddit": {},
                "stocktwits": {}
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., "social.linkedin.email")
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if "." in key:
            parts = key.split(".")
            current = self.config
            for part in parts[:-1]:
                if part not in current:
                    return default
                current = current[part]
            return current.get(parts[-1], default)
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., "social.linkedin.email")
            value: Configuration value
        """
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
    
    def get_env(self, env_var: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a value from an environment variable.
        
        Args:
            env_var: Environment variable name
            default: Default value if not set
            
        Returns:
            Environment variable value or default
        """
        return os.environ.get(env_var, default)

# Create a singleton instance
config = SocialConfig() 