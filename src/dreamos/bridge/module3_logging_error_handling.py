"""
Module 3: Logging & Error Handling

This is an implementation of the Logging & Error Handling module for the Dream.OS bridge system.
It provides logging and error handling capabilities for the bridge modules.
"""

import time
import json
import traceback
from typing import Dict, Any, Optional, Union

def log(event_data: Dict[str, Any], log_level: str = "INFO") -> str:
    """
    Log an event
    
    Args:
        event_data: Dictionary containing event information
        log_level: Severity level (INFO, WARNING, ERROR, FATAL)
        
    Returns:
        Event ID (string)
    """
    if not isinstance(event_data, dict):
        raise ValueError("Event data must be a dictionary")
    
    # Validate log level
    valid_levels = ["INFO", "WARNING", "ERROR", "FATAL"]
    if log_level not in valid_levels:
        log_level = "INFO"
    
    # Generate event ID and timestamp
    timestamp = time.time()
    event_id = f"{int(timestamp)}_{log_level}"
    
    # Create log entry
    log_entry = {
        "event_id": event_id,
        "timestamp": timestamp,
        "level": log_level,
        "data": event_data
    }
    
    # In a real implementation, this would write to a log file or database
    # For now, we just print the log entry
    print(f"[{log_level}] {event_id}")
    
    return event_id

def handle_error(error: Exception, context: Optional[Dict[str, Any]] = None, error_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Handle an error
    
    Args:
        error: The exception that was caught
        context: Additional context about where the error occurred
        error_code: Optional specific error code
        
    Returns:
        Dictionary containing error handling result
    """
    if not isinstance(error, Exception):
        raise ValueError("Error must be an Exception")
    
    # Create context if not provided
    if context is None:
        context = {}
    
    # Generate error ID and timestamp
    timestamp = time.time()
    error_id = f"err_{int(timestamp)}"
    
    # Create error entry
    error_entry = {
        "error_id": error_id,
        "timestamp": timestamp,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "error_code": error_code,
        "context": context,
        "traceback": traceback.format_exc()
    }
    
    # Log the error
    log(error_entry, log_level="ERROR")
    
    # Return error handling result
    return {
        "error_id": error_id,
        "status": "error_logged",
        "handled": True,
        "error_code": error_code,
        "error_type": type(error).__name__,
        "error_message": str(error)
    } 