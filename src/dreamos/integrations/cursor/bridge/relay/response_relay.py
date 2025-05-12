"""Response Relay
==============

Handles the relay of THEA responses to agent inboxes.
Monitors the bridge outbox and moves responses to appropriate agent inboxes.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set

from ..feedback.thea_response_handler import TheaResponseHandler
from ..schemas.thea_response_schema import TheaResponse

logger = logging.getLogger(__name__)


class ResponseRelay:
    """Relays THEA responses to agent inboxes."""

    def __init__(
        self,
        outbox_dir: Path,
        agent_inbox_base: Path,
        polling_interval: float = 1.0,
        max_retries: int = 3
    ):
        """Initialize the response relay.
        
        Args:
            outbox_dir: Directory containing THEA responses
            agent_inbox_base: Base directory for agent inboxes
            polling_interval: How often to check for new responses (seconds)
            max_retries: Maximum number of retries for failed relays
        """
        self.outbox_dir = Path(outbox_dir)
        self.agent_inbox_base = Path(agent_inbox_base)
        self.polling_interval = polling_interval
        self.max_retries = max_retries
        
        # Initialize response handler
        self.response_handler = TheaResponseHandler(outbox_dir)
        
        # Track processed responses
        self.processed_responses: Set[str] = set()
        
        # Track relay attempts
        self._relay_attempts: Dict[str, int] = {}
        
        # Ensure directories exist
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        self.agent_inbox_base.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized response relay with outbox: {outbox_dir}")
        logger.info(f"Agent inbox base: {agent_inbox_base}")

    def _get_agent_inbox(self, agent_id: str) -> Path:
        """Get the inbox directory for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Path to the agent's inbox directory
        """
        # Create agent directory if it doesn't exist
        agent_dir = self.agent_inbox_base / f"Agent-{agent_id}"
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Create inbox directory if it doesn't exist
        inbox_dir = agent_dir / "inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        
        return inbox_dir

    def _relay_response(self, response_file: Path) -> bool:
        """Relay a single response to the appropriate agent's inbox.
        
        Args:
            response_file: Path to the response file
            
        Returns:
            True if relay was successful, False otherwise
        """
        try:
            # Read and parse response
            response_data = json.loads(response_file.read_text())
            response = TheaResponse.from_dict(response_data)
            
            if not response:
                logger.error(f"Failed to parse response from {response_file}")
                return False
                
            # Extract agent ID from task ID
            task_id = response.task_id
            if not task_id or "_" not in task_id:
                logger.error(f"Invalid task ID format in {response_file}")
                return False
                
            agent_id = task_id.split("_")[0].replace("agent-", "")
            
            # Get agent inbox
            inbox_dir = self._get_agent_inbox(agent_id)
            
            # Add relay metadata
            relay_data = response.to_dict()
            relay_data["metadata"] = relay_data.get("metadata", {})
            relay_data["metadata"]["relay_time"] = datetime.utcnow().isoformat()
            relay_data["metadata"]["relay_status"] = "delivered"
            
            # Write response to inbox
            inbox_file = inbox_dir / f"{task_id}.json"
            inbox_file.write_text(json.dumps(relay_data, indent=2))
            
            # Verify inbox file was written
            if not inbox_file.exists():
                logger.error(f"Failed to write inbox file: {inbox_file}")
                return False
            
            # Only remove from outbox after successful write
            response_file.unlink()
            
            # Clear retry count
            if task_id in self._relay_attempts:
                del self._relay_attempts[task_id]
                
            logger.info(f"Relayed response for task {task_id} to Agent-{agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error relaying response for task {task_id}: {str(e)}")
            return False

    def process_outbox(self) -> int:
        """Process all new responses in the outbox.
        
        Returns:
            Number of successfully relayed responses
        """
        processed = 0
        
        # Get all response files
        response_files = list(self.outbox_dir.glob("*.json"))
        logger.info(f"Found {len(response_files)} response files in outbox")
        
        for response_file in response_files:
            task_id = response_file.stem
            logger.info(f"Processing task {task_id}")
            
            # Skip if max retries exceeded
            if self._relay_attempts.get(task_id, 0) >= self.max_retries:
                logger.error(f"Failed to relay response after {self.max_retries} attempts: {response_file}")
                continue
                
            # Try to relay
            if self._relay_response(response_file):
                processed += 1
                logger.info(f"Successfully processed task {task_id}")
            else:
                # Increment retry count
                self._relay_attempts[task_id] = self._relay_attempts.get(task_id, 0) + 1
                logger.warning(f"Incremented retry count for task {task_id}: {self._relay_attempts[task_id]}")
                
        return processed

    def run(self):
        """Run the relay loop.
        
        Args:
            stop_event: Optional event to signal stopping
        """
        logger.info("Starting response relay loop")
        
        while True:
            try:
                # Process outbox
                processed = self.process_outbox()
                if processed > 0:
                    logger.info(f"Relayed {processed} responses")
                    
                # Wait before next check
                time.sleep(self.polling_interval)
                
            except Exception as e:
                logger.error(f"Error in relay loop: {str(e)}")
                time.sleep(self.polling_interval)
            
        logger.info("Response relay loop stopped") 