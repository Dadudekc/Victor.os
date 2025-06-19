# DEPRECATED: This file has been replaced by src/bridge/injector.py

"""
Bridge Injector Module
----------------------
Handles validation, normalization, and routing of incoming requests.
Implements the logging and error handling patterns from the logging module.
"""

import time
import uuid
import json
import datetime
import jsonschema
from typing import Dict, Any, Callable, Optional

# Import Module 3 components
from bridge.module3 import BridgeLogger, ErrorHandler

class BridgeInjector:
    """
    Main class for the Bridge Injector module.
    Serves as the primary entry point for external commands into the Dream.OS bridge system.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Bridge Injector with the given configuration.
        
        Args:
            config: Configuration dictionary containing logger_config and other settings
        """
        # Initialize configuration
        self.config = config
        
        # Initialize logger from Module 3
        self.logger = BridgeLogger(config.get('logger_config', {}))
        
        # Initialize error handler from Module 3
        self.error_handler = ErrorHandler(self.logger)
        
        # Load command schemas
        self.schemas = self._load_command_schemas()
        
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
        
        # Log initialization
        self.logger.log({
            "source": "Bridge_Injector",
            "status": "INFO",
            "message": "Bridge Injector initialized successfully",
            "payload": {"config": {k: v for k, v in config.items() if k != "logger_config"}}
        })
    
    def _load_command_schemas(self) -> Dict[str, Any]:
        """
        Load command validation schemas from configuration or default locations.
        
        Returns:
            Dictionary of command schemas by command type
        """
        schemas = {}
        schema_sources = self.config.get('schema_sources', ['runtime/schemas/commands'])
        
        try:
            # Default base schema for all commands
            base_schema = {
                "type": "object",
                "required": ["command_type", "source"],
                "properties": {
                    "command_type": {"type": "string"},
                    "payload": {"type": "object"},
                    "source": {"type": "string"},
                    "metadata": {"type": "object"},
                    "command_id": {"type": "string"}
                }
            }
            
            schemas["default"] = base_schema
            
            # Load specific command schemas from config or files
            if 'command_schemas' in self.config:
                for cmd_type, schema in self.config['command_schemas'].items():
                    schemas[cmd_type] = schema
            else:
                # In a real implementation, this would load from files
                # For simplicity, we're including a few example schemas here
                schemas["EXECUTE_TASK"] = {
                    "type": "object",
                    "required": ["command_type", "source", "payload"],
                    "properties": {
                        "command_type": {"type": "string", "enum": ["EXECUTE_TASK"]},
                        "payload": {
                            "type": "object",
                            "required": ["task_id"],
                            "properties": {
                                "task_id": {"type": "string"},
                                "parameters": {"type": "object"}
                            }
                        },
                        "source": {"type": "string"},
                        "metadata": {"type": "object"},
                        "command_id": {"type": "string"}
                    }
                }
                
                schemas["GET_STATUS"] = {
                    "type": "object",
                    "required": ["command_type", "source"],
                    "properties": {
                        "command_type": {"type": "string", "enum": ["GET_STATUS"]},
                        "payload": {"type": "object"},
                        "source": {"type": "string"},
                        "metadata": {"type": "object"},
                        "command_id": {"type": "string"}
                    }
                }
            
            return schemas
            
        except Exception as e:
            self.logger.log({
                "source": "Bridge_Injector",
                "status": "ERROR",
                "message": "Failed to load command schemas",
                "errorDetails": {
                    "errorCode": "SCHEMA_LOAD_FAILURE",
                    "errorMessage": str(e)
                }
            }, log_level="ERROR")
            
            # Return at least the default schema
            return {"default": base_schema}
    
    def _initialize_validators(self) -> Dict[str, Callable]:
        """
        Initialize the command validators.
        
        Returns:
            Dictionary of validator functions by command type
        """
        validators = {
            "default": lambda cmd: self._validate_command(cmd, "default")
        }
        
        # Create validators for each schema
        for cmd_type in self.schemas:
            if cmd_type != "default":
                validators[cmd_type] = lambda cmd, cmd_type=cmd_type: self._validate_command(cmd, cmd_type)
        
        return validators
    
    def _validate_command(self, command_data: Dict[str, Any], schema_key: str) -> Dict[str, Any]:
        """
        Validate a command against its schema.
        
        Args:
            command_data: The command data to validate
            schema_key: The schema key to validate against
            
        Returns:
            Validation result dictionary with is_valid, error_message, and errors
        """
        schema = self.schemas.get(schema_key, self.schemas["default"])
        
        try:
            jsonschema.validate(instance=command_data, schema=schema)
            return {
                "is_valid": True,
                "error_message": None,
                "errors": None
            }
        except jsonschema.exceptions.ValidationError as e:
            return {
                "is_valid": False,
                "error_message": str(e),
                "errors": {
                    "path": list(e.path),
                    "message": e.message,
                    "schema_path": list(e.schema_path)
                }
            }
    
    def _initialize_routers(self) -> Dict[str, Callable]:
        """
        Initialize the command routers.
        
        Returns:
            Dictionary of router functions by command type
        """
        # In a complete implementation, these would route to appropriate handlers
        # For now, we'll implement stub routers for demonstration
        def default_router(cmd):
            return {
                "status": "error",
                "error": {
                    "code": "UNKNOWN_COMMAND_TYPE",
                    "message": f"No handler for command type: {cmd.get('command_type')}"
                }
            }
        
        def execute_task_router(cmd):
            # This would normally call into the task execution system
            return {
                "status": "success",
                "command_id": cmd.get("command_id"),
                "result": {
                    "message": f"Task {cmd.get('payload', {}).get('task_id')} executed successfully",
                    "data": {
                        "execution_id": str(uuid.uuid4()),
                        "status": "COMPLETED"
                    }
                }
            }
        
        def get_status_router(cmd):
            # This would normally retrieve actual status
            return {
                "status": "success",
                "command_id": cmd.get("command_id"),
                "result": {
                    "message": "System status retrieved successfully",
                    "data": {
                        "system_status": "OPERATIONAL",
                        "metrics": {
                            "uptime_seconds": int(time.time() - self.stats["start_time"]),
                            "commands_processed": self.stats["commands_processed"]
                        }
                    }
                }
            }
        
        routers = {
            "default": default_router,
            "EXECUTE_TASK": execute_task_router,
            "GET_STATUS": get_status_router
        }
        
        # Add custom routers from config if provided
        if 'command_routers' in self.config:
            routers.update(self.config['command_routers'])
        
        return routers
    
    def _initialize_telemetry(self) -> Optional[Any]:
        """
        Initialize telemetry integration if Module 2 is available.
        
        Returns:
            Telemetry instance or None if not available
        """
        try:
            # Check if Module 2 telemetry is available
            from bridge.module2 import BridgeTelemetry
            
            telemetry_config = self.config.get('telemetry_config', {})
            telemetry = BridgeTelemetry(telemetry_config)
            
            self.logger.log({
                "source": "Bridge_Injector",
                "status": "INFO",
                "message": "Telemetry integration initialized"
            })
            
            return telemetry
            
        except ImportError:
            self.logger.log({
                "source": "Bridge_Injector",
                "status": "INFO",
                "message": "Telemetry module (Module 2) not available, continuing without telemetry"
            })
            
            return None
        except Exception as e:
            self.logger.log({
                "source": "Bridge_Injector",
                "status": "WARNING",
                "message": "Failed to initialize telemetry integration",
                "errorDetails": {
                    "errorCode": "TELEMETRY_INIT_FAILURE",
                    "errorMessage": str(e)
                }
            }, log_level="WARNING")
            
            return None
    
    def process_command(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming command by validating, normalizing, and routing to the appropriate handler.
        
        Args:
            command_data: Dictionary containing command information
            
        Returns:
            Dictionary containing the command response
        """
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
            
            # Record telemetry if available
            if self.telemetry:
                self.telemetry.record_event({
                    "event_type": "COMMAND_RECEIVED",
                    "source": "bridge_injector",
                    "data": {
                        "command_type": command_data.get("command_type"),
                        "command_id": command_data["command_id"],
                        "source": command_data.get("source")
                    }
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
            
            # Record telemetry for command completion if available
            if self.telemetry:
                self.telemetry.record_event({
                    "event_type": "COMMAND_COMPLETED",
                    "source": "bridge_injector",
                    "data": {
                        "command_type": command_data.get("command_type"),
                        "command_id": command_data["command_id"],
                        "status": result.get("status"),
                        "processing_time_ms": result["metadata"]["processing_time_ms"]
                    }
                })
                
                # Record metrics
                self.telemetry.record_metric(
                    "command_processing_time_ms",
                    result["metadata"]["processing_time_ms"],
                    context={
                        "command_type": command_data.get("command_type"),
                        "status": result.get("status")
                    }
                )
            
            # Log command completion
            self.logger.log({
                "source": "Bridge_Injector",
                "status": "INFO",
                "message": f"Command processed: {command_data.get('command_type')}",
                "payload": {
                    "command_id": command_data["command_id"],
                    "status": result.get("status"),
                    "processing_time_ms": result["metadata"]["processing_time_ms"]
                }
            })
            
            return result
            
        except Exception as e:
            # Handle unexpected errors
            error_response = self.error_handler.handle_exception(e, context={"command_data": command_data})
            
            # Record telemetry for error if available
            if hasattr(self, 'telemetry') and self.telemetry:
                self.telemetry.record_event({
                    "event_type": "COMMAND_ERROR",
                    "source": "bridge_injector",
                    "data": {
                        "command_type": command_data.get("command_type"),
                        "command_id": command_data.get("command_id", "UNKNOWN"),
                        "error_code": error_response.get("error", {}).get("code"),
                        "error_message": error_response.get("error", {}).get("message")
                    }
                })
            
            return error_response
            
    def health_check(self) -> Dict[str, Any]:
        """
        Return health status of the Injector module.
        
        Returns:
            Dictionary containing health status information
        """
        uptime_seconds = int(time.time() - self.stats["start_time"])
        total_commands = self.stats["commands_processed"]
        success_rate = 0.0 if total_commands == 0 else self.stats["successful_commands"] / total_commands
        
        return {
            "status": "healthy",
            "version": self.config.get("version", "0.9.0"),
            "uptime_seconds": uptime_seconds,
            "stats": {
                "commands_processed": total_commands,
                "success_rate": success_rate,
                "average_processing_time_ms": 0  # Would be calculated from metrics in a real implementation
            }
        }


# Module-level functions for easier usage

def process_command(command_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Process a command using the Bridge Injector.
    
    Args:
        command_data: The command to process
        config: Optional configuration for the injector
        
    Returns:
        Command processing result
    """
    # Use singleton pattern for default configuration
    global _default_injector
    
    if config is not None:
        # Create a new injector with the provided config
        injector = BridgeInjector(config)
        return injector.process_command(command_data)
    else:
        # Use or create the default injector
        if '_default_injector' not in globals():
            _default_injector = BridgeInjector({
                'logger_config': {
                    'log_path': 'runtime/logs/bridge_injector.jsonl',
                    'enable_console': True
                }
            })
        
        return _default_injector.process_command(command_data)

def health_check(config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get health status of the Bridge Injector.
    
    Args:
        config: Optional configuration for the injector
        
    Returns:
        Health status information
    """
    global _default_injector
    
    if config is not None:
        # Create a new injector with the provided config
        injector = BridgeInjector(config)
        return injector.health_check()
    else:
        # Use or create the default injector
        if '_default_injector' not in globals():
            _default_injector = BridgeInjector({
                'logger_config': {
                    'log_path': 'runtime/logs/bridge_injector.jsonl',
                    'enable_console': True
                }
            })
        
        return _default_injector.health_check() 