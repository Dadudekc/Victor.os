"""
config.py - Centralized Configuration Management

This module provides centralized configuration settings for the BasicBot trading system.
It loads settings from environment variables, config files, and provides sensible defaults.

Usage:
    from basicbot.config import config
    api_key = config.ALPACA_API_KEY
    symbol = config.SYMBOL
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TypeVar, Callable, cast
from dotenv import load_dotenv

T = TypeVar('T')

# Determine the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if present
env_path = PROJECT_ROOT / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path))


class Config:
    """
    Configuration class for BasicBot with environment variable support.
    """
    
    def __init__(self):
        # API keys and endpoints
        self.ALPACA_API_KEY = os.getenv('ALPACA_API_KEY', '')
        self.ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', '')
        self.ALPACA_BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        
        # Trading settings
        self.SYMBOL = os.getenv('TRADING_SYMBOL', 'TSLA')
        self.TIMEFRAME = os.getenv('TIMEFRAME', '5Min')
        self.TRADING_MODE = os.getenv('TRADING_MODE', 'backtest').lower()
        
        # Strategy parameters
        self.MA_SHORT = int(os.getenv('MA_SHORT', '50'))
        self.MA_LONG = int(os.getenv('MA_LONG', '200'))
        self.RSI_LENGTH = int(os.getenv('RSI_LENGTH', '14'))
        self.RSI_OVERBOUGHT = int(os.getenv('RSI_OVERBOUGHT', '70'))
        self.RSI_OVERSOLD = int(os.getenv('RSI_OVERSOLD', '30'))
        
        # Database settings
        self.DB_TYPE = os.getenv('DB_TYPE', 'postgresql')
        self.POSTGRES_DBNAME = os.getenv('POSTGRES_DBNAME', 'basicbot')
        self.POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
        self.POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'postgres')
        self.POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
        self.POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', '5432'))
        
        # Logging settings
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_DIR = os.getenv('LOG_DIR', str(PROJECT_ROOT / 'logs'))
        
        # Model settings
        self.MODEL_SAVE_PATH = os.getenv('MODEL_SAVE_PATH', str(PROJECT_ROOT / 'models'))
        
        # Ensure directories exist
        Path(self.LOG_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.MODEL_SAVE_PATH).mkdir(parents=True, exist_ok=True)
    
    def get_env(self, key: str, default: Optional[T] = None, cast_func: Optional[Callable[[str], T]] = None) -> T:
        """
        Get an environment variable with optional default value and type casting.
        
        Args:
            key: The environment variable name
            default: Default value if not found
            cast_func: Function to cast the string value to a different type
            
        Returns:
            The value of the environment variable, cast to the appropriate type
        """
        value = os.getenv(key)
        
        if value is None:
            return cast(T, default)
        
        if cast_func is not None:
            try:
                return cast_func(value)
            except (ValueError, TypeError):
                if default is not None:
                    return cast(T, default)
                raise ValueError(f"Cannot cast {key}={value} using {cast_func.__name__}")
        
        return cast(T, value)
    
    def validate(self) -> List[str]:
        """
        Validate configuration settings and return a list of errors, if any.
        
        Returns:
            List of error messages, empty if no errors
        """
        errors = []
        
        # Check critical API settings
        if self.TRADING_MODE == 'live':
            if not self.ALPACA_API_KEY:
                errors.append("ALPACA_API_KEY is required for live trading")
            if not self.ALPACA_SECRET_KEY:
                errors.append("ALPACA_SECRET_KEY is required for live trading")
        
        # Check trading settings
        if not self.SYMBOL:
            errors.append("SYMBOL is required")
        
        if self.TRADING_MODE not in ['live', 'backtest']:
            errors.append(f"Invalid TRADING_MODE: {self.TRADING_MODE}. Must be 'live' or 'backtest'")
        
        return errors


# Create a singleton instance
config = Config()

# For testing
if __name__ == "__main__":
    errors = config.validate()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Configuration is valid")
        
        # Print current configuration
        print("\nCurrent configuration:")
        for key, value in vars(config).items():
            if not key.startswith('__'):
                # Hide sensitive information
                if 'KEY' in key or 'PASSWORD' in key:
                    value = '****' if value else 'Not set'
                print(f"  {key}: {value}") 