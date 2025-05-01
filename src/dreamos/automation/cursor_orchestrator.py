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

import tenacity  # Assuming tenacity was added by Agent 4
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)

# EDIT END
from selenium.webdriver.support import expected_conditions as EC

# Local imports (assuming sibling modules)
# from .response_retriever import ResponseRetriever # Logic will be integrated
# from .cursor_injector import inject_prompt # Logic will be integrated
from dreamos.coordination.agent_bus import AgentBus, BaseEvent, EventType
from dreamos.coordination.event_payloads import (
    AgentStatusChangePayload,
    CursorEventPayload,
    CursorResultEvent,
    CursorResultPayload,
)
from dreamos.core.config import AppConfig

# EDIT START: Import core ToolError
from dreamos.core.errors import ToolError as CoreToolError

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
INPUT_COORDS_FILE = CONFIG_DIR / "cursor_agent_coords.json"
COPY_COORDS_FILE = CONFIG_DIR / "cursor_agent_copy_coords.json"

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
        config: AppConfig,  # Require AppConfig
        input_coords_path: Optional[Path] = None,
        copy_coords_path: Optional[Path] = None,
        agent_bus: Optional[AgentBus] = None,
    ):
        """Initializes the CursorOrchestrator singleton instance.

        Loads coordinates, initializes agent statuses, uses AppConfig for settings,
        and optionally accepts an AgentBus instance.

        Args:
            config: The loaded AppConfig instance containing settings.
            input_coords_path: Path to input coordinates JSON. Defaults to value in config dir.
            copy_coords_path: Path to copy coordinates JSON. Defaults to value in config dir.
            agent_bus: Optional AgentBus instance. If None, gets the default singleton.

        Raises:
            CursorOrchestratorError: If UI dependencies missing or no coords loaded.
            ValueError: If config object is not provided.
        """
        if not config:
            raise ValueError("AppConfig instance is required for CursorOrchestrator.")

        if not UI_AUTOMATION_AVAILABLE:
            raise CursorOrchestratorError(
                "Dependencies (pyautogui, pyperclip) not installed."
            )

        if hasattr(self, "_initialized") and self._initialized:
            return

        self.config = config.cursor_orchestrator  # Store nested config
        # Use provided paths or default relative to config dir
        self.input_coords_path = input_coords_path or INPUT_COORDS_FILE
        self.copy_coords_path = copy_coords_path or COPY_COORDS_FILE
        self.agent_bus = agent_bus or AgentBus()
        self.input_coordinates: Dict[str, Tuple[int, int]] = {}
        self.copy_coordinates: Dict[str, Tuple[int, int]] = {}
        self.agent_status: Dict[str, AgentStatus] = {}
        self._load_all_coordinates()
        self._initialize_agent_status()
        self._listener_task: Optional[asyncio.Task] = None
        self._initialized = True
        logger.info("CursorOrchestrator initialized with config.")

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

                # Assuming status changes are system events, use AgentStatusChangePayload
                payload = AgentStatusChangePayload(
                    agent_id=agent_id,
                    status=status,
                    task_id=base_event_data.get(
                        "task_id"
                    ),  # Get optional fields from input
                    error_message=base_event_data.get("error"),
                    # Add other fields from AgentStatusChangePayload if present in event_data
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
                        f"Failed to dispatch status event {event_type} for {agent_id}: {e}"
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
        """Injects a prompt into the specified agent's Cursor chat input window.

        Handles moving the mouse, clicking, clearing, pasting/typing the prompt,
        and submitting (pressing Enter).

        Args:
            agent_id: The ID of the target agent's Cursor window.
            prompt: The text content of the prompt to inject.
            timeout: (Currently unused) Timeout duration for the operation.
            correlation_id: Optional correlation ID for event tracking.

        Returns:
            True if the injection sequence completed without raising an exception,
            False otherwise (e.g., missing coordinates, agent not IDLE, pyautogui error).

        Raises:
            CursorOrchestratorError: Can be raised indirectly if UI automation fails critically.

        Notes:
            - Requires the agent status to be "IDLE" to proceed.
            - Sets agent status to "INJECTING", then "AWAITING_RESPONSE" on success,
              or "ERROR" on failure.
            - Emits AgentBus events (CURSOR_INJECT_SUCCESS/FAILURE).
        """
        if agent_id not in self.input_coordinates:
            logger.error(f"inject_prompt: No input coordinates for {agent_id}")
            failure_payload = CursorResultPayload(
                operation="inject",
                status="FAILURE",
                message="Missing coordinates",
                correlation_id=correlation_id,
            )
            failure_event = CursorResultEvent(
                event_type=EventType.CURSOR_INJECT_FAILURE,
                source_id="CursorOrchestrator",
                data=failure_payload,
            )
            try:
                asyncio.create_task(self.agent_bus.dispatch_event(failure_event))
            except Exception as e:
                logger.error(
                    f"Failed to dispatch event {EventType.CURSOR_INJECT_FAILURE}: {e}"
                )
            await self._set_agent_status(agent_id, "ERROR")
            return False

        current_status = await self.get_agent_status(agent_id)
        if current_status != "IDLE":
            logger.warning(
                f"inject_prompt: Agent {agent_id} is not IDLE (status: {current_status}). Aborting injection."
            )
            failure_payload = CursorResultPayload(
                operation="inject",
                status="FAILURE",
                message=f"Agent not IDLE (status: {current_status})",
                correlation_id=correlation_id,
            )
            failure_event = CursorResultEvent(
                event_type=EventType.CURSOR_INJECT_FAILURE,
                source_id="CursorOrchestrator",
                data=failure_payload,
            )
            try:
                asyncio.create_task(self.agent_bus.dispatch_event(failure_event))
            except Exception as e:
                logger.error(
                    f"Failed to dispatch event {EventType.CURSOR_INJECT_FAILURE}: {e}"
                )
            await self._set_agent_status(agent_id, "ERROR")
            return False

        x, y = self.input_coordinates[agent_id]
        logger.info(
            f"Injecting prompt for {agent_id} at ({x}, {y}). Length: {len(prompt)}"
        )
        await self._set_agent_status(
            agent_id,
            "INJECTING",
            EventType.CURSOR_ACTION_START,
            {"operation": "inject", "correlation_id": correlation_id},
        )

        try:
            # TODO: Implement window focus check before performing sequence
            logger.debug(
                f"[State Check] Proceeding with injection for {agent_id} - assumes window focused."
            )
            # Call the sequence using asyncio.to_thread for blocking IO
            await asyncio.to_thread(
                self._perform_injection_sequence, x, y, prompt, agent_id
            )
            logger.info(f"Injection sequence seemingly completed for {agent_id}.")
            await self._set_agent_status(agent_id, "AWAITING_RESPONSE")

            # Dispatch success event
            success_payload = CursorResultPayload(
                operation="inject", status="SUCCESS", correlation_id=correlation_id
            )
            success_event = CursorResultEvent(
                event_type=EventType.CURSOR_INJECT_SUCCESS,
                source_id="CursorOrchestrator",
                data=success_payload,
            )
            try:
                asyncio.create_task(self.agent_bus.dispatch_event(success_event))
            except Exception as e:
                logger.error(
                    f"Failed to dispatch event {EventType.CURSOR_INJECT_SUCCESS}: {e}"
                )
            return True
        except Exception as e:
            logger.exception(
                f"Generic error during injection sequence for {agent_id}: {e}"
            )
            # Re-raise to be caught by the calling method
            raise CursorOrchestratorError(f"Injection sequence failed: {e}") from e
        finally:
            logger.debug(f"_perform_injection_sequence for {agent_id} finished.")

    def _perform_injection_sequence(
        self, x: int, y: int, text: str, agent_id_for_log: str
    ):
        """Executes the PyAutoGUI sequence for injecting text.
        Handles potential UI automation exceptions.
        """
        if not pyautogui:
            raise CursorOrchestratorError("PyAutoGUI is not available")

        logger.debug(f"_perform_injection_sequence for {agent_id_for_log} starting.")
        # Configurable delays
        move_delay = self.config.get("move_delay", 0.1)
        click_delay = self.config.get("click_delay", 0.1)
        type_interval = self.config.type_interval_seconds  # Use config
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
            logger.debug(f"[{agent_id_for_log}] Submitting (Enter)")
            pyautogui.press("enter")
            time.sleep(click_delay * 2)
        except Exception as e:
            logger.exception(
                f"Generic error during injection sequence for {agent_id_for_log}: {e}"
            )
            # Re-raise to be caught by the calling method
            raise CursorOrchestratorError(f"Injection sequence failed: {e}") from e
        finally:
            logger.debug(
                f"_perform_injection_sequence for {agent_id_for_log} finished."
            )

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
            - Emits AgentBus events (CURSOR_RETRIEVE_SUCCESS/FAILURE).
        """
        if agent_id not in self.copy_coordinates:
            logger.error(f"retrieve_response: No copy coordinates for {agent_id}")
            failure_payload = CursorResultPayload(
                operation="retrieve",
                status="FAILURE",
                message="Missing copy coordinates",
                correlation_id=correlation_id,
            )
            failure_event = CursorResultEvent(
                event_type=EventType.CURSOR_RETRIEVE_FAILURE,
                source_id="CursorOrchestrator",
                data=failure_payload,
            )
            try:
                asyncio.create_task(self.agent_bus.dispatch_event(failure_event))
            except Exception as e:
                logger.error(
                    f"Failed to dispatch event {EventType.CURSOR_RETRIEVE_FAILURE}: {e}"
                )
            await self._set_agent_status(agent_id, "ERROR")
            return None

        current_status = await self.get_agent_status(agent_id)
        if current_status != "AWAITING_RESPONSE":
            logger.warning(
                f"retrieve_response: Agent {agent_id} is not AWAITING_RESPONSE (status: {current_status}). Aborting retrieval."
            )
            return None

        x, y = self.copy_coordinates[agent_id]
        retrieved_text = None
        success = False
        error_reason = "Unknown error during retrieval sequence"

        try:
            await self._set_agent_status(agent_id, "COPYING")
            # Use tenacity for retries
            retryer = tenacity.AsyncRetrying(
                stop=tenacity.stop_after_attempt(self.config.retry_attempts),
                wait=tenacity.wait_fixed(self.config.retry_delay_seconds),
                retry=tenacity.retry_if_exception_type(RETRYABLE_UI_EXCEPTIONS),
                before_sleep=self._log_retry_attempt,  # Log before sleeping
                reraise=True,  # Reraise the exception after max attempts
            )
            retrieved_text = await retryer.call(
                lambda: asyncio.to_thread(self._perform_copy_sequence, x, y, agent_id)
            )

            if retrieved_text is not None:
                logger.info(
                    f"retrieve_response: Successfully retrieved response for {agent_id}."
                )
                await self._set_agent_status(agent_id, "IDLE")
                success_payload = CursorResultPayload(
                    operation="retrieve",
                    status="SUCCESS",
                    retrieved_content=retrieved_text,  # Include content
                    correlation_id=correlation_id,
                )
                success_event = CursorResultEvent(
                    event_type=EventType.CURSOR_RETRIEVE_SUCCESS,
                    source_id="CursorOrchestrator",
                    data=success_payload,
                )
                try:
                    asyncio.create_task(self.agent_bus.dispatch_event(success_event))
                except Exception as e:
                    logger.error(
                        f"Failed to dispatch event {EventType.CURSOR_RETRIEVE_SUCCESS}: {e}"
                    )
                success = True
            else:
                # This case might indicate _perform_copy_sequence handled an error internally
                # but didn't raise a retryable exception, or returned None.
                error_reason = (
                    "Retrieval sequence returned None (check logs for specific error)"
                )
                logger.error(f"retrieve_response failed for {agent_id}: {error_reason}")

        except tenacity.RetryError as e:
            # Retries exhausted
            final_error = e.last_attempt.exception()
            error_reason = (
                f"Failed after {self.config.retry_attempts} retries: {final_error}"
            )
            logger.error(
                f"retrieve_response failed for {agent_id} after retries: {error_reason}",
                exc_info=final_error,
            )
            # Don't set status here, let finally block handle it
        except Exception as e:
            # Catch other unexpected errors
            error_reason = f"Unexpected Error: {type(e).__name__}: {e}"
            logger.error(
                f"retrieve_response failed for {agent_id}: {error_reason}",
                exc_info=True,
            )
            # Don't set status here, let finally block handle it

        finally:
            if not success:
                logger.warning(
                    f"Finalizing retrieve_response for {agent_id} with status ERROR due to: {error_reason}"
                )
                # Publish failure event
                failure_payload = CursorResultPayload(
                    operation="retrieve",
                    status="FAILURE",
                    message=str(error_reason)[:200],  # Truncate long messages
                    correlation_id=correlation_id,
                )
                failure_event = CursorResultEvent(
                    event_type=EventType.CURSOR_RETRIEVE_FAILURE,
                    source_id="CursorOrchestrator",
                    data=failure_payload,
                )
                try:
                    asyncio.create_task(self.agent_bus.dispatch_event(failure_event))
                except Exception as e:
                    logger.error(
                        f"Failed to dispatch event {EventType.CURSOR_RETRIEVE_FAILURE}: {e}"
                    )
                await self._set_agent_status(agent_id, "ERROR")

        return retrieved_text if success else None

    def _perform_copy_sequence(
        self, x: int, y: int, agent_id_for_log: str
    ) -> Optional[str]:
        """Executes the PyAutoGUI sequence for copying text.
        Handles potential UI automation exceptions.
        """
        if not pyautogui or not pyperclip:
            raise CursorOrchestratorError("PyAutoGUI or Pyperclip is not available")

        logger.debug(f"_perform_copy_sequence for {agent_id_for_log} starting.")
        original_clipboard = ""
        try:
            # Clear clipboard first for better reliability
            if pyperclip:
                logger.debug(f"[{agent_id_for_log}] Clearing clipboard")
                pyperclip.copy("")
            else:
                logger.error(
                    f"Cannot perform copy sequence for {agent_id_for_log}: pyperclip is not available."
                )
                # Raise a specific error if pyperclip is missing, making it potentially non-retryable
                # depending on how RETRYABLE_UI_EXCEPTIONS is defined.
                raise CursorOrchestratorError("Pyperclip dependency is not available.")

            logger.debug(f"[{agent_id_for_log}] Moving mouse to Copy button ({x}, {y})")
            pyautogui.moveTo(x, y, duration=0.1)
            time.sleep(0.1)
            logger.debug(f"[{agent_id_for_log}] Clicking Copy button")
            pyautogui.click()
            time.sleep(0.2)

            logger.debug(f"[{agent_id_for_log}] Pasting from clipboard")
            response_text = pyperclip.paste()

            if not response_text:
                logger.warning(
                    f"Clipboard empty after copy click for agent {agent_id_for_log}."
                )
                # Decide if empty clipboard should cause a retry. If so, raise an exception here.
                # For now, returning empty string means success but no content.
                # Example if retry needed: raise TransientClipboardError("Clipboard empty after copy")
                return ""
            return response_text
        except (
            FailSafeException,
            PyperclipException,
        ) as ui_error:  # Catch specific known exceptions
            logger.exception(
                f"UI/Clipboard error in _perform_copy_sequence for agent {agent_id_for_log}: {ui_error}"
            )
            raise  # Re-raise to be caught by tenacity
        except Exception as e:
            logger.exception(
                f"Unexpected error in _perform_copy_sequence for agent {agent_id_for_log}: {e}"
            )
            raise  # Re-raise other errors too
        finally:
            # Restore mouse position (best effort)
            try:
                pyautogui.moveTo(original_pos.x, original_pos.y, duration=0.1)
            except Exception:
                pass  # Ignore errors during restore
            # Restore original clipboard content
            if original_clipboard:
                pyperclip.copy(original_clipboard)
            logger.debug(f"_perform_copy_sequence for {agent_id_for_log} finished.")

    @retry_on_exception(max_attempts=2, exceptions=(FailSafeException,), delay=0.5)
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
        """
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
                    f"Failed to dispatch event {EventType.CURSOR_WINDOW_UNRESPONSIVE}: {pub_e}"
                )

        return is_healthy

    # --- AgentBus Listener Logic ---
    async def start_listening(self):
        """Subscribes to relevant AgentBus events and starts the listener task."""
        if not self.agent_bus:
            logger.error("Cannot start listener: AgentBus not provided.")
            return

        if self._listener_task and not self._listener_task.done():
            logger.warning("Listener task already running.")
            return

        try:
            # Subscribe to specific request events
            # Consider using a pattern like "cursor.*.request" if many related events
            await self.agent_bus.subscribe(
                EventType.CURSOR_INJECT_REQUEST.value, self._handle_cursor_action_event
            )
            await self.agent_bus.subscribe(
                EventType.CURSOR_RETRIEVE_REQUEST.value,
                self._handle_cursor_action_event,
            )
            logger.info(
                "Subscribed to CURSOR_INJECT_REQUEST and CURSOR_RETRIEVE_REQUEST events."
            )
            # We don't need a separate task loop if subscribe handles callbacks directly
            # If subscribe requires polling, a task loop would be needed here.
            # Assuming subscribe sets up direct callbacks/awaitables.
            self._listener_task = (
                asyncio.current_task()
            )  # Or None if subscribe doesn't need a task

        except Exception as e:
            logger.exception(f"Failed to subscribe to cursor events: {e}")

    async def _handle_cursor_action_event(self, event: BaseEvent):
        """Handles incoming cursor action requests from the AgentBus."""
        logger.debug(
            f"Received cursor action event: Type={event.event_type.value}, Source={event.source_id}, Data={event.data}"
        )

        target_agent_id = event.data.get("target_agent_id")
        if not target_agent_id:
            logger.error(
                f"Received {event.event_type.value} event with missing 'target_agent_id'. Ignoring."
            )
            return

        if event.event_type == EventType.CURSOR_INJECT_REQUEST:
            prompt_text = event.data.get("prompt_text")
            if prompt_text is None:  # Allow empty string prompts
                logger.error(
                    f"Received CURSOR_INJECT_REQUEST for {target_agent_id} with missing 'prompt_text'. Ignoring."
                )
                return
            # Don't await here - let it run in the background
            asyncio.create_task(self.inject_prompt(target_agent_id, prompt_text))

        elif event.event_type == EventType.CURSOR_RETRIEVE_REQUEST:
            # Don't await here - let it run in the background
            # The requesting agent will need to listen for the corresponding SUCCESS/FAILURE event
            asyncio.create_task(self.retrieve_response(target_agent_id))
        else:
            logger.warning(
                f"Received unexpected event type in cursor handler: {event.event_type.value}"
            )

    async def initialize(self):
        """Initializes async components, including starting the AgentBus listener."""
        logger.info("CursorOrchestrator async initialization starting...")
        await self.start_listening()  # Start listening on initialize
        logger.info("CursorOrchestrator async initialization complete.")
        pass

    async def shutdown(self):
        """Performs cleanup actions, such as stopping the AgentBus listener."""
        logger.info("CursorOrchestrator shutting down...")
        # TODO: Implement proper unsubscription if AgentBus supports it
        # REMOVED - Implemented via ENHANCE-AGENTBUS-001
        if self._listener_task and not self._listener_task.done():
            logger.info("Cancelling listener task.")
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        logger.info("CursorOrchestrator shut down.")
        pass

    # --- Tenacity Retry Logger ---
    def _log_retry_attempt(self, retry_state: tenacity.RetryCallState):
        """(Internal) Logs information about a retry attempt using instance logger."""
        attempt_num = retry_state.attempt_number
        wait_time = getattr(retry_state.next_action, "sleep", 0)
        error = retry_state.outcome.exception() if retry_state.outcome else None
        self.logger.warning(
            f"Retrying UI operation (Attempt {attempt_num}/{self.config.retry_attempts}) after error: {error}. "
            f"Waiting {wait_time:.2f}s before next attempt."
        )


# --- Singleton Accessor ---
_cursor_orchestrator_instance: Optional[CursorOrchestrator] = None
_orchestrator_init_lock = asyncio.Lock()


async def get_cursor_orchestrator(
    config: AppConfig, agent_bus: Optional[AgentBus] = None
) -> CursorOrchestrator:
    """Provides access to the singleton CursorOrchestrator instance...
    Args:
        config: The AppConfig instance (required).
        agent_bus: Optional AgentBus instance...
    """
    global _cursor_orchestrator_instance
    if not config:
        raise ValueError("AppConfig is required to get CursorOrchestrator instance.")

    if _cursor_orchestrator_instance is None:
        async with _orchestrator_init_lock:
            if _cursor_orchestrator_instance is None:
                logger.info(
                    "Creating and initializing CursorOrchestrator singleton instance."
                )
                bus_to_use = agent_bus or AgentBus()
                # Pass the required config object
                instance = CursorOrchestrator(config=config, agent_bus=bus_to_use)
                await instance.initialize()
                _cursor_orchestrator_instance = instance
    return _cursor_orchestrator_instance
