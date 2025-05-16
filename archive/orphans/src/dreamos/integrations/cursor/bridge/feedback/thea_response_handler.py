"""THEA Response Handler
====================

Handles validation and processing of THEA (ChatGPT) responses.
Ensures responses conform to the expected schema and handles any necessary transformations.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union

from ..schemas.thea_response_schema import ResponseStatus, TheaResponse

logger = logging.getLogger(__name__)


class TheaResponseHandler:
    """Handles THEA responses with validation and processing."""

    def __init__(self, outbox_dir: Union[str, Path]):
        """Initialize the response handler.

        Args:
            outbox_dir: Directory where responses are written
        """
        self.outbox_dir = Path(outbox_dir)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized THEA response handler with outbox: {self.outbox_dir}")

    def validate_response(self, response_data: Dict) -> bool:
        """Validate a response against the schema.

        Args:
            response_data: Response data to validate

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            response = TheaResponse.from_dict(response_data)
            return response.validate()
        except Exception as e:
            logger.error(f"Response validation failed: {e}")
            return False

    def process_response(self, response_data: Dict, task_id: str) -> bool:
        """Process and store a validated response.

        Args:
            response_data: Response data to process
            task_id: ID of the task this response is for

        Returns:
            bool: True if processing succeeded, False otherwise
        """
        try:
            # Validate the response
            if not self.validate_response(response_data):
                logger.error(f"Invalid response data for task {task_id}")
                return False

            # Create response object
            response = TheaResponse.from_dict(response_data)

            # Ensure task_id matches
            if response.task_id != task_id:
                logger.error(f"Task ID mismatch: {response.task_id} != {task_id}")
                return False

            # Write to outbox
            outbox_file = self.outbox_dir / f"{task_id}.json"
            outbox_file.write_text(response.to_json())

            logger.info(f"Successfully processed response for task {task_id}")
            return True

        except Exception as e:
            logger.error(f"Error processing response for task {task_id}: {e}")
            return False

    def get_response(self, task_id: str) -> Optional[TheaResponse]:
        """Retrieve a processed response.

        Args:
            task_id: ID of the task to get response for

        Returns:
            Optional[TheaResponse]: The response if found, None otherwise
        """
        try:
            response_file = self.outbox_dir / f"{task_id}.json"
            if not response_file.exists():
                return None

            response_data = json.loads(response_file.read_text())
            return TheaResponse.from_dict(response_data)

        except Exception as e:
            logger.error(f"Error retrieving response for task {task_id}: {e}")
            return None

    def mark_as_escalated(self, task_id: str, reason: str) -> bool:
        """Mark a response as requiring escalation.

        Args:
            task_id: ID of the task to escalate
            reason: Reason for escalation

        Returns:
            bool: True if escalation succeeded, False otherwise
        """
        try:
            response = self.get_response(task_id)
            if not response:
                return False

            # Update status and add metadata
            response.status = ResponseStatus.ESCALATED
            if not response.metadata:
                response.metadata = {}
            response.metadata["escalation_reason"] = reason
            response.metadata["escalation_time"] = datetime.utcnow().isoformat()

            # Write updated response
            outbox_file = self.outbox_dir / f"{task_id}.json"
            outbox_file.write_text(response.to_json())

            logger.info(f"Marked task {task_id} as escalated: {reason}")
            return True

        except Exception as e:
            logger.error(f"Error escalating task {task_id}: {e}")
            return False
