import asyncio
from typing import Dict, Any
import logging

from ..nexus.task_nexus import TaskNexus
from .pending_monitor import PendingTaskMonitor

logger = logging.getLogger(__name__)

class TaskMonitoringService:
    def __init__(self, task_nexus: TaskNexus, config: Dict[str, Any]):
        self.task_nexus = task_nexus
        self.config = config
        self.pending_monitor = PendingTaskMonitor(task_nexus, config)
        self.running = False
        
    async def start(self) -> None:
        """Start the monitoring service."""
        self.running = True
        while self.running:
            try:
                await self.pending_monitor.check_pending_tasks()
                # Add other monitoring checks here
                
                # Wait for next check interval
                await asyncio.sleep(self.config.get("check_interval_seconds", 300))
            except Exception as e:
                logger.error(f"Error in task monitoring service: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(10)
                
    async def stop(self) -> None:
        """Stop the monitoring service."""
        self.running = False 