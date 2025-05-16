"""Response Relay
==============

Handles the relay of THEA responses to agent inboxes.
Monitors the bridge outbox and moves responses to appropriate agent inboxes.
"""

import json
import logging
import os
import time
import traceback
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
        max_retries: int = 3,
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
        try:
            self.outbox_dir.mkdir(parents=True, exist_ok=True)
            self.agent_inbox_base.mkdir(parents=True, exist_ok=True)
            logger.info(f"Initialized response relay with outbox: {outbox_dir}")
            logger.info(f"Agent inbox base: {agent_inbox_base}")
        except Exception as e:
            logger.error(f"Failed to initialize directories: {str(e)}")
            traceback.print_exc()
            raise

    def _get_agent_inbox(self, agent_id: str) -> Path:
        """Get the inbox directory for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Path to the agent's inbox directory
        """
        try:
            # Create agent directory if it doesn't exist
            agent_dir = self.agent_inbox_base / f"Agent-{agent_id}"
            agent_dir.mkdir(parents=True, exist_ok=True)

            # Create inbox directory if it doesn't exist
            inbox_dir = agent_dir / "inbox"
            inbox_dir.mkdir(parents=True, exist_ok=True)

            return inbox_dir
        except Exception as e:
            logger.error(
                f"Failed to create agent inbox directory for Agent-{agent_id}: {str(e)}"
            )
            traceback.print_exc()
            raise

    def _safe_read_json(self, file_path: Path) -> Optional[dict]:
        """Safely read and parse a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            Parsed JSON data or None if failed
        """
        try:
            with open(file_path, "r") as f:
                content = f.read()
                return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {file_path}: {str(e)}")
            traceback.print_exc()
            return None
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {str(e)}")
            traceback.print_exc()
            return None

    def _safe_write_json(self, file_path: Path, data: dict) -> bool:
        """Safely write JSON data to a file.

        Args:
            file_path: Path to write to
            data: Data to write

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            return True
        except Exception as e:
            logger.error(f"Failed to write to {file_path}: {str(e)}")
            traceback.print_exc()
            return False

    def _relay_response(self, response_file: Path) -> bool:
        """Relay a single response to the appropriate agent's inbox.

        Args:
            response_file: Path to the response file

        Returns:
            True if relay was successful, False otherwise
        """
        task_id = None
        try:
            # Read and parse response
            response_data = self._safe_read_json(response_file)
            if not response_data:
                return False

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
            if relay_data is None:
                logger.error(f"Failed to convert response to dict for task {task_id}")
                return False

            # Ensure metadata dict exists
            if "metadata" not in relay_data:
                relay_data["metadata"] = {}
            elif relay_data["metadata"] is None:
                relay_data["metadata"] = {}

            # Add relay metadata
            relay_data["metadata"]["relay_time"] = datetime.utcnow().isoformat()
            relay_data["metadata"]["relay_status"] = "delivered"

            # Write response to inbox
            inbox_file = inbox_dir / f"{task_id}.json"
            if not self._safe_write_json(inbox_file, relay_data):
                return False

            # Verify inbox file was written
            if not inbox_file.exists():
                logger.error(f"Failed to write inbox file: {inbox_file}")
                return False

            # Only remove from outbox after successful write
            try:
                response_file.unlink()
            except Exception as e:
                logger.error(f"Failed to remove outbox file {response_file}: {str(e)}")
                traceback.print_exc()
                return False

            # Clear retry count
            if task_id in self._relay_attempts:
                del self._relay_attempts[task_id]

            logger.info(f"Relayed response for task {task_id} to Agent-{agent_id}")
            return True

        except Exception as e:
            logger.error(f"Error relaying response for task {task_id}: {str(e)}")
            traceback.print_exc()
            return False

    def process_outbox(self) -> int:
        """Process all new responses in the outbox.

        Returns:
            Number of successfully relayed responses
        """
        processed = 0

        try:
            # Get all response files
            response_files = list(self.outbox_dir.glob("*.json"))
            logger.info(f"Found {len(response_files)} response files in outbox")

            for response_file in response_files:
                task_id = response_file.stem
                logger.info(f"Processing task {task_id}")

                # Skip if max retries exceeded
                if self._relay_attempts.get(task_id, 0) >= self.max_retries:
                    logger.error(
                        f"Failed to relay response after {self.max_retries} attempts: {response_file}"
                    )
                    continue

                # Try to relay
                if self._relay_response(response_file):
                    processed += 1
                    logger.info(f"Successfully processed task {task_id}")
                else:
                    # Increment retry count
                    self._relay_attempts[task_id] = (
                        self._relay_attempts.get(task_id, 0) + 1
                    )
                    logger.warning(
                        f"Incremented retry count for task {task_id}: {self._relay_attempts[task_id]}"
                    )

            return processed

        except Exception as e:
            logger.error(f"Error processing outbox: {str(e)}")
            traceback.print_exc()
            return processed

    def run(self):
        """Run the relay loop."""
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
                traceback.print_exc()
                time.sleep(self.polling_interval)

        logger.info("Response relay loop stopped")
