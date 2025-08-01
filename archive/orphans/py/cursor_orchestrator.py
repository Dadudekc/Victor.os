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
        f"CursorOrchestrator requires pyautogui and pyperclip. Install them first. Error: {e}"  # noqa: E501
    )
    pyautogui = None
    pyperclip = None
    # Define FailSafeException and PyperclipException as generic Exception if modules not found  # noqa: E501
    # to avoid NameErrors later, though functionality will be broken.
    if "pyautogui" not in str(e):
        FailSafeException = Exception  # Fallback
    if "pyperclip" not in str(e):
        PyperclipException = Exception  # Fallback
    UI_AUTOMATION_AVAILABLE = False

import tenacity  # Assuming tenacity was added by Agent 4

# EDIT START: Add AppConfig import for type hint
from dreamos.core.config import AppConfig

# Local imports (assuming sibling modules)
# from .response_retriever import ResponseRetriever # Logic will be integrated
# from .cursor_injector import inject_prompt # Logic will be integrated
from dreamos.core.coordination.agent_bus import AgentBus, BaseEvent, EventType
from dreamos.core.coordination.event_payloads import (
    AgentStatusEventPayload,
    CursorResultPayload,
)
from dreamos.core.coordination.event_types import EventType

# EDIT END
# EDIT START: Import core ToolError and new wait utility
from dreamos.core.errors import ToolError as CoreToolError

# EDIT START: Import retry decorator # ADDED BY THEA / Agent-1 Auto-Correction
from dreamos.utils.decorators import retry_on_exception
from dreamos.utils.gui_utils import wait_for_element

# EDIT START: Remove unused Selenium imports
# from selenium.common.exceptions import (
#     NoSuchElementException,
#     TimeoutException,
#     WebDriverException,
# )
# from selenium.webdriver.support import expected_conditions as EC
# EDIT END


# EDIT START: Remove import of find_project_root - use AppConfig
# from dreamos.utils.project_root import find_project_root
# EDIT END

# EDIT START: Import pygetwindow if available for recovery checks
try:
    import pygetwindow

    PYGETWINDOW_AVAILABLE = True
except ImportError:
    pygetwindow = None
    PYGETWINDOW_AVAILABLE = False
    # Warning already logged during main import attempts
# EDIT END

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
    asyncio.TimeoutError,  # If timeouts are implemented and raised
    # Add other potentially transient exceptions here
)


# EDIT START: Change inheritance to CoreToolError
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
        config: AppConfig,  # Use direct type hint
        agent_bus: Optional[AgentBus] = None,
    ):
        """Initializes the CursorOrchestrator singleton instance.

        Loads coordinates, initializes agent statuses, uses AppConfig for settings,
        and optionally accepts an AgentBus instance.

        Args:
            config: The loaded AppConfig instance containing settings.
            agent_bus: Optional AgentBus instance. If None, gets the default singleton.

        Raises:
            CursorOrchestratorError: If UI dependencies missing or no coords loaded.
            ValueError: If config object is not provided.
        """
        # EDIT START: Remove local import patch for AppConfig
        # from dreamos.utils.import_debugger import try_import
        # AppConfig_local = try_import(lambda: __import__("dreamos.core.config", fromlist=["AppConfig"]).AppConfig, label="CursorOrchestrator.__init__ -> AppConfig")
        # EDIT END

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

        self._app_config = config  # Store the full config passed in

        # Ensure gui_automation exists on the config object before accessing its attributes
        if not hasattr(config, "gui_automation") or config.gui_automation is None:
            raise CursorOrchestratorError(
                "gui_automation settings missing in AppConfig for CursorOrchestrator."
            )

        self.config = config.gui_automation  # Keep direct access to relevant section

        # Ensure paths are available on self.config (which is config.gui_automation)
        if (
            not hasattr(self.config, "input_coords_file_path")
            or self.config.input_coords_file_path is None
        ):
            raise CursorOrchestratorError(
                "input_coords_file_path missing in GuiAutomationConfig."
            )
        if (
            not hasattr(self.config, "copy_coords_file_path")
            or self.config.copy_coords_file_path is None
        ):
            raise CursorOrchestratorError(
                "copy_coords_file_path missing in GuiAutomationConfig."
            )

        self.input_coords_path = Path(self.config.input_coords_file_path).resolve()
        self.copy_coords_path = Path(self.config.copy_coords_file_path).resolve()
        self.agent_bus = agent_bus or AgentBus()
        self.input_coordinates: Dict[str, Tuple[int, int]] = {}
        self.copy_coordinates: Dict[str, Tuple[int, int]] = {}
        self.agent_status: Dict[str, AgentStatus] = {}
        self._load_all_coordinates()  # This can raise CursorOrchestratorError
        self._initialize_agent_status()
        self._initialized = True
        logger.info("CursorOrchestrator initialized.")

    def _load_all_coordinates(self):
        """Loads both input and copy coordinates."""
        try:
            if self.input_coords_path.exists():
                with open(self.input_coords_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.input_coordinates = {
                        agent_id: (coords["x"], coords["y"])
                        for agent_id, coords in data.items()
                        if isinstance(coords, dict) and "x" in coords and "y" in coords
                    }
                logger.info(f"Loaded {len(self.input_coordinates)} input coordinates.")
            else:
                logger.error(
                    f"Input coordinates file not found: {self.input_coords_path}"
                )

            if self.copy_coords_path.exists():
                with open(self.copy_coords_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.copy_coordinates = {
                        agent_id: tuple(coords)
                        for agent_id, coords in data.items()
                        if isinstance(coords, list)
                        and len(coords) == 2
                        and all(isinstance(c, int) for c in coords)
                    }
                logger.info(f"Loaded {len(self.copy_coordinates)} copy coordinates.")
            else:
                logger.error(
                    f"Copy coordinates file not found: {self.copy_coords_path}"
                )

            if not self.input_coordinates and not self.copy_coordinates:
                raise CursorOrchestratorError(
                    "No coordinates loaded. Orchestrator cannot function."
                )

        except Exception as e:
            logger.exception(f"Error loading coordinates: {e}")
            raise CursorOrchestratorError(f"Failed to load coordinates: {e}")

    def _initialize_agent_status(self):
        """Initializes status for all agents found in coordinates."""
        all_agent_ids = set(self.input_coordinates.keys()) | set(
            self.copy_coordinates.keys()
        )
        for agent_id in all_agent_ids:
            self.agent_status[agent_id] = "IDLE"
        logger.info(f"Initialized status for {len(all_agent_ids)} agents.")

    async def _set_agent_status(
        self,
        agent_id: str,
        status: AgentStatus,
        event_type: Optional[EventType] = None,
        event_data: Optional[Dict] = None,
    ):
        """(Internal) Sets agent status and optionally emits an event."""
        async with self._lock:
            self.agent_status[agent_id] = status
            logger.debug(f"Status change: {agent_id} -> {status}")

            if event_type and self.agent_bus:
                # Combine base data with specific payload structure
                base_event_data = event_data or {}
                correlation_id = base_event_data.get("correlation_id")

                # Assuming status changes are system events, use AgentStatusEventPayload  # noqa: E501
                payload = AgentStatusEventPayload(
                    agent_id=agent_id,
                    status=status,
                    task_id=base_event_data.get(
                        "task_id"
                    ),  # Get optional fields from input
                    error_message=base_event_data.get("error"),
                    # Add other fields from AgentStatusEventPayload if present in event_data  # noqa: E501
                )

                event = BaseEvent(
                    event_type=event_type,  # Use the passed event_type
                    source_id="CursorOrchestrator",
                    data=payload.__dict__,  # Convert dataclass to dict
                    correlation_id=correlation_id,
                )
                try:
                    # Use create_task for fire-and-forget dispatch
                    asyncio.create_task(self.agent_bus.dispatch_event(event))
                    logger.debug(f"Dispatched event {event_type.value} for {agent_id}")
                except Exception as e:
                    logger.error(
                        f"Failed to dispatch status event {event_type} for {agent_id}: {e}"  # noqa: E501
                    )

    async def get_agent_status(self, agent_id: str) -> AgentStatus:
        """Retrieves the current operational status of a specific agent's Cursor window.

        Args:
            agent_id: The ID of the agent whose status is requested.

        Returns:
            The current AgentStatus (e.g., "IDLE", "INJECTING", "ERROR", "UNKNOWN").
        """
        async with self._lock:
            return self.agent_status.get(agent_id, "UNKNOWN")

    # --- Core Interaction Methods ---

    async def inject_prompt(
        self,
        agent_id: str,
        prompt: str,
        timeout: Optional[float] = None,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Injects a prompt into the specified agent's Cursor window.

        Handles window focus, UI automation, and state management.

        Args:
            agent_id: The ID of the target agent's Cursor window.
            prompt: The text prompt to inject.
            timeout: (Currently unused) Timeout duration.
            correlation_id: Optional correlation ID for event tracking.

        Returns:
            True if injection was successful, False otherwise.

        Raises:
            CursorOrchestratorError: For critical UI automation failures.
        """
        # Target for log messages, include correlation_id if available
        log_target_id = f"{agent_id}{f' (CorrID: {correlation_id})' if correlation_id else ''}"  # noqa E501

        if agent_id not in self.input_coordinates:
            logger.error(
                f"inject_prompt for {log_target_id}: No input coordinates found."
            )
            # Publish failure event
            payload = CursorResultPayload(
                operation="inject",
                status="FAILURE",
                message="Missing input coordinates",
                correlation_id=correlation_id,
            )
            await self.agent_bus.publish(
                Event(type=EventType.CURSOR_OPERATION_RESULT, data=payload.model_dump())
            )
            return False

        # Check and set agent status
        current_status = await self.get_agent_status(agent_id)
        if current_status not in [AgentStatus.IDLE, AgentStatus.AWAITING_USER_INPUT]:
            logger.warning(
                f"inject_prompt for {log_target_id}: Agent not IDLE or AWAITING_USER_INPUT (Status: {current_status}). Injection aborted."  # noqa E501
            )
            # Publish failure event
            payload = CursorResultPayload(
                operation="inject",
                status="FAILURE",
                message=f"Agent not ready, status: {current_status}",
                correlation_id=correlation_id,
            )
            await self.agent_bus.publish(
                Event(type=EventType.CURSOR_OPERATION_RESULT, data=payload.model_dump())
            )
            return False

        await self._set_agent_status(
            agent_id,
            AgentStatus.INJECTING,
        )

        x, y = self.input_coordinates[agent_id]
        target_window_title = (
            self.agent_window_titles.get(agent_id) or self.config.target_window_title
        )

        try:
            logger.info(
                f"Injecting prompt for {log_target_id} (len: {len(prompt)}). Coords: ({x},{y}), Window: '{target_window_title}'"  # noqa E501
            )
            # Use a retry mechanism for the UI automation part
            retry_decorator = retry_on_exception(
                max_attempts=self.config.retry_attempts,
                exceptions=RETRYABLE_UI_EXCEPTIONS,
                delay=self.config.retry_delay_seconds,
                logger=logger,
                log_message_prefix=f"inject_prompt UI for {log_target_id}: ",
            )
            # The function to be retried needs to be defined or callable here.
            # We wrap _perform_injection_sequence.
            # Note: If _perform_injection_sequence itself has @retry, this creates nested retries.
            # Ensure only one layer of retry for the same operation.
            # Assuming _perform_injection_sequence does NOT have @retry for this specific call pattern.

            # Wrapped function for retry
            def injection_task():
                self._perform_injection_sequence(
                    x, y, prompt, log_target_id, target_window_title
                )

            # Execute with retry
            await asyncio.to_thread(retry_decorator(injection_task))

            logger.info(f"Prompt injection successful for {log_target_id}.")
            await self._set_agent_status(
                agent_id,
                AgentStatus.AWAITING_RESPONSE,
            )
            # Publish success event
            payload = CursorResultPayload(
                operation="inject",
                status="SUCCESS",
                correlation_id=correlation_id,
            )
            await self.agent_bus.publish(
                Event(type=EventType.CURSOR_OPERATION_RESULT, data=payload.model_dump())
            )
            return True
        except (
            CursorOrchestratorError
        ) as e:  # Catch specific errors from _perform_injection_sequence
            logger.error(
                f"inject_prompt for {log_target_id} failed: {e}", exc_info=False
            )  # Set exc_info=False if e already contains good summary
            await self._set_agent_status(
                agent_id,
                AgentStatus.ERROR,
                event_data={"error": str(e), "correlation_id": correlation_id},
            )
            # Publish failure event
            payload = CursorResultPayload(
                operation="inject",
                status="FAILURE",
                message=str(e),
                correlation_id=correlation_id,
            )
            await self.agent_bus.publish(
                Event(type=EventType.CURSOR_OPERATION_RESULT, data=payload.model_dump())
            )
            return False
        except Exception as e:  # Catch any other unexpected errors
            logger.exception(
                f"Unexpected error during inject_prompt for {log_target_id}: {e}"
            )
            await self._set_agent_status(
                agent_id,
                AgentStatus.ERROR,
                event_data={"error": str(e), "correlation_id": correlation_id},
            )
            # Publish failure event for unexpected errors
            payload = CursorResultPayload(
                operation="inject",
                status="FAILURE",
                message=f"Unexpected error: {e}",
                correlation_id=correlation_id,
            )
            await self.agent_bus.publish(
                Event(type=EventType.CURSOR_OPERATION_RESULT, data=payload.model_dump())
            )
            return False

    # EDIT START: Add helper for focus check and recovery
    def _check_and_recover_focus(
        self, target_title: str, agent_id_for_log: str
    ) -> bool:
        """Checks if the target window is active, attempts recovery if not."""
        if not PYGETWINDOW_AVAILABLE or pygetwindow is None:
            logger.warning(
                f"[{agent_id_for_log}] Cannot check window focus: pygetwindow not available."  # noqa: E501
            )
            return True  # Assume focus is okay if we cannot check

        try:
            active_window = pygetwindow.getActiveWindow()
            if active_window and target_title.lower() in active_window.title.lower():
                logger.debug(
                    f"[{agent_id_for_log}] Window focus confirmed: {active_window.title}"  # noqa: E501
                )
                return True  # Focus is correct
            else:
                active_title = active_window.title if active_window else "None"
                logger.warning(
                    f"[{agent_id_for_log}] Target window '{target_title}' not active. Current: '{active_title}'. Attempting recovery (ESC)..."  # noqa: E501
                )
                # Attempt recovery (simple ESC press)
                if pyautogui:
                    pyautogui.press("esc")
                    time.sleep(0.3)  # Short pause after recovery attempt
                    # Re-check focus
                    active_window = pygetwindow.getActiveWindow()
                    if (
                        active_window
                        and target_title.lower() in active_window.title.lower()
                    ):
                        logger.info(
                            f"[{agent_id_for_log}] Recovery successful. Target window now active."  # noqa: E501
                        )
                        return True
                    else:
                        active_title = active_window.title if active_window else "None"
                        logger.error(
                            f"[{agent_id_for_log}] Recovery failed. Active window still '{active_title}'."  # noqa: E501
                        )
                        return False
                else:
                    logger.error(
                        f"[{agent_id_for_log}] Cannot attempt recovery: pyautogui not available."  # noqa: E501
                    )
                    return False  # Recovery impossible
        except Exception as e:
            logger.error(
                f"[{agent_id_for_log}] Error during window focus check/recovery: {e}",
                exc_info=True,
            )
            return False  # Assume failure on error

    # EDIT END

    def _perform_injection_sequence(
        self, x: int, y: int, text: str, agent_id_for_log: str, target_window_title: str
    ):
        """Executes the PyAutoGUI sequence for injecting text.

        Checks for window existence/focus before acting.
        Handles potential UI automation exceptions.
        """
        if not pyautogui:
            raise CursorOrchestratorError("PyAutoGUI is not available")

        logger.debug(f"_perform_injection_sequence for {agent_id_for_log} starting.")

        # --- ADDED: Window Focus/Existence Check ---
        try:
            target_windows = pyautogui.getWindowsWithTitle(target_window_title)
            if not target_windows:
                raise CursorOrchestratorError(
                    f"Target window '{target_window_title}' not found."
                )

            window = target_windows[0]  # Assume first match is the correct one
            if not window.isActive:
                logger.warning(
                    f"Target window '{target_window_title}' found but not active. Attempting to activate."  # noqa: E501
                )
                try:
                    window.activate()
                    time.sleep(0.5)  # Give time for activation
                    if not window.isActive:
                        raise CursorOrchestratorError(
                            f"Failed to activate target window '{target_window_title}'."
                        )
                except Exception as act_err:
                    raise CursorOrchestratorError(
                        f"Error activating target window '{target_window_title}': {act_err}"  # noqa: E501
                    )
            logger.debug(f"Target window '{target_window_title}' is active.")
        except Exception as win_err:
            logger.error(f"Window check failed for '{target_window_title}': {win_err}")
            raise CursorOrchestratorError(
                f"Window check failed: {win_err}"
            ) from win_err
        # --- END Window Check ---

        # Configurable delays
        move_delay = self.config.min_pause_seconds
        click_delay = self.config.min_pause_seconds
        type_interval = self.config.type_interval_seconds
        try:
            logger.debug(f"[{agent_id_for_log}] Moving mouse to ({x}, {y})")
            pyautogui.moveTo(x, y, duration=move_delay)
            time.sleep(click_delay)
            logger.debug(f"[{agent_id_for_log}] Clicking input field")
            pyautogui.click()
            time.sleep(click_delay * 2)
            logger.debug(f"[{agent_id_for_log}] Clearing field (Ctrl+A, Del)")
            pyautogui.hotkey("ctrl", "a")
            time.sleep(click_delay / 2)
            pyautogui.press("delete")
            time.sleep(click_delay)
            if pyperclip:
                logger.debug(
                    f"[{agent_id_for_log}] Copying text (len: {len(text)}) to clipboard"
                )
                pyperclip.copy(text)
                time.sleep(click_delay / 2)
                logger.debug(f"[{agent_id_for_log}] Pasting text (Ctrl+V)")
                pyautogui.hotkey("ctrl", "v")
            else:
                logger.debug(
                    f"[{agent_id_for_log}] Typing text (len: {len(text)}) fallback"
                )
                pyautogui.write(text, interval=type_interval)
            time.sleep(click_delay)

            # EDIT START: Check focus before pressing Enter
            if not self._check_and_recover_focus(target_window_title, agent_id_for_log):
                raise CursorOrchestratorError(
                    "Window focus lost or recovery failed before sending Enter."
                )
            # EDIT END

            logger.debug(f"[{agent_id_for_log}] Submitting (Enter)")
            pyautogui.press("enter")

            # EDIT START: Replace fixed sleep with explicit wait for readiness indicator
            # time.sleep(0.1) # REMOVED fixed sleep
            if (
                not self._app_config
                or not self._app_config.paths
                or not self._app_config.paths.project_root
            ):
                raise CursorOrchestratorError(
                    "AppConfig or project_root path missing for GUI snippets."
                )
            snippets_dir = (
                self._app_config.paths.project_root
                / "runtime"
                / "assets"
                / "gui_snippets"
            )
            readiness_image = snippets_dir / "cursor_response_ready_indicator.png"
            if readiness_image.exists():
                logger.info(
                    f"[{agent_id_for_log}] Waiting for response readiness indicator..."
                )
                wait_result = wait_for_element(
                    readiness_image, timeout=15.0
                )  # Increased timeout
                if wait_result:
                    logger.info(
                        f"[{agent_id_for_log}] Response readiness indicator found."
                    )
                else:
                    logger.warning(
                        f"[{agent_id_for_log}] Timeout waiting for response readiness indicator. Proceeding cautiously."  # noqa: E501
                    )
                    # Consider raising an error or different handling if indicator is critical  # noqa: E501
            else:
                logger.warning(
                    f"[{agent_id_for_log}] Readiness indicator image not found ({readiness_image.name}). Falling back to short fixed delay."  # noqa: E501
                )
                time.sleep(
                    1.0
                )  # Use a slightly longer fallback delay than original 0.1s
            # EDIT END

        except (
            FailSafeException,
            PyperclipException,
            CursorOrchestratorError,
        ) as e:  # Added CursorOrchestratorError
            logger.error(
                f"[{agent_id_for_log}] UI interaction failed during injection: {e}"
            )
            raise CursorOrchestratorError(f"Injection sequence error: {e}")
        except Exception as e:
            logger.exception(
                f"[{agent_id_for_log}] Unexpected error during injection: {e}"
            )
            raise CursorOrchestratorError(f"Unexpected injection error: {e}")

    async def retrieve_response(
        self,
        agent_id: str,
        timeout: Optional[float] = None,
        correlation_id: Optional[str] = None,
    ) -> Optional[str]:
        """Retrieves the latest response from the specified agent's Cursor window.

        Handles clicking the copy button and retrieving text from the clipboard.

        Args:
            agent_id: The ID of the target agent's Cursor window.
            timeout: (Currently unused) Timeout duration.
            correlation_id: Optional correlation ID for event tracking.

        Returns:
            The retrieved text content as a string, or None if retrieval fails.

        Raises:
            CursorOrchestratorError: Can be raised indirectly if UI automation fails critically.

        Notes:
            - Requires agent status to be "AWAITING_RESPONSE".
            - Sets agent status to "COPYING", then "IDLE" on success or "ERROR" on failure.
            - Emits AgentBus events (CURSOR_OPERATION_RESULT with appropriate payload).
        """  # noqa: E501
        log_target_id = f"{agent_id}{f' (CorrID: {correlation_id})' if correlation_id else ''}"  # noqa E501

        if agent_id not in self.copy_coordinates:
            logger.error(f"retrieve_response for {log_target_id}: No copy coordinates.")
            payload = CursorResultPayload(
                operation="retrieve",
                status="FAILURE",
                message="Missing copy coordinates",
                correlation_id=correlation_id,
            )
            await self.agent_bus.publish(
                Event(type=EventType.CURSOR_OPERATION_RESULT, data=payload.model_dump())
            )
            return None

        current_status = await self.get_agent_status(agent_id)
        if current_status != AgentStatus.AWAITING_RESPONSE:
            logger.warning(
                f"retrieve_response for {log_target_id}: Agent not AWAITING_RESPONSE (Status: {current_status}). Retrieval aborted."  # noqa E501
            )
            payload = CursorResultPayload(
                operation="retrieve",
                status="FAILURE",
                message=f"Agent not awaiting response, status: {current_status}",
                correlation_id=correlation_id,
            )
            await self.agent_bus.publish(
                Event(type=EventType.CURSOR_OPERATION_RESULT, data=payload.model_dump())
            )
            return None

        await self._set_agent_status(agent_id, AgentStatus.COPYING)

        x, y = self.copy_coordinates[agent_id]
        target_window_title = (
            self.agent_window_titles.get(agent_id) or self.config.target_window_title
        )
        # Determine copy attempts from config, default to 1 if not specified
        # EDIT START: Use self.config.copy_attempts directly with a default
        copy_attempts = self.config.copy_attempts if self.config else 1
        # EDIT END

        retrieved_text: Optional[str] = None
        last_error: Optional[Exception] = None

        logger.info(
            f"Retrieving response for {log_target_id}. Coords: ({x},{y}), Window: '{target_window_title}', Attempts: {copy_attempts}"  # noqa E501
        )

        # --- Wrap the core copy logic for retry ---
        # Wrapped function for retry.
        # Ensure _perform_copy_sequence does not have its own @retry decorator
        # if this retry_decorator is applied here, to avoid nested retries.
        # _perform_copy_sequence is already decorated with retry, so we just call it.

        # EDIT START: Call the already-decorated _perform_copy_sequence directly
        # No need for an additional retry decorator here if _perform_copy_sequence handles it.
        try:
            # Check focus before attempting copy
            if not self._check_and_recover_focus(target_window_title, log_target_id):
                raise CursorOrchestratorError(
                    "Window focus lost or recovery failed before copy."
                )  # noqa E501

            retrieved_text = self._perform_copy_sequence(
                x, y, log_target_id, target_window_title=target_window_title
            )  # Pass target_window_title
            if (
                retrieved_text is None
            ):  # If retryable _perform_copy_sequence returned None after attempts
                raise CursorOrchestratorError(
                    "Copy sequence failed after multiple retries, returned None."
                )
            last_error = None  # Clear last_error if successful
        except RETRYABLE_UI_EXCEPTIONS as e:  # Catch specific retryable exceptions
            logger.warning(
                f"UI attempt failed for {log_target_id} (will be retried by _perform_copy_sequence if configured): {e}"
            )  # noqa E501
            last_error = e  # Store for potential final failure reporting
            # The retry is handled by _perform_copy_sequence's decorator
            # If it exhausts retries, it will raise, or return None.
            # If _perform_copy_sequence returns None, it's caught above.
            # If it raises non-RETRYABLE_UI_EXCEPTIONS, it's caught by the generic Exception below.
        except CursorOrchestratorError as e:  # Catch specific errors like focus loss
            logger.error(
                f"retrieve_response for {log_target_id} failed: {e}", exc_info=False
            )
            last_error = e
        except Exception as e:  # Catch any other unexpected error
            logger.exception(
                f"Unexpected error during retrieve_response for {log_target_id}: {e}"
            )
            last_error = e
        # EDIT END

        if retrieved_text is not None:
            logger.info(
                f"Response retrieved successfully for {log_target_id} (len: {len(retrieved_text)})."
            )
            await self._set_agent_status(agent_id, AgentStatus.IDLE)
            payload = CursorResultPayload(
                operation="retrieve",
                status="SUCCESS",
                retrieved_content=retrieved_text,
                correlation_id=correlation_id,
            )
            await self.agent_bus.publish(
                Event(type=EventType.CURSOR_OPERATION_RESULT, data=payload.model_dump())
            )
            return retrieved_text
        else:
            error_message = (
                f"Failed to retrieve response after {copy_attempts} attempt(s)."
            )
            if last_error:
                error_message += f" Last error: {last_error}"
            logger.error(f"retrieve_response for {log_target_id}: {error_message}")
            await self._set_agent_status(
                agent_id,
                AgentStatus.ERROR,
                event_data={"error": error_message, "correlation_id": correlation_id},
            )
            payload = CursorResultPayload(
                operation="retrieve",
                status="FAILURE",
                message=error_message,
                correlation_id=correlation_id,
            )
            await self.agent_bus.publish(
                Event(type=EventType.CURSOR_OPERATION_RESULT, data=payload.model_dump())
            )
            return None

    @retry_on_exception(max_attempts=3, exceptions=RETRYABLE_UI_EXCEPTIONS, delay=1.0)
    def _perform_copy_sequence(
        self, x: int, y: int, agent_id_for_log: str, target_window_title: str
    ) -> Optional[str]:
        """Clicks the copy button and retrieves text from the clipboard."""
        logger.info(f"Attempting copy sequence for agent {agent_id_for_log}...")
        if not self._check_and_recover_focus(target_window_title, agent_id_for_log):
            logger.warning(
                f"Focus check/recovery failed for agent {agent_id_for_log} before copy."
            )
            # Proceed cautiously, focus might be okay or user might intervene

        try:
            initial_clipboard = pyperclip.paste()
            logger.debug("Cleared clipboard (initial content check)")
            pyperclip.copy("")  # Clear clipboard before clicking copy

            # Short pause before click
            time.sleep(self.config.pause_before_action)

            logger.debug(
                f"Clicking copy coordinates for {agent_id_for_log}: ({x}, {y})"
            )
            pyautogui.click(x, y)
            logger.debug("Copy button clicked.")

            # Wait for clipboard to update, WITH TIMEOUT
            clipboard_wait_start = time.monotonic()
            clipboard_timeout = self.config.get(
                "clipboard_wait_timeout", 5.0
            )  # Get timeout from config or default to 5s
            copied_text = None
            while time.monotonic() - clipboard_wait_start < clipboard_timeout:
                try:
                    current_clipboard = pyperclip.paste()
                    if current_clipboard and current_clipboard != initial_clipboard:
                        copied_text = current_clipboard
                        logger.info(
                            f"Clipboard updated for agent {agent_id_for_log} after {time.monotonic() - clipboard_wait_start:.2f}s."
                        )
                        break  # Exit loop successfully
                    time.sleep(0.1)  # Short poll interval
                except PyperclipException as clip_err:
                    # Handle potential intermittent clipboard access errors during polling
                    logger.warning(f"Error accessing clipboard during wait: {clip_err}")
                    time.sleep(0.2)  # Slightly longer pause after error

            if copied_text is None:
                logger.error(
                    f"Clipboard did not update within {clipboard_timeout}s timeout for agent {agent_id_for_log}."
                )
                raise asyncio.TimeoutError(
                    "Clipboard update timed out."
                )  # Raise specific error

            # Add pause after copy if needed
            time.sleep(self.config.pause_after_action)

            return copied_text

        except FailSafeException:
            logger.error("PyAutoGUI fail-safe triggered during copy sequence.")
            raise CursorOrchestratorError("Fail-safe triggered")
        except PyperclipException as e:
            logger.error(f"Pyperclip error during copy sequence: {e}")
            raise CursorOrchestratorError(f"Clipboard error: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error in _perform_copy_sequence for agent {agent_id_for_log}: {e}",
                exc_info=True,
            )
            raise CursorOrchestratorError(f"Unexpected copy error: {e}")

    @retry_on_exception(
        max_attempts=2, exceptions=(FailSafeException,), delay=0.5
    )  # noqa: F821
    def _perform_health_check_click(self, x: int, y: int, agent_id_for_log: str):
        """Performs the click action for health check with basic retry."""
        logger.debug(
            f"Performing health check click for {agent_id_for_log} at ({x}, {y})."
        )
        pyautogui.click(x, y, duration=0.1)
        time.sleep(0.2)  # Brief pause after click

    async def check_window_health(self, agent_id: str) -> bool:
        """Checks if the agent's Cursor window is responsive by clicking its input field.

        Args:
            agent_id: The ID of the agent window to check.

        Returns:
            True if the window is likely responsive (click succeeded), False otherwise.

        Notes:
            - Sets agent status to "UNRESPONSIVE" if the check fails.
            - Emits CURSOR_WINDOW_UNRESPONSIVE event on failure.
        """  # noqa: E501
        if agent_id not in self.input_coordinates:
            logger.error(f"check_window_health: No input coordinates for {agent_id}")
            # Cannot check health without coords, assume unresponsive?
            await self._set_agent_status(agent_id, "UNRESPONSIVE")
            return False

        x, y = self.input_coordinates[agent_id]
        current_status = await self.get_agent_status(agent_id)
        is_healthy = False
        error_reason = "Unknown error during health check"

        try:
            logger.info(f"Checking health for agent {agent_id}...")
            # Run the synchronous click in a thread
            await asyncio.to_thread(self._perform_health_check_click, x, y, agent_id)
            is_healthy = True
            logger.info(f"Health check PASSED for agent {agent_id}.")
            # If agent was unresponsive, reset status to IDLE after successful check
            if current_status == "UNRESPONSIVE":
                logger.info(f"Agent {agent_id} recovered. Setting status to IDLE.")
                await self._set_agent_status(agent_id, "IDLE")

        except FailSafeException as e:
            error_reason = f"FailSafe triggered during health check: {e}"
            logger.error(f"Health check FAILED for {agent_id}: {error_reason}")
        except Exception as e:
            error_reason = f"Unexpected error during health check: {e}"
            logger.error(
                f"Health check FAILED for {agent_id}: {error_reason}", exc_info=True
            )

        if not is_healthy:
            # Publish event only if check fails
            await self._set_agent_status(agent_id, "UNRESPONSIVE")
            # Assuming a generic payload for now, as no specific one exists for this
            # A CursorUnresponsivePayload could be created if needed.
            failure_payload_dict = {"agent_id": agent_id, "reason": error_reason}
            failure_event = BaseEvent(
                event_type=EventType.CURSOR_WINDOW_UNRESPONSIVE,
                source_id="CursorOrchestrator",
                data=failure_payload_dict,  # Use dict directly
            )
            try:
                asyncio.create_task(self.agent_bus.dispatch_event(failure_event))
            except Exception as pub_e:
                logger.error(
                    f"Failed to dispatch event {EventType.CURSOR_WINDOW_UNRESPONSIVE}: {pub_e}"  # noqa: E501
                )

        return is_healthy

    # --- AgentBus Listener Logic ---
    async def start_listening(self):
        """Subscribes to relevant AgentBus events and starts the listener task."""
        if not self.agent_bus:
            logger.error("Cannot start listener: AgentBus not provided.")
            return

        # EDIT START: Remove listener task logic, store handlers for unsubscription
        # if self._listener_task and not self._listener_task.done():
        #     logger.warning(\"Listener task already running.\")
        #     return
        self._subscribed_handlers = (
            []
        )  # Initialize list to store (topic, handler) tuples  # noqa: E501
        # EDIT END

        try:
            # Subscribe to specific request events
            inject_topic = EventType.CURSOR_INJECT_REQUEST.value
            retrieve_topic = EventType.CURSOR_RETRIEVE_REQUEST.value
            handler = self._handle_cursor_action_event

            await self.agent_bus.subscribe(inject_topic, handler)
            self._subscribed_handlers.append((inject_topic, handler))

            await self.agent_bus.subscribe(retrieve_topic, handler)
            self._subscribed_handlers.append((retrieve_topic, handler))

            logger.info(
                f"Subscribed handler to {inject_topic} and {retrieve_topic} events."
            )
            # We don't need a separate task loop if subscribe handles callbacks directly
            # If subscribe requires polling, a task loop would be needed here.
            # Assuming subscribe sets up direct callbacks/awaitables.
            # REMOVED: self._listener_task assignment
            # self._listener_task = (
            #     asyncio.current_task()
            # )  # Or None if subscribe doesn't need a task

        except BusError as e:  # Catch specific bus errors if defined  # noqa: F821
            logger.exception(f"AgentBus error during subscription: {e}")
        except Exception as e:
            logger.exception(f"Failed to subscribe to cursor events: {e}")

    async def _handle_cursor_action_event(self, event: BaseEvent):
        """Handles incoming cursor action requests from the AgentBus."""
        logger.debug(
            f"Received cursor action event: Type={event.event_type.value}, Source={event.source_id}, Data={event.data}"  # noqa: E501
        )

        target_agent_id = event.data.get("target_agent_id")
        if not target_agent_id:
            logger.error(
                f"Received {event.event_type.value} event with missing 'target_agent_id'. Ignoring."  # noqa: E501
            )
            return

        if event.event_type == EventType.CURSOR_INJECT_REQUEST:
            prompt_text = event.data.get("prompt_text")
            if prompt_text is None:  # Allow empty string prompts
                logger.error(
                    f"Received CURSOR_INJECT_REQUEST for {target_agent_id} with missing 'prompt_text'. Ignoring."  # noqa: E501
                )
                return
            # Don't await here - let it run in the background
            asyncio.create_task(self.inject_prompt(target_agent_id, prompt_text))

        elif event.event_type == EventType.CURSOR_RETRIEVE_REQUEST:
            # Don't await here - let it run in the background
            # The requesting agent will need to listen for the corresponding SUCCESS/FAILURE event  # noqa: E501
            asyncio.create_task(self.retrieve_response(target_agent_id))
        else:
            logger.warning(
                f"Received unexpected event type in cursor handler: {event.event_type.value}"  # noqa: E501
            )

    async def initialize(self):
        """Initializes async components, including starting the AgentBus listener."""
        logger.info("CursorOrchestrator async initialization starting...")
        await self.start_listening()  # Start listening on initialize
        logger.info("CursorOrchestrator async initialization complete.")
        pass

    async def shutdown(self):
        """Performs cleanup actions, such as unsubscribing AgentBus handlers."""
        logger.info("CursorOrchestrator shutting down...")

        # EDIT START: Implement unsubscription
        if hasattr(self, "_subscribed_handlers") and self._subscribed_handlers:
            logger.info(
                f"Unsubscribing {len(self._subscribed_handlers)} AgentBus handlers..."
            )
            unsubscribe_tasks = []
            for topic, handler in self._subscribed_handlers:
                try:
                    # Assume agent_bus.unsubscribe exists and takes topic, handler
                    unsubscribe_tasks.append(self.agent_bus.unsubscribe(topic, handler))
                except AttributeError:
                    logger.error(
                        "AgentBus does not support 'unsubscribe'. Cannot clean up handlers."  # noqa: E501
                    )
                    break  # Stop trying if method is missing
                except Exception as e:
                    logger.error(f"Error initiating unsubscribe for {topic}: {e}")

            if unsubscribe_tasks:
                results = await asyncio.gather(
                    *unsubscribe_tasks, return_exceptions=True
                )
                for (topic, _), result in zip(self._subscribed_handlers, results):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to unsubscribe from {topic}: {result}")
                    else:
                        logger.debug(f"Successfully unsubscribed from {topic}")
            self._subscribed_handlers = []  # Clear the list
        else:
            logger.info("No subscribed handlers found to unsubscribe.")
        # EDIT END

        # EDIT START: Remove old listener task cancellation logic
        # if self._listener_task and not self._listener_task.done():
        #     logger.info(\"Cancelling listener task.\")
        #     self._listener_task.cancel()
        #     try:
        #         await self._listener_task
        #     except asyncio.CancelledError:
        #         pass
        # EDIT END
        logger.info("CursorOrchestrator shut down.")
        pass

    # --- Tenacity Retry Logger ---
    def _log_retry_attempt(self, retry_state: tenacity.RetryCallState):
        """(Internal) Logs information about a retry attempt using instance logger."""
        attempt_num = retry_state.attempt_number
        wait_time = getattr(retry_state.next_action, "sleep", 0)
        error = retry_state.outcome.exception() if retry_state.outcome else None
        self.logger.warning(
            f"Retrying UI operation (Attempt {attempt_num}/{self.config.retry_attempts}) after error: {error}. "  # noqa: E501
            f"Waiting {wait_time:.2f}s before next attempt."
        )


# --- Singleton Accessor ---
_cursor_orchestrator_instance: Optional[CursorOrchestrator] = None
_orchestrator_init_lock = asyncio.Lock()


async def get_cursor_orchestrator(
    # Remove default config loading, rely on prior initialization
    config: Optional[AppConfig] = None,
    agent_bus: Optional[AgentBus] = None,
) -> CursorOrchestrator:
    """Factory function to get the CursorOrchestrator singleton instance.

    IMPORTANT: Assumes the singleton has ALREADY been initialized elsewhere
    (e.g., by SwarmController) with the correct AppConfig and AgentBus.
    This function primarily serves to retrieve the existing singleton instance.
    If called before initialization, it will raise an error.

    Args:
        config: (Deprecated/Ignored) Config is expected to be set during initial creation.
        agent_bus: (Deprecated/Ignored) AgentBus is expected to be set during initial creation.

    Returns:
        The initialized CursorOrchestrator singleton instance.

    Raises:
        CursorOrchestratorError: If the orchestrator hasn't been initialized yet.
    """
    if (
        CursorOrchestrator._instance is None
        or not CursorOrchestrator._instance._initialized
    ):
        # If the instance hasn't been created and initialized yet (e.g., by SwarmController),
        # trying to initialize it here without guaranteed correct config/bus is problematic.
        # It's better to enforce that initialization happens first.
        logger.error(
            "get_cursor_orchestrator called before CursorOrchestrator was initialized!"
        )
        raise CursorOrchestratorError(
            "CursorOrchestrator instance not initialized. Ensure SwarmController or main entry point initializes it first."
        )

    # Log warning if config or agent_bus were passed, as they are ignored now
    if config is not None or agent_bus is not None:
        logger.warning(
            "get_cursor_orchestrator received config/agent_bus arguments, but they are ignored as initialization should pre-exist."
        )

    return CursorOrchestrator._instance
