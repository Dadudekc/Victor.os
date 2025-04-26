# social/core/coordination/cursor/locator_service.py

import logging
from typing import Optional, Dict, Any

# Assuming CursorElementLocator and ElementInfo are defined elsewhere
from .cursor_element_locator import CursorElementLocator, ElementInfo # Corrected import

logger = logging.getLogger("CursorLocatorService")

# Placeholder for ElementInfo type if not imported
# ElementInfo = Dict[str, Any] # Type is now imported

class CursorLocatorService:
    """Service layer for locating UI elements within Cursor."""

    def __init__(self, locator_controller: CursorElementLocator):
        """Initializes the service with an element locator controller instance."""
        # TODO: Add type hint for locator_controller when its definition is known
        if not isinstance(locator_controller, CursorElementLocator):
             raise TypeError("controller must be an instance of CursorElementLocator")
        self.locator_controller = locator_controller
        logger.info(f"CursorLocatorService initialized with controller: {type(locator_controller).__name__}")

    async def find_element_by_text(self, text: str, timeout: int = 10) -> Optional[ElementInfo]:
        """
        Finds an element containing specific text using the locator controller.

        Args:
            text: The text to search for within an element.
            timeout: Maximum time in seconds to search.

        Returns:
            A dictionary with element information (e.g., bbox, id) or None if not found/error.
        """
        logger.info(f"Service request: Find element by text '{text}' (timeout={timeout}s)")
        try:
            # Assuming locator_controller.find_element_by_text is synchronous
            # Use asyncio.to_thread if this becomes a blocking issue
            return self.locator_controller.find_element_by_text(text, timeout=timeout)
        except Exception as e:
            logger.error(f"Failed to find element by text '{text}': {e}", exc_info=True)
            return None

    async def find_element_by_id(self, element_id: str, timeout: int = 10) -> Optional[ElementInfo]:
        """
        Finds an element by its accessibility ID or similar identifier.

        Args:
            element_id: The ID to search for.
            timeout: Maximum time in seconds to search.

        Returns:
            A dictionary with element information or None if not found/error.
        """
        logger.info(f"Service request: Find element by ID '{element_id}' (timeout={timeout}s)")
        try:
            # Assuming locator_controller.find_element_by_id is synchronous
            return self.locator_controller.find_element_by_id(element_id, timeout=timeout)
        except Exception as e:
            logger.error(f"Failed to find element by ID '{element_id}': {e}", exc_info=True)
            return None

    async def find_element_by_image(self, image_path: str, confidence: float = 0.8, timeout: int = 15) -> Optional[ElementInfo]:
        """
        Finds an element based on image matching.

        Args:
            image_path: Path to the template image.
            confidence: Minimum matching confidence level (implementation specific).
            timeout: Maximum time in seconds to search.

        Returns:
            A dictionary with element information or None if not found/error.
        """
        logger.info(f"Service request: Find element by image '{image_path}' (confidence={confidence:.1f}, timeout={timeout}s)")
        try:
            # Assuming locator_controller.find_element_by_image is synchronous
            return self.locator_controller.find_element_by_image(image_path, confidence=confidence, timeout=timeout)
        except Exception as e:
            logger.error(f"Failed to find element by image '{image_path}': {e}", exc_info=True)
            return None 
