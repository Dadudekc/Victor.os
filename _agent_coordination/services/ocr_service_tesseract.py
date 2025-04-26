# _agent_coordination/services/ocr_service_tesseract.py

import asyncio
import time
import uuid
from difflib import SequenceMatcher
from typing import Optional

import cv2
import pytesseract
from PIL import Image

from ..services.ocr_service import OCRService
from ..core.config import CursorCoordinatorConfig


class TesseractOCRService(OCRService):
    """
    Concrete OCRService using Tesseract via pytesseract, running capture in an executor.
    """
    def __init__(
        self,
        config: CursorCoordinatorConfig,
        instance_controller: Any
    ):
        self.config = config
        self.instance_controller = instance_controller
        # Configure tesseract command if provided
        if hasattr(config, 'tesseract_cmd') and config.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = config.tesseract_cmd

    async def capture_new_text(
        self,
        instance_id: str,
        last_text: str,
        timeout: float
    ) -> Optional[str]:
        """
        Waits up to `timeout` seconds for a new text segment from the Cursor instance via OCR.
        """
        start_time = time.time()
        loop = asyncio.get_running_loop()

        while time.time() - start_time < timeout:
            # Wait between retries
            await asyncio.sleep(self.config.ocr_retry_interval)

            # Capture screenshot on executor to avoid blocking
            screenshot_np = await loop.run_in_executor(None, self._capture_screenshot, instance_id)
            if screenshot_np is None:
                continue

            # Convert to RGB PIL Image
            img_rgb = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)

            # Run OCR in executor
            try:
                text = await loop.run_in_executor(None, pytesseract.image_to_string, pil_img)
            except Exception:
                return None

            text = text.strip()
            if text and text != last_text:
                # Compute diff
                matcher = SequenceMatcher(None, last_text, text, autojunk=False)
                parts = []
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag in ('insert', 'replace'):
                        parts.append(text[j1:j2])
                new_segment = '\n'.join(parts).strip()
                if new_segment:
                    return new_segment
                else:
                    return text
        return None

    def _capture_screenshot(self, instance_id: str):
        """
        Blocking call to instance_controller to get a screenshot numpy array.
        """
        instance = self.instance_controller.get_instance_by_id(instance_id)
        if instance is None or not hasattr(instance, 'capture'):
            return None
        return instance.capture() 