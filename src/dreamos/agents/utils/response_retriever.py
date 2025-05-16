"""
Response Retriever Module

This module handles reading from inbox.json and managing agent responses.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ResponseRetriever:
    """Handles reading from inbox.json and managing agent responses."""
    
    def __init__(self, workspace_root):
        from pathlib import Path
        self.workspace_root = Path(workspace_root)
        self.inbox_path = self.workspace_root / "runtime/agent_comms/agent_mailboxes"
        
    def get_inbox_path(self, agent_id: str) -> Optional[Path]:
        """Get the inbox path for a specific agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Optional[Path]: Path to the agent's inbox file, or None if invalid
        """
        try:
            agent_dir = self.inbox_path / f"Agent-{agent_id}"
            agent_dir.mkdir(parents=True, exist_ok=True)
            return agent_dir / "inbox.json"
        except Exception as e:
            logger.error(f"Error getting inbox path for agent {agent_id}: {e}")
            return None
        
    def get_agent_inbox(self, agent_id: str) -> Path:
        """Get the inbox path for a specific agent."""
        return self.inbox_path / f"Agent-{agent_id}" / "inbox.json"
        
    def read_inbox(self, agent_id: str) -> List[Dict[str, Any]]:
        """Read messages from an agent's inbox."""
        inbox_path = self.get_agent_inbox(agent_id)
        try:
            if not inbox_path.exists():
                return []
                
            with open(inbox_path, 'r') as f:
                messages = json.load(f)
                if not isinstance(messages, list):
                    logger.error(f"Invalid inbox format for {agent_id}")
                    return []
                return messages
        except Exception as e:
            logger.error(f"Error reading inbox for {agent_id}: {e}")
            return []
            
    def clear_inbox(self, agent_id: str) -> bool:
        """Clear an agent's inbox after processing."""
        inbox_path = self.get_agent_inbox(agent_id)
        try:
            if inbox_path.exists():
                with open(inbox_path, 'w') as f:
                    json.dump([], f)
                return True
            return False
        except Exception as e:
            logger.error(f"Error clearing inbox for {agent_id}: {e}")
            return False
            
    def get_unread_messages(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get unread messages from an agent's inbox."""
        messages = self.read_inbox(agent_id)
        return [msg for msg in messages if not msg.get('read', False)]
        
    def mark_as_read(self, agent_id: str, message_id: str) -> bool:
        """Mark a specific message as read."""
        inbox_path = self.get_agent_inbox(agent_id)
        try:
            if not inbox_path.exists():
                return False
                
            with open(inbox_path, 'r') as f:
                messages = json.load(f)
                
            for msg in messages:
                if msg.get('message_id') == message_id:
                    msg['read'] = True
                    msg['read_at'] = datetime.utcnow().isoformat()
                    
            with open(inbox_path, 'w') as f:
                json.dump(messages, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error marking message as read for {agent_id}: {e}")
            return False 