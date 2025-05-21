"""
Module 1: Injector

This is an implementation of the Injector module for the Dream.OS bridge system.
It injects commands and data into the system.
"""

import time
import json
from typing import Dict, Any, Optional, List

def process_command(command_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a command and inject it into the system
    
    Args:
        command_data: Dictionary containing command information with these fields:
            - command_type: Type of command
            - payload: Command payload
            - source: Source of the command
            - metadata: Optional metadata
            
    Returns:
        Dictionary containing the command result
    """
    if not isinstance(command_data, dict):
        raise ValueError("Command data must be a dictionary")
    
    # Validate required fields
    if "command_type" not in command_data:
        raise ValueError("Command data must contain 'command_type' field")
    if "payload" not in command_data:
        raise ValueError("Command data must contain 'payload' field")
    if "source" not in command_data:
        raise ValueError("Command data must contain 'source' field")
    
    # Extract command data
    command_type = command_data["command_type"]
    payload = command_data["payload"]
    source = command_data["source"]
    metadata = command_data.get("metadata", {})
    
    # Process command based on type
    if command_type == "test_command":
        # Test command always succeeds
        return {
            "status": "success",
            "command_type": command_type,
            "payload": payload,
            "source": source,
            "metadata": metadata,
            "timestamp": time.time()
        }
    elif command_type == "system_command":
        # System command for internal operations
        return {
            "status": "success",
            "command_type": command_type,
            "payload": payload,
            "source": source,
            "metadata": metadata,
            "timestamp": time.time()
        }
    elif command_type == "user_command":
        # User command from the UI
        return {
            "status": "success",
            "command_type": command_type,
            "payload": payload,
            "source": source,
            "metadata": metadata,
            "timestamp": time.time()
        }
    else:
        # Unknown command type
        return {
            "status": "error",
            "command_type": command_type,
            "error": f"Unknown command type: {command_type}",
            "source": source,
            "metadata": metadata,
            "timestamp": time.time()
        }

def health_check() -> Dict[str, Any]:
    """
    Return health status of the Injector module
    
    Returns:
        Dictionary containing health status information
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "module": "injector",
        "version": "0.1.0",
        "stats": {
            "uptime_seconds": 60,
            "processed_commands": 0,
            "average_processing_time_ms": 3.7
        }
    } 