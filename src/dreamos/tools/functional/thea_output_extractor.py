"""THEA Output Extractor

A robust utility for extracting THEA's responses from the Cursor interface.
Uses visual cue detection and dynamic waiting to ensure reliable extraction.
"""

import logging
import time
from pathlib import Path
from typing import Optional, Tuple

import pyautogui
import pyperclip

from dreamos.core.config import AppConfig
from dreamos.utils.common_utils import get_utc_iso_timestamp

logger = logging.getLogger(__name__)

# Constants
RESPONSE_CHECK_INTERVAL = 1.0  # Seconds between checks
MAX_WAIT_TIME = 60.0  # Maximum time to wait for response
CONFIDENCE_THRESHOLD = 0.8  # Image matching confidence

class TheaOutputExtractor:
    """Extracts THEA's responses from Cursor with improved reliability."""

    def __init__(self, config: AppConfig):
        """Initialize the extractor.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.gui_images_dir = Path(config.get("paths.gui_images", "runtime/assets/gui_templates"))
        self.response_complete_cue = self.gui_images_dir / "thea_response_complete_cue.png"
        
        # Ensure the cue image exists
        if not self.response_complete_cue.exists():
            logger.warning("Response complete cue image not found. Will use fallback methods.")
            self.response_complete_cue = None

    def extract_response(self) -> Optional[str]:
        """Extract THEA's response using the most reliable method available.
        
        Returns:
            Optional[str]: The extracted response text, or None if extraction failed
        """
        # Try visual cue detection first if available
        if self.response_complete_cue and self.response_complete_cue.exists():
            return self._extract_with_visual_cue()
        
        # Fall back to clipboard monitoring
        return self._extract_with_clipboard_monitoring()

    def _extract_with_visual_cue(self) -> Optional[str]:
        """Extract response using visual cue detection.
        
        Returns:
            Optional[str]: The extracted response text, or None if extraction failed
        """
        start_time = time.time()
        last_clipboard = pyperclip.paste()
        
        while time.time() - start_time < MAX_WAIT_TIME:
            # Check for visual cue
            try:
                location = pyautogui.locateOnScreen(
                    str(self.response_complete_cue),
                    confidence=CONFIDENCE_THRESHOLD
                )
                if location:
                    # Cue found, wait a moment for text to be fully rendered
                    time.sleep(0.5)
                    return self._get_clipboard_text()
            except Exception as e:
                logger.debug(f"Visual cue detection failed: {e}")
            
            # Check if clipboard content changed
            current_clipboard = pyperclip.paste()
            if current_clipboard != last_clipboard:
                return current_clipboard
            
            time.sleep(RESPONSE_CHECK_INTERVAL)
        
        logger.warning("Timeout waiting for THEA response")
        return None

    def _extract_with_clipboard_monitoring(self) -> Optional[str]:
        """Extract response by monitoring clipboard changes.
        
        Returns:
            Optional[str]: The extracted response text, or None if extraction failed
        """
        start_time = time.time()
        last_clipboard = pyperclip.paste()
        last_change_time = start_time
        
        while time.time() - start_time < MAX_WAIT_TIME:
            current_clipboard = pyperclip.paste()
            
            if current_clipboard != last_clipboard:
                # Clipboard changed, wait to see if it stabilizes
                time.sleep(0.5)
                if pyperclip.paste() == current_clipboard:
                    return current_clipboard
                last_change_time = time.time()
            
            # If no changes for 5 seconds, assume response is complete
            if time.time() - last_change_time > 5.0:
                return current_clipboard
            
            time.sleep(RESPONSE_CHECK_INTERVAL)
        
        logger.warning("Timeout waiting for THEA response")
        return None

    def _get_clipboard_text(self) -> Optional[str]:
        """Get text from clipboard with error handling.
        
        Returns:
            Optional[str]: Clipboard text or None if empty/invalid
        """
        try:
            text = pyperclip.paste()
            return text if text and text.strip() else None
        except Exception as e:
            logger.error(f"Error getting clipboard text: {e}")
            return None

def extract_thea_response(config: AppConfig) -> Optional[str]:
    """Convenience function to extract THEA's response.
    
    Args:
        config: Application configuration
        
    Returns:
        Optional[str]: The extracted response text, or None if extraction failed
    """
    extractor = TheaOutputExtractor(config)
    return extractor.extract_response() 