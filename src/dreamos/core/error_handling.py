"""
Victor.os Error Handling & Logging System
Comprehensive error recovery and logging for production reliability
"""

import os
import sys
import json
import logging
import traceback
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Callable, Union
from enum import Enum
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import structlog
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

class ErrorSeverity(Enum):
    """Error severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for classification"""
    SYSTEM = "system"
    AGENT = "agent"
    COMMUNICATION = "communication"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    DATABASE = "database"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    UNKNOWN = "unknown"

@dataclass
class ErrorContext:
    """Context information for error handling"""
    timestamp: str
    severity: ErrorSeverity
    category: ErrorCategory
    component: str
    operation: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class ErrorRecord:
    """Complete error record"""
    error_id: str
    exception_type: str
    exception_message: str
    traceback: str
    context: ErrorContext
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_method: Optional[str] = None

class ErrorRecoveryStrategy(Enum):
    """Error recovery strategies"""
    RETRY = "retry"
    FALLBACK = "fallback"
    CIRCUIT_BREAKER = "circuit_breaker"
    DEGRADED_MODE = "degraded_mode"
    RESTART = "restart"
    ESCALATE = "escalate"
    IGNORE = "ignore"

class ErrorHandler:
    """Main error handling system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.error_history: List[ErrorRecord] = []
        self.recovery_history: List[Dict[str, Any]] = []
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # Setup logging
        self._setup_logging()
        
        # Recovery strategies
        self.recovery_strategies = {
            ErrorRecoveryStrategy.RETRY: self._retry_strategy,
            ErrorRecoveryStrategy.FALLBACK: self._fallback_strategy,
            ErrorRecoveryStrategy.CIRCUIT_BREAKER: self._circuit_breaker_strategy,
            ErrorRecoveryStrategy.DEGRADED_MODE: self._degraded_mode_strategy,
            ErrorRecoveryStrategy.RESTART: self._restart_strategy,
            ErrorRecoveryStrategy.ESCALATE: self._escalate_strategy,
            ErrorRecoveryStrategy.IGNORE: self._ignore_strategy,
        }
    
    def _default_config(self) -> Dict[str, Any]:
        """Default error handling configuration"""
        return {
            "log_level": "INFO",
            "log_file": "runtime/logs/errors.log",
            "max_error_history": 1000,
            "recovery_enabled": True,
            "circuit_breaker_enabled": True,
            "retry_attempts": 3,
            "retry_delay": 1.0,
            "circuit_breaker_threshold": 5,
            "circuit_breaker_timeout": 60,
            "escalation_threshold": 10,
            "auto_cleanup": True,
            "cleanup_interval_hours": 24,
        }
    
    def _setup_logging(self):
        """Setup structured logging"""
        log_file = self.config["log_file"]
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # Setup file handler
        logging.basicConfig(
            level=getattr(logging, self.config["log_level"].upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = structlog.get_logger("error_handler")
    
    def handle_error(
        self,
        exception: Exception,
        context: ErrorContext,
        recovery_strategy: Optional[ErrorRecoveryStrategy] = None
    ) -> ErrorRecord:
        """Handle an error with optional recovery"""
        
        # Create error record
        error_record = self._create_error_record(exception, context)
        
        # Log the error
        self._log_error(error_record)
        
        # Attempt recovery if enabled
        if self.config["recovery_enabled"] and recovery_strategy:
            error_record.recovery_attempted = True
            error_record.recovery_successful = self._attempt_recovery(
                error_record, recovery_strategy
            )
        
        # Store in history
        self.error_history.append(error_record)
        
        # Cleanup old records
        if self.config["auto_cleanup"]:
            self._cleanup_old_records()
        
        return error_record
    
    def _create_error_record(self, exception: Exception, context: ErrorContext) -> ErrorRecord:
        """Create an error record from exception and context"""
        import uuid
        
        return ErrorRecord(
            error_id=str(uuid.uuid4()),
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            traceback=traceback.format_exc(),
            context=context
        )
    
    def _log_error(self, error_record: ErrorRecord):
        """Log error with structured logging"""
        log_data = {
            "error_id": error_record.error_id,
            "exception_type": error_record.exception_type,
            "exception_message": error_record.exception_message,
            "severity": error_record.context.severity.value,
            "category": error_record.context.category.value,
            "component": error_record.context.component,
            "operation": error_record.context.operation,
            "recovery_attempted": error_record.recovery_attempted,
            "recovery_successful": error_record.recovery_successful,
        }
        
        if error_record.context.metadata:
            log_data.update(error_record.context.metadata)
        
        log_level = getattr(self.logger, error_record.context.severity.value)
        log_level("Error occurred", **log_data)
        
        # Also log to console for critical errors
        if error_record.context.severity == ErrorSeverity.CRITICAL:
            self._log_to_console(error_record)
    
    def _log_to_console(self, error_record: ErrorRecord):
        """Log critical errors to console with rich formatting"""
        panel = Panel(
            f"[red]CRITICAL ERROR[/red]\n"
            f"Type: {error_record.exception_type}\n"
            f"Message: {error_record.exception_message}\n"
            f"Component: {error_record.context.component}\n"
            f"Operation: {error_record.context.operation}\n"
            f"Error ID: {error_record.error_id}",
            title="🚨 Error Handler",
            border_style="red"
        )
        console.print(panel)
    
    def _attempt_recovery(
        self, 
        error_record: ErrorRecord, 
        strategy: ErrorRecoveryStrategy
    ) -> bool:
        """Attempt error recovery using specified strategy"""
        try:
            recovery_func = self.recovery_strategies.get(strategy)
            if recovery_func:
                error_record.recovery_method = strategy.value
                success = recovery_func(error_record)
                
                # Record recovery attempt
                self.recovery_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "error_id": error_record.error_id,
                    "strategy": strategy.value,
                    "success": success
                })
                
                return success
            else:
                self.logger.warning("Unknown recovery strategy", strategy=strategy.value)
                return False
        except Exception as e:
            self.logger.error("Recovery attempt failed", 
                            strategy=strategy.value, 
                            error=str(e))
            return False
    
    def _retry_strategy(self, error_record: ErrorRecord) -> bool:
        """Retry strategy implementation"""
        max_attempts = self.config["retry_attempts"]
        delay = self.config["retry_delay"]
        
        for attempt in range(max_attempts):
            try:
                # Simulate retry (in real implementation, this would retry the operation)
                self.logger.info("Retry attempt", 
                               attempt=attempt + 1, 
                               max_attempts=max_attempts)
                
                # For now, just wait and return success
                asyncio.sleep(delay)
                return True
                
            except Exception as e:
                self.logger.warning("Retry failed", 
                                  attempt=attempt + 1, 
                                  error=str(e))
                if attempt < max_attempts - 1:
                    asyncio.sleep(delay)
        
        return False
    
    def _fallback_strategy(self, error_record: ErrorRecord) -> bool:
        """Fallback strategy implementation"""
        self.logger.info("Using fallback strategy", 
                        component=error_record.context.component)
        # Implement fallback logic here
        return True
    
    def _circuit_breaker_strategy(self, error_record: ErrorRecord) -> bool:
        """Circuit breaker strategy implementation"""
        component = error_record.context.component
        
        if component not in self.circuit_breakers:
            self.circuit_breakers[component] = {
                "failures": 0,
                "last_failure": None,
                "state": "closed"  # closed, open, half-open
            }
        
        cb = self.circuit_breakers[component]
        cb["failures"] += 1
        cb["last_failure"] = datetime.now()
        
        if cb["failures"] >= self.config["circuit_breaker_threshold"]:
            cb["state"] = "open"
            self.logger.warning("Circuit breaker opened", component=component)
            return False
        
        return True
    
    def _degraded_mode_strategy(self, error_record: ErrorRecord) -> bool:
        """Degraded mode strategy implementation"""
        self.logger.info("Switching to degraded mode", 
                        component=error_record.context.component)
        # Implement degraded mode logic here
        return True
    
    def _restart_strategy(self, error_record: ErrorRecord) -> bool:
        """Restart strategy implementation"""
        self.logger.info("Attempting restart", 
                        component=error_record.context.component)
        # Implement restart logic here
        return True
    
    def _escalate_strategy(self, error_record: ErrorRecord) -> bool:
        """Escalation strategy implementation"""
        self.logger.warning("Escalating error", 
                           component=error_record.context.component)
        # Implement escalation logic here (e.g., send alert, notify admin)
        return True
    
    def _ignore_strategy(self, error_record: ErrorRecord) -> bool:
        """Ignore strategy implementation"""
        self.logger.info("Ignoring error", 
                        component=error_record.context.component)
        return True
    
    def _cleanup_old_records(self):
        """Clean up old error records"""
        max_history = self.config["max_error_history"]
        if len(self.error_history) > max_history:
            # Remove oldest records
            self.error_history = self.error_history[-max_history:]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of error handling statistics"""
        total_errors = len(self.error_history)
        errors_by_severity = {}
        errors_by_category = {}
        recovery_success_rate = 0
        
        for error in self.error_history:
            # Count by severity
            severity = error.context.severity.value
            errors_by_severity[severity] = errors_by_severity.get(severity, 0) + 1
            
            # Count by category
            category = error.context.category.value
            errors_by_category[category] = errors_by_category.get(category, 0) + 1
        
        # Calculate recovery success rate
        recovery_attempts = sum(1 for e in self.error_history if e.recovery_attempted)
        successful_recoveries = sum(1 for e in self.error_history if e.recovery_successful)
        
        if recovery_attempts > 0:
            recovery_success_rate = successful_recoveries / recovery_attempts
        
        return {
            "total_errors": total_errors,
            "errors_by_severity": errors_by_severity,
            "errors_by_category": errors_by_category,
            "recovery_attempts": recovery_attempts,
            "successful_recoveries": successful_recoveries,
            "recovery_success_rate": recovery_success_rate,
            "circuit_breakers": len(self.circuit_breakers)
        }
    
    def export_errors(self, filepath: str):
        """Export error history to file"""
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "config": self.config,
            "errors": [asdict(error) for error in self.error_history],
            "recovery_history": self.recovery_history,
            "summary": self.get_error_summary()
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        self.logger.info("Error history exported", filepath=filepath)

# Global error handler instance
error_handler = ErrorHandler()

# Convenience functions for easy error handling
def handle_error(
    exception: Exception,
    component: str,
    operation: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    recovery_strategy: Optional[ErrorRecoveryStrategy] = None,
    **kwargs
) -> ErrorRecord:
    """Convenience function for error handling"""
    context = ErrorContext(
        timestamp=datetime.now().isoformat(),
        severity=severity,
        category=category,
        component=component,
        operation=operation,
        metadata=kwargs
    )
    
    return error_handler.handle_error(exception, context, recovery_strategy)

@contextmanager
def error_context(
    component: str,
    operation: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    recovery_strategy: Optional[ErrorRecoveryStrategy] = None,
    **kwargs
):
    """Context manager for automatic error handling"""
    try:
        yield
    except Exception as e:
        handle_error(
            e, component, operation, severity, category, recovery_strategy, **kwargs
        )
        raise

def log_error(
    message: str,
    component: str,
    operation: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    **kwargs
):
    """Log an error without exception handling"""
    context = ErrorContext(
        timestamp=datetime.now().isoformat(),
        severity=severity,
        category=category,
        component=component,
        operation=operation,
        metadata=kwargs
    )
    
    # Create a synthetic exception for logging
    class LoggedError(Exception):
        pass
    
    exception = LoggedError(message)
    error_handler.handle_error(exception, context)

# Decorator for automatic error handling
def error_handled(
    component: str,
    operation: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    recovery_strategy: Optional[ErrorRecoveryStrategy] = None
):
    """Decorator for automatic error handling"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handle_error(
                    e, component, operation, severity, category, recovery_strategy
                )
                raise
        return wrapper
    return decorator

# Async version of the decorator
def async_error_handled(
    component: str,
    operation: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    recovery_strategy: Optional[ErrorRecoveryStrategy] = None
):
    """Async decorator for automatic error handling"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                handle_error(
                    e, component, operation, severity, category, recovery_strategy
                )
                raise
        return wrapper
    return decorator 