"""
Jarvis Core module for core Jarvis AI functionality.
"""

from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging
import json
import time

from ..utils.common_utils import get_logger


@dataclass
class JarvisCommand:
    """Represents a command to Jarvis."""
    
    command_id: str
    command_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JarvisResponse:
    """Represents a response from Jarvis."""
    
    command_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class JarvisCore:
    """Core Jarvis AI functionality."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = get_logger("JarvisCore")
        
        # Command handlers
        self.command_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
        
        # State management
        self.is_running = False
        self.command_queue: List[JarvisCommand] = []
        self.response_history: List[JarvisResponse] = []
        
        # Statistics
        self.stats = {
            "commands_processed": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "average_response_time": 0.0
        }
    
    def _register_default_handlers(self):
        """Register default command handlers."""
        self.register_handler("echo", self._handle_echo)
        self.register_handler("status", self._handle_status)
        self.register_handler("help", self._handle_help)
        self.register_handler("system_info", self._handle_system_info)
        self.register_handler("process_data", self._handle_process_data)
        self.register_handler("analyze", self._handle_analyze)
    
    def register_handler(self, command_type: str, handler: Callable):
        """Register a command handler."""
        self.command_handlers[command_type] = handler
        self.logger.info(f"Registered handler for command type: {command_type}")
    
    async def process_command(self, command: JarvisCommand) -> JarvisResponse:
        """Process a Jarvis command."""
        start_time = time.time()
        
        try:
            self.logger.info(f"Processing command: {command.command_type}")
            
            # Get handler
            handler = self.command_handlers.get(command.command_type)
            if not handler:
                raise ValueError(f"Unknown command type: {command.command_type}")
            
            # Execute handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler(command.parameters)
            else:
                result = handler(command.parameters)
            
            # Create response
            execution_time = time.time() - start_time
            response = JarvisResponse(
                command_id=command.command_id,
                success=True,
                result=result,
                execution_time=execution_time
            )
            
            self.stats["successful_commands"] += 1
            self._update_average_response_time(execution_time)
            
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            response = JarvisResponse(
                command_id=command.command_id,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
            
            self.stats["failed_commands"] += 1
            self.logger.error(f"Command failed: {e}")
            
            return response
        finally:
            self.stats["commands_processed"] += 1
            self.response_history.append(response)
    
    def _handle_echo(self, parameters: Dict[str, Any]) -> str:
        """Handle echo command."""
        message = parameters.get("message", "Hello from Jarvis!")
        return f"Echo: {message}"
    
    def _handle_status(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status command."""
        return {
            "status": "operational",
            "uptime": time.time(),
            "stats": self.stats.copy(),
            "queue_size": len(self.command_queue),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _handle_help(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle help command."""
        return {
            "available_commands": list(self.command_handlers.keys()),
            "description": "Jarvis Core - AI Assistant",
            "version": "1.0.0"
        }
    
    def _handle_system_info(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system info command."""
        import platform
        import psutil
        
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage('/').percent
        }
    
    def _handle_process_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data processing command."""
        data = parameters.get("data", [])
        operation = parameters.get("operation", "count")
        
        if operation == "count":
            result = len(data)
        elif operation == "sum":
            result = sum(data) if all(isinstance(x, (int, float)) for x in data) else "Invalid data type"
        elif operation == "average":
            if all(isinstance(x, (int, float)) for x in data):
                result = sum(data) / len(data) if data else 0
            else:
                result = "Invalid data type"
        else:
            result = "Unknown operation"
        
        return {
            "operation": operation,
            "input_size": len(data),
            "result": result
        }
    
    def _handle_analyze(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analysis command."""
        text = parameters.get("text", "")
        
        # Simple text analysis
        word_count = len(text.split())
        char_count = len(text)
        sentence_count = text.count('.') + text.count('!') + text.count('?')
        
        return {
            "word_count": word_count,
            "character_count": char_count,
            "sentence_count": sentence_count,
            "average_word_length": char_count / word_count if word_count > 0 else 0
        }
    
    def _update_average_response_time(self, execution_time: float):
        """Update average response time statistic."""
        total_commands = self.stats["successful_commands"] + self.stats["failed_commands"]
        if total_commands > 0:
            current_avg = self.stats["average_response_time"]
            self.stats["average_response_time"] = (
                (current_avg * (total_commands - 1) + execution_time) / total_commands
            )
    
    async def add_command(self, command_type: str, parameters: Dict[str, Any] = None,
                         priority: int = 1, source: Optional[str] = None) -> str:
        """Add a command to the queue."""
        import uuid
        
        command_id = str(uuid.uuid4())
        command = JarvisCommand(
            command_id=command_id,
            command_type=command_type,
            parameters=parameters or {},
            priority=priority,
            source=source
        )
        
        self.command_queue.append(command)
        self.logger.info(f"Added command {command_id} to queue")
        
        return command_id
    
    async def get_command_status(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific command."""
        # Check if command is in queue
        for command in self.command_queue:
            if command.command_id == command_id:
                return {
                    "status": "queued",
                    "command_type": command.command_type,
                    "timestamp": command.timestamp.isoformat()
                }
        
        # Check response history
        for response in self.response_history:
            if response.command_id == command_id:
                return {
                    "status": "completed",
                    "success": response.success,
                    "execution_time": response.execution_time,
                    "timestamp": response.timestamp.isoformat()
                }
        
        return None
    
    async def run(self):
        """Main Jarvis core loop."""
        self.logger.info("Starting Jarvis Core")
        self.is_running = True
        
        while self.is_running:
            try:
                # Process commands in queue
                if self.command_queue:
                    # Sort by priority (higher priority first)
                    self.command_queue.sort(key=lambda x: x.priority, reverse=True)
                    command = self.command_queue.pop(0)
                    
                    response = await self.process_command(command)
                    self.logger.info(f"Processed command {command.command_id}")
                
                # Sleep to prevent busy waiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in Jarvis core loop: {e}")
                await asyncio.sleep(1)
    
    def stop(self):
        """Stop Jarvis core."""
        self.logger.info("Stopping Jarvis Core")
        self.is_running = False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get Jarvis core statistics."""
        return {
            "status": "running" if self.is_running else "stopped",
            "statistics": self.stats.copy(),
            "queue_size": len(self.command_queue),
            "response_history_size": len(self.response_history),
            "available_commands": list(self.command_handlers.keys()),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def clear_history(self):
        """Clear response history."""
        self.response_history.clear()
        self.logger.info("Response history cleared")
    
    def get_recent_responses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent responses."""
        recent = self.response_history[-limit:] if self.response_history else []
        return [
            {
                "command_id": response.command_id,
                "success": response.success,
                "execution_time": response.execution_time,
                "timestamp": response.timestamp.isoformat()
            }
            for response in recent
        ] 