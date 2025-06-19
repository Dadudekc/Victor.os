# Module 1: Injector

**Component Name:** Bridge Module 1 - Injector  
**Version:** 0.9.0  
**Author:** Agent-4 (Integration Specialist)  
**Created:** 2025-05-21  
**Status:** IN_PROGRESS  
**Dependencies:** Module 3 - Logging & Error Handling Layer  

## 1. Overview

The Injector module serves as the primary entry point for external commands into the Dream.OS bridge system. It handles validation, normalization, and routing of incoming requests to appropriate processing modules. The Injector implements the standardized error handling and logging patterns established by Module 3 to ensure operational stability and fault tolerance.

## 2. Interface Definition

### 2.1 Input

```python
# Main entry point for external commands
def process_command(command_data: dict) -> dict:
    """
    Process an incoming command by validating, normalizing, and routing to the appropriate handler
    
    Args:
        command_data: Dictionary containing command information with these required fields:
            - command_type: The type of command to execute
            - payload: The command-specific payload
            - source: The source of the command
            - metadata: Additional command metadata
        
    Returns:
        Dictionary containing the command response
    """
    pass

# Health check endpoint
def health_check() -> dict:
    """
    Return health status of the Injector module
    
    Returns:
        Dictionary containing health status information
    """
    pass
```

### 2.2 Output

```python
# Standard successful response format
{
    "status": "success",
    "command_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "result": {
        "message": "Command processed successfully",
        "data": { ... }  # Command-specific result data
    },
    "metadata": {
        "processing_time_ms": 127,
        "source_module": "injector",
        "destination_module": "bridge_core"
    }
}

# Standard health check response
{
    "status": "healthy",
    "version": "0.9.0",
    "uptime_seconds": 3600,
    "stats": {
        "commands_processed": 127,
        "success_rate": 0.98,
        "average_processing_time_ms": 135
    }
}
```

### 2.3 Error Handling

```python
# Example of error handling pattern (using Module 3 patterns)
try:
    # Validate the command data against schema
    validation_result = validate_command_data(command_data)
    
    if not validation_result["is_valid"]:
        # Log validation failure
        logger.log({
            "source": "Bridge_Injector",
            "status": "ERROR",
            "payload": command_data,
            "message": "Command validation failed.",
            "errorDetails": {
                "errorCode": "INVALID_COMMAND",
                "errorMessage": validation_result["error_message"]
            }
        }, log_level="ERROR")
        
        # Return standardized error response
        return {
            "status": "error",
            "error": {
                "code": "INVALID_COMMAND",
                "message": validation_result["error_message"],
                "details": {
                    "validation_errors": validation_result["errors"],
                    "received_command": command_data
                }
            }
        }
        
    # Process the command...
    
except Exception as e:
    # Use error handler from Module 3
    return error_handler.handle_exception(e, context={"command_data": command_data})
```

## 3. Implementation Details

### 3.1 Core Logic

```python
class BridgeInjector:
    def __init__(self, config):
        # Initialize configuration
        self.config = config
        
        # Initialize logger from Module 3
        self.logger = BridgeLogger(config.get('logger_config', {}))
        
        # Initialize error handler from Module 3
        self.error_handler = ErrorHandler(self.logger)
        
        # Initialize command validators
        self.validators = self._initialize_validators()
        
        # Initialize command routers
        self.routers = self._initialize_routers()
        
        # Initialize telemetry (if Module 2 is available)
        self.telemetry = self._initialize_telemetry()
        
        # Statistics tracking
        self.stats = {
            "commands_processed": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "start_time": time.time()
        }
    
    def process_command(self, command_data):
        try:
            # Start timing
            start_time = time.time()
            
            # Generate command ID if not provided
            if "command_id" not in command_data:
                command_data["command_id"] = str(uuid.uuid4())
                
            # Log command receipt
            self.logger.log({
                "source": "Bridge_Injector",
                "status": "INFO",
                "message": f"Received command: {command_data.get('command_type', 'UNKNOWN')}",
                "payload": {"command_id": command_data["command_id"]}
            })
            
            # Validate command
            command_type = command_data.get("command_type")
            if not command_type:
                return self.error_handler.create_error_response(
                    "MISSING_COMMAND_TYPE",
                    "Command type not specified"
                )
                
            validator = self.validators.get(command_type, self.validators.get("default"))
            validation_result = validator(command_data)
            
            if not validation_result["is_valid"]:
                return self.error_handler.create_error_response(
                    "INVALID_COMMAND",
                    validation_result["error_message"],
                    {"validation_errors": validation_result["errors"]}
                )
                
            # Check for infinite loops before proceeding
            if self.logger.detect_infinite_loop(command_data):
                return self.error_handler.create_error_response(
                    "LOOP_DETECTED",
                    "Command appears to be in an infinite loop"
                )
                
            # Track recursion for nested calls
            if not self.logger.track_recursion(increment=True):
                return self.error_handler.create_error_response(
                    "STACK_EXHAUSTION",
                    "Maximum command processing depth reached"
                )
            
            # Route command to appropriate handler
            router = self.routers.get(command_type, self.routers.get("default"))
            result = router(command_data)
            
            # Decrement recursion tracker
            self.logger.track_recursion(increment=False)
            
            # Update statistics
            self.stats["commands_processed"] += 1
            if result.get("status") == "success":
                self.stats["successful_commands"] += 1
            else:
                self.stats["failed_commands"] += 1
                
            # Add metadata
            result["metadata"] = {
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "source_module": "injector",
                "command_id": command_data["command_id"]
            }
            
            return result
            
        except Exception as e:
            # Handle unexpected errors
            return self.error_handler.handle_exception(e, context={"command_data": command_data})
```

### 3.2 Key Components

- **Command Validators**: Schema-based validation for all incoming commands
- **Command Routers**: Map command types to appropriate handlers
- **Telemetry Integration**: Optional integration with Module 2 for telemetry
- **Health Monitoring**: Self-monitoring capabilities
- **Rate Limiting**: Protection against command flooding
- **Schema Registry**: Centralized schema storage for validation

### 3.3 Data Flow

1. Command received from external source
2. Command validated against schema
3. Command checked for infinite loops and recursion limits
4. Command routed to appropriate handler
5. Result processed and returned
6. Statistics updated

## 4. Integration Points

### 4.1 Dependencies

| Component | Version | Purpose | Owner |
|-----------|---------|---------|-------|
| Module 3 - Logging & Error Handling | v1.0.0 | Provides logging and error handling | Agent-5 |
| Module 2 - Telemetry | v0.9.0 (Optional) | Provides telemetry capabilities | Agent-4 |

### 4.2 Required Services

- **Bridge Core**: For command execution
- **Schema Registry**: For validation schemas
- **Rate Limiter**: For command rate limiting

### 4.3 Integration Example

```python
# Example showing how to integrate with the Injector module
from bridge.module1 import BridgeInjector

# Initialize
injector = BridgeInjector(config={
    'logger_config': {
        'log_path': 'runtime/logs/injector_logs.jsonl',
        'enable_console': True
    }
})

# Process a command
command_data = {
    'command_type': 'EXECUTE_TASK',
    'payload': {
        'task_id': '12345',
        'parameters': {
            'param1': 'value1',
            'param2': 'value2'
        }
    },
    'source': 'web_ui',
    'metadata': {
        'user_id': 'user_123',
        'session_id': 'session_456'
    }
}

result = injector.process_command(command_data)

# Handle result
if result["status"] == "success":
    # Handle success case
    print(f"Command executed successfully: {result['result']}")
else:
    # Handle error case
    print(f"Command failed: {result['error']['message']}")
```

## 5. Testing Strategy

### 5.1 Unit Tests

```python
# Example unit test for command validation
def test_command_validation():
    # Arrange
    injector = BridgeInjector(config={'logger_config': {'enable_console': False}})
    valid_command = {
        'command_type': 'EXECUTE_TASK',
        'payload': {'task_id': '12345'},
        'source': 'test'
    }
    invalid_command = {
        'command_type': 'EXECUTE_TASK',
        # Missing required payload
        'source': 'test'
    }
    
    # Act
    valid_result = injector.process_command(valid_command)
    invalid_result = injector.process_command(invalid_command)
    
    # Assert
    assert valid_result["status"] == "success"
    assert invalid_result["status"] == "error"
    assert invalid_result["error"]["code"] == "INVALID_COMMAND"
```

### 5.2 Integration Tests

The Injector module should be tested in combination with:

1. **Module 3**: Ensure logging and error handling work properly
2. **Module 2** (if available): Verify telemetry data collection
3. **Bridge Core**: Test end-to-end command processing

### 5.3 Validation Approach

Validation should focus on:
1. Command validation accuracy
2. Error handling completeness
3. Performance under load
4. Correct routing of commands
5. Infinite loop detection

## 6. Known Limitations

- **Complex Commands**: Commands with deeply nested structures may have validation performance impacts
- **Custom Validators**: Adding custom validators requires code changes rather than configuration
- **Synchronous Processing**: Currently processes commands synchronously; asynchronous processing planned for future

## 7. Future Enhancements

- **Asynchronous Processing**: Add support for asynchronous command processing
- **Command Prioritization**: Implement priority queues for command processing
- **Enhanced Validation**: Support for more complex validation rules
- **Distributed Operation**: Support for operating across multiple nodes

---

*This documentation follows the Dream.OS Knowledge Sharing Protocol. This implementation follows the error handling and logging patterns established by Module 3.* 