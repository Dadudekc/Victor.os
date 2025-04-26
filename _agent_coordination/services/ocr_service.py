# _agent_coordination/services/ocr_service.py

import asyncio
from abc import ABC, abstractmethod
from typing import Optional

class OCRService(ABC):
    """
    Service responsible for capturing and processing OCR-based responses from Cursor instances.
    """
    @abstractmethod
    async def capture_new_text(
        self,
        instance_id: str,
        last_text: str,
        timeout: float
    ) -> Optional[str]:
        """
        Captures new text using OCR for a given Cursor instance.

        Args:
            instance_id: ID of the Cursor instance.
            last_text: The previously seen text to compute diffs.
            timeout: Time in seconds to wait for new text.

        Returns:
            The newly captured text segment or None if timed out.
        """
        ... 
