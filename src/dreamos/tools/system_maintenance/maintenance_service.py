"""
DreamOS System Maintenance Service

Provides scheduled execution of system maintenance tasks including:
- Backup cleanup
- Log consolidation
- Test directory management
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from dreamos.tools.system_maintenance.cleanup_duplicates import DuplicatesCleaner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('runtime/logs/maintenance_service.log')
    ]
)

class MaintenanceService:
    """Service that manages scheduled system maintenance tasks."""
    
    def __init__(self, workspace_root: Path):
        """Initialize the maintenance service.
        
        Args:
            workspace_root: Root directory of the workspace
        """
        self.workspace_root = workspace_root
        self.scheduler = AsyncIOScheduler()
        self._running = False
        
        # Default schedule - can be overridden
        self.schedule = {
            'cleanup_job': {
                'trigger': CronTrigger(hour=2, minute=0),  # Run at 2 AM
                'func': self._run_cleanup,
                'id': 'system_cleanup'
            }
            # Add more scheduled jobs here
        }
    
    async def _run_cleanup(self):
        """Execute the system cleanup task."""
        try:
            logging.info("Starting scheduled system cleanup...")
            cleaner = DuplicatesCleaner(self.workspace_root)
            cleaner.run_cleanup()
            logging.info("Scheduled system cleanup completed")
        except Exception as e:
            logging.error(f"Error in scheduled cleanup: {e}", exc_info=True)
    
    async def start(self):
        """Start the maintenance service scheduler."""
        if self._running:
            logging.warning("Maintenance service already running")
            return
            
        try:
            # Add scheduled jobs
            for job_name, config in self.schedule.items():
                self.scheduler.add_job(
                    func=config['func'],
                    trigger=config['trigger'],
                    id=config['id'],
                    replace_existing=True
                )
                logging.info(f"Scheduled maintenance job: {job_name}")
            
            self.scheduler.start()
            self._running = True
            logging.info("Maintenance service started")
            
        except Exception as e:
            logging.error(f"Failed to start maintenance service: {e}")
            self._running = False
            raise
    
    async def stop(self):
        """Stop the maintenance service scheduler."""
        if not self._running:
            logging.warning("Maintenance service not running")
            return
            
        try:
            self.scheduler.shutdown()
            self._running = False
            logging.info("Maintenance service stopped")
        except Exception as e:
            logging.error(f"Error stopping maintenance service: {e}")
            raise
    
    @property
    def is_running(self) -> bool:
        """Check if the service is currently running."""
        return self._running
    
    async def run_cleanup_now(self):
        """Run cleanup immediately without waiting for schedule."""
        await self._run_cleanup()

async def main():
    """Run the maintenance service."""
    service = MaintenanceService(Path.cwd())
    try:
        await service.start()
        # Keep running until interrupted
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        await service.stop()

if __name__ == "__main__":
    asyncio.run(main()) 