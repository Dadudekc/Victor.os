"""
Lifecycle skills module for agent lifecycle management.
"""

from typing import Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import logging


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Circuit is open, requests are blocked
    HALF_OPEN = "half_open"  # Testing if service is recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker for fault tolerance."""
    
    name: str
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    expected_exception: type = Exception
    
    def __post_init__(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.logger = logging.getLogger(f"CircuitBreaker.{self.name}")
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.logger.info(f"Circuit {self.name} transitioning to HALF_OPEN")
            else:
                raise Exception(f"Circuit {self.name} is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.logger.info(f"Circuit {self.name} reset to CLOSED")
        
        self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.warning(f"Circuit {self.name} opened after {self.failure_count} failures")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True
        
        return datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)


class StableAutonomousLoop:
    """Stable autonomous loop for agent operation."""
    
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        self.agent_id = agent_id
        self.config = config or {
            "max_iterations": 1000,
            "iteration_timeout": 30,  # seconds
            "error_backoff": 5,  # seconds
            "max_consecutive_errors": 3
        }
        
        self.is_running = False
        self.iteration_count = 0
        self.consecutive_errors = 0
        self.last_error_time = None
        self.logger = logging.getLogger(f"StableAutonomousLoop.{agent_id}")
        
        # Circuit breaker for error handling
        self.circuit_breaker = CircuitBreaker(
            name=f"loop_{agent_id}",
            failure_threshold=self.config["max_consecutive_errors"],
            recovery_timeout=self.config["error_backoff"]
        )
    
    async def start(self, main_loop_func: Callable):
        """Start the autonomous loop."""
        self.is_running = True
        self.logger.info(f"Starting autonomous loop for agent {self.agent_id}")
        
        try:
            while self.is_running and self.iteration_count < self.config["max_iterations"]:
                try:
                    # Execute main loop function with circuit breaker
                    await self.circuit_breaker.call(main_loop_func)
                    
                    # Reset error count on success
                    self.consecutive_errors = 0
                    self.iteration_count += 1
                    
                    # Small delay to prevent tight loops
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    self.consecutive_errors += 1
                    self.last_error_time = datetime.utcnow()
                    
                    self.logger.error(f"Error in iteration {self.iteration_count}: {e}")
                    
                    # Check if we should stop due to too many consecutive errors
                    if self.consecutive_errors >= self.config["max_consecutive_errors"]:
                        self.logger.error(f"Too many consecutive errors, stopping loop")
                        break
                    
                    # Wait before retrying
                    await asyncio.sleep(self.config["error_backoff"])
                    
        except Exception as e:
            self.logger.error(f"Fatal error in autonomous loop: {e}")
        finally:
            self.is_running = False
            self.logger.info(f"Autonomous loop stopped for agent {self.agent_id}")
    
    def stop(self):
        """Stop the autonomous loop."""
        self.is_running = False
        self.logger.info(f"Stopping autonomous loop for agent {self.agent_id}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current loop status."""
        return {
            "agent_id": self.agent_id,
            "is_running": self.is_running,
            "iteration_count": self.iteration_count,
            "consecutive_errors": self.consecutive_errors,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "circuit_state": self.circuit_breaker.state.value
        } 