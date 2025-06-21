"""
Victor.os API Gateway System
Phase 3: Integration Ecosystem - API gateway for external integrations
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import structlog
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pydantic import BaseModel, ValidationError
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
logger = structlog.get_logger("api_gateway")

class APIVersion(Enum):
    """API version enumeration"""
    V1 = "v1"
    V2 = "v2"
    BETA = "beta"

class EndpointType(Enum):
    """API endpoint types"""
    REST = "rest"
    GRAPHQL = "graphql"
    WEBSOCKET = "websocket"
    GRPC = "grpc"

@dataclass
class APIEndpoint:
    """API endpoint configuration"""
    path: str
    method: str
    handler: Callable
    version: APIVersion
    endpoint_type: EndpointType
    rate_limit: Optional[int] = None
    authentication_required: bool = True
    description: str = ""
    tags: List[str] = None

@dataclass
class APIMetrics:
    """API metrics for monitoring"""
    endpoint: str
    method: str
    request_count: int
    response_time_avg: float
    error_count: int
    last_request_time: float
    success_rate: float

class APIRequest(BaseModel):
    """Base API request model"""
    request_id: str
    timestamp: float
    method: str
    path: str
    headers: Dict[str, str]
    body: Optional[Dict[str, Any]] = None

class APIResponse(BaseModel):
    """Base API response model"""
    request_id: str
    timestamp: float
    status_code: int
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

class APIGateway:
    """API Gateway for Victor.os external integrations"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.app = FastAPI(
            title="Victor.os API Gateway",
            description="API Gateway for Victor.os external integrations",
            version="1.0.0",
            docs_url="/docs" if self.config["enable_docs"] else None,
            redoc_url="/redoc" if self.config["enable_docs"] else None
        )
        
        # Setup middleware
        self._setup_middleware()
        
        # API state
        self.endpoints: Dict[str, APIEndpoint] = {}
        self.metrics: Dict[str, APIMetrics] = {}
        self.rate_limiters: Dict[str, Any] = {}
        self.authentication_handlers: Dict[str, Callable] = {}
        
        # Setup security
        self.security = HTTPBearer()
        
        # Register default endpoints
        self._register_default_endpoints()
        
        # Start metrics collection
        self._start_metrics_collection()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for API gateway"""
        return {
            "host": "0.0.0.0",
            "port": 8000,
            "enable_docs": True,
            "enable_cors": True,
            "cors_origins": ["*"],
            "trusted_hosts": ["*"],
            "rate_limiting": True,
            "default_rate_limit": 100,  # requests per minute
            "authentication": True,
            "api_keys": {},
            "request_logging": True,
            "response_logging": True,
            "metrics_collection": True,
            "health_check_interval": 30,
            "max_request_size": 10 * 1024 * 1024,  # 10MB
            "request_timeout": 30,
            "enable_compression": True,
            "enable_cache": True,
            "cache_ttl": 300,  # 5 minutes
        }
    
    def _setup_middleware(self):
        """Setup API gateway middleware"""
        # CORS middleware
        if self.config["enable_cors"]:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config["cors_origins"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        
        # Trusted hosts middleware
        self.app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=self.config["trusted_hosts"]
        )
        
        # Custom middleware for metrics and logging
        self.app.middleware("http")(self._request_middleware)
    
    async def _request_middleware(self, request: Request, call_next):
        """Custom middleware for request processing"""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log request
        if self.config["request_logging"]:
            await self._log_request(request, request_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Update metrics
            await self._update_metrics(request, response, response_time)
            
            # Log response
            if self.config["response_logging"]:
                await self._log_response(request, response, response_time)
            
            # Add response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = str(response_time)
            
            return response
            
        except Exception as e:
            # Handle errors
            logger.error("Request processing error", 
                        request_id=request_id,
                        error=str(e))
            
            # Update error metrics
            await self._update_error_metrics(request)
            
            # Return error response
            return Response(
                content=json.dumps({"error": "Internal server error"}),
                status_code=500,
                media_type="application/json"
            )
    
    async def _log_request(self, request: Request, request_id: str):
        """Log incoming request"""
        try:
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.json()
                except:
                    body = await request.body()
            
            log_data = {
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "body": body,
                "timestamp": time.time()
            }
            
            logger.info("API Request", **log_data)
            
        except Exception as e:
            logger.error("Failed to log request", error=str(e))
    
    async def _log_response(self, request: Request, response: Response, response_time: float):
        """Log outgoing response"""
        try:
            log_data = {
                "request_id": getattr(request.state, 'request_id', 'unknown'),
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "response_time": response_time,
                "timestamp": time.time()
            }
            
            logger.info("API Response", **log_data)
            
        except Exception as e:
            logger.error("Failed to log response", error=str(e))
    
    async def _update_metrics(self, request: Request, response: Response, response_time: float):
        """Update API metrics"""
        try:
            endpoint_key = f"{request.method}:{request.url.path}"
            
            if endpoint_key not in self.metrics:
                self.metrics[endpoint_key] = APIMetrics(
                    endpoint=request.url.path,
                    method=request.method,
                    request_count=0,
                    response_time_avg=0.0,
                    error_count=0,
                    last_request_time=0.0,
                    success_rate=1.0
                )
            
            metrics = self.metrics[endpoint_key]
            metrics.request_count += 1
            metrics.last_request_time = time.time()
            
            # Update average response time
            total_time = metrics.response_time_avg * (metrics.request_count - 1) + response_time
            metrics.response_time_avg = total_time / metrics.request_count
            
            # Update success rate
            if response.status_code >= 400:
                metrics.error_count += 1
            
            metrics.success_rate = 1.0 - (metrics.error_count / metrics.request_count)
            
        except Exception as e:
            logger.error("Failed to update metrics", error=str(e))
    
    async def _update_error_metrics(self, request: Request):
        """Update error metrics"""
        try:
            endpoint_key = f"{request.method}:{request.url.path}"
            
            if endpoint_key in self.metrics:
                self.metrics[endpoint_key].error_count += 1
                self.metrics[endpoint_key].last_request_time = time.time()
                
        except Exception as e:
            logger.error("Failed to update error metrics", error=str(e))
    
    def _register_default_endpoints(self):
        """Register default API endpoints"""
        # Health check endpoint
        self.register_endpoint(
            path="/health",
            method="GET",
            handler=self._health_check,
            version=APIVersion.V1,
            endpoint_type=EndpointType.REST,
            authentication_required=False,
            description="Health check endpoint"
        )
        
        # Metrics endpoint
        self.register_endpoint(
            path="/metrics",
            method="GET",
            handler=self._get_metrics,
            version=APIVersion.V1,
            endpoint_type=EndpointType.REST,
            description="API metrics endpoint"
        )
        
        # Status endpoint
        self.register_endpoint(
            path="/status",
            method="GET",
            handler=self._get_status,
            version=APIVersion.V1,
            endpoint_type=EndpointType.REST,
            description="API gateway status"
        )
        
        # Agent endpoints
        self.register_endpoint(
            path="/agents",
            method="GET",
            handler=self._list_agents,
            version=APIVersion.V1,
            endpoint_type=EndpointType.REST,
            description="List all agents"
        )
        
        self.register_endpoint(
            path="/agents/{agent_id}",
            method="GET",
            handler=self._get_agent,
            version=APIVersion.V1,
            endpoint_type=EndpointType.REST,
            description="Get agent details"
        )
        
        self.register_endpoint(
            path="/agents/{agent_id}/tasks",
            method="POST",
            handler=self._create_task,
            version=APIVersion.V1,
            endpoint_type=EndpointType.REST,
            description="Create agent task"
        )
    
    def register_endpoint(self, path: str, method: str, handler: Callable, 
                         version: APIVersion, endpoint_type: EndpointType,
                         rate_limit: Optional[int] = None,
                         authentication_required: bool = True,
                         description: str = "", tags: List[str] = None):
        """Register a new API endpoint"""
        try:
            endpoint_key = f"{method}:{path}"
            
            endpoint = APIEndpoint(
                path=path,
                method=method,
                handler=handler,
                version=version,
                endpoint_type=endpoint_type,
                rate_limit=rate_limit or self.config["default_rate_limit"],
                authentication_required=authentication_required,
                description=description,
                tags=tags or []
            )
            
            self.endpoints[endpoint_key] = endpoint
            
            # Register with FastAPI
            self._register_fastapi_endpoint(endpoint)
            
            logger.info("API endpoint registered", 
                       path=path,
                       method=method,
                       version=version.value)
            
        except Exception as e:
            logger.error("Failed to register endpoint", 
                        path=path,
                        method=method,
                        error=str(e))
    
    def _register_fastapi_endpoint(self, endpoint: APIEndpoint):
        """Register endpoint with FastAPI"""
        try:
            # Create route function
            async def route_handler(request: Request, **kwargs):
                # Check authentication
                if endpoint.authentication_required:
                    await self._authenticate_request(request)
                
                # Check rate limiting
                if self.config["rate_limiting"]:
                    await self._check_rate_limit(request, endpoint)
                
                # Call handler
                return await endpoint.handler(request, **kwargs)
            
            # Register route
            if endpoint.method == "GET":
                self.app.get(endpoint.path)(route_handler)
            elif endpoint.method == "POST":
                self.app.post(endpoint.path)(route_handler)
            elif endpoint.method == "PUT":
                self.app.put(endpoint.path)(route_handler)
            elif endpoint.method == "DELETE":
                self.app.delete(endpoint.path)(route_handler)
            elif endpoint.method == "PATCH":
                self.app.patch(endpoint.path)(route_handler)
            
        except Exception as e:
            logger.error("Failed to register FastAPI endpoint", 
                        path=endpoint.path,
                        error=str(e))
    
    async def _authenticate_request(self, request: Request):
        """Authenticate API request"""
        try:
            if not self.config["authentication"]:
                return
            
            # Check for API key in headers
            api_key = request.headers.get("X-API-Key")
            if api_key and api_key in self.config["api_keys"]:
                return
            
            # Check for Bearer token
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                if token in self.config["api_keys"]:
                    return
            
            raise HTTPException(status_code=401, detail="Authentication required")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Authentication error", error=str(e))
            raise HTTPException(status_code=401, detail="Authentication failed")
    
    async def _check_rate_limit(self, request: Request, endpoint: APIEndpoint):
        """Check rate limiting for endpoint"""
        try:
            # Simplified rate limiting - in real implementation, use Redis or similar
            client_ip = request.client.host
            endpoint_key = f"{client_ip}:{endpoint.path}"
            
            current_time = time.time()
            
            # Check if client has exceeded rate limit
            if hasattr(request.app.state, 'rate_limits'):
                if endpoint_key in request.app.state.rate_limits:
                    last_request_time = request.app.state.rate_limits[endpoint_key]
                    time_diff = current_time - last_request_time
                    
                    if time_diff < (60 / endpoint.rate_limit):  # Rate limit window
                        raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            # Update rate limit tracking
            if not hasattr(request.app.state, 'rate_limits'):
                request.app.state.rate_limits = {}
            
            request.app.state.rate_limits[endpoint_key] = current_time
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Rate limiting error", error=str(e))
    
    # Default endpoint handlers
    async def _health_check(self, request: Request):
        """Health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0",
            "uptime": time.time() - getattr(self, '_start_time', time.time())
        }
    
    async def _get_metrics(self, request: Request):
        """Get API metrics"""
        return {
            "metrics": {
                endpoint: asdict(metrics) for endpoint, metrics in self.metrics.items()
            },
            "total_requests": sum(m.request_count for m in self.metrics.values()),
            "total_errors": sum(m.error_count for m in self.metrics.values()),
            "average_response_time": sum(m.response_time_avg for m in self.metrics.values()) / len(self.metrics) if self.metrics else 0
        }
    
    async def _get_status(self, request: Request):
        """Get API gateway status"""
        return {
            "status": "running",
            "endpoints": len(self.endpoints),
            "active_connections": 0,  # Would track in real implementation
            "config": {
                "rate_limiting": self.config["rate_limiting"],
                "authentication": self.config["authentication"],
                "cors_enabled": self.config["enable_cors"]
            }
        }
    
    async def _list_agents(self, request: Request):
        """List all agents"""
        # This would integrate with the agent system
        return {
            "agents": [
                {"id": "agent-1", "name": "Agent 1", "status": "active"},
                {"id": "agent-2", "name": "Agent 2", "status": "idle"}
            ],
            "total": 2
        }
    
    async def _get_agent(self, request: Request, agent_id: str):
        """Get agent details"""
        # This would integrate with the agent system
        return {
            "id": agent_id,
            "name": f"Agent {agent_id}",
            "status": "active",
            "created_at": time.time(),
            "last_activity": time.time()
        }
    
    async def _create_task(self, request: Request, agent_id: str):
        """Create agent task"""
        try:
            body = await request.json()
            
            # This would integrate with the task system
            task_id = str(uuid.uuid4())
            
            return {
                "task_id": task_id,
                "agent_id": agent_id,
                "status": "created",
                "created_at": time.time()
            }
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    async def start(self):
        """Start the API gateway server"""
        try:
            self._start_time = time.time()
            
            logger.info("Starting API Gateway", 
                       host=self.config["host"],
                       port=self.config["port"])
            
            # Start server
            uvicorn.run(
                self.app,
                host=self.config["host"],
                port=self.config["port"],
                log_level="info"
            )
            
        except Exception as e:
            logger.error("Failed to start API Gateway", error=str(e))
    
    def _start_metrics_collection(self):
        """Start background metrics collection"""
        if self.config["metrics_collection"]:
            asyncio.create_task(self._metrics_collection_loop())
    
    async def _metrics_collection_loop(self):
        """Background metrics collection loop"""
        while True:
            try:
                # Clean up old metrics
                current_time = time.time()
                for endpoint_key, metrics in list(self.metrics.items()):
                    if current_time - metrics.last_request_time > 3600:  # 1 hour
                        del self.metrics[endpoint_key]
                
                await asyncio.sleep(self.config["health_check_interval"])
                
            except Exception as e:
                logger.error("Metrics collection error", error=str(e))
                await asyncio.sleep(60)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get API gateway system status"""
        return {
            "status": "running",
            "endpoints_registered": len(self.endpoints),
            "active_metrics": len(self.metrics),
            "config": {
                "host": self.config["host"],
                "port": self.config["port"],
                "rate_limiting": self.config["rate_limiting"],
                "authentication": self.config["authentication"],
                "cors_enabled": self.config["enable_cors"],
                "docs_enabled": self.config["enable_docs"]
            },
            "endpoints": [
                {
                    "path": endpoint.path,
                    "method": endpoint.method,
                    "version": endpoint.version.value,
                    "type": endpoint.endpoint_type.value,
                    "authentication_required": endpoint.authentication_required
                }
                for endpoint in self.endpoints.values()
            ]
        } 