"""Empathy logger for Dream.OS."""

import logging
import json
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class EmpathyLogger:
    """Logs empathy-related events and metrics."""
    
    def __init__(self, log_dir: str = "logs/empathy"):
        """Initialize the empathy logger.
        
        Args:
            log_dir: Directory to store empathy logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Initialized EmpathyLogger in %s", log_dir)
    
    def log_interaction(self, interaction_data: Dict[str, Any]) -> None:
        """Log an empathy-related interaction.
        
        Args:
            interaction_data: Data about the interaction to log
        """
        timestamp = datetime.utcnow().isoformat()
        log_file = self.log_dir / f"empathy_{timestamp}.json"
        
        with open(log_file, "w") as f:
            json.dump({
                "timestamp": timestamp,
                "data": interaction_data
            }, f, indent=2)
        
        logger.debug("Logged empathy interaction to %s", log_file) 