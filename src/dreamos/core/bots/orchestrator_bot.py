import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

# NOTE: ChatGPTScraper is conceptual - represents this AI's response generation
# from chatgptscraper import ChatGPTScraper

# Dependency: pip install pyautogui
try:
    import pyautogui

    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    # Logged later in OrchestratorBot init

# EDIT START: Add pyperclip dependency check
try:
    import pyperclip

    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    # Logged later in OrchestratorBot init
# EDIT END

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Removed incorrect import of CursorOrchestrator here, assuming it's used elsewhere if needed
# from ..automation.cursor_orchestrator import CursorOrchestrator, CursorOrchestratorError
from ..config import AppConfig  # Adjusted relative import

# from ..coordination.agent_bus import AgentBus, BaseEvent # F401 Unused

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# EDIT START: Define CORRECT base mailboxes dir and bot's inbox using agent_comms
# MAILBOXES_DIR = Path("runtime/mailboxes") # OLD PATH
AGENT_COMMS_DIR = Path("runtime/agent_comms")
MAILBOXES_DIR = AGENT_COMMS_DIR / "agent_mailboxes"  # CORRECTED PATH
BOT_AGENT_ID = "Agent-8"  # The bot acts as/for the current Captain (Agent-8)
BOT_INBOX_DIR = MAILBOXES_DIR / BOT_AGENT_ID / "inbox"
ORCHESTRATOR_CAPABILITIES = [
    "TASK_ORCHESTRATION",
    "AGENT_MONITORING",
    "SYSTEM_REPORTING",
    "GUI_INTERACTION",  # EDIT: Added capability
]
# EDIT END

# Using a simple set for processed files in this run, might need persistence later
PROCESSED = set()

# --- Proposed Cursor Action Schema ---
# {
#   "message_id": "uuid_string", // REQUIRED
#   "action_type": "typewrite | press | click | hotkey | scroll | moveto | screenshot", // REQUIRED
#   "parameters": { ... }, // REQUIRED (structure depends on action_type)
#   "target_window_identifier": "string | null", // Optional hint
#   "timestamp_utc": "iso_timestamp_string" // REQUIRED
# }
# --- End Schema ---


# EDIT START: Define OrchestratorBot Class
class OrchestratorBot:
    """Provides centralized methods for GUI interaction via PyAutoGUI."""

    def __init__(self, config: Optional[AppConfig], agent_id: str = "OrchestratorBot"):
        self.config = config
        self.agent_id = agent_id
        if not PYAUTOGUI_AVAILABLE:
            logger.error("PyAutoGUI library not found. GUI interactions will fail.")
            # Optionally raise an error or set a flag
            self.gui_enabled = False
        else:
            self.gui_enabled = True
            logger.info(
                f"OrchestratorBot [{self.agent_id}] initialized for GUI interaction."
            )
        # EDIT START: Add check for pyperclip
        if not PYPERCLIP_AVAILABLE:
            logger.warning(
                "Pyperclip library not found. Clipboard operations will fail."
            )
            self.clipboard_enabled = False
        else:
            self.clipboard_enabled = True
        # EDIT END

    def _check_enabled(self):
        if not self.gui_enabled:
            raise RuntimeError(
                "OrchestratorBot GUI capabilities disabled (PyAutoGUI not installed)"
            )

    # EDIT START: Add specific check for clipboard
    def _check_clipboard_enabled(self):
        if not self.clipboard_enabled:
            raise RuntimeError(
                "OrchestratorBot clipboard capabilities disabled (Pyperclip not installed)"
            )

    # EDIT END

    def typewrite(self, text: str, interval: float = 0.01):
        """Types the given text with a specified interval between keys."""
        self._check_enabled()
        try:
            pyautogui.typewrite(text, interval=interval)
            logger.debug(f"[{self.agent_id}] Executed typewrite.")
            return True
        except Exception as e:
            logger.error(
                f"[{self.agent_id}] PyAutoGUI typewrite failed: {e}", exc_info=True
            )
            return False

    def press(self, keys: str | List[str]):
        """Presses the specified key(s)."""
        self._check_enabled()
        try:
            pyautogui.press(keys)
            logger.debug(f"[{self.agent_id}] Executed press: {keys}")
            return True
        except Exception as e:
            logger.error(
                f"[{self.agent_id}] PyAutoGUI press failed for keys '{keys}': {e}",
                exc_info=True,
            )
            return False

    def hotkey(self, *keys: str):
        """Presses the specified keys simultaneously (hotkey)."""
        self._check_enabled()
        try:
            pyautogui.hotkey(*keys)
            logger.debug(f"[{self.agent_id}] Executed hotkey: {keys}")
            return True
        except Exception as e:
            logger.error(
                f"[{self.agent_id}] PyAutoGUI hotkey failed for keys '{keys}': {e}",
                exc_info=True,
            )
            return False

    def click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.1,
    ):
        """Performs a mouse click."""
        self._check_enabled()
        try:
            pyautogui.click(x=x, y=y, button=button, clicks=clicks, interval=interval)
            logger.debug(
                f"[{self.agent_id}] Executed click at ({x},{y}), button={button}, clicks={clicks}."
            )
            return True
        except Exception as e:
            logger.error(
                f"[{self.agent_id}] PyAutoGUI click failed at ({x},{y}): {e}",
                exc_info=True,
            )
            return False

    def scroll(self, amount: int):
        """Scrolls the mouse wheel."""
        self._check_enabled()
        try:
            pyautogui.scroll(amount)
            logger.debug(f"[{self.agent_id}] Executed scroll: {amount}")
            return True
        except Exception as e:
            logger.error(
                f"[{self.agent_id}] PyAutoGUI scroll failed: {e}", exc_info=True
            )
            return False

    def move_to(self, x: int, y: int, duration: float = 0.1):
        """Moves the mouse cursor to the specified coordinates."""
        self._check_enabled()
        try:
            pyautogui.moveTo(x, y, duration=duration)
            logger.debug(f"[{self.agent_id}] Executed moveto: ({x}, {y})")
            return True
        except Exception as e:
            logger.error(
                f"[{self.agent_id}] PyAutoGUI move_to failed for ({x},{y}): {e}",
                exc_info=True,
            )
            return False

    def screenshot(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        save_path: Optional[str | Path] = None,
    ):
        """Takes a screenshot, optionally of a specific region, and optionally saves it."""
        self._check_enabled()
        try:
            image = pyautogui.screenshot(region=region)
            logger.debug(f"[{self.agent_id}] Executed screenshot.")
            if save_path:
                save_path = Path(save_path)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                image.save(str(save_path))
                logger.info(f"[{self.agent_id}] Screenshot saved to {save_path}")
            return image  # Returns PIL image object
        except Exception as e:
            logger.error(
                f"[{self.agent_id}] PyAutoGUI screenshot failed: {e}", exc_info=True
            )
            return None

    def get_windows_by_title(self, title: str) -> List[Any]:
        """Finds windows matching the given title substring. Returns a list of window objects (type depends on platform)."""
        self._check_enabled()
        try:
            windows = pyautogui.getWindowsWithTitle(title)
            logger.debug(
                f"[{self.agent_id}] Found {len(windows)} window(s) with title containing '{title}'."
            )
            return windows
        except Exception as e:
            logger.error(
                f"[{self.agent_id}] PyAutoGUI getWindowsWithTitle failed for title '{title}': {e}",
                exc_info=True,
            )
            return []

    def locate_center_on_screen(
        self, image_path: str | Path, confidence: float = 0.9, grayscale: bool = False
    ) -> Optional[Tuple[int, int]]:
        """Locates the center coordinates of an image on the screen."""
        self._check_enabled()
        try:
            location = pyautogui.locateCenterOnScreen(
                str(image_path), confidence=confidence, grayscale=grayscale
            )
            if location:
                logger.debug(
                    f"[{self.agent_id}] Located image '{image_path}' at center {location}."
                )
                return (location.x, location.y)  # Return as tuple
            else:
                logger.debug(
                    f"[{self.agent_id}] Image '{image_path}' not found on screen."
                )
                return None
        except pyautogui.ImageNotFoundException:
            logger.warning(
                f"[{self.agent_id}] Image '{image_path}' not found on screen (ImageNotFoundException)."
            )
            return None
        except Exception as e:
            logger.error(
                f"[{self.agent_id}] PyAutoGUI locateCenterOnScreen failed for image '{image_path}': {e}",
                exc_info=True,
            )
            return None

    # EDIT START: Add locate_on_screen method
    def locate_on_screen(
        self, image_path: str | Path, confidence: float = 0.9, grayscale: bool = False
    ) -> Optional[Any]:
        """Locates an image on the screen, returning the bounding box (PyAutoGUI Box object) or None."""
        self._check_enabled()
        try:
            # Note: Returns a Box(left, top, width, height) object or None
            location = pyautogui.locateOnScreen(
                str(image_path), confidence=confidence, grayscale=grayscale
            )
            if location:
                logger.debug(
                    f"[{self.agent_id}] Located image '{image_path}' at {location}."
                )
            else:
                logger.debug(
                    f"[{self.agent_id}] Image '{image_path}' not found on screen."
                )
            return location
        except pyautogui.ImageNotFoundException:
            logger.warning(
                f"[{self.agent_id}] Image '{image_path}' not found on screen (ImageNotFoundException)."
            )
            return None
        except Exception as e:
            logger.error(
                f"[{self.agent_id}] PyAutoGUI locateOnScreen failed for image '{image_path}': {e}",
                exc_info=True,
            )
            return None

    # EDIT END

    # EDIT START: Add activate_window method
    def activate_window(self, title: str, timeout: int = 5) -> bool:
        """Attempts to find and activate a window by its title."""
        self._check_enabled()
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                windows = self.get_windows_by_title(title)
                if windows:
                    win = windows[0]  # Attempt with the first match
                    if win.isMinimized:
                        win.restore()
                        time.sleep(0.2)  # Give time for restore
                    # Sometimes activate needs a small delay or retry
                    win.activate()
                    time.sleep(0.5)  # Give time for activation
                    if win.isActive:
                        logger.info(
                            f"[{self.agent_id}] Successfully activated window with title containing '{title}'."
                        )
                        return True
                    else:
                        # Try bringing to front as another method
                        # Note: bringToFront might not be available on all platforms/pyautogui versions
                        try:
                            win.bringToFront()
                            time.sleep(0.5)
                            if win.isActive:
                                logger.info(
                                    f"[{self.agent_id}] Successfully activated window (via bringToFront) '{title}'."
                                )
                                return True
                        except AttributeError:
                            logger.warning(
                                f"[{self.agent_id}] win.bringToFront() not available."
                            )
                        except Exception as bring_e:
                            logger.warning(
                                f"[{self.agent_id}] Error during bringToFront for '{title}': {bring_e}"
                            )

                logger.debug(
                    f"[{self.agent_id}] Window '{title}' not active yet, retrying..."
                )
            except Exception as e:
                logger.error(
                    f"[{self.agent_id}] Error finding/activating window '{title}': {e}",
                    exc_info=True,
                )
                # Don't retry immediately on error, wait for loop
            time.sleep(0.5)  # Wait before retrying search/activation

        logger.error(
            f"[{self.agent_id}] Failed to activate window '{title}' within {timeout} seconds."
        )
        return False

    # EDIT END

    # EDIT START: Add clipboard methods
    def get_clipboard_content(self) -> Optional[str]:
        """Gets the current content of the clipboard."""
        self._check_clipboard_enabled()
        try:
            content = pyperclip.paste()
            logger.debug(f"[{self.agent_id}] Got clipboard content.")
            return content
        except Exception as e:
            logger.error(
                f"[{self.agent_id}] Failed to get clipboard content: {e}", exc_info=True
            )
            return None

    def copy_to_clipboard(self, text: str) -> bool:
        """Copies the given text to the clipboard."""
        self._check_clipboard_enabled()
        try:
            pyperclip.copy(text)
            logger.debug(f"[{self.agent_id}] Copied text to clipboard.")
            return True
        except Exception as e:
            logger.error(
                f"[{self.agent_id}] Failed to copy text to clipboard: {e}",
                exc_info=True,
            )
            return False

    # EDIT END


# EDIT END: Define OrchestratorBot Class


class NewMsgHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith(".msg"):
            return

        msg_path = Path(event.src_path)
        # Avoid processing own output messages or files already handled
        if f"_{BOT_AGENT_ID}_" in msg_path.name or msg_path in PROCESSED:
            return

        try:
            # Add a small delay to ensure file write is complete
            time.sleep(0.2)
            # Check file exists and modification time (slightly longer window)
            if msg_path.exists() and msg_path.stat().st_mtime < time.time() - 0.5:
                if msg_path not in PROCESSED:
                    logger.info(f"Detected new message in inbox: {msg_path.name}")
                    PROCESSED.add(msg_path)
                    handle_message(msg_path)
        except FileNotFoundError:
            logger.warning(f"File disappeared before processing: {msg_path.name}")
        except Exception as e:
            logger.error(
                f"Error during file check/processing trigger for {msg_path.name}: {e}",
                exc_info=True,
            )


def handle_message(msg_path: Path):
    raw_text = ""  # Initialize raw_text
    data = None
    sender_agent_id = "UNKNOWN_SENDER"
    message_id = None  # Initialize message_id
    # EDIT: Instantiate bot here temporarily for direct calls below
    # Proper implementation would involve a central bot instance or service
    bot = OrchestratorBot(config=None, agent_id=f"MessageHandler_{BOT_AGENT_ID}")

    try:
        logger.info(f"Handling message: {msg_path.name}")
        raw_text = msg_path.read_text(encoding="utf-8")
        logger.info(
            f"Read {len(raw_text)} bytes from {msg_path.name}. Attempting JSON decode..."
        )
        logger.debug(f"First 50 chars: {repr(raw_text[:50])}")
        data = json.loads(raw_text)
        sender_agent_id = data.get(
            "sender", sender_agent_id
        )  # Update sender if present

        # --- Step 1: Validate against Cursor Action Schema ---
        if not isinstance(data, dict):
            raise ValueError("Message content is not a JSON object.")

        message_id = data.get("message_id")
        action_type = data.get("action_type")
        parameters = data.get("parameters")
        _timestamp_utc = data.get("timestamp_utc")  # Renamed
        _target_window = data.get("target_window_identifier")  # Optional, Renamed

        required_fields = ["message_id", "action_type", "parameters", "timestamp_utc"]
        missing_fields = [field for field in required_fields if data.get(field) is None]

        if missing_fields:
            raise ValueError(
                f"Message validation failed: Missing required fields: {', '.join(missing_fields)}"
            )
        if not isinstance(parameters, dict):
            raise ValueError(
                "Message validation failed: 'parameters' field must be a dictionary."
            )

        # Validate action_type (optional, but good practice)
        valid_actions = [
            "typewrite",
            "press",
            "click",
            "hotkey",
            "scroll",
            "moveto",
            "screenshot",
        ]
        if action_type not in valid_actions:
            raise ValueError(
                f"Message validation failed: Invalid 'action_type': {action_type}. Must be one of {valid_actions}"
            )

        logger.info(
            f"Validated Cursor action message (ID: {message_id}, Type: {action_type}) from {sender_agent_id}"
        )

        # --- Step 2: Execute PyAutoGUI Action ---
        execution_status = "PENDING"  # Start with pending
        execution_details = f"Attempting action '{action_type}'."
        execution_success = False  # Track success

        try:
            logger.info(
                f"[{message_id}] Executing action via OrchestratorBot: {action_type} with params: {parameters}"
            )

            # EDIT: Use OrchestratorBot methods
            if action_type == "typewrite":
                text_to_type = parameters.get("text")
                interval = parameters.get("interval", 0.01)
                if text_to_type is None:
                    raise ValueError(
                        "Missing required 'text' parameter for typewrite action."
                    )
                execution_success = bot.typewrite(
                    str(text_to_type), interval=float(interval)
                )

            elif action_type == "press":
                keys = parameters.get("keys")
                if keys is None:
                    raise ValueError(
                        "Missing required 'keys' parameter for press action."
                    )
                if not (isinstance(keys, str) or isinstance(keys, list)):
                    raise ValueError(
                        "Invalid type for 'keys' parameter (must be string or list)."
                    )
                execution_success = bot.press(keys)

            elif action_type == "click":
                x = parameters.get("x")
                y = parameters.get("y")
                button = parameters.get("button", "left")
                clicks = parameters.get("clicks", 1)
                interval = parameters.get("interval", 0.1)
                execution_success = bot.click(
                    x=x,
                    y=y,
                    button=button,
                    clicks=int(clicks),
                    interval=float(interval),
                )

            elif action_type == "hotkey":
                keys = parameters.get("keys")
                if not keys or not isinstance(keys, list):
                    raise ValueError(
                        "Missing or invalid 'keys' parameter (must be list)."
                    )
                execution_success = bot.hotkey(*keys)

            elif action_type == "scroll":
                amount = parameters.get("amount")
                if amount is None:
                    raise ValueError("Missing required 'amount' parameter.")
                execution_success = bot.scroll(int(amount))

            elif action_type == "moveto":
                x = parameters.get("x")
                y = parameters.get("y")
                duration = parameters.get("duration", 0.1)
                if x is None or y is None:
                    raise ValueError("Missing required 'x' or 'y'.")
                execution_success = bot.move_to(
                    int(x), int(y), duration=float(duration)
                )

            elif action_type == "screenshot":
                region = parameters.get("region")
                save_path = parameters.get("save_path")
                if region and not (
                    isinstance(region, list)
                    and len(region) == 4
                    and all(isinstance(n, int) for n in region)
                ):
                    raise ValueError(
                        "Invalid 'region' parameter (must be list of 4 ints or null)."
                    )
                img_result = bot.screenshot(
                    region=tuple(region) if region else None, save_path=save_path
                )
                execution_success = img_result is not None
                # How to return image data? For now, just success/fail
            # {{ EDIT END: Implement pyautogui calls }}

            if execution_success:
                execution_status = "SUCCESS"
                execution_details = f"Action '{action_type}' executed successfully."
                logger.info(f"[{message_id}] {execution_details}")
            else:
                # Error logged within bot methods
                execution_status = "FAILED"
                execution_details = (
                    f"Action '{action_type}' failed during execution (see logs)."
                )
                logger.warning(f"[{message_id}] {execution_details}")

        except (
            ValueError,
            TypeError,
            pyautogui.PyAutoGUIException if PYAUTOGUI_AVAILABLE else OSError,
        ) as exec_error:
            execution_status = "FAILED"
            error_msg = f"Error executing action '{action_type}': {exec_error}"
            logger.error(f"[{message_id}] {error_msg}", exc_info=True)
            execution_details = error_msg

        # --- Step 3: Write back a response message ---
        # Use the status determined during execution
        # response_body = execution_details # OLD
        response_message_type = "ACTION_STATUS"
        response_payload_details = {
            "original_message_id": message_id,
            "status": execution_status,
            "details": execution_details,
        }

        timestamp_str = (
            datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
        filename_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

        reply = {
            "timestamp_utc_iso": timestamp_str,
            "sender": BOT_AGENT_ID,
            "target": sender_agent_id,
            "message_type": response_message_type,
            "payload": response_payload_details,
        }

        sender_inbox = MAILBOXES_DIR / sender_agent_id / "inbox"
        sender_inbox.mkdir(parents=True, exist_ok=True)
        out_path = (
            sender_inbox
            / f"{filename_ts}_{BOT_AGENT_ID}_{sender_agent_id}_{message_id}.reply.msg"
        )

        out_path.write_text(json.dumps(reply, indent=2), encoding="utf-8")
        logger.info(f"[{message_id}] Wrote response message to {out_path}")

        # --- Step 4: Clean up processed message ---
        try:
            msg_path.unlink()
            logger.info(f"[{message_id}] Deleted processed message: {msg_path.name}")
            PROCESSED.discard(msg_path)
        except OSError as e:
            logger.error(
                f"[{message_id}] Error deleting processed message {msg_path.name}: {e}"
            )

    except (json.JSONDecodeError, ValueError) as e:
        # Handle JSON parsing or validation errors
        error_details = f"JSON/Validation Error in {msg_path.name}: {e}."
        if isinstance(e, json.JSONDecodeError):
            error_details += (
                f" Pos {e.pos}: {e.msg}. Raw text start: {repr(raw_text[:80])}"
            )
        logger.error(error_details)
        # Move corrupted/invalid file
        try:
            error_dir = BOT_INBOX_DIR / "error_validation"
            error_dir.mkdir(parents=True, exist_ok=True)
            target_error_path = error_dir / msg_path.name
            if not target_error_path.exists():
                msg_path.rename(target_error_path)
                logger.info(
                    f"Moved invalid message {msg_path.name} to {target_error_path}"
                )
            else:
                logger.warning(
                    f"Invalid message {msg_path.name} already exists in error dir. Deleting original."
                )
                msg_path.unlink()
            PROCESSED.discard(msg_path)
            # Optionally send a failure response back if sender and message_id were parsed
            # Requires parsing attempt even on failure
            if sender_agent_id != "UNKNOWN_SENDER":
                fallback_message_id = message_id or f"unknown_{uuid.uuid4().hex[:8]}"
                # ... (construct and send failure response) ...
                logger.info(
                    f"Sent failure notification for invalid message {fallback_message_id} from {sender_agent_id}"
                )
        except Exception as move_e:
            logger.error(
                f"Failed to move/delete invalid message {msg_path.name}: {move_e}",
                exc_info=True,
            )

    except Exception as e:
        # Catchall for other unexpected errors
        logger.error(
            f"Unhandled error handling message {msg_path.name} (Message ID: {message_id}): {e}",
            exc_info=True,
        )
        # Optionally send a failure response back
        if sender_agent_id != "UNKNOWN_SENDER":
            fallback_message_id = message_id or f"unknown_{uuid.uuid4().hex[:8]}"
            # ... (construct and send failure response) ...
            logger.info(
                f"Sent failure notification for message {fallback_message_id} due to unhandled error."
            )


# Main bot logic
async def run_orchestrator_bot(config: AppConfig):
    logger.info("Initializing bot...")
    # EDIT START: Ensure bot's CORRECTED inbox directory exists
    BOT_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Monitoring directory: {BOT_INBOX_DIR}")
    # EDIT END

    event_handler = NewMsgHandler()
    observer = Observer()
    # EDIT START: Monitor the bot's specific CORRECTED inbox directory
    observer.schedule(event_handler, str(BOT_INBOX_DIR), recursive=False)
    # EDIT END
    logger.info("File system observer scheduled.")

    # Add check for dependencies
    try:
        import watchdog

        # import pyautogui # Check only if needed/enabled
    except ImportError as e:
        logger.critical(
            f"CRITICAL ERROR: Missing dependency - {e}. Please install requirements:"
        )
        logger.critical("pip install watchdog")  # Removed pyautogui for now
        sys.exit(1)

    logger.info("Starting observer...")
    observer.start()
    logger.info("Bot active. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nKeyboardInterrupt received. Stopping observer...")
        observer.stop()
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in the main loop: {e}", exc_info=True
        )
        # traceback.print_exc()
        observer.stop()

    observer.join()
    logger.info("Observer stopped. Bot shutting down.")
