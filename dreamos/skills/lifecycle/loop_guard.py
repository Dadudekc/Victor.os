"""
Loop Guard implementation for protecting autonomous agent loops.
"""
import time
import logging
import threading
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)

class LoopGuard:
    """
    A context manager that protects autonomous loops from common failure modes:
    - Detects and recovers from hangs using watchdog timers
    - Limits maximum execution time per cycle
    - Monitors resource usage across cycles
    - Prevents unbounded growth of logs or state
    
    Usage:
        with LoopGuard(timeout=60, memory_limit_mb=1000) as guard:
            # Loop operations here
            while condition:
                # ...cycle operations...
                guard.reset_watchdog()  # Reset watchdog timer
    """
    
    def __init__(
        self, 
        timeout: int = 300,  # 5 minutes default timeout
        memory_limit_mb: Optional[int] = None,
        max_log_entries: int = 1000,
        on_timeout: Optional[Callable] = None,
        on_resource_limit: Optional[Callable] = None
    ):
        """
        Initialize a new LoopGuard.
        
        Args:
            timeout: Maximum time in seconds for any cycle before watchdog triggers
            memory_limit_mb: Maximum memory usage in MB (None for no limit)
            max_log_entries: Maximum number of log entries to keep
            on_timeout: Callback function when timeout occurs
            on_resource_limit: Callback function when resource limit is reached
        """
        self.timeout = timeout
        self.memory_limit_mb = memory_limit_mb
        self.max_log_entries = max_log_entries
        self.on_timeout = on_timeout
        self.on_resource_limit = on_resource_limit
        
        self.start_time = None
        self.watchdog_timer = None
        self.resources = {}
        self.log_queue = []
        
    def __enter__(self):
        """Set up the loop guard when entering context."""
        self.start_time = time.time()
        self._start_watchdog()
        self._monitor_resources()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up when exiting context."""
        self._stop_watchdog()
        self._log_resource_usage()
        return False  # Don't suppress exceptions
        
    def reset_watchdog(self):
        """Reset the watchdog timer."""
        self._stop_watchdog()
        self._start_watchdog()
        
    def log(self, message: str, level: str = "INFO"):
        """
        Add a log entry, maintaining maximum log size.
        
        Args:
            message: The log message
            level: Log level (INFO, WARNING, ERROR, etc.)
        """
        self.log_queue.append({
            "timestamp": time.time(),
            "level": level,
            "message": message
        })
        
        # Trim log if it exceeds maximum size
        if len(self.log_queue) > self.max_log_entries:
            self.log_queue = self.log_queue[-self.max_log_entries:]
            
        # Log to actual logger as well
        getattr(logger, level.lower())(message)
        
    def get_logs(self):
        """Get all logs collected by this guard."""
        return self.log_queue
        
    def _start_watchdog(self):
        """Start the watchdog timer."""
        def _watchdog_triggered():
            logger.error(f"Watchdog timeout after {self.timeout} seconds")
            if self.on_timeout:
                self.on_timeout()
                
        self.watchdog_timer = threading.Timer(self.timeout, _watchdog_triggered)
        self.watchdog_timer.daemon = True
        self.watchdog_timer.start()
        
    def _stop_watchdog(self):
        """Stop the watchdog timer."""
        if self.watchdog_timer:
            self.watchdog_timer.cancel()
            self.watchdog_timer = None
            
    def _monitor_resources(self):
        """Start monitoring resource usage."""
        # Record initial resource usage
        self.resources["start"] = self._get_resource_usage()
        
    def _log_resource_usage(self):
        """Log resource usage at the end of the context."""
        end_resources = self._get_resource_usage()
        self.resources["end"] = end_resources
        self.resources["delta"] = {
            k: end_resources.get(k, 0) - self.resources["start"].get(k, 0)
            for k in end_resources
        }
        
        # Check if memory limit is exceeded
        if (self.memory_limit_mb and 
            end_resources.get("memory_mb", 0) > self.memory_limit_mb):
            logger.warning(
                f"Memory usage ({end_resources['memory_mb']}MB) "
                f"exceeds limit ({self.memory_limit_mb}MB)"
            )
            if self.on_resource_limit:
                self.on_resource_limit()
                
    def _get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage.
        
        Returns:
            Dict with resource usage metrics
        """
        # This is a placeholder - in a real implementation, we would
        # use psutil or similar to get actual resource usage
        return {
            "memory_mb": 0,  # Placeholder
            "cpu_percent": 0,  # Placeholder
            "open_files": 0,  # Placeholder
            "threads": threading.active_count()
        } 