"""
Error Recovery module for handling and recovering from various error types.
"""

from typing import Dict, Any, List, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import logging
import traceback
import time


class ErrorType(Enum):
    """Types of errors that can occur in the system."""
    
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    VALIDATION_ERROR = "validation_error"
    PERMISSION_ERROR = "permission_error"
    RESOURCE_ERROR = "resource_error"
    CONFIGURATION_ERROR = "configuration_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorContext:
    """Context information for an error."""
    
    error_type: ErrorType
    error_message: str
    timestamp: datetime
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    backoff_delay: float = 1.0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ErrorRecoveryStrategy:
    """Strategy for recovering from specific error types."""
    
    def __init__(self, error_type: ErrorType, recovery_func: Callable, 
                 max_retries: int = 3, backoff_multiplier: float = 2.0):
        self.error_type = error_type
        self.recovery_func = recovery_func
        self.max_retries = max_retries
        self.backoff_multiplier = backoff_multiplier
    
    async def execute(self, context: ErrorContext, *args, **kwargs) -> Any:
        """Execute the recovery strategy with retry logic."""
        for attempt in range(self.max_retries):
            try:
                return await self.recovery_func(context, *args, **kwargs)
            except Exception as e:
                context.retry_count += 1
                context.error_message = str(e)
                
                if context.retry_count >= self.max_retries:
                    raise
                
                # Exponential backoff
                delay = context.backoff_delay * (self.backoff_multiplier ** attempt)
                await asyncio.sleep(delay)


class ErrorRecoveryManager:
    """Manages error recovery strategies and execution."""
    
    def __init__(self):
        self.strategies: Dict[ErrorType, ErrorRecoveryStrategy] = {}
        self.error_history: List[ErrorContext] = []
        self.logger = logging.getLogger("ErrorRecoveryManager")
        
        # Register default strategies
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register default recovery strategies."""
        self.register_strategy(
            ErrorType.NETWORK_ERROR,
            self._network_recovery_strategy,
            max_retries=5,
            backoff_multiplier=2.0
        )
        
        self.register_strategy(
            ErrorType.TIMEOUT_ERROR,
            self._timeout_recovery_strategy,
            max_retries=3,
            backoff_multiplier=1.5
        )
        
        self.register_strategy(
            ErrorType.VALIDATION_ERROR,
            self._validation_recovery_strategy,
            max_retries=1,
            backoff_multiplier=1.0
        )
        
        self.register_strategy(
            ErrorType.PERMISSION_ERROR,
            self._permission_recovery_strategy,
            max_retries=2,
            backoff_multiplier=1.0
        )
        
        self.register_strategy(
            ErrorType.RESOURCE_ERROR,
            self._resource_recovery_strategy,
            max_retries=3,
            backoff_multiplier=2.0
        )
    
    def register_strategy(self, error_type: ErrorType, recovery_func: Callable,
                         max_retries: int = 3, backoff_multiplier: float = 2.0):
        """Register a recovery strategy for an error type."""
        strategy = ErrorRecoveryStrategy(
            error_type, recovery_func, max_retries, backoff_multiplier
        )
        self.strategies[error_type] = strategy
        self.logger.info(f"Registered recovery strategy for {error_type.value}")
    
    async def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Any:
        """Handle an error using appropriate recovery strategy."""
        error_type = self._classify_error(error)
        error_context = ErrorContext(
            error_type=error_type,
            error_message=str(error),
            timestamp=datetime.utcnow(),
            agent_id=context.get("agent_id") if context else None,
            task_id=context.get("task_id") if context else None,
            metadata=context or {}
        )
        
        self.error_history.append(error_context)
        self.logger.warning(f"Handling {error_type.value} error: {error}")
        
        # Get recovery strategy
        strategy = self.strategies.get(error_type)
        if not strategy:
            self.logger.error(f"No recovery strategy for {error_type.value}")
            raise error
        
        # Execute recovery strategy
        try:
            return await strategy.execute(error_context, error, context)
        except Exception as recovery_error:
            self.logger.error(f"Recovery failed for {error_type.value}: {recovery_error}")
            raise recovery_error
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify an error into an ErrorType."""
        error_str = str(error).lower()
        
        if any(word in error_str for word in ["network", "connection", "socket"]):
            return ErrorType.NETWORK_ERROR
        elif any(word in error_str for word in ["timeout", "timed out"]):
            return ErrorType.TIMEOUT_ERROR
        elif any(word in error_str for word in ["validation", "invalid", "format"]):
            return ErrorType.VALIDATION_ERROR
        elif any(word in error_str for word in ["permission", "access", "unauthorized"]):
            return ErrorType.PERMISSION_ERROR
        elif any(word in error_str for word in ["resource", "memory", "disk", "quota"]):
            return ErrorType.RESOURCE_ERROR
        elif any(word in error_str for word in ["config", "configuration", "setting"]):
            return ErrorType.CONFIGURATION_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    # Default recovery strategies
    async def _network_recovery_strategy(self, context: ErrorContext, 
                                        error: Exception, original_context: Dict[str, Any]) -> Any:
        """Recovery strategy for network errors."""
        self.logger.info(f"Attempting network recovery (attempt {context.retry_count + 1})")
        
        # Simulate network recovery
        await asyncio.sleep(1)
        
        # In a real implementation, you might:
        # - Check network connectivity
        # - Retry the original operation
        # - Use fallback endpoints
        # - Switch to offline mode
        
        return {"status": "recovered", "strategy": "network_retry"}
    
    async def _timeout_recovery_strategy(self, context: ErrorContext,
                                       error: Exception, original_context: Dict[str, Any]) -> Any:
        """Recovery strategy for timeout errors."""
        self.logger.info(f"Attempting timeout recovery (attempt {context.retry_count + 1})")
        
        # Increase timeout for retry
        if "timeout" in original_context:
            original_context["timeout"] *= 2
        
        return {"status": "recovered", "strategy": "timeout_increase"}
    
    async def _validation_recovery_strategy(self, context: ErrorContext,
                                          error: Exception, original_context: Dict[str, Any]) -> Any:
        """Recovery strategy for validation errors."""
        self.logger.info(f"Attempting validation recovery (attempt {context.retry_count + 1})")
        
        # Try to fix validation issues
        # This might involve data cleaning, format conversion, etc.
        
        return {"status": "recovered", "strategy": "validation_fix"}
    
    async def _permission_recovery_strategy(self, context: ErrorContext,
                                          error: Exception, original_context: Dict[str, Any]) -> Any:
        """Recovery strategy for permission errors."""
        self.logger.info(f"Attempting permission recovery (attempt {context.retry_count + 1})")
        
        # Try to refresh permissions or use alternative credentials
        
        return {"status": "recovered", "strategy": "permission_refresh"}
    
    async def _resource_recovery_strategy(self, context: ErrorContext,
                                        error: Exception, original_context: Dict[str, Any]) -> Any:
        """Recovery strategy for resource errors."""
        self.logger.info(f"Attempting resource recovery (attempt {context.retry_count + 1})")
        
        # Try to free up resources or use alternative resources
        
        return {"status": "recovered", "strategy": "resource_cleanup"}
    
    def get_error_statistics(self, time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get error statistics within a time window."""
        if not time_window:
            errors = self.error_history
        else:
            cutoff_time = datetime.utcnow() - time_window
            errors = [e for e in self.error_history if e.timestamp >= cutoff_time]
        
        if not errors:
            return {"total_errors": 0, "error_types": {}, "recovery_rate": 0.0}
        
        # Count error types
        error_types = {}
        for error in errors:
            error_type = error.error_type.value
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # Calculate recovery rate (simplified)
        recovery_rate = 0.8  # Placeholder - in real implementation, track actual recoveries
        
        return {
            "total_errors": len(errors),
            "error_types": error_types,
            "recovery_rate": recovery_rate,
            "most_common_error": max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        }
    
    def clear_error_history(self):
        """Clear error history."""
        self.error_history.clear()
        self.logger.info("Error history cleared") 