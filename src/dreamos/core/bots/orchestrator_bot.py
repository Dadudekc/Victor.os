import asyncio
import json
import logging
import sys
import time
import traceback
import uuid  # Needed for potential fallback message_id
from datetime import datetime, timezone
from pathlib import Path

# NOTE: ChatGPTScraper is conceptual - represents this AI's response generation
# from chatgptscraper import ChatGPTScraper
import pyautogui  # Dependency: pip install pyautogui
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from ..automation.cursor_orchestrator import CursorOrchestrator, CursorOrchestratorError
from ..config import AppConfig  # Adjusted relative import
from ..coordination.agent_bus import AgentBus, BaseEvent

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

        try:
            # TODO: Implement window targeting using target_window hint (Task IMPL-CURSOR-TARGETING-001)
            # target_window = focus_cursor_window(target_window)
            # if not target_window:
            #    raise RuntimeError("Failed to find or focus Cursor window")
            # logger.info(f"[{message_id}] Focused target window.") # Add log after successful focus

            logger.info(
                f"[{message_id}] Executing action: {action_type} with params: {parameters}"
            )

            # {{ EDIT START: Implement pyautogui calls }}
            if action_type == "typewrite":
                text_to_type = parameters.get("text")
                interval = parameters.get("interval", 0.01)  # Default interval
                if text_to_type is None:  # Check for None specifically
                    raise ValueError(
                        "Missing required 'text' parameter for typewrite action."
                    )
                pyautogui.typewrite(str(text_to_type), interval=float(interval))
                logger.info(f"[{message_id}] Executed typewrite.")

            elif action_type == "press":
                keys = parameters.get("keys")
                if keys is None:
                    raise ValueError(
                        "Missing required 'keys' parameter for press action."
                    )
                # Handle single key string or list of keys
                if isinstance(keys, str):
                    pyautogui.press(keys)
                elif isinstance(keys, list):
                    pyautogui.press(keys)
                else:
                    raise ValueError(
                        "Invalid type for 'keys' parameter (must be string or list)."
                    )
                logger.info(f"[{message_id}] Executed press: {keys}")

            elif action_type == "click":
                # Extract params with defaults, handle potential None for x, y
                x = parameters.get("x")
                y = parameters.get("y")
                button = parameters.get("button", "left")
                clicks = parameters.get("clicks", 1)
                interval = parameters.get("interval", 0.1)
                pyautogui.click(
                    x=x,
                    y=y,
                    button=button,
                    clicks=int(clicks),
                    interval=float(interval),
                )
                logger.info(
                    f"[{message_id}] Executed click at ({x},{y}), button={button}, clicks={clicks}."
                )

            elif action_type == "hotkey":
                keys = parameters.get("keys")
                if not keys or not isinstance(keys, list):
                    raise ValueError(
                        "Missing or invalid 'keys' parameter for hotkey action (must be a list)."
                    )
                pyautogui.hotkey(*keys)  # Unpack list into arguments
                logger.info(f"[{message_id}] Executed hotkey: {keys}")

            elif action_type == "scroll":
                amount = parameters.get("amount")
                if amount is None:
                    raise ValueError(
                        "Missing required 'amount' parameter for scroll action."
                    )
                pyautogui.scroll(int(amount))
                logger.info(f"[{message_id}] Executed scroll: {amount}")

            elif action_type == "moveto":
                x = parameters.get("x")
                y = parameters.get("y")
                duration = parameters.get("duration", 0.1)
                if x is None or y is None:
                    raise ValueError(
                        "Missing required 'x' or 'y' parameter for moveto action."
                    )
                pyautogui.moveTo(int(x), int(y), duration=float(duration))
                logger.info(f"[{message_id}] Executed moveto: ({x}, {y})")

            elif action_type == "screenshot":
                region = parameters.get("region")  # Optional: list [x, y, w, h]
                save_path = parameters.get("save_path")  # Optional

                if region and not (
                    isinstance(region, list)
                    and len(region) == 4
                    and all(isinstance(n, int) for n in region)
                ):
                    raise ValueError(
                        "Invalid 'region' parameter for screenshot (must be list of 4 ints or null)."
                    )

                image = pyautogui.screenshot(region=tuple(region) if region else None)
                if save_path:
                    Path(save_path).parent.mkdir(
                        parents=True, exist_ok=True
                    )  # Ensure dir exists
                    image.save(save_path)
                    logger.info(
                        f"[{message_id}] Executed screenshot and saved to {save_path}"
                    )
                    # Optionally return path in details?
                else:
                    logger.info(
                        f"[{message_id}] Executed screenshot (image data captured, not saved)."
                    )
                    # Note: Returning image data via JSON response is not practical.
                    # Maybe log success, or indicate path if saved.

            else:
                # This case should not be reached due to earlier validation, but included for safety
                raise ValueError(
                    f"Unknown action type '{action_type}' cannot be executed."
                )

            # If execution reaches here without error:
            execution_status = "EXECUTED_SUCCESSFULLY"
            execution_details = f"Action '{action_type}' executed successfully."
            # {{ EDIT END }}

        except (ValueError, TypeError, pyautogui.PyAutoGUIException) as exec_error:
            # Catch specific parameter errors or pyautogui errors
            error_msg = f"Error executing action '{action_type}': {exec_error}"
            logger.error(f"[{message_id}] {error_msg}", exc_info=True)
            execution_status = "EXECUTION_FAILED"
            execution_details = error_msg
        except Exception as e:
            # Catch any other unexpected errors during execution
            error_msg = f"Unexpected error during '{action_type}' execution: {e}"
            logger.error(f"[{message_id}] {error_msg}", exc_info=True)
            execution_status = "EXECUTION_FAILED"
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
