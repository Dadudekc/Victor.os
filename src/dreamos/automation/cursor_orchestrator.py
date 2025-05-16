import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, Literal, Optional, Tuple, Type

# Attempt PyAutoGUI/Pyperclip imports
try:
    import pyautogui
    import pyperclip
    from pyautogui import FailSafeException
    from pyperclip import PyperclipException

    UI_AUTOMATION_AVAILABLE = True
except ImportError as e:
    logging.error(
        f"CursorOrchestrator requires pyautogui and pyperclip. Install them first. Error: {e}"
    )
    pyautogui = None
    pyperclip = None
    # Define FailSafeException and PyperclipException as generic Exception if modules not found
    # to avoid NameErrors later, though functionality will be broken.
    if "pyautogui" not in str(e):
        FailSafeException = Exception  # Fallback
    if "pyperclip" not in str(e):
        PyperclipException = Exception  # Fallback
    UI_AUTOMATION_AVAILABLE = False

import tenacity

from src.dreamos.core.config import AppConfig
from src.dreamos.core.coordination.agent_bus import AgentBus, BaseEvent, EventType
from src.dreamos.core.coordination.event_payloads import (
    AgentStatusEventPayload,
    CursorResultPayload,
)
from src.dreamos.core.errors import ToolError as CoreToolError
from src.dreamos.utils.decorators import retry_on_exception
from src.dreamos.utils.gui_utils import wait_for_element

# Import pygetwindow if available for recovery checks
try:
    import pygetwindow
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    pygetwindow = None
    PYGETWINDOW_AVAILABLE = False

logger = logging.getLogger(__name__)

# Agent Status Types
AgentStatus = Literal[
    "UNKNOWN",
    "IDLE",
    "INJECTING",
    "AWAITING_RESPONSE",
    "COPYING",
    "ERROR",
    "UNRESPONSIVE",
]

# Define tuple of retryable exceptions
RETRYABLE_UI_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    FailSafeException,
    PyperclipException,
    asyncio.TimeoutError,
)

class CursorOrchestratorError(CoreToolError):
    """Custom exception for Cursor Orchestrator errors."""
    pass

class CursorOrchestrator:
    """Manages interaction with multiple Cursor UI instances.

    Provides methods to inject prompts, retrieve responses, and manage the state
    of Cursor windows associated with specific agent IDs. Operates as a singleton.
    Handles coordinate loading and orchestrates UI automation via pyautogui/pyperclip.
    """

    _instance = None
    _lock = asyncio.Lock()
    _initialization_lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(CursorOrchestrator, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        config: AppConfig,
        agent_bus: Optional[AgentBus] = None,
    ):
        """Initializes the CursorOrchestrator singleton instance.

        Args:
            config: The loaded AppConfig instance containing settings.
            agent_bus: Optional AgentBus instance. If None, gets the default singleton.

        Raises:
            CursorOrchestratorError: If UI dependencies missing or no coords loaded.
            ValueError: If config object is not provided.
        """
        if not config:
            logger.error(
                "CRITICAL: AppConfig instance was not provided to CursorOrchestrator.__init__."
            )
            raise ValueError("AppConfig instance is required for CursorOrchestrator.")

        if not UI_AUTOMATION_AVAILABLE:
            raise CursorOrchestratorError(
                "Dependencies (pyautogui, pyperclip) not installed."
            )

        if hasattr(self, "_initialized") and self._initialized:
            logger.debug("CursorOrchestrator already initialized.")
            return

        self._app_config = config
        self.config = config.gui_automation

        if not hasattr(self.config, "input_coords_file_path") or self.config.input_coords_file_path is None:
            raise CursorOrchestratorError(
                "input_coords_file_path missing in GuiAutomationConfig."
            )
        if not hasattr(self.config, "copy_coords_file_path") or self.config.copy_coords_file_path is None:
            raise CursorOrchestratorError(
                "copy_coords_file_path missing in GuiAutomationConfig."
            )

        self.input_coords_path = Path(self.config.input_coords_file_path).resolve()
        self.copy_coords_path = Path(self.config.copy_coords_file_path).resolve()
        self.agent_bus = agent_bus or AgentBus()
        self.input_coordinates: Dict[str, Tuple[int, int]] = {}
        self.copy_coordinates: Dict[str, Tuple[int, int]] = {}
        self.agent_status: Dict[str, AgentStatus] = {}
        self._load_all_coordinates()
        self._initialize_agent_status()
        self._initialized = True
        logger.info("CursorOrchestrator initialized.")

    def _load_all_coordinates(self):
        """Loads all coordinate mappings from JSON files."""
        try:
            if not self.input_coords_path.exists():
                raise CursorOrchestratorError(
                    f"Input coordinates file not found: {self.input_coords_path}"
                )
            if not self.copy_coords_path.exists():
                raise CursorOrchestratorError(
                    f"Copy coordinates file not found: {self.copy_coords_path}"
                )

            with open(self.input_coords_path, "r") as f:
                self.input_coordinates = json.load(f)
            with open(self.copy_coords_path, "r") as f:
                self.copy_coordinates = json.load(f)

            if not self.input_coordinates or not self.copy_coordinates:
                raise CursorOrchestratorError("No coordinates loaded from files.")
        except Exception as e:
            raise CursorOrchestratorError(f"Failed to load coordinates: {e}")

    def _initialize_agent_status(self):
        """Initialize status tracking for all known agents."""
        for agent_id in self.input_coordinates.keys():
            self.agent_status[agent_id] = "IDLE"

    async def _set_agent_status(
        self,
        agent_id: str,
        status: AgentStatus,
        event_type: Optional[EventType] = None,
        event_data: Optional[Dict] = None,
    ):
        """Updates agent status and emits event if provided."""
        async with self._lock:
            self.agent_status[agent_id] = status
            if event_type and event_data:
                await self.agent_bus.emit(
                    event_type,
                    AgentStatusEventPayload(
                        agent_id=agent_id,
                        status=status,
                        data=event_data,
                    ),
                )

    async def get_agent_status(self, agent_id: str) -> AgentStatus:
        """Gets current status of specified agent."""
        async with self._lock:
            return self.agent_status.get(agent_id, "UNKNOWN")

    async def inject_prompt(
        self,
        agent_id: str,
        prompt: str,
        timeout: Optional[float] = None,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Injects a prompt into the specified agent's Cursor window.

        Args:
            agent_id: The ID of the target agent.
            prompt: The text to inject.
            timeout: Optional timeout in seconds.
            correlation_id: Optional correlation ID for tracking.

        Returns:
            bool: True if injection was successful.

        Raises:
            CursorOrchestratorError: If injection fails.
        """
        if agent_id not in self.input_coordinates:
            raise CursorOrchestratorError(f"Unknown agent ID: {agent_id}")

        await self._set_agent_status(
            agent_id,
            "INJECTING",
            EventType.AGENT_STATUS_CHANGED,
            {"correlation_id": correlation_id},
        )

        try:
            x, y = self.input_coordinates[agent_id]
            target_window_title = f"Cursor - Agent {agent_id}"

            def injection_task():
                self._perform_injection_sequence(x, y, prompt, agent_id, target_window_title)

            if timeout:
                await asyncio.wait_for(
                    asyncio.to_thread(injection_task),
                    timeout=timeout,
                )
            else:
                await asyncio.to_thread(injection_task)

            await self._set_agent_status(
                agent_id,
                "AWAITING_RESPONSE",
                EventType.AGENT_STATUS_CHANGED,
                {"correlation_id": correlation_id},
            )
            return True

        except asyncio.TimeoutError:
            await self._set_agent_status(
                agent_id,
                "ERROR",
                EventType.AGENT_STATUS_CHANGED,
                {"error": "Injection timeout", "correlation_id": correlation_id},
            )
            raise CursorOrchestratorError(f"Injection timeout for agent {agent_id}")
        except Exception as e:
            await self._set_agent_status(
                agent_id,
                "ERROR",
                EventType.AGENT_STATUS_CHANGED,
                {"error": str(e), "correlation_id": correlation_id},
            )
            raise CursorOrchestratorError(f"Injection failed for agent {agent_id}: {e}")

    def _check_and_recover_focus(
        self, target_title: str, agent_id_for_log: str
    ) -> bool:
        """Checks and recovers window focus if needed."""
        if not PYGETWINDOW_AVAILABLE:
            logger.warning("pygetwindow not available for focus recovery")
            return True

        try:
            target_window = pygetwindow.getWindowsWithTitle(target_title)
            if not target_window:
                logger.error(f"Window not found: {target_title}")
                return False

            target_window = target_window[0]
            if not target_window.isActive:
                logger.info(f"Recovering focus for {target_title}")
                target_window.activate()
                time.sleep(0.5)  # Allow window to activate
            return True
        except Exception as e:
            logger.error(f"Focus recovery failed: {e}")
            return False

    def _perform_injection_sequence(
        self, x: int, y: int, text: str, agent_id_for_log: str, target_window_title: str
    ):
        """Performs the actual injection sequence."""
        if not self._check_and_recover_focus(target_window_title, agent_id_for_log):
            raise CursorOrchestratorError("Failed to recover window focus")

        try:
            # Click the target location
            pyautogui.click(x, y)
            time.sleep(0.1)

            # Clear existing text (Ctrl+A, Delete)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.press("delete")
            time.sleep(0.1)

            # Type the new text
            pyautogui.write(text)
            time.sleep(0.1)

            # Press Enter to submit
            pyautogui.press("enter")

        except FailSafeException:
            raise CursorOrchestratorError("Fail-safe triggered during injection")
        except Exception as e:
            raise CursorOrchestratorError(f"Injection sequence failed: {e}")

    async def retrieve_response(
        self,
        agent_id: str,
        timeout: Optional[float] = None,
        correlation_id: Optional[str] = None,
    ) -> Optional[str]:
        """Retrieves response from specified agent's Cursor window.

        Args:
            agent_id: The ID of the target agent.
            timeout: Optional timeout in seconds.
            correlation_id: Optional correlation ID for tracking.

        Returns:
            Optional[str]: The retrieved response text, or None if failed.

        Raises:
            CursorOrchestratorError: If retrieval fails.
        """
        if agent_id not in self.copy_coordinates:
            raise CursorOrchestratorError(f"Unknown agent ID: {agent_id}")

        await self._set_agent_status(
            agent_id,
            "COPYING",
            EventType.AGENT_STATUS_CHANGED,
            {"correlation_id": correlation_id},
        )

        try:
            x, y = self.copy_coordinates[agent_id]
            target_window_title = f"Cursor - Agent {agent_id}"

            def copy_task():
                return self._perform_copy_sequence(x, y, agent_id, target_window_title)

            if timeout:
                response = await asyncio.wait_for(
                    asyncio.to_thread(copy_task),
                    timeout=timeout,
                )
            else:
                response = await asyncio.to_thread(copy_task)

            if response:
                await self._set_agent_status(
                    agent_id,
                    "IDLE",
                    EventType.AGENT_STATUS_CHANGED,
                    {"correlation_id": correlation_id},
                )
                return response
            else:
                await self._set_agent_status(
                    agent_id,
                    "ERROR",
                    EventType.AGENT_STATUS_CHANGED,
                    {"error": "Empty response", "correlation_id": correlation_id},
                )
                return None

        except asyncio.TimeoutError:
            await self._set_agent_status(
                agent_id,
                "ERROR",
                EventType.AGENT_STATUS_CHANGED,
                {"error": "Retrieval timeout", "correlation_id": correlation_id},
            )
            raise CursorOrchestratorError(f"Retrieval timeout for agent {agent_id}")
        except Exception as e:
            await self._set_agent_status(
                agent_id,
                "ERROR",
                EventType.AGENT_STATUS_CHANGED,
                {"error": str(e), "correlation_id": correlation_id},
            )
            raise CursorOrchestratorError(f"Retrieval failed for agent {agent_id}: {e}")

    @retry_on_exception(max_attempts=3, exceptions=RETRYABLE_UI_EXCEPTIONS, delay=1.0)
    def _perform_copy_sequence(
        self, x: int, y: int, agent_id_for_log: str, target_window_title: str
    ) -> Optional[str]:
        """Performs the copy sequence with retries."""
        if not self._check_and_recover_focus(target_window_title, agent_id_for_log):
            raise CursorOrchestratorError("Failed to recover window focus")

        try:
            # Click the target location
            pyautogui.click(x, y)
            time.sleep(0.1)

            # Select all and copy
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.1)

            # Get clipboard content
            return pyperclip.paste()

        except FailSafeException:
            raise CursorOrchestratorError("Fail-safe triggered during copy")
        except PyperclipException as e:
            raise CursorOrchestratorError(f"Clipboard error: {e}")
        except Exception as e:
            raise CursorOrchestratorError(f"Copy sequence failed: {e}")

    @retry_on_exception(max_attempts=2, exceptions=(FailSafeException,), delay=0.5)
    def _perform_health_check_click(self, x: int, y: int, agent_id_for_log: str):
        """Performs a health check click with retries."""
        try:
            pyautogui.click(x, y)
            time.sleep(0.1)
        except FailSafeException:
            raise CursorOrchestratorError("Fail-safe triggered during health check")

    async def check_window_health(self, agent_id: str) -> bool:
        """Checks if the agent's Cursor window is responsive.

        Args:
            agent_id: The ID of the target agent.

        Returns:
            bool: True if window is healthy, False otherwise.

        Raises:
            CursorOrchestratorError: If health check fails.
        """
        if agent_id not in self.input_coordinates:
            raise CursorOrchestratorError(f"Unknown agent ID: {agent_id}")

        try:
            x, y = self.input_coordinates[agent_id]
            target_window_title = f"Cursor - Agent {agent_id}"

            if not self._check_and_recover_focus(target_window_title, agent_id):
                return False

            await asyncio.to_thread(
                self._perform_health_check_click, x, y, agent_id
            )
            return True

        except Exception as e:
            logger.error(f"Health check failed for agent {agent_id}: {e}")
            return False

    async def start_listening(self):
        """Starts listening for cursor action events."""
        logger.info("Starting CursorOrchestrator event listener...")
        self.agent_bus.subscribe(EventType.CURSOR_ACTION, self._handle_cursor_action_event)
        logger.info("CursorOrchestrator listener started.")

    async def _handle_cursor_action_event(self, event: BaseEvent):
        """Handles cursor action events from the bus."""
        try:
            if not isinstance(event.payload, dict):
                logger.error("Invalid event payload type")
                return

            action = event.payload.get("action")
            agent_id = event.payload.get("agent_id")
            prompt = event.payload.get("prompt")

            if not all([action, agent_id]):
                logger.error("Missing required event payload fields")
                return

            if action == "inject" and prompt:
                await self.inject_prompt(agent_id, prompt)
            elif action == "retrieve":
                response = await self.retrieve_response(agent_id)
                if response:
                    await self.agent_bus.emit(
                        EventType.CURSOR_RESULT,
                        CursorResultPayload(
                            agent_id=agent_id,
                            result=response,
                        ),
                    )

        except Exception as e:
            logger.error(f"Error handling cursor action event: {e}")

    async def initialize(self):
        """Initializes the orchestrator asynchronously."""
        logger.info("CursorOrchestrator async initialization starting...")
        await self.start_listening()
        logger.info("CursorOrchestrator async initialization complete.")

    async def shutdown(self):
        """Shuts down the orchestrator gracefully."""
        logger.info("CursorOrchestrator shutting down...")
        try:
            # Unsubscribe from events
            self.agent_bus.unsubscribe(EventType.CURSOR_ACTION, self._handle_cursor_action_event)
            
            # Reset agent statuses
            async with self._lock:
                for agent_id in self.agent_status:
                    self.agent_status[agent_id] = "UNKNOWN"
            
            # Clear instance
            self._instance = None
            self._initialized = False
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            logger.info("CursorOrchestrator shut down.")

async def get_cursor_orchestrator(
    config: Optional[AppConfig] = None,
    agent_bus: Optional[AgentBus] = None,
) -> CursorOrchestrator:
    """Factory function to get the CursorOrchestrator singleton instance.

    Args:
        config: Optional AppConfig instance. Required if not already initialized.
        agent_bus: Optional AgentBus instance.

    Returns:
        The initialized CursorOrchestrator singleton instance.

    Raises:
        CursorOrchestratorError: If the orchestrator hasn't been initialized yet.
    """
    if (
        CursorOrchestrator._instance is None
        or not CursorOrchestrator._instance._initialized
    ):
        if not config:
            raise CursorOrchestratorError(
                "get_cursor_orchestrator called before CursorOrchestrator was initialized!"
            )
        return CursorOrchestrator(config, agent_bus)

    return CursorOrchestrator._instance 