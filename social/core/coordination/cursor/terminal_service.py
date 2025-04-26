"""
Provides a high-level async service interface for interacting with the Cursor terminal.
Wraps the synchronous CursorTerminalController.
"""
import logging
from typing import List, Optional, Any

# Relative import assumes this service is in the same directory as the controller file
from .cursor_terminal_controller import CursorTerminalController

logger = logging.getLogger(__name__)

class CursorTerminalService:
    """Service layer for Cursor terminal operations."""

    def __init__(self, controller: CursorTerminalController):
        """
        Initializes the service with a terminal controller instance.

        Args:
            controller: The CursorTerminalController instance to wrap.
        """
        if not isinstance(controller, CursorTerminalController):
             raise TypeError("controller must be an instance of CursorTerminalController")
        self.controller = controller
        logger.info(f"CursorTerminalService initialized with controller for identifier: {self.controller.identifier}")

    async def run_command(self, command: str, wait: bool = True) -> bool:
        """
        Runs a command in the associated Cursor terminal.

        Args:
            command: The command string to execute.
            wait: If True, waits for command completion before returning.

        Returns:
            True if the command execution was successful (or started successfully if wait=False),
            False otherwise.
        """
        logger.info(f"Service request: Run command '{command}' (wait={wait})")
        try:
            # Note: Calling synchronous controller method directly from async method.
            # Consider using asyncio.to_thread in production if controller methods are blocking.
            success = self.controller.run_command(command, wait_for_completion=wait)
            return success
        except Exception as e:
            logger.error(f"Error running command '{command}' via controller: {e}", exc_info=True)
            return False

    async def get_output(self, max_lines: Optional[int] = None) -> Optional[List[str]]:
        """
        Retrieves the recent output lines from the associated Cursor terminal.

        Args:
            max_lines: Optional maximum number of recent lines to retrieve.

        Returns:
            A list of output lines, or None if an error occurred.
        """
        logger.debug(f"Service request: Get output (max_lines={max_lines})")
        try:
            # Note: Calling synchronous controller method directly from async method.
            output = self.controller.get_output(max_lines=max_lines)
            # Controller returns [] on success but no output, ensure we don't return None in that case
            return output if output is not None else []
        except Exception as e:
            logger.error(f"Error getting output from controller: {e}", exc_info=True)
            return None

    async def get_current_directory(self) -> Optional[str]:
        """
        Gets the current working directory simulated by the controller.

        Returns:
            The current working directory path, or None if unavailable.
        """
        logger.debug("Service request: Get current directory")
        try:
            # Note: Calling synchronous controller method directly from async method.
            return self.controller.get_current_directory()
        except Exception as e:
            logger.error(f"Error getting current directory from controller: {e}", exc_info=True)
            return None

    async def send_input(self, text_input: str) -> bool:
        """
        Sends input text to the currently running process in the terminal.

        Args:
            text_input: The text to send (newline is typically appended by controller).

        Returns:
            True if input was sent successfully, False otherwise.
        """
        logger.info(f"Service request: Send input '{text_input[:50]}...'")
        try:
            # Note: Calling synchronous controller method directly from async method.
            return self.controller.send_input(text_input)
        except Exception as e:
            logger.error(f"Error sending input via controller: {e}", exc_info=True)
            return False

    async def is_busy(self) -> bool:
        """
        Checks if the terminal controller is currently executing a command.

        Returns:
            True if busy, False otherwise.
        """
        logger.debug("Service request: Check if busy")
        try:
            # Note: Calling synchronous controller method directly from async method.
            return self.controller.is_busy()
        except Exception as e:
            logger.error(f"Error checking busy state via controller: {e}", exc_info=True)
            # Default to assuming busy on error? Or False? Let's assume not busy on error.
            return False 
