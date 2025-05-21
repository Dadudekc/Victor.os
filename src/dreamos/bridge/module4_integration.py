"""
Dream.OS Bridge Integration Module

This module handles the integration between the Cursor Agent Bridge and external systems.
It provides authentication, data transformation, and secure communication capabilities.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime, timedelta
import hashlib
import hmac
import base64
import aiohttp
import websockets
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from collections import deque, defaultdict
import jsonschema
from prometheus_client import Counter, Histogram, Gauge, start_http_server

logger = logging.getLogger(__name__)

# Prometheus metrics
MESSAGE_SENT = Counter(
    'bridge_message_sent_total',
    'Total number of messages sent',
    ['system_id', 'status']
)

MESSAGE_RECEIVED = Counter(
    'bridge_message_received_total',
    'Total number of messages received',
    ['system_id', 'status']
)

MESSAGE_LATENCY = Histogram(
    'bridge_message_latency_seconds',
    'Message processing latency in seconds',
    ['system_id', 'operation']
)

QUEUE_SIZE = Gauge(
    'bridge_queue_size',
    'Current size of message queue',
    ['system_id']
)

ACTIVE_CONNECTIONS = Gauge(
    'bridge_active_connections',
    'Number of active connections',
    ['system_id', 'transport_type']
)

@dataclass
class QueuedMessage:
    """Represents a message in the queue with retry information."""
    message: Dict[str, Any]
    system_id: str
    timestamp: datetime
    retry_count: int = 0
    last_attempt: Optional[datetime] = None
    next_retry: Optional[datetime] = None

class MessageQueue:
    """Manages message queuing and retry logic."""
    
    def __init__(self, max_retries: int = 3, retry_delay: int = 5):
        self.queue: deque[QueuedMessage] = deque()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._lock = asyncio.Lock()
        
    async def add_message(self, message: Dict[str, Any], system_id: str) -> None:
        """Add a message to the queue."""
        async with self._lock:
            queued = QueuedMessage(
                message=message,
                system_id=system_id,
                timestamp=datetime.utcnow()
            )
            self.queue.append(queued)
            logger.info(f"Message queued for system {system_id}")
            
    async def get_next_message(self) -> Optional[QueuedMessage]:
        """Get the next message to process."""
        async with self._lock:
            if not self.queue:
                return None
                
            now = datetime.utcnow()
            for i, msg in enumerate(self.queue):
                if msg.next_retry is None or msg.next_retry <= now:
                    return msg
            return None
            
    async def mark_failed(self, message: QueuedMessage) -> bool:
        """Mark a message as failed and schedule retry if possible."""
        async with self._lock:
            message.retry_count += 1
            message.last_attempt = datetime.utcnow()
            
            if message.retry_count >= self.max_retries:
                logger.error(f"Message failed after {self.max_retries} retries")
                self.queue.remove(message)
                return False
                
            # Exponential backoff
            delay = self.retry_delay * (2 ** (message.retry_count - 1))
            message.next_retry = datetime.utcnow() + timedelta(seconds=delay)
            logger.info(f"Scheduled retry {message.retry_count} in {delay} seconds")
            return True
            
    async def mark_success(self, message: QueuedMessage) -> None:
        """Mark a message as successfully delivered."""
        async with self._lock:
            self.queue.remove(message)
            logger.info(f"Message successfully delivered to system {message.system_id}")

class Transport(ABC):
    """Abstract base class for transport mechanisms."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the external system."""
        pass
        
    @abstractmethod
    async def disconnect(self) -> bool:
        """Close connection to the external system."""
        pass
        
    @abstractmethod
    async def send(self, message: Dict[str, Any]) -> bool:
        """Send a message to the external system."""
        pass
        
    @abstractmethod
    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive a message from the external system."""
        pass

class WebSocketTransport(Transport):
    """WebSocket-based transport implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.websocket = None
        self.connected = False
        
    async def connect(self) -> bool:
        """Establish WebSocket connection."""
        try:
            self.websocket = await websockets.connect(
                self.config['endpoint'],
                ping_interval=30,
                ping_timeout=10
            )
            self.connected = True
            logger.info(f"WebSocket connection established to {self.config['endpoint']}")
            return True
        except Exception as e:
            logger.error(f"WebSocket connection failed: {str(e)}")
            return False
            
    async def disconnect(self) -> bool:
        """Close WebSocket connection."""
        try:
            if self.websocket:
                await self.websocket.close()
                self.connected = False
                logger.info("WebSocket connection closed")
            return True
        except Exception as e:
            logger.error(f"WebSocket disconnection failed: {str(e)}")
            return False
            
    async def send(self, message: Dict[str, Any]) -> bool:
        """Send message via WebSocket."""
        if not self.connected:
            if not await self.connect():
                return False
                
        try:
            await self.websocket.send(json.dumps(message))
            logger.info("Message sent via WebSocket")
            return True
        except Exception as e:
            logger.error(f"WebSocket send failed: {str(e)}")
            self.connected = False
            return False
            
    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive message via WebSocket."""
        if not self.connected:
            if not await self.connect():
                return None
                
        try:
            message = await self.websocket.recv()
            return json.loads(message)
        except Exception as e:
            logger.error(f"WebSocket receive failed: {str(e)}")
            self.connected = False
            return None

class HTTPTransport(Transport):
    """HTTP-based transport implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.session = None
        self.connected = False
        
    async def connect(self) -> bool:
        """Establish HTTP session."""
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config['timeout'])
            )
            self.connected = True
            logger.info(f"HTTP session established for {self.config['base_url']}")
            return True
        except Exception as e:
            logger.error(f"HTTP session creation failed: {str(e)}")
            return False
            
    async def disconnect(self) -> bool:
        """Close HTTP session."""
        try:
            if self.session:
                await self.session.close()
                self.connected = False
                logger.info("HTTP session closed")
            return True
        except Exception as e:
            logger.error(f"HTTP session closure failed: {str(e)}")
            return False
            
    async def send(self, message: Dict[str, Any]) -> bool:
        """Send message via HTTP."""
        if not self.connected:
            if not await self.connect():
                return False
                
        try:
            async with self.session.post(
                self.config['base_url'],
                json=message,
                timeout=self.config['timeout']
            ) as response:
                success = response.status == 200
                if success:
                    logger.info("Message sent via HTTP")
                else:
                    logger.error(f"HTTP send failed with status {response.status}")
                return success
        except Exception as e:
            logger.error(f"HTTP send failed: {str(e)}")
            self.connected = False
            return False
            
    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive message via HTTP (long polling)."""
        if not self.connected:
            if not await self.connect():
                return None
                
        try:
            async with self.session.get(
                f"{self.config['base_url']}/messages",
                timeout=self.config['timeout']
            ) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"HTTP receive failed with status {response.status}")
                return None
        except Exception as e:
            logger.error(f"HTTP receive failed: {str(e)}")
            self.connected = False
            return None

class RateLimiter:
    """Manages rate limiting for external systems."""
    
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
        self._lock = asyncio.Lock()
        
    async def check_rate_limit(self, system_id: str) -> bool:
        """
        Check if a system has exceeded its rate limit.
        
        Args:
            system_id: System identifier
            
        Returns:
            bool: True if within rate limit, False if exceeded
        """
        async with self._lock:
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=self.time_window)
            
            # Remove old requests
            self.requests[system_id] = [
                req_time for req_time in self.requests[system_id]
                if req_time > window_start
            ]
            
            # Check if limit exceeded
            if len(self.requests[system_id]) >= self.max_requests:
                logger.warning(f"Rate limit exceeded for system {system_id}")
                return False
                
            # Add new request
            self.requests[system_id].append(now)
            return True
            
    async def get_remaining_requests(self, system_id: str) -> int:
        """
        Get the number of remaining requests for a system.
        
        Args:
            system_id: System identifier
            
        Returns:
            int: Number of remaining requests
        """
        async with self._lock:
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=self.time_window)
            
            # Remove old requests
            self.requests[system_id] = [
                req_time for req_time in self.requests[system_id]
                if req_time > window_start
            ]
            
            return max(0, self.max_requests - len(self.requests[system_id]))

class MessageValidator:
    """Validates messages against schemas."""
    
    def __init__(self, schemas: Dict[str, Dict[str, Any]]):
        self.schemas = schemas
        
    def validate_message(self, system_id: str, message: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a message against its schema.
        
        Args:
            system_id: System identifier
            message: Message to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if system_id not in self.schemas:
            return False, f"No schema found for system {system_id}"
            
        try:
            jsonschema.validate(instance=message, schema=self.schemas[system_id])
            return True, None
        except jsonschema.exceptions.ValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Validation error: {str(e)}"

class MetricsCollector:
    """Collects and exposes system metrics."""
    
    def __init__(self, port: int = 9090):
        self.port = port
        self._start_metrics_server()
        
    def _start_metrics_server(self):
        """Start the Prometheus metrics server."""
        try:
            start_http_server(self.port)
            logger.info(f"Metrics server started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {str(e)}")
            
    def record_message_sent(self, system_id: str, status: str):
        """Record a message sent event."""
        MESSAGE_SENT.labels(system_id=system_id, status=status).inc()
        
    def record_message_received(self, system_id: str, status: str):
        """Record a message received event."""
        MESSAGE_RECEIVED.labels(system_id=system_id, status=status).inc()
        
    def record_latency(self, system_id: str, operation: str, duration: float):
        """Record operation latency."""
        MESSAGE_LATENCY.labels(system_id=system_id, operation=operation).observe(duration)
        
    def update_queue_size(self, system_id: str, size: int):
        """Update queue size metric."""
        QUEUE_SIZE.labels(system_id=system_id).set(size)
        
    def update_connection_count(self, system_id: str, transport_type: str, count: int):
        """Update active connections metric."""
        ACTIVE_CONNECTIONS.labels(system_id=system_id, transport_type=transport_type).set(count)

class ExternalSystemIntegration:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.authenticated_systems = {}
        self.data_transformers = {}
        self.transports = {}
        self.message_queue = MessageQueue(
            max_retries=config.get('max_retries', 3),
            retry_delay=config.get('retry_delay', 5)
        )
        self.rate_limiter = RateLimiter(
            max_requests=config.get('rate_limit', {}).get('max_requests', 100),
            time_window=config.get('rate_limit', {}).get('time_window', 60)
        )
        self.message_validator = MessageValidator(
            schemas=config.get('schemas', {})
        )
        self.metrics = MetricsCollector(
            port=config.get('metrics', {}).get('port', 9090)
        )
        self._setup_logging()
        self._start_message_processor()
        
    def _setup_logging(self):
        """Configure logging for the integration module."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    def authenticate_system(self, system_id: str, credentials: Dict[str, str]) -> bool:
        """
        Authenticate an external system using provided credentials.
        
        Args:
            system_id: Unique identifier for the external system
            credentials: Authentication credentials
            
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # Verify credentials against stored configuration
            if self._verify_credentials(system_id, credentials):
                self.authenticated_systems[system_id] = {
                    'authenticated_at': datetime.utcnow(),
                    'last_activity': datetime.utcnow()
                }
                logger.info(f"System {system_id} authenticated successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Authentication failed for system {system_id}: {str(e)}")
            return False
            
    def _verify_credentials(self, system_id: str, credentials: Dict[str, str]) -> bool:
        """
        Verify system credentials against stored configuration.
        
        Args:
            system_id: System identifier
            credentials: Authentication credentials
            
        Returns:
            bool: True if credentials are valid
        """
        if system_id not in self.config['systems']:
            return False
            
        stored_credentials = self.config['systems'][system_id]['credentials']
        return self._compare_credentials(credentials, stored_credentials)
        
    def _compare_credentials(self, provided: Dict[str, str], stored: Dict[str, str]) -> bool:
        """
        Securely compare provided credentials with stored credentials.
        
        Args:
            provided: Credentials provided by the system
            stored: Stored credentials for comparison
            
        Returns:
            bool: True if credentials match
        """
        try:
            return hmac.compare_digest(
                self._hash_credentials(provided),
                self._hash_credentials(stored)
            )
        except Exception:
            return False
            
    def _hash_credentials(self, credentials: Dict[str, str]) -> str:
        """
        Hash credentials for secure comparison.
        
        Args:
            credentials: Credentials to hash
            
        Returns:
            str: Hashed credentials
        """
        cred_str = json.dumps(credentials, sort_keys=True)
        return base64.b64encode(
            hmac.new(
                self.config['security']['key'].encode(),
                cred_str.encode(),
                hashlib.sha256
            ).digest()
        ).decode()
        
    def transform_data(self, system_id: str, data: Dict[str, Any], direction: str) -> Dict[str, Any]:
        """
        Transform data between internal and external formats.
        
        Args:
            system_id: System identifier
            data: Data to transform
            direction: 'in' for external to internal, 'out' for internal to external
            
        Returns:
            Dict[str, Any]: Transformed data
        """
        try:
            transformer = self._get_transformer(system_id, direction)
            return transformer(data)
        except Exception as e:
            logger.error(f"Data transformation failed: {str(e)}")
            raise
            
    def _get_transformer(self, system_id: str, direction: str):
        """
        Get the appropriate data transformer for a system and direction.
        
        Args:
            system_id: System identifier
            direction: Transformation direction
            
        Returns:
            callable: Data transformer function
        """
        if system_id not in self.data_transformers:
            self.data_transformers[system_id] = self._load_transformers(system_id)
        return self.data_transformers[system_id][direction]
        
    def _load_transformers(self, system_id: str) -> Dict[str, callable]:
        """
        Load data transformers for a system.
        
        Args:
            system_id: System identifier
            
        Returns:
            Dict[str, callable]: Mapping of direction to transformer function
        """
        # Load transformer configuration from system config
        config = self.config['systems'][system_id]['transformers']
        return {
            'in': self._create_transformer(config['in']),
            'out': self._create_transformer(config['out'])
        }
        
    def _create_transformer(self, config: Dict[str, Any]) -> callable:
        """
        Create a data transformer function from configuration.
        
        Args:
            config: Transformer configuration
            
        Returns:
            callable: Transformer function
        """
        def transform(data: Dict[str, Any]) -> Dict[str, Any]:
            result = {}
            for field, mapping in config['fields'].items():
                if mapping in data:
                    result[field] = data[mapping]
            return result
        return transform
        
    def _start_message_processor(self):
        """Start the background message processor task."""
        asyncio.create_task(self._process_message_queue())
        
    async def _process_message_queue(self):
        """Process messages in the queue."""
        while True:
            try:
                message = await self.message_queue.get_next_message()
                if message:
                    start_time = datetime.utcnow()
                    
                    # Check rate limit
                    if not await self.rate_limiter.check_rate_limit(message.system_id):
                        await asyncio.sleep(1)
                        continue
                        
                    # Validate message
                    is_valid, error = self.message_validator.validate_message(
                        message.system_id,
                        message.message
                    )
                    if not is_valid:
                        logger.error(f"Message validation failed: {error}")
                        self.metrics.record_message_sent(message.system_id, 'validation_failed')
                        await self.message_queue.mark_failed(message)
                        continue
                        
                    success = await self._send_message_internal(
                        message.system_id,
                        message.message
                    )
                    
                    # Record metrics
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    self.metrics.record_latency(message.system_id, 'send', duration)
                    self.metrics.record_message_sent(
                        message.system_id,
                        'success' if success else 'failed'
                    )
                    
                    if success:
                        await self.message_queue.mark_success(message)
                    else:
                        await self.message_queue.mark_failed(message)
                        
                    # Update queue size
                    self.metrics.update_queue_size(
                        message.system_id,
                        len(self.message_queue.queue)
                    )
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error processing message queue: {str(e)}")
                await asyncio.sleep(1)
                
    async def _send_message_internal(self, system_id: str, message: Dict[str, Any]) -> bool:
        """Internal method to send a message without queuing."""
        try:
            if not self._is_authenticated(system_id):
                raise ValueError(f"System {system_id} not authenticated")
                
            external_message = self.transform_data(system_id, message, 'out')
            transport = await self._get_transport(system_id)
            
            if not transport:
                return False
                
            success = await transport.send(external_message)
            
            if success:
                self._update_activity(system_id)
                logger.info(f"Message sent to system {system_id}")
                
                # Update connection metrics
                transport_type = type(transport).__name__.lower()
                self.metrics.update_connection_count(
                    system_id,
                    transport_type,
                    1 if transport.connected else 0
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send message to system {system_id}: {str(e)}")
            return False
            
    async def send_message(self, system_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to an external system with validation and rate limiting.
        
        Args:
            system_id: System identifier
            message: Message to send
            
        Returns:
            bool: True if message queued successfully
        """
        try:
            if not self._is_authenticated(system_id):
                raise ValueError(f"System {system_id} not authenticated")
                
            # Validate message before queuing
            is_valid, error = self.message_validator.validate_message(system_id, message)
            if not is_valid:
                logger.error(f"Message validation failed: {error}")
                self.metrics.record_message_sent(system_id, 'validation_failed')
                return False
                
            # Check rate limit
            if not await self.rate_limiter.check_rate_limit(system_id):
                logger.warning(f"Rate limit exceeded for system {system_id}")
                self.metrics.record_message_sent(system_id, 'rate_limited')
                return False
                
            await self.message_queue.add_message(message, system_id)
            logger.info(f"Message queued for system {system_id}")
            
            # Update queue size
            self.metrics.update_queue_size(system_id, len(self.message_queue.queue))
            return True
        except Exception as e:
            logger.error(f"Failed to queue message for system {system_id}: {str(e)}")
            self.metrics.record_message_sent(system_id, 'error')
            return False
            
    def _is_authenticated(self, system_id: str) -> bool:
        """
        Check if a system is authenticated.
        
        Args:
            system_id: System identifier
            
        Returns:
            bool: True if system is authenticated
        """
        return system_id in self.authenticated_systems
        
    async def _get_transport(self, system_id: str) -> Optional[Transport]:
        """
        Get or create the transport mechanism for a system.
        
        Args:
            system_id: System identifier
            
        Returns:
            Optional[Transport]: Transport instance or None if creation fails
        """
        if system_id not in self.transports:
            try:
                transport_config = self.config['systems'][system_id]['transport']
                if transport_config['type'] == 'websocket':
                    transport = WebSocketTransport(transport_config)
                elif transport_config['type'] == 'http':
                    transport = HTTPTransport(transport_config)
                else:
                    logger.error(f"Unsupported transport type: {transport_config['type']}")
                    return None
                    
                if await transport.connect():
                    self.transports[system_id] = transport
                else:
                    return None
            except Exception as e:
                logger.error(f"Failed to create transport for system {system_id}: {str(e)}")
                return None
                
        return self.transports[system_id]
        
    def _update_activity(self, system_id: str):
        """
        Update the last activity timestamp for a system.
        
        Args:
            system_id: System identifier
        """
        if system_id in self.authenticated_systems:
            self.authenticated_systems[system_id]['last_activity'] = datetime.utcnow()
            
    async def close(self):
        """Close all transport connections."""
        for system_id, transport in self.transports.items():
            try:
                await transport.disconnect()
            except Exception as e:
                logger.error(f"Failed to close transport for system {system_id}: {str(e)}")

    async def get_system_status(self, system_id: str) -> Dict[str, Any]:
        """
        Get the current status of a system.
        
        Args:
            system_id: System identifier
            
        Returns:
            Dict[str, Any]: System status information
        """
        status = {
            'authenticated': self._is_authenticated(system_id),
            'remaining_requests': await self.rate_limiter.get_remaining_requests(system_id),
            'queue_size': len(self.message_queue.queue),
            'last_activity': self.authenticated_systems.get(system_id, {}).get('last_activity')
        }
        
        # Add transport status
        if system_id in self.transports:
            transport = self.transports[system_id]
            status['transport'] = {
                'type': type(transport).__name__,
                'connected': transport.connected
            }
            
        return status 