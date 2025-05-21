"""
Circuit Breaker pattern implementation for Dream.OS agents.

The Circuit Breaker pattern prevents cascading failures by temporarily disabling
operations that are consistently failing, allowing the system to recover.
"""
import time
import logging
import threading
from enum import Enum
from typing import Optional, Dict, Any, Callable, List

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Possible states for a circuit breaker."""
    CLOSED = "closed"  # Normal operation - circuit is closed/connected
    OPEN = "open"     # Circuit is open/disconnected - operation is disabled
    HALF_OPEN = "half_open"  # Testing if operation can be re-enabled


class CircuitBreaker:
    """
    Implements the Circuit Breaker pattern to protect operations that might fail.
    
    The circuit breaker:
    - Tracks failure rates for specific operations
    - Temporarily disables operations with persistent failures
    - Implements exponential backoff for retries
    - Provides alternative paths when operations are disabled
    
    Usage:
        with CircuitBreaker("file_operation") as breaker:
            # Operation that might fail
            result = perform_risky_operation()
            breaker.record_success()
    """
    
    # Class-level registry of all circuit breakers
    _registry: Dict[str, 'CircuitBreaker'] = {}
    _registry_lock = threading.RLock()
    
    def __init__(
        self,
        operation_name: str,
        failure_threshold: int = 5,
        reset_timeout: int = 60,
        half_open_max_calls: int = 1,
        exponential_backoff_factor: float = 2.0,
        max_backoff: int = 3600,  # 1 hour
        alternative_action: Optional[Callable] = None
    ):
        """
        Initialize a circuit breaker for an operation.
        
        Args:
            operation_name: Name of the operation being protected
            failure_threshold: Number of failures before opening circuit
            reset_timeout: Time in seconds before testing if circuit can be closed
            half_open_max_calls: Max calls allowed in half-open state
            exponential_backoff_factor: Multiplier for successive reset timeouts
            max_backoff: Maximum reset timeout in seconds
            alternative_action: Function to call when circuit is open
        """
        self.operation_name = operation_name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_max_calls = half_open_max_calls
        self.backoff_factor = exponential_backoff_factor
        self.max_backoff = max_backoff
        self.alternative_action = alternative_action
        
        # State variables
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.successful_calls = 0
        self.current_timeout = reset_timeout
        self.half_open_calls = 0
        
        # Register this circuit breaker
        with CircuitBreaker._registry_lock:
            CircuitBreaker._registry[operation_name] = self
    
    def __enter__(self):
        """
        Enter the context, checking if operation should proceed.
        
        Raises:
            RuntimeError: If circuit is open and operation should not proceed
        """
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.current_timeout:
                # Transition to half-open state to test if operation can succeed
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info(f"Circuit {self.operation_name} transitioned to half-open state")
            else:
                # Circuit is open, don't allow operation
                if self.alternative_action:
                    logger.info(f"Circuit {self.operation_name} open, running alternative action")
                    self.alternative_action()
                else:
                    logger.warning(f"Circuit {self.operation_name} open, operation skipped")
                raise RuntimeError(f"Circuit {self.operation_name} is open")
                
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                # Don't allow more than max calls in half-open state
                logger.warning(f"Circuit {self.operation_name} half-open call limit reached")
                raise RuntimeError(f"Circuit {self.operation_name} half-open call limit reached")
            self.half_open_calls += 1
            
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context, recording success or failure.
        
        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        if exc_type is not None:
            # An exception occurred
            try:
                # Use error recovery system if available
                from dreamos.skills.error_recovery import classify_error, log_error
                
                # Classify the error and log it
                error_type = classify_error(exc_val)
                log_error(
                    error=exc_val,
                    error_type=error_type,
                    operation=self.operation_name,
                    context={"circuit_state": self.state.value}
                )
                
                # Record failure with error type information
                self.record_failure(error_type=error_type)
            except ImportError:
                # Error recovery system not available, use simple failure recording
                logger.debug("Error recovery system not available, using simple failure recording")
                self.record_failure()
            
            return False  # Don't suppress the exception
            
        # No exception, record success
        self.record_success()
        return False  # Don't suppress any exceptions
    
    def record_success(self):
        """Record a successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            # In half-open state, successful call allows transition back to closed
            self.successful_calls += 1
            if self.successful_calls >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.current_timeout = self.reset_timeout  # Reset timeout
                logger.info(f"Circuit {self.operation_name} closed after successful test calls")
        
        if self.state == CircuitState.CLOSED:
            # In closed state, reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)
            self.successful_calls += 1
    
    def record_failure(self, error_type=None):
        """
        Record a failed operation.
        
        Args:
            error_type: Optional type of error that occurred
        """
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # In half-open state, failure immediately opens circuit again
            # with increased timeout using exponential backoff
            self.state = CircuitState.OPEN
            self.current_timeout = min(
                self.current_timeout * self.backoff_factor, 
                self.max_backoff
            )
            logger.warning(
                f"Circuit {self.operation_name} reopened after failure in half-open state. "
                f"New timeout: {self.current_timeout}s"
            )
            
        if self.state == CircuitState.CLOSED:
            # In closed state, increment failure count
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                # Open the circuit after threshold failures
                self.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit {self.operation_name} opened after {self.failure_count} failures"
                )
    
    @classmethod
    def get_circuit_breaker(cls, operation_name: str) -> Optional['CircuitBreaker']:
        """
        Get a circuit breaker by operation name.
        
        Args:
            operation_name: Name of the operation
            
        Returns:
            CircuitBreaker instance or None if not found
        """
        with cls._registry_lock:
            return cls._registry.get(operation_name)
    
    @classmethod
    def get_all_circuits(cls) -> List[Dict[str, Any]]:
        """
        Get status information for all circuit breakers.
        
        Returns:
            List of dictionaries with circuit breaker status
        """
        result = []
        with cls._registry_lock:
            for name, breaker in cls._registry.items():
                result.append({
                    "name": name,
                    "state": breaker.state.value,
                    "failure_count": breaker.failure_count,
                    "successful_calls": breaker.successful_calls,
                    "last_failure": breaker.last_failure_time,
                    "current_timeout": breaker.current_timeout
                })
        return result 