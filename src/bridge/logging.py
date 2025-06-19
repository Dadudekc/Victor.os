"""
Bridge Logging Module
-------------------
Provides comprehensive logging and error handling capabilities for the Dream.OS Bridge system.
Implements standardized logging formats, error classification, recursive call prevention, 
and auto-recovery mechanisms.
"""

import os
import time
import uuid
import json
import datetime
import traceback
import collections
from typing import Dict, Any, Optional, List, Callable
from collections import defaultdict

class BridgeLogger:
    """
    Core logging system with error tracking and reporting.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Bridge Logger with the given configuration.
        
        Args:
            config: Configuration dictionary containing logging settings
        """
        self.log_path = config.get('log_path', 'runtime/logs/bridge_logs.jsonl')
        self.max_log_size = config.get('max_log_size', 10 * 1024 * 1024)  # 10MB default
        self.log_rotation_count = config.get('log_rotation_count', 5)
        self.enable_console = config.get('enable_console', True)
        self.min_log_level = config.get('min_log_level', 'INFO')
        
        # Initialize hash tracker for loop detection
        self.recent_payloads = collections.deque(maxlen=100)
        
        # Initialize recursion depth tracking
        self.current_recursion_depth = 0
        self.max_recursion_depth = config.get('max_recursion_depth', 100)
        
        # Initialize error counters for auto-reboot detection
        self.error_counters = defaultdict(lambda: {"count": 0, "first_seen": None})
        
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(self.log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Log initialization
        self.log({
            "source": "Bridge_Logger",
            "status": "INFO",
            "message": "Logger initialized successfully",
            "payload": {k: v for k, v in config.items() if k not in ['max_log_size']}
        })
    
    def log(self, event_data: Dict[str, Any], log_level: str = "INFO") -> str:
        """
        Log an event to the unified logging system.
        
        Args:
            event_data: Dictionary containing event information
            log_level: Severity level (INFO, WARNING, ERROR, FATAL)
            
        Returns:
            String event ID of the logged event
        """
        # Generate event ID if not provided
        if "eventId" not in event_data:
            event_data["eventId"] = str(uuid.uuid4())
            
        # Add timestamp if not provided
        if "timestamp" not in event_data:
            event_data["timestamp"] = datetime.datetime.utcnow().isoformat()
            
        # Add log level
        event_data["logLevel"] = log_level
        
        # Write to log file
        self._write_log(event_data)
        
        # Print to console if enabled
        if self.enable_console:
            self._print_log(event_data)
        
        # Check for critical errors
        if log_level == "ERROR" or log_level == "FATAL":
            self._process_error(event_data)
            
        return event_data["eventId"]
    
    def _write_log(self, event_data: Dict[str, Any]) -> None:
        """
        Write event data to the log file.
        
        Args:
            event_data: The event data to log
        """
        try:
            # Check if log rotation is needed
            if os.path.exists(self.log_path) and os.path.getsize(self.log_path) > self.max_log_size:
                self._rotate_logs()
            
            # Truncate payload if very large to prevent log file bloat
            if "payload" in event_data and isinstance(event_data["payload"], dict):
                payload_str = json.dumps(event_data["payload"])
                if len(payload_str) > 1024 * 1024:  # 1MB
                    event_data["payload"] = {
                        "truncated": True,
                        "original_size": len(payload_str),
                        "summary": str(event_data["payload"])[:1000] + "..."
                    }
            
            # Write event to log file
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_data) + '\n')
                
        except Exception as e:
            # Fall back to console if file logging fails
            if self.enable_console:
                print(f"ERROR: Failed to write to log file: {str(e)}")
                print(f"Log event: {json.dumps(event_data)}")
    
    def _print_log(self, event_data: Dict[str, Any]) -> None:
        """
        Print event data to the console in a readable format.
        
        Args:
            event_data: The event data to print
        """
        log_level = event_data.get("logLevel", "INFO")
        log_levels = {
            "DEBUG": "\033[37m[DEBUG]\033[0m",  # Gray
            "INFO": "\033[32m[INFO]\033[0m",    # Green
            "WARNING": "\033[33m[WARNING]\033[0m",  # Yellow
            "ERROR": "\033[31m[ERROR]\033[0m",  # Red
            "FATAL": "\033[41m[FATAL]\033[0m"   # Red background
        }
        
        level_str = log_levels.get(log_level, f"[{log_level}]")
        timestamp = event_data.get("timestamp", datetime.datetime.utcnow().isoformat())
        source = event_data.get("source", "unknown")
        message = event_data.get("message", "No message provided")
        
        print(f"{timestamp} {level_str} [{source}] {message}")
        
        # Print error details if present
        if "errorDetails" in event_data:
            error_code = event_data["errorDetails"].get("errorCode", "UNKNOWN_ERROR")
            error_message = event_data["errorDetails"].get("errorMessage", "No error message provided")
            print(f"  Error: {error_code} - {error_message}")
    
    def _rotate_logs(self) -> None:
        """
        Rotate log files to prevent excessive size.
        """
        try:
            # Rotate existing log files
            for i in range(self.log_rotation_count - 1, 0, -1):
                src = f"{self.log_path}.{i}" if i > 1 else self.log_path
                dst = f"{self.log_path}.{i + 1}"
                
                if os.path.exists(src):
                    if os.path.exists(dst):
                        os.remove(dst)
                    os.rename(src, dst)
            
            # Rename current log file
            if os.path.exists(self.log_path):
                os.rename(self.log_path, f"{self.log_path}.1")
                
        except Exception as e:
            # Log rotation failure - just print and continue
            if self.enable_console:
                print(f"WARNING: Failed to rotate log files: {str(e)}")
    
    def _process_error(self, event_data: Dict[str, Any]) -> None:
        """
        Process and track errors for auto-recovery detection.
        
        Args:
            event_data: The error event data
        """
        # Track error frequency for critical errors
        if "errorDetails" in event_data and "errorCode" in event_data["errorDetails"]:
            error_code = event_data["errorDetails"]["errorCode"]
            now = time.time()
            
            if error_code not in self.error_counters:
                self.error_counters[error_code] = {"count": 0, "first_seen": now}
                
            self.error_counters[error_code]["count"] += 1
            
            # Check for excessive errors (3+ critical errors of same type within 10 minutes)
            if (self.error_counters[error_code]["count"] >= 3 and 
                    now - self.error_counters[error_code]["first_seen"] < 600):  # 10 minutes
                # Log auto-reboot trigger
                self.log({
                    "source": event_data.get("source", "Bridge_System"),
                    "status": "ERROR",
                    "message": f"Auto-reboot triggered due to excessive critical errors.",
                    "errorDetails": {
                        "errorCode": "AUTO_REBOOT_TRIGGERED",
                        "errorMessage": f"{self.error_counters[error_code]['count']} critical errors ({error_code}) detected within 10 minutes."
                    }
                }, log_level="FATAL")
                
                # Trigger auto-reboot
                self._trigger_reboot()
    
    def _trigger_reboot(self) -> None:
        """
        Trigger an automatic reboot of the bridge system.
        """
        # In a real implementation, this would initiate a controlled reboot
        # For now, we'll just log the intention
        try:
            self.log({
                "source": "Bridge_System",
                "status": "WARNING",
                "message": "System reboot initiated due to excessive errors",
                "payload": {
                    "error_counters": {k: v["count"] for k, v in self.error_counters.items()}
                }
            }, log_level="WARNING")
            
            # Reset error counters after reboot
            self.error_counters = defaultdict(lambda: {"count": 0, "first_seen": None})
            
        except Exception as e:
            # Last resort console output
            if self.enable_console:
                print(f"CRITICAL: Failed to log reboot trigger: {str(e)}")
    
    def _hash_payload(self, payload: Any) -> str:
        """
        Create a hash of a payload for loop detection.
        
        Args:
            payload: The payload to hash
            
        Returns:
            String hash of the payload
        """
        try:
            # Convert payload to string and create a simple hash
            # In a real implementation, a more sophisticated hashing algorithm would be used
            payload_str = json.dumps(payload, sort_keys=True)
            return str(hash(payload_str))
        except Exception:
            # Fall back to string representation if JSON conversion fails
            return str(hash(str(payload)))
    
    def detect_infinite_loop(self, payload: Any) -> bool:
        """
        Detect potential infinite loops based on payload repetition.
        
        Args:
            payload: The payload to check for repetition
            
        Returns:
            True if an infinite loop is detected, False otherwise
        """
        # Create a hash of the payload to detect repetition
        payload_hash = self._hash_payload(payload)
        
        # Count occurrences of this hash in recent payloads
        occurrences = sum(1 for h in self.recent_payloads if h == payload_hash)
        
        # Add current hash to recent payloads
        self.recent_payloads.append(payload_hash)
        
        # If we've seen this exact payload 5+ times recently, it's likely an infinite loop
        if occurrences >= 5:
            self.log({
                "source": "Bridge_System",
                "status": "ERROR",
                "payload": {"repeating_payload_hash": payload_hash},
                "message": "Potential infinite loop detected based on payload hash repetition.",
                "errorDetails": {
                    "errorCode": "LOOP_DETECTED",
                    "errorMessage": f"Payload hash '{payload_hash[:6]}...' repeated {occurrences} times within {len(self.recent_payloads)} cycles."
                }
            }, log_level="ERROR")
            
            return True
            
        return False
    
    def track_recursion(self, increment: bool = True) -> bool:
        """
        Track and limit recursion depth to prevent stack overflow.
        
        Args:
            increment: True to increment the depth, False to decrement
            
        Returns:
            False if maximum recursion depth is reached, True otherwise
        """
        if increment:
            self.current_recursion_depth += 1
            
            # Check if we've exceeded the maximum recursion depth
            if self.current_recursion_depth >= self.max_recursion_depth:
                self.log({
                    "source": "Bridge_System",
                    "status": "ERROR",
                    "message": "Recursion depth exceeded threshold.",
                    "errorDetails": {
                        "errorCode": "STACK_EXHAUSTION",
                        "errorMessage": f"Maximum recursion depth ({self.max_recursion_depth}) reached."
                    }
                }, log_level="ERROR")
                
                # Reset depth and return error indicator
                self.current_recursion_depth = 0
                return False
        else:
            # Decrement the recursion depth when returning from a call
            self.current_recursion_depth = max(0, self.current_recursion_depth - 1)
            
        return True


class ErrorHandler:
    """
    Standardized error response generation and handling.
    """
    
    def __init__(self, logger: BridgeLogger):
        """
        Initialize the Error Handler with a logger instance.
        
        Args:
            logger: The BridgeLogger instance to use for logging errors
        """
        self.logger = logger
    
    def handle_exception(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle an exception and generate a standardized error response.
        
        Args:
            error: The exception that was caught
            context: Additional context about where the error occurred
            
        Returns:
            Standardized error response dictionary
        """
        # Generate error code based on exception type
        error_code = self._get_error_code_from_exception(error)
        
        # Get exception details
        error_message = str(error)
        error_traceback = traceback.format_exc()
        
        # Log the error
        self.logger.log({
            "source": context.get("source", "Bridge_System"),
            "status": "ERROR",
            "message": f"Exception caught: {error_message}",
            "payload": context or {},
            "errorDetails": {
                "errorCode": error_code,
                "errorMessage": error_message,
                "errorTraceback": error_traceback
            }
        }, log_level="ERROR")
        
        # Create and return standardized error response
        return self.create_error_response(
            error_code,
            error_message,
            {
                "exception_type": error.__class__.__name__,
                "context": context
            }
        )
    
    def create_error_response(self, error_code: str, error_message: str, error_details: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a standardized error response.
        
        Args:
            error_code: The error code
            error_message: The error message
            error_details: Additional error details
            
        Returns:
            Standardized error response dictionary
        """
        return {
            "status": "error",
            "error": {
                "code": error_code,
                "message": error_message,
                "details": error_details or {}
            }
        }
    
    def _get_error_code_from_exception(self, error: Exception) -> str:
        """
        Generate an error code based on the exception type.
        
        Args:
            error: The exception
            
        Returns:
            String error code
        """
        # Map common exception types to error codes
        exception_type = error.__class__.__name__
        
        error_code_map = {
            "ValueError": "INVALID_VALUE",
            "TypeError": "TYPE_ERROR",
            "KeyError": "MISSING_KEY",
            "IndexError": "INDEX_OUT_OF_RANGE",
            "FileNotFoundError": "FILE_NOT_FOUND",
            "PermissionError": "PERMISSION_DENIED",
            "TimeoutError": "OPERATION_TIMEOUT",
            "ConnectionError": "CONNECTION_ERROR",
            "ImportError": "IMPORT_ERROR",
            "RuntimeError": "RUNTIME_ERROR",
            "NotImplementedError": "NOT_IMPLEMENTED",
            "AssertionError": "ASSERTION_FAILED",
            "AttributeError": "ATTRIBUTE_ERROR",
            "OSError": "OPERATING_SYSTEM_ERROR",
            "IOError": "IO_ERROR",
            "ZeroDivisionError": "DIVISION_BY_ZERO",
            "MemoryError": "MEMORY_ERROR",
            "StopIteration": "ITERATION_STOPPED",
            "SyntaxError": "SYNTAX_ERROR",
            "UnboundLocalError": "UNBOUND_LOCAL",
            "NameError": "NAME_ERROR"
        }
        
        return error_code_map.get(exception_type, "UNEXPECTED_ERROR") 