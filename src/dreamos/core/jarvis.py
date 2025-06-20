"""
Jarvis Client module for interacting with Jarvis AI system.
"""

from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging
import json
import aiohttp
import time

from ..utils.common_utils import get_logger


@dataclass
class JarvisRequest:
    """Represents a request to Jarvis."""
    
    request_id: str
    command: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    timestamp: datetime = field(default_factory=datetime.utcnow)
    timeout: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JarvisResponse:
    """Represents a response from Jarvis."""
    
    request_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class JarvisClient:
    """Client for interacting with Jarvis AI system."""
    
    def __init__(self, base_url: str = "http://localhost:8080", 
                 api_key: Optional[str] = None,
                 timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.logger = get_logger("JarvisClient")
        
        # Session management
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_connected = False
        
        # Request tracking
        self.pending_requests: Dict[str, JarvisRequest] = {}
        self.completed_requests: Dict[str, JarvisResponse] = {}
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0
        }
    
    async def connect(self) -> bool:
        """Connect to Jarvis server."""
        try:
            if self.session is None:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                self.session = aiohttp.ClientSession(
                    base_url=self.base_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                )
            
            # Test connection
            async with self.session.get("/health") as response:
                if response.status == 200:
                    self.is_connected = True
                    self.logger.info("Connected to Jarvis server")
                    return True
                else:
                    self.logger.error(f"Failed to connect to Jarvis server: {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error connecting to Jarvis server: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Jarvis server."""
        if self.session:
            await self.session.close()
            self.session = None
        
        self.is_connected = False
        self.logger.info("Disconnected from Jarvis server")
    
    async def send_command(self, command: str, parameters: Optional[Dict[str, Any]] = None,
                          timeout: Optional[int] = None) -> JarvisResponse:
        """Send a command to Jarvis."""
        if not self.is_connected:
            await self.connect()
        
        request_id = f"req_{int(time.time() * 1000)}"
        request = JarvisRequest(
            request_id=request_id,
            command=command,
            parameters=parameters or {},
            timeout=timeout or self.timeout
        )
        
        self.pending_requests[request_id] = request
        self.stats["total_requests"] += 1
        
        try:
            start_time = time.time()
            
            # Prepare request data
            request_data = {
                "command": command,
                "parameters": parameters or {},
                "request_id": request_id
            }
            
            # Send request
            async with self.session.post("/api/command", json=request_data) as response:
                response_data = await response.json()
                
                execution_time = time.time() - start_time
                
                if response.status == 200:
                    result = JarvisResponse(
                        request_id=request_id,
                        success=True,
                        result=response_data.get("result"),
                        execution_time=execution_time,
                        metadata=response_data.get("metadata", {})
                    )
                    self.stats["successful_requests"] += 1
                else:
                    result = JarvisResponse(
                        request_id=request_id,
                        success=False,
                        error=response_data.get("error", "Unknown error"),
                        execution_time=execution_time
                    )
                    self.stats["failed_requests"] += 1
                
                # Update average response time
                self._update_average_response_time(execution_time)
                
                # Store completed request
                self.completed_requests[request_id] = result
                del self.pending_requests[request_id]
                
                self.logger.info(f"Command '{command}' completed in {execution_time:.2f}s")
                return result
                
        except Exception as e:
            execution_time = time.time() - start_time
            result = JarvisResponse(
                request_id=request_id,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
            
            self.stats["failed_requests"] += 1
            self.completed_requests[request_id] = result
            del self.pending_requests[request_id]
            
            self.logger.error(f"Command '{command}' failed: {e}")
            return result
    
    async def send_async_command(self, command: str, parameters: Optional[Dict[str, Any]] = None,
                                callback: Optional[Callable] = None) -> str:
        """Send a command asynchronously with optional callback."""
        request_id = f"async_{int(time.time() * 1000)}"
        request = JarvisRequest(
            request_id=request_id,
            command=command,
            parameters=parameters or {}
        )
        
        self.pending_requests[request_id] = request
        self.stats["total_requests"] += 1
        
        # Create background task
        asyncio.create_task(self._execute_async_command(request_id, callback))
        
        return request_id
    
    async def _execute_async_command(self, request_id: str, callback: Optional[Callable] = None):
        """Execute an async command."""
        request = self.pending_requests[request_id]
        
        try:
            result = await self.send_command(request.command, request.parameters)
            
            # Call callback if provided
            if callback:
                await callback(result)
                
        except Exception as e:
            self.logger.error(f"Async command {request_id} failed: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get Jarvis system status."""
        if not self.is_connected:
            return {"status": "disconnected"}
        
        try:
            async with self.session.get("/api/status") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"status": "error", "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_capabilities(self) -> List[str]:
        """Get available Jarvis capabilities."""
        if not self.is_connected:
            return []
        
        try:
            async with self.session.get("/api/capabilities") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("capabilities", [])
                else:
                    return []
        except Exception as e:
            self.logger.error(f"Error getting capabilities: {e}")
            return []
    
    async def execute_workflow(self, workflow_name: str, 
                             parameters: Optional[Dict[str, Any]] = None) -> JarvisResponse:
        """Execute a Jarvis workflow."""
        return await self.send_command("execute_workflow", {
            "workflow": workflow_name,
            "parameters": parameters or {}
        })
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get status of a running workflow."""
        if not self.is_connected:
            return {"status": "disconnected"}
        
        try:
            async with self.session.get(f"/api/workflow/{workflow_id}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"status": "error", "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        if not self.is_connected:
            return False
        
        try:
            async with self.session.delete(f"/api/workflow/{workflow_id}") as response:
                return response.status == 200
        except Exception as e:
            self.logger.error(f"Error canceling workflow {workflow_id}: {e}")
            return False
    
    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific request."""
        if request_id in self.pending_requests:
            request = self.pending_requests[request_id]
            return {
                "status": "pending",
                "command": request.command,
                "timestamp": request.timestamp.isoformat()
            }
        elif request_id in self.completed_requests:
            response = self.completed_requests[request_id]
            return {
                "status": "completed",
                "success": response.success,
                "timestamp": response.timestamp.isoformat(),
                "execution_time": response.execution_time
            }
        else:
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "connection_status": "connected" if self.is_connected else "disconnected",
            "pending_requests": len(self.pending_requests),
            "completed_requests": len(self.completed_requests),
            "statistics": self.stats.copy(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _update_average_response_time(self, execution_time: float):
        """Update average response time statistic."""
        total_requests = self.stats["successful_requests"] + self.stats["failed_requests"]
        if total_requests > 0:
            current_avg = self.stats["average_response_time"]
            self.stats["average_response_time"] = (
                (current_avg * (total_requests - 1) + execution_time) / total_requests
            )
    
    async def health_check(self) -> bool:
        """Perform a health check on the Jarvis connection."""
        try:
            status = await self.get_status()
            return status.get("status") == "healthy"
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    async def reconnect(self) -> bool:
        """Reconnect to Jarvis server."""
        self.logger.info("Attempting to reconnect to Jarvis server")
        await self.disconnect()
        return await self.connect()
    
    def clear_history(self):
        """Clear request history."""
        self.pending_requests.clear()
        self.completed_requests.clear()
        self.logger.info("Cleared request history")


class JarvisManager:
    """Manager for multiple Jarvis connections."""
    
    def __init__(self):
        self.clients: Dict[str, JarvisClient] = {}
        self.logger = get_logger("JarvisManager")
    
    async def add_client(self, name: str, base_url: str, 
                        api_key: Optional[str] = None) -> bool:
        """Add a new Jarvis client."""
        try:
            client = JarvisClient(base_url, api_key)
            if await client.connect():
                self.clients[name] = client
                self.logger.info(f"Added Jarvis client: {name}")
                return True
            else:
                self.logger.error(f"Failed to connect Jarvis client: {name}")
                return False
        except Exception as e:
            self.logger.error(f"Error adding Jarvis client {name}: {e}")
            return False
    
    def get_client(self, name: str) -> Optional[JarvisClient]:
        """Get a Jarvis client by name."""
        return self.clients.get(name)
    
    async def remove_client(self, name: str) -> bool:
        """Remove a Jarvis client."""
        if name in self.clients:
            client = self.clients[name]
            await client.disconnect()
            del self.clients[name]
            self.logger.info(f"Removed Jarvis client: {name}")
            return True
        return False
    
    async def send_command_to_all(self, command: str, 
                                 parameters: Optional[Dict[str, Any]] = None) -> Dict[str, JarvisResponse]:
        """Send a command to all connected clients."""
        results = {}
        
        for name, client in self.clients.items():
            try:
                result = await client.send_command(command, parameters)
                results[name] = result
            except Exception as e:
                self.logger.error(f"Error sending command to {name}: {e}")
                results[name] = JarvisResponse(
                    request_id="",
                    success=False,
                    error=str(e)
                )
        
        return results
    
    def get_all_statistics(self) -> Dict[str, Any]:
        """Get statistics from all clients."""
        stats = {}
        for name, client in self.clients.items():
            stats[name] = client.get_statistics()
        return stats
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Perform health check on all clients."""
        results = {}
        for name, client in self.clients.items():
            results[name] = await client.health_check()
        return results 