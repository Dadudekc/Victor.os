"""
System Maintenance Integration for Dream.OS Bootstrap Runner

Integrates system maintenance tasks into the agent bootstrap framework.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .config import AgentBootstrapConfig
from .cursor_messaging import CursorAgentMessenger
from dreamos.tools.system_maintenance.cleanup_duplicates import DuplicatesCleaner

class MaintenanceManager:
    """Manages system maintenance tasks within the agent bootstrap framework."""
    
    def __init__(self, config: AgentBootstrapConfig):
        self.config = config
        self.logger = logging.getLogger(f"{config.agent_id}.maintenance")
        self.workspace_root = Path(config.project_root)
        self.cursor_messenger = CursorAgentMessenger(config)
        
    async def run_maintenance(self) -> Dict[str, Any]:
        """Run maintenance tasks and return results."""
        try:
            self.logger.info("Starting system maintenance tasks...")
            
            # Send maintenance start message to agent
            await self.cursor_messenger.send_message(
                "Starting system maintenance tasks. This may take several minutes..."
            )
            
            # Initialize cleaner
            cleaner = DuplicatesCleaner(self.workspace_root)
            
            # Run cleanup
            cleaner.run_cleanup()
            
            # Get report
            report_path = self.workspace_root / "runtime" / "reports" / "cleanup_report.json"
            if report_path.exists():
                import json
                with open(report_path) as f:
                    report = json.load(f)
            else:
                report = {
                    "timestamp": datetime.now().isoformat(),
                    "stats": {
                        "backup_chains_removed": 0,
                        "space_freed_mb": 0,
                        "errors": []
                    }
                }
            
            # Send completion message with results
            status_message = (
                f"Maintenance completed:\n"
                f"- Removed {report['stats']['backup_chains_removed']} backup chains\n"
                f"- Freed {report['stats']['space_freed_mb']} MB of space\n"
                f"- Errors: {len(report['stats']['errors'])}"
            )
            
            await self.cursor_messenger.send_message(status_message)
            
            # Wait for agent acknowledgment
            await self.cursor_messenger.wait_for_response(timeout=300)  # 5 minute timeout
            
            self.logger.info(
                f"Maintenance completed: removed {report['stats']['backup_chains_removed']} "
                f"chains, freed {report['stats']['space_freed_mb']} MB"
            )
            
            return report
            
        except Exception as e:
            error_msg = f"Error during maintenance: {str(e)}"
            self.logger.error(error_msg)
            
            # Notify agent of failure
            await self.cursor_messenger.send_message(
                f"❌ Maintenance failed: {error_msg}\n"
                "Please check logs for details."
            )
            
            return {
                "timestamp": datetime.now().isoformat(),
                "error": error_msg,
                "stats": {
                    "backup_chains_removed": 0,
                    "space_freed_mb": 0,
                    "errors": [error_msg]
                }
            } 