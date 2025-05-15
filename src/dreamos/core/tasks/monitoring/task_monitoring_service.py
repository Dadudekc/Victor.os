"""Task Monitoring Service for Dream.OS.

Service that periodically checks for stalled tasks and other task-related issues.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from ..nexus.task_nexus import TaskNexus
from .pending_monitor import PendingTaskMonitor

logger = logging.getLogger(__name__)


class TaskMonitoringService:
    """Service that periodically checks for stalled tasks and other task-related issues."""

    def __init__(self, task_nexus: TaskNexus, config: Dict[str, Any]):
        """Initialize the TaskMonitoringService.
        
        Args:
            task_nexus: The TaskNexus instance to monitor
            config: Configuration dictionary with keys:
                - check_interval_seconds: How often to check for stalled tasks
                - pending_timeout_seconds: Time in seconds before a PENDING task is considered stalled
                - escalation_strategy: Strategy for handling stalled tasks
        """
        self.task_nexus = task_nexus
        self.config = config
        self.pending_monitor = PendingTaskMonitor(task_nexus, config)
        self.running = False
        logger.info("TaskMonitoringService initialized with config: %s", config)

    async def start(self) -> None:
        """Start the monitoring service."""
        if self.running:
            logger.warning("TaskMonitoringService is already running")
            return
            
        self.running = True
        logger.info("TaskMonitoringService started")
        
        while self.running:
            try:
                await self.pending_monitor.check_pending_tasks()
                # Add other monitoring checks here as needed
                
                # Wait for next check interval
                check_interval = self.config.get("check_interval_seconds", 300)
                logger.debug(f"Waiting {check_interval} seconds until next check")
                await asyncio.sleep(check_interval)
            except Exception as e:
                logger.error(f"Error in task monitoring service: {e}", exc_info=True)
                # Wait a bit before retrying
                await asyncio.sleep(10)
                
    async def stop(self) -> None:
        """Stop the monitoring service."""
        if not self.running:
            logger.warning("TaskMonitoringService is not running")
            return
            
        self.running = False
        logger.info("TaskMonitoringService stopped")
        
    @property
    def is_running(self) -> bool:
        """Check if the service is currently running."""
        return self.running
        
    async def run_single_check(self) -> None:
        """Run a single check cycle without waiting.
        
        This is useful for testing or manual checks.
        """
        try:
            logger.info("Running single check cycle")
            await self.pending_monitor.check_pending_tasks()
            # Add other monitoring checks here as needed
        except Exception as e:
            logger.error(f"Error in single check cycle: {e}", exc_info=True) 