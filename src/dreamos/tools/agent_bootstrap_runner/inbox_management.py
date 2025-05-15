"""
Inbox management utilities for agent onboarding.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from .config import AgentConfig

def create_seed_inbox(logger: logging.Logger, config: AgentConfig) -> bool:
    """
    Create initial inbox structure for an agent.
    
    Args:
        logger: Logger instance
        config: Agent configuration
        
    Returns:
        bool: True if successful
    """
    try:
        # Create required directories
        config.inbox_dir.mkdir(parents=True, exist_ok=True)
        config.processed_dir.mkdir(parents=True, exist_ok=True)
        config.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Create initial state file if it doesn't exist
        if not config.state_file.exists():
            initial_state = {
                "agent_id": config.agent_id,
                "status": "initializing",
                "last_update": datetime.now(timezone.utc).isoformat(),
                "cycle_count": 0,
                "processed_messages": []
            }
            config.state_file.write_text(json.dumps(initial_state, indent=2))
            logger.info(f"Created initial state file for {config.agent_id}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error creating seed inbox: {e}")
        return False

def update_inbox_with_prompt(logger: logging.Logger, config: AgentConfig, prompt: str) -> bool:
    """
    Update agent's inbox with a new prompt message.
    
    Args:
        logger: Logger instance
        config: Agent configuration
        prompt: The prompt message to add
        
    Returns:
        bool: True if successful
    """
    try:
        # Create prompt file in inbox
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        prompt_file = config.inbox_dir / f"prompt_{timestamp}.md"
        
        prompt_file.write_text(prompt)
        logger.info(f"Added prompt to inbox: {prompt_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating inbox with prompt: {e}")
        return False 