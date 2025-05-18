# Module 3: Logging & Error Handling Layer

**Component Name:** Bridge Module 3 - Logging & Error Handling Layer  
**Version:** 1.0.0  
**Author:** Agent-5 (Knurlshade)  
**Created:** 2025-05-20  
**Status:** IMPLEMENTED  
**Dependencies:** Bridge Core System  

## 1. Overview

Module 3 provides comprehensive logging and error handling capabilities for the Dream.OS Bridge system. It serves as the critical foundation for system monitoring, error detection, prevention, and recovery. The module implements standardized logging formats, error classification, recursive call prevention, and auto-recovery mechanisms that should be adopted by all other bridge modules.

## 2. Interface Definition

### 2.1 Input

```python
# Standard logging interface
def log(event_data: dict, log_level: str = "INFO") -> str:
    """
    Log an event to the unified logging system
    
    Args:
        event_data: Dictionary containing event information
        log_level: Severity level (INFO, WARNING, ERROR, FATAL)
        
    Returns:
        String event ID of the logged event
    """
    pass

# Error handling interface
def handle_error(error: Exception, context: dict = None, error_code: str = None) -> dict:
    """
    Standardized error handling that logs and formats errors
    
    Args:
        error: The exception that was caught
        context: Additional context about where the error occurred
        error_code: Optional specific error code
        
    Returns:
        Standardized error response dictionary
    """
    pass
```

### 2.2 Output

```python
# Standard log entry format
{
    "eventId": "f47ac10b-58cc-4372-a567-0e02b2c3d479", 
    "timestamp": "2025-05-18T14:32:17.123Z", 
    "source": "Bridge_Relay", 
    "status": "ERROR", 
    "payload": {"malformed_data": "..."}, 
    "logLevel": "ERROR", 
    "message": "Payload validation failed against schema.", 
    "errorDetails": {
        "errorCode": "MALFORMED_PAYLOAD", 
        "errorMessage": "Schema validation error: Missing required property 'expected_field'"
    }
}

# Standard error response format
{
    "status": "error",
    "error": {
        "code": "MALFORMED_PAYLOAD",
        "message": "Schema validation error: Missing required property 'expected_field'",
        "details": {
            "missing_field": "expected_field",
            "payload_received": {"malformed_data": "..."}
        }
    }
}
```

### 2.3 Error Handling

```python
# Example of error handling pattern
try:
    result = validate_payload(payload)
except ValidationError as e:
    # Log with standard format
    log({
        "source": "Bridge_Relay",
        "status": "ERROR",
        "payload": payload,
        "message": "Payload validation failed against schema.",
        "errorDetails": {
            "errorCode": "MALFORMED_PAYLOAD",
            "errorMessage": str(e)
        }
    }, log_level="ERROR")
    
    # Return standardized error response
    return {
        "status": "error",
        "error": {
            "code": "MALFORMED_PAYLOAD",
            "message": str(e),
            "details": {
                "missing_field": e.field_name,
                "payload_received": payload
            }
        }
    }
```

## 3. Implementation Details

### 3.1 Core Logic

```python
class BridgeLogger:
    def __init__(self, config):
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
        
    def log(self, event_data, log_level="INFO"):
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
        
        # Check for critical errors
        if log_level == "ERROR" or log_level == "FATAL":
            self._process_error(event_data)
            
        return event_data["eventId"]
        
    def _process_error(self, event_data):
        # Track error frequency for critical errors
        if "errorDetails" in event_data and "errorCode" in event_data["errorDetails"]:
            error_code = event_data["errorDetails"]["errorCode"]
            now = time.time()
            
            if error_code not in self.error_counters:
                self.error_counters[error_code] = {"count": 0, "first_seen": now}
                
            self.error_counters[error_code]["count"] += 1
            
            # Check for excessive errors (3+ critical errors of same type within 10 cycles)
            if (self.error_counters[error_code]["count"] >= 3 and 
                    now - self.error_counters[error_code]["first_seen"] < 600):  # 10 minutes
                # Log auto-reboot trigger
                self.log({
                    "source": event_data.get("source", "Bridge_System"),
                    "status": "ERROR",
                    "message": f"Auto-reboot triggered due to excessive critical errors.",
                    "errorDetails": {
                        "errorCode": "AUTO_REBOOT_TRIGGERED",
                        "errorMessage": f"{self.error_counters[error_code]['count']} critical errors ({error_code}) detected within 10 cycles."
                    }
                }, log_level="FATAL")
                
                # Trigger auto-reboot
                self._trigger_reboot()
    
    def detect_infinite_loop(self, payload):
        # Create a hash of the payload to detect repetition
        payload_hash = self._hash_payload(payload)
        
        # Count occurrences of this hash in recent payloads
        occurrences = sum(1 for h in self.recent_payloads if h == payload_hash)
        
        # Add current hash to recent payloads
        self.recent_payloads.append(payload_hash)
        
        # If we've seen this exact payload 5+ times recently, it's likely an infinite loop
        if occurrences >= 5:
            self.log({
                "source": "Bridge_Relay",
                "status": "ERROR",
                "payload": {"repeating_command": "..."},
                "message": "Potential infinite loop detected based on payload hash repetition.",
                "errorDetails": {
                    "errorCode": "LOOP_DETECTED",
                    "errorMessage": f"Payload hash '{payload_hash[:6]}...' repeated {occurrences} times within {len(self.recent_payloads)} cycles."
                }
            }, log_level="ERROR")
            
            return True
            
        return False
        
    def track_recursion(self, increment=True):
        if increment:
            self.current_recursion_depth += 1
            
            # Check if we've exceeded the maximum recursion depth
            if self.current_recursion_depth >= self.max_recursion_depth:
                self.log({
                    "source": "Bridge_Relay",
                    "status": "ERROR",
                    "payload": None,
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
```

### 3.2 Key Components

- **BridgeLogger**: Core logging system with error tracking and reporting
- **ValidationSystem**: Schema-based validation for all incoming/outgoing data
- **ErrorHandler**: Standardized error response generation
- **LoopDetector**: Identifies potential infinite loops
- **RecursionTracker**: Prevents stack overflow from excessive recursion
- **AutoReboot**: Initiates recovery when error thresholds are crossed

### 3.3 Data Flow

1. Bridge operations generate events or encounter errors
2. Events/errors are processed through the logging system
3. Patterns of errors are detected and tracked
4. Excessive errors trigger auto-recovery mechanisms
5. All events are stored in structured logs for analysis

## 4. Integration Points

### 4.1 Dependencies

| Component | Version | Purpose | Owner |
|-----------|---------|---------|-------|
| Bridge Core | v1.0 | Provides base bridge functionality | Agent-1 |
| Config Manager | v1.2 | Provides configuration values | Agent-2 |

### 4.2 Required Services

- **File System Access**: For log file writing
- **Time Services**: For accurate timestamping
- **UUID Generation**: For unique event IDs

### 4.3 Integration Example

```python
# Example showing how to integrate with Module 3
from bridge.modules.module3 import BridgeLogger, ErrorHandler

# Initialize
logger = BridgeLogger(config={
    "log_path": "runtime/logs/my_component_logs.jsonl",
    "enable_console": True
})

error_handler = ErrorHandler(logger)

# Log an informational event
logger.log({
    "source": "My_Component",
    "status": "SUCCESS",
    "message": "Operation completed successfully",
    "data": {"operation_details": "..."}
})

# Handle errors with try/except
try:
    result = process_data(input_data)
    
    # Check for infinite loops before proceeding
    if logger.detect_infinite_loop(result):
        return error_handler.create_error_response("LOOP_DETECTED")
        
    # Track recursion for nested calls
    if not logger.track_recursion(increment=True):
        return error_handler.create_error_response("STACK_EXHAUSTION")
    
    # Process result
    final_result = further_process(result)
    
    # Decrement recursion tracker when done
    logger.track_recursion(increment=False)
    
    return final_result
    
except Exception as e:
    # Let the error handler create a standardized response
    return error_handler.handle_exception(e, context={"input_data": input_data})
```

## 5. Testing Strategy

### 5.1 Unit Tests

```python
def test_error_logging():
    # Arrange
    logger = BridgeLogger(config={"enable_console": False})
    test_error = {"errorCode": "TEST_ERROR", "message": "Test error"}
    
    # Act
    event_id = logger.log({
        "source": "Test",
        "status": "ERROR",
        "errorDetails": test_error
    }, log_level="ERROR")
    
    # Assert
    assert event_id is not None
    assert len(event_id) > 0
    
def test_infinite_loop_detection():
    # Arrange
    logger = BridgeLogger(config={"enable_console": False})
    payload = {"command": "test"}
    
    # Act
    results = []
    for i in range(10):
        results.append(logger.detect_infinite_loop(payload))
    
    # Assert
    assert results[0:4] == [False, False, False, False]
    assert True in results  # Should detect a loop after 5 repetitions
```

### 5.2 Integration Tests

Module 3 should be tested in combination with:

1. **Bridge Core**: Ensure logging properly captures bridge events
2. **Other Modules**: Verify all modules properly implement error handling patterns
3. **Auto-Recovery**: Test that excessive errors trigger recovery mechanisms

### 5.3 Validation Approach

Validation should focus on:
1. Log format compliance with the specified schema
2. Error handling behavior in various failure scenarios
3. Recovery mechanisms triggering under the right conditions
4. Performance impact of logging on overall system

## 6. Known Limitations

- **Large Payload Handling**: Payloads over 1MB are truncated in logs to prevent log file bloat
- **Error Counter Reset**: Error counters are reset on system restart, which may mask recurring issues
- **Performance Impact**: Extensive logging may impact system performance in high-throughput scenarios

## 7. Future Enhancements

- **Remote Logging**: Add capability to send logs to remote monitoring systems
- **Log Compression**: Implement on-the-fly compression for historical logs
- **Enhanced Analytics**: Add real-time analysis of error patterns
- **Predictive Recovery**: Use error patterns to predict and prevent future failures

---

*This documentation follows the Dream.OS Knowledge Sharing Protocol. This implementation serves as the reference pattern for error handling and logging across all bridge modules.* 