# social/core/coordination/cursor/window_service.py

import logging
from typing import Optional, Tuple

# Assuming CursorWindowController is defined elsewhere
from .cursor_window_controller import CursorWindowController # Corrected import

logger = logging.getLogger("CursorWindowService")

class CursorWindowService:
    """
    High-level service wrapper for controlling the Cursor application window.
    Delegates to the injected low-level window controller.
    """

    def __init__(self, window_controller: CursorWindowController):
        """Initializes the service with a window controller instance."""
        # TODO: Add type hint for window_controller when its definition is known
        if not isinstance(window_controller, CursorWindowController):
             raise TypeError("controller must be an instance of CursorWindowController")
        self.window_controller = window_controller
        logger.info(f"CursorWindowService initialized with controller: {type(window_controller).__name__}")

    async def focus(self, window_title: Optional[str] = None) -> bool:
        """
        Brings the Cursor window to the foreground and ensures it's ready for input.
        If a specific title is needed, it can be passed explicitly.
        """
        try:
            logger.info(f"Service request: Focusing Cursor window{' titled ' + window_title if window_title else ''}...")
            # Assuming window_controller.focus_window is async
            return await self.window_controller.focus_window(window_title)
        except Exception as e:
            logger.error(f"Failed to focus window: {e}", exc_info=True)
            return False

    async def resize(self, width: int, height: int) -> bool:
        """
        Resizes the Cursor window to the specified dimensions.
        """
        try:
            logger.info(f"Service request: Resizing window to width={width}, height={height}...")
            # Assuming window_controller.resize_window is async
            return await self.window_controller.resize_window(width, height)
        except Exception as e:
            logger.error(f"Failed to resize window: {e}", exc_info=True)
            return False

    async def move(self, x: int, y: int) -> bool:
        """
        Moves the Cursor window to the specified (x, y) screen coordinates.
        """
        try:
            logger.info(f"Service request: Moving window to position x={x}, y={y}...")
            # Assuming window_controller.move_window is async
            return await self.window_controller.move_window(x, y)
        except Exception as e:
            logger.error(f"Failed to move window: {e}", exc_info=True)
            return False

    async def get_bounds(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Returns the bounding box of the window as (x, y, width, height).
        """
        try:
            logger.debug("Service request: Get window bounds")
            # Assuming window_controller.get_window_bounds is async
            bounds = await self.window_controller.get_window_bounds()
            logger.info(f"Window bounds obtained: {bounds}")
            return bounds
        except Exception as e:
            logger.error(f"Failed to get window bounds: {e}", exc_info=True)
            return None

    async def is_active(self) -> bool:
        """
        Checks if the Cursor window is currently focused and receiving input.
        """
        try:
            logger.debug("Service request: Check if window is active")
            # Assuming window_controller.is_window_active is async
            active = await self.window_controller.is_window_active()
            logger.debug(f"Window active status: {active}")
            return active
        except Exception as e:
            logger.error(f"Failed to check window active status: {e}", exc_info=True)
            return False

    async def minimize(self) -> bool:
        """
        Minimizes the Cursor window.
        """
        try:
            logger.info("Service request: Minimizing Cursor window...")
            # Assuming window_controller.minimize is async
            return await self.window_controller.minimize()
        except Exception as e:
            logger.error(f"Failed to minimize window: {e}", exc_info=True)
            return False

    async def restore(self) -> bool:
        """
        Restores the Cursor window if it was minimized.
        """
        try:
            logger.info("Service request: Restoring Cursor window...")
            # Assuming window_controller.restore is async
            return await self.window_controller.restore()
        except Exception as e:
            logger.error(f"Failed to restore window: {e}", exc_info=True)
            return False 