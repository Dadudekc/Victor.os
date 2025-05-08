# src/dreamos/tools/cursor_bridge/cursor_bridge.py
import hashlib
import json
import logging
import os  # Import os module
import platform
import re  # Add re for parsing
import sys  # Keep sys import for stderr
import time
import uuid  # For telemetry IDs
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Initialize Logger Immediately After Imports
logger = logging.getLogger(__name__)

# --- Non-standard library imports ---
import pyautogui
import pyperclip  # For reliable pasting
from dreamos.core.config import get_config #, AppConfig, DEFAULT_CONFIG_PATH (AppConfig not needed directly for get_config)
from dreamos.core.coordination.agent_bus import AgentBus  # Import only AgentBus
from PIL import Image  # Requires Pillow
from pydantic import BaseModel, Field  # Ensure Field is imported for BusMessage

try:
    from dreamos.core.coordination.enums import MessageType
except ImportError:
    logger.warning(
        "Failed to import MessageType from enums. Assuming placeholder or string usage."
    )

    class MessageTypePlaceholder:
        BRIDGE_STATUS_UPDATE = "BRIDGE_STATUS_UPDATE"

    MessageType = MessageTypePlaceholder()

# --- NEW IMPORT ---
# Import the legacy web scraper
# try:
#     # Assumes chatgpt_scraper is reachable via python path or relative import
#     from dreamos.services.utils.chatgpt_scraper import ChatGPTScraper
#     CHATGPT_SCRAPER_AVAILABLE = True
#     logger.info("Successfully imported ChatGPTScraper.")
# except ImportError as e:
#     logger.error(f"Failed to import ChatGPTScraper: {e}. Web relay functionality disabled.")
#     ChatGPTScraper = None # Ensure variable exists
#     CHATGPT_SCRAPER_AVAILABLE = False
# --- END NEW IMPORT ---

# Configuration (Consider moving to config file or class)
CURSOR_WINDOW_TITLE_SUBSTRING = "Cursor"  # Adjust if needed
DEFAULT_TYPE_INTERVAL = 0.01  # Seconds between keystrokes
FOCUS_WAIT_TIME = 0.5  # Seconds to wait after focusing window
PASTE_WAIT_TIME = 0.1  # Seconds to wait after paste command

# Default coordinates if image/OCR fails (Should be configured)
DEFAULT_INPUT_X, DEFAULT_INPUT_Y = 100, 200  # Placeholder

# Response reading config
RESPONSE_AREA_REGION = None  # (left, top, width, height) - MUST BE CONFIGURED
RESPONSE_POLL_INTERVAL = 0.5  # Seconds between checks
RESPONSE_STABILITY_THRESHOLD = 2.0  # Seconds of no change to declare stable
RESPONSE_TIMEOUT = 60.0  # Max seconds to wait for a response

try:
    import pytesseract  # Requires pytesseract and Tesseract OCR engine

    PYTESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None
    PYTESSERACT_AVAILABLE = False
    logger.warning("Pytesseract not found. OCR functionality will be unavailable.")

# Placeholder Imports
# from dreamos.core.coordination.agent_bus import AgentBus, BusMessage, MessageType
# --- Mock AgentBus for standalone development ---
# EDIT START: Remove Mock AgentBus and import real one
# class MockAgentBus:
#     def publish(self, message):
#         logger.info(f"[MockAgentBus] Publish: {message}")
# class BusMessage:
#     def __init__(self, msg_type, payload, sender_id):
#         self.type = msg_type
#         self.payload = payload
#         self.sender = sender_id
#     def __str__(self): return f"BusMessage(Type={self.type}, Sender={self.sender}, Payload={self.payload})"
# class MessageType:
#     BRIDGE_STATUS_UPDATE = "BRIDGE_STATUS_UPDATE"
# --- End Mock ---
# EDIT END

# --- Swarm State Synchronization (Module 5) --- #

AGENT_ID = "CursorBridgeTool"  # ID for messages sent by this module
# bus = AgentBus() # Get singleton instance - Using Mock for now
# EDIT START: Use real AgentBus instance
# bus = MockAgentBus()
try:
    bus = AgentBus()  # Get singleton instance
    # EDIT START: Publish initializing status
    publish_bridge_status("INITIALIZING")
    # EDIT END
except Exception as bus_e:
    logger.error(f"Failed to instantiate AgentBus: {bus_e}. Status updates disabled.")
    bus = None  # Disable bus if instantiation fails
# EDIT END


# --- Define BusMessage Locally --- TODO: Move to appropriate shared location
class BusMessage(BaseModel):
    msg_type: str  # Using str for now, ideally the imported MessageType enum
    payload: Dict[str, Any] = Field(default_factory=dict)
    sender_id: str
    # Add Field import if not already present globally
    from pydantic import Field  # Local import is okay here


def publish_bridge_status(status: str, details: Optional[dict] = None):
    """Publishes bridge status updates (MessageType.BRIDGE_STATUS_UPDATE) to the AgentBus.

    Payload adheres to the schema: src/dreamos/schemas/bridge_status_schema.json
    Requires AgentBus instance.
    """
    if bus is None:
        logger.warning(f"AgentBus not available. Skipping status publish: {status}")
        return
    payload = {
        "status": status,  # e.g., "INJECTING", "EXTRACTING", "IDLE", "ERROR"
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "details": details or {},
    }
    # Use the locally defined BusMessage class
    message = BusMessage(
        msg_type=MessageType.BRIDGE_STATUS_UPDATE,  # Use imported/placeholder MessageType
        payload=payload,
        sender_id=AGENT_ID,
    )
    try:
        bus.publish(message)
        logger.info(f"Published bridge status: {status}")
    except Exception as e:
        logger.error(f"Failed to publish bridge status to AgentBus: {e}")


# Define custom exception for the bridge
class CursorBridgeError(Exception):
    """Custom exception for Cursor Bridge specific errors."""

    pass


class CursorInjectError(CursorBridgeError):
    """Indicates an error during the injection phase (focusing, pasting, etc.)."""

    pass


class CursorExtractError(CursorBridgeError):
    """Indicates an error during the extraction phase (capture, OCR, stabilization)."""

    pass


# --- Configuration Loading Helper ---


def _get_bridge_config(key: str, default: Any, config: AppConfig) -> Any:
    """Safely retrieves config value from config.tools.cursor_bridge.{key}.
    Requires a valid AppConfig instance.
    """
    if (
        not config
        or not hasattr(config, "tools")
        or not hasattr(config.tools, "cursor_bridge")
    ):
        logger.warning(
            f"AppConfig object missing 'tools.cursor_bridge' structure. Cannot find key '{key}'. Returning default."
        )
        return default

    # Access nested attribute safely
    bridge_config_section = getattr(config.tools, "cursor_bridge", None)
    if bridge_config_section:
        return getattr(bridge_config_section, key, default)
    else:
        logger.warning(
            f"AppConfig.tools missing 'cursor_bridge' attribute. Cannot find key '{key}'. Returning default."
        )
        return default


# EDIT: Helper to load config if not provided
def _ensure_config(config: Optional[AppConfig]) -> AppConfig:
    if config is None:
        logger.warning(
            "AppConfig not provided to cursor_bridge function. Attempting to load default config."
        )
        try:
            # This assumes DEFAULT_CONFIG_PATH is correctly set in core.config
            return AppConfig.load(str(DEFAULT_CONFIG_PATH))
        except Exception as e:
            logger.error(
                f"Failed to load default AppConfig: {e}. Bridge functionality may be impaired.",
                exc_info=True,
            )
            # Create a default empty AppConfig as a last resort to prevent crashes
            # This might need refinement based on required config fields
            return AppConfig()
    return config


# --- Payload Handling --- #


def handle_gpt_payload(payload: dict, config: Optional[AppConfig] = None):
    """Processes structured payload (type: code|text, content: str) and injects via inject_prompt_into_cursor."""
    config = _ensure_config(config)  # Ensure config is loaded
    content_type = payload.get("type")
    content = payload.get("content")

    if not content_type or not isinstance(content, str):
        raise ValueError(
            f"Invalid payload format. Requires 'type' and 'content': {payload}"
        )

    prepared_content = ""
    if content_type.lower() == "code":
        # Basic cleanup for code - remove leading/trailing whitespace/newlines
        prepared_content = content.strip()
        logger.info(f"Handling 'code' payload (length: {len(prepared_content)} chars).")
    elif content_type.lower() == "text":
        # For text, ensure it's treated as a single block
        prepared_content = content
        logger.info(f"Handling 'text' payload (length: {len(prepared_content)} chars).")
    else:
        raise ValueError(f"Unsupported payload type: {content_type}")

    try:
        publish_bridge_status(
            "INJECTING",
            {"payload_type": content_type, "content_length": len(prepared_content)},
        )
        inject_prompt_into_cursor(prepared_content, config)
        # Inject success telemetry is already inside inject_prompt_into_cursor
    except (ValueError, CursorInjectError) as e:
        publish_bridge_status("ERROR", {"operation": "inject", "error": str(e)})
        raise  # Re-raise original error
    # finally:
    # Optionally publish IDLE status if not immediately extracting
    # publish_bridge_status("IDLE")


# --- Core Functions (Injection) --- #


def find_and_focus_cursor_window(config: Optional[AppConfig] = None):
    """Finds Cursor window and focuses it.
    Uses Config: window_title_substring, focus_wait_seconds
    """
    config = _ensure_config(config)  # Ensure config is loaded
    title_substring = _get_bridge_config("window_title_substring", "Cursor", config)
    focus_wait = _get_bridge_config("focus_wait_seconds", 0.5, config)
    try:
        windows = pyautogui.getWindowsWithTitle(title_substring)
        if not windows:
            raise CursorInjectError(
                f"No window found with title containing '{title_substring}'"
            )

        # Assuming the first match is the correct one
        cursor_window = windows[0]
        logger.debug(f"Found Cursor window: {cursor_window.title}")

        # Different focus methods per OS might be needed for reliability
        os_type = platform.system()
        if os_type == "Windows":
            if cursor_window.isMinimized:
                cursor_window.restore()
            if not cursor_window.isActive:
                cursor_window.activate()
        elif os_type == "Darwin":  # macOS
            # macOS requires different handling, potentially AppleScript or other libs
            # For now, basic activate()
            if not cursor_window.isActive:
                cursor_window.activate()  # Might not be reliable on Mac
        else:  # Linux
            if not cursor_window.isActive:
                cursor_window.activate()

        time.sleep(focus_wait)  # Use configured wait time

        # Verify focus (optional but recommended)
        active_window = pyautogui.getActiveWindow()
        if active_window is None or title_substring not in active_window.title:
            logger.warning(
                f"Attempted to focus Cursor window ({title_substring}), but active window is now: {active_window.title if active_window else 'None'}"
            )
            # Consider raising error based on config?

        return cursor_window

    except pyautogui.PyAutoGUIException as e:
        # EDIT START: Add Telemetry Push on Failure
        push_telemetry(
            {
                "event": "focus_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error_details": str(e),
            },
            config,
        )
        # EDIT END
        logger.error(
            f"PyAutoGUI error finding/focusing Cursor window: {e}", exc_info=True
        )
        raise CursorInjectError(f"PyAutoGUI error focusing window: {e}") from e
    except Exception as e:
        # EDIT START: Add Telemetry Push on Failure
        push_telemetry(
            {
                "event": "focus_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error_details": str(e),
            },
            config,
        )
        # EDIT END
        logger.error(
            f"Unexpected error finding/focusing Cursor window: {e}", exc_info=True
        )
        raise CursorInjectError(f"Unexpected error focusing window: {e}") from e


def inject_prompt_into_cursor(prompt: str, config: Optional[AppConfig] = None):
    """Injects prompt into focused Cursor input field.
    Uses Config: paste_wait_seconds, input_coord_x, input_coord_y, paths.gui_snippets (for image location)
    """
    config = _ensure_config(config)  # Ensure config is loaded
    paste_wait = _get_bridge_config("paste_wait_seconds", 0.1, config)
    try:
        find_and_focus_cursor_window(config)  # Pass config

        # TODO: Need to locate the chat input field reliably
        input_field_coords = None
        input_field_image_path = None

        # Attempt 1: Locate via image template
        # Use config helper for path - assumes AppConfig structure
        gui_snippets_dir = _get_bridge_config("gui_snippets_dir", None, config)
        if gui_snippets_dir:
            input_field_image_path = Path(gui_snippets_dir) / "cursor_input_field.png"
            if input_field_image_path.is_file():
                try:
                    logger.debug(
                        f"Attempting to locate input field using image: {input_field_image_path}"
                    )
                    # Confidence can be adjusted
                    location = pyautogui.locateCenterOnScreen(
                        str(input_field_image_path), confidence=0.8
                    )
                    if location:
                        input_field_coords = (location.x, location.y)
                        logger.info(
                            f"Located input field via image at: {input_field_coords}"
                        )
                    else:
                        logger.warning("Input field image not found on screen.")
                except pyautogui.PyAutoGUIException as img_e:
                    logger.warning(f"PyAutoGUI error during image location: {img_e}")
                except Exception as img_e:  # Catch potential Pillow errors etc.
                    logger.warning(
                        f"Error locating image {input_field_image_path}: {img_e}"
                    )
            else:
                logger.warning(
                    f"Input field image template not found at: {input_field_image_path}"
                )

        # Fallback 2: Use configured coordinates
        if input_field_coords is None:
            conf_x = _get_bridge_config("input_coord_x", None, config)
            conf_y = _get_bridge_config("input_coord_y", None, config)

            if conf_x is None or conf_y is None:
                logger.error(
                    "Cursor input field coordinates (input_coord_x, input_coord_y) are not configured in AppConfig under 'tools.cursor_bridge' and image template failed or was not found. Cannot proceed with injection."
                )
                raise CursorInjectError(
                    "Input field coordinates not configured and image location failed."
                )

            input_field_coords = (conf_x, conf_y)
            logger.warning(
                f"Input field image not found or failed. Using configured input coordinates: {input_field_coords}"
            )

        # Click the determined location
        pyautogui.click(input_field_coords)
        time.sleep(0.1)

        # Clear field (Ctrl+A, Del) - More reliable than assuming empty
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.press("delete")
        time.sleep(0.05)

        # Paste prompt
        original_clipboard = pyperclip.paste()
        pyperclip.copy(prompt)
        time.sleep(paste_wait)  # Use configured wait time
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)  # Small delay after paste

        pyautogui.press("enter")
        logger.info("Prompt injected and Enter pressed.")
        # EDIT START: Add Telemetry Push on Success
        push_telemetry(
            {
                "event": "inject_success",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": f"Injected prompt length: {len(prompt)}",
            },
            config,
        )
        # EDIT END

        # Restore clipboard
        pyperclip.copy(original_clipboard)

    except CursorInjectError:
        # Error already logged by find_and_focus or pushed telemetry there
        raise  # Re-raise to signal failure
    except pyautogui.PyAutoGUIException as e:
        # EDIT START: Add Telemetry Push on Failure
        push_telemetry(
            {
                "event": "inject_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error_details": f"PyAutoGUI error: {e}",
            },
            config,
        )
        # EDIT END
        logger.error(f"PyAutoGUI error during prompt injection: {e}", exc_info=True)
        raise CursorInjectError(f"PyAutoGUI error injecting prompt: {e}") from e
    except Exception as e:
        # EDIT START: Add Telemetry Push on Failure
        push_telemetry(
            {
                "event": "inject_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error_details": f"Unexpected error: {e}",
            },
            config,
        )
        # EDIT END
        # Catch potential clipboard errors too
        logger.error(f"Unexpected error during prompt injection: {e}", exc_info=True)
        raise CursorInjectError(f"Unexpected error injecting prompt: {e}") from e


# --- Core Functions (Extraction) --- #


def configure_response_area(region: tuple[int, int, int, int]):
    """DEPRECATED: Sets the global RESPONSE_AREA_REGION. Use config instead."""
    # global RESPONSE_AREA_REGION
    logger.warning(
        "configure_response_area is deprecated. Set 'tools.cursor_bridge.response_area_region' in config."
    )
    # if (
    #     isinstance(region, tuple)
    #     and len(region) == 4
    #     and all(isinstance(x, int) for x in region)
    # ):
    #     RESPONSE_AREA_REGION = region
    #     logger.info(f"Response area configured: {RESPONSE_AREA_REGION}")
    # else:
    #     raise ValueError(
    #         "Invalid region format. Must be tuple of 4 integers (left, top, width, height)."
    #     )


def capture_response_area(
    config: Optional[AppConfig] = None,
    region_override: Optional[tuple[int, int, int, int]] = None,
) -> Image.Image | None:
    """Captures screenshot of response area.
    Uses Config: response_area_region (if region_override not provided)
    """
    """Captures a screenshot of the response area (located via image or config)."""
    config = _ensure_config(config)
    region_to_use = region_override
    if not region_to_use:
        region_to_use = _get_bridge_config("response_area_region", None, config)
        if not region_to_use:
            logger.error(
                "Response area region is not configured ('tools.cursor_bridge.response_area_region') and not found via image."
            )
            raise CursorExtractError("Response area region not configured or located.")
        if not (
            isinstance(region_to_use, (list, tuple))
            and len(region_to_use) == 4
            and all(isinstance(x, int) for x in region_to_use)
        ):
            logger.error(
                f"Invalid response_area_region format in config: {region_to_use}. Expected [left, top, width, height]."
            )
            raise CursorExtractError("Invalid response_area_region format.")

    logger.debug(f"Capturing screenshot of region: {region_to_use}")
    try:
        screenshot = pyautogui.screenshot(
            region=tuple(region_to_use)
        )  # Ensure it's a tuple
        return screenshot
    except pyautogui.PyAutoGUIException as e:
        # EDIT START: Add Telemetry Push on Failure
        push_telemetry(
            {
                "event": "capture_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error_details": f"PyAutoGUI error: {e}",
            },
            config,
        )
        # EDIT END
        logger.error(f"PyAutoGUI error capturing screenshot: {e}", exc_info=True)
        raise CursorExtractError(f"PyAutoGUI error capturing screenshot: {e}") from e
    except Exception as e:
        # EDIT START: Add Telemetry Push on Failure
        push_telemetry(
            {
                "event": "capture_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error_details": f"Unexpected error: {e}",
            },
            config,
        )
        # EDIT END
        logger.error(f"Unexpected error capturing screenshot: {e}", exc_info=True)
        raise CursorExtractError(f"Unexpected error capturing screenshot: {e}") from e


def extract_text_from_image(
    image: Image.Image, config: Optional[AppConfig] = None
) -> str:
    """Extracts text from the provided image using Tesseract OCR."""
    config = _ensure_config(config)
    if not PYTESSERACT_AVAILABLE:
        raise CursorExtractError("Pytesseract is not installed or available.")

    # Optional: Get Tesseract path from config if needed
    tesseract_cmd_path_str = _get_bridge_config("tesseract_cmd_path", None, config)
    if tesseract_cmd_path_str:  # If the path is configured
        tesseract_cmd_path_obj = Path(tesseract_cmd_path_str)
        if tesseract_cmd_path_obj.is_file():
            logger.info(
                f"Using custom Tesseract executable path: {tesseract_cmd_path_obj}"
            )
            pytesseract.tesseract_cmd = str(tesseract_cmd_path_obj)
        else:
            # Configured path is invalid, log error and Pytesseract will attempt its default (PATH lookup).
            logger.error(
                f"Configured Tesseract executable path 'tools.cursor_bridge.tesseract_cmd_path': \"{tesseract_cmd_path_str}\" is invalid or not a file. Pytesseract will attempt to use its default (system PATH), which may fail if Tesseract is not installed correctly there."
            )
            # Not setting pytesseract.tesseract_cmd here means it uses its internal default.
    else:
        logger.debug(
            "No custom Tesseract path configured ('tools.cursor_bridge.tesseract_cmd_path'). Pytesseract will use its default (system PATH)."
        )

    try:
        text = pytesseract.image_to_string(image)
        logger.debug(f"Extracted text length: {len(text)}")
        return text
    except Exception as e:
        # EDIT START: Add Telemetry Push on Failure
        push_telemetry(
            {
                "event": "ocr_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error_details": str(e),
            },
            config,
        )
        # EDIT END
        logger.error(f"Error during Tesseract OCR processing: {e}", exc_info=True)
        raise CursorExtractError(f"Error during Tesseract OCR: {e}") from e


def monitor_and_extract_response(
    config: Optional[AppConfig] = None,
) -> str:
    """Monitors the response area for stable text and extracts it."""
    config = _ensure_config(config)
    timeout_seconds = _get_bridge_config("response_timeout_seconds", 60.0, config)
    stability_threshold = _get_bridge_config("response_stability_seconds", 2.0, config)
    poll_interval = _get_bridge_config("response_poll_interval_seconds", 0.5, config)
    max_extract_retries = _get_bridge_config("response_extract_max_retries", 3, config)

    start_time = time.monotonic()
    last_change_time = start_time
    last_text = ""
    last_image_hash = ""
    extract_error_count = 0

    logger.info(
        f"Monitoring response area for stable text (Timeout: {timeout_seconds}s, Stability: {stability_threshold}s)"
    )

    response_area_image_path = None
    gui_snippets_dir = _get_bridge_config("gui_snippets_dir", None, config)
    if gui_snippets_dir:
        response_area_image_path = Path(gui_snippets_dir) / "cursor_response_area.png"
        if not response_area_image_path.is_file():
            logger.warning(
                f"Response area image template not found: {response_area_image_path}"
            )
            response_area_image_path = (
                None  # Fallback to configured region if image missing
            )

    try:
        publish_bridge_status(
            "EXTRACTING",
            {
                "timeout_config_s": timeout_seconds,
                "stability_config_s": stability_threshold,
            },
        )
        while time.monotonic() - start_time < timeout_seconds:
            try:
                current_region = _get_bridge_config(
                    "response_area_region", None, config
                )
                if response_area_image_path:
                    try:
                        location = pyautogui.locateOnScreen(
                            str(response_area_image_path), confidence=0.8
                        )
                        if location:
                            # Use located region (left, top, width, height)
                            current_region = (
                                location.left,
                                location.top,
                                location.width,
                                location.height,
                            )
                            logger.debug(
                                f"Located response area via image at: {current_region}"
                            )
                        else:
                            logger.warning(
                                "Response area image not found on screen, falling back to configured region."
                            )
                            # Fallthrough to use configured region if image not found
                    except pyautogui.PyAutoGUIException as img_e:
                        logger.warning(
                            f"PyAutoGUI error locating response area image: {img_e}, falling back to configured region."
                        )
                    except Exception as img_e:
                        logger.warning(
                            f"Error locating response area image {response_area_image_path}: {img_e}, falling back to configured region."
                        )

                current_image = capture_response_area(
                    config, region_override=current_region
                )  # Pass region override

                if current_image is None:  # Should not happen if config is validated
                    time.sleep(poll_interval)
                    continue

                # Use image hash for faster change detection before OCR
                current_image_bytes = current_image.tobytes()
                current_image_hash = hashlib.sha256(current_image_bytes).hexdigest()

                if current_image_hash != last_image_hash:
                    logger.debug(
                        f"Image hash changed. Old: {last_image_hash[:8]}, New: {current_image_hash[:8]}"
                    )
                    current_text = extract_text_from_image(
                        current_image, config
                    ).strip()
                    if current_text != last_text:
                        logger.debug(
                            f"Text changed (Length: {len(current_text)}). Resetting stability timer."
                        )
                        last_text = current_text
                        last_change_time = time.monotonic()
                    else:
                        logger.debug(
                            "Image changed but extracted text is identical. Treating as stable."
                        )
                        # Consider image changed but text didn't as potentially stable
                        pass
                    last_image_hash = (
                        current_image_hash  # Update hash only if image really changed
                    )
                else:
                    logger.debug("Image hash stable.")
                    # Image unchanged, assume text is stable
                    pass

                # Check for stability
                if time.monotonic() - last_change_time >= stability_threshold:
                    if last_text:
                        stability_duration = time.monotonic() - last_change_time
                        logger.info(
                            f"Response stabilized after {stability_duration:.2f} seconds."
                        )
                        # EDIT START: Add Telemetry Push on Success
                        push_telemetry(
                            {
                                "event": "extract_success",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "stability_duration_s": stability_duration,
                                "response_length": len(last_text),
                            },
                            config,
                        )
                        # EDIT END
                        publish_bridge_status(
                            "IDLE", {"reason": "Extraction successful"}
                        )
                        return last_text
                    else:
                        # Stable but empty, keep waiting
                        logger.debug("Area is stable but empty.")

            except CursorExtractError as e:
                extract_error_count += 1
                logger.warning(
                    f"Extraction error during monitoring: {e}. Retry {extract_error_count}/{max_extract_retries}..."
                )
                if extract_error_count >= max_extract_retries:
                    logger.error(
                        f"Maximum extraction retries ({max_extract_retries}) reached. Aborting."
                    )
                    # EDIT START: Add Telemetry Push on Failure (Max Retries)
                    push_telemetry(
                        {
                            "event": "extract_error_retries",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "error_details": f"Max retries ({max_extract_retries}) reached: {e}",
                        },
                        config,
                    )
                    # EDIT END
                    publish_bridge_status(
                        "ERROR",
                        {
                            "operation": "extract",
                            "error": f"Max retries ({max_extract_retries}) reached: {e}",
                        },
                    )
                    raise CursorExtractError(
                        f"Max extraction retries reached: {e}"
                    ) from e
                # Fallthrough to time.sleep if retry limit not reached
            except Exception as e:
                # EDIT START: Add Telemetry Push on Failure
                push_telemetry(
                    {
                        "event": "extract_error_unexpected",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "error_details": f"Unexpected monitoring loop error: {e}",
                    },
                    config,
                )
                # EDIT END
                logger.error(
                    f"Unexpected error during monitoring loop: {e}", exc_info=True
                )
                # Decide whether to raise or continue polling
                publish_bridge_status(
                    "ERROR", {"operation": "extract_unexpected", "error": str(e)}
                )
                raise CursorExtractError(
                    "Unexpected error during response monitoring"
                ) from e

            time.sleep(poll_interval)

        # Timeout occurred
        timeout_value = time.monotonic() - start_time  # Actual duration
        logger.error(
            f"Timeout ({timeout_seconds}s) waiting for stable response. Actual duration: {timeout_value:.2f}s"
        )
        # EDIT START: Add Telemetry Push on Failure (Timeout)
        push_telemetry(
            {
                "event": "extract_timeout",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "timeout_config_s": timeout_seconds,
                "actual_duration_s": timeout_value,
            },
            config,
        )
        # EDIT END
        publish_bridge_status(
            "ERROR",
            {
                "operation": "extract",
                "error": "Timeout occurred but exception not raised properly?",
            },
        )
        raise CursorExtractError("Timeout waiting for stable response.")

    except CursorExtractError as e:
        # Telemetry pushed inside exception handling
        publish_bridge_status("ERROR", {"operation": "extract", "error": str(e)})
        raise  # Re-raise
    except Exception as e:
        # Telemetry pushed inside exception handling
        publish_bridge_status(
            "ERROR", {"operation": "extract_unexpected", "error": str(e)}
        )
        raise CursorExtractError("Unexpected error during response monitoring") from e

    # Should not be reached if timeout raises exception properly
    publish_bridge_status(
        "ERROR",
        {
            "operation": "extract",
            "error": "Timeout occurred but exception not raised properly?",
        },
    )
    raise CursorExtractError(
        "Timeout waiting for stable response."
    )  # Ensure exception is raised


# --- Output Summarizer (Module 7) --- #


def summarize_cursor_output(raw_text: str, max_length: int = 500) -> str:
    """Summarizes the raw text output from Cursor (placeholder)."""
    if not isinstance(raw_text, str):
        return "[Invalid Input Type]"

    # Placeholder: Simple truncation
    summary = raw_text[:max_length]
    if len(raw_text) > max_length:
        summary += "... (truncated)"

    # TODO: Implement LLM-based summarization for better results
    logger.info(
        f"Summarized output (length: {len(summary)} chars). Original length: {len(raw_text)} chars."
    )
    return summary


def interact_with_cursor(prompt: str, config: Optional[AppConfig] = None) -> str:
    """Injects prompt, monitors for response, extracts, summarizes and returns it."""
    config = _ensure_config(config)
    try:
        structured_payload = {"type": "text", "content": prompt}
        handle_gpt_payload(structured_payload, config)

        raw_response = monitor_and_extract_response(config)

        # EDIT START: Add summarization step
        summary_max_len = _get_bridge_config("summary_max_length", 500, config)
        summarized_response = summarize_cursor_output(
            raw_response, max_length=summary_max_len
        )
        # EDIT END

        return summarized_response  # Return summarized response
    except CursorBridgeError as e:
        logger.error(f"Cursor interaction failed: {e}")
        raise  # Re-raise the specific bridge error
    except Exception as e:
        logger.critical(
            f"Critical unexpected error during interaction: {e}", exc_info=True
        )
        # Wrap unexpected errors
        raise CursorBridgeError(f"Unexpected critical error: {e}") from e


# --- Telemetry / Feedback Loop --- #

# TELEMETRY_LOG_FILE = Path("runtime/telemetry/bridge_telemetry.jsonl") # REMOVED global


def parse_bridge_log(log_line: str) -> Optional[dict]:
    """Parses a bridge log line to extract telemetry data (basic example)."""
    # Example: Look for specific log messages indicating success/failure
    injection_success_match = re.search(
        r"INFO: Prompt injected and Enter pressed.", log_line
    )
    if injection_success_match:
        # Find timestamp (assuming standard log format)
        ts_match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})", log_line)
        timestamp = ts_match.group(1) if ts_match else "Unknown"
        return {
            "event": "inject_success",
            "timestamp": timestamp,
            "details": "Prompt injection confirmed.",
        }

    extraction_success_match = re.search(
        r"INFO: Response stabilized after (\d+\.\d+) seconds.", log_line
    )
    if extraction_success_match:
        ts_match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})", log_line)
        timestamp = ts_match.group(1) if ts_match else "Unknown"
        stability_time = float(extraction_success_match.group(1))
        return {
            "event": "extract_success",
            "timestamp": timestamp,
            "stability_duration_s": stability_time,
        }

    error_match = re.search(
        r"ERROR: (Cursor interaction failed|Timeout waiting for stable response|.+? error during .+?: .+)",
        log_line,
    )
    if error_match:
        ts_match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})", log_line)
        timestamp = ts_match.group(1) if ts_match else "Unknown"
        error_details = error_match.group(1).strip()
        event_type = "extract_timeout" if "Timeout" in error_details else "bridge_error"
        return {
            "event": event_type,
            "timestamp": timestamp,
            "error_details": error_details,
        }

    # Add more parsing rules as needed
    return None


def push_telemetry(telemetry_data: dict, config: Optional[AppConfig] = None):
    """Pushes telemetry data to the configured log file."""
    # Get telemetry log file path from config, with a default
    default_log_path = Path("runtime/telemetry/bridge_telemetry.jsonl")
    try:
        # Try resolving relative to project root if config path isn't absolute
        # Assuming PROJECT_ROOT might be accessible or AppConfig handles resolution
        configured_path_str = _get_bridge_config(
            "telemetry_log_file", str(default_log_path), config
        )
        telemetry_log_path = Path(configured_path_str)
        if not telemetry_log_path.is_absolute():
            # Basic attempt to make it relative to runtime if not absolute
            # A more robust solution would use config.resolve() if available
            try:
                runtime_path = _get_bridge_config("runtime_path", "runtime", config)
                telemetry_log_path = Path(runtime_path) / telemetry_log_path
                logger.debug(
                    f"Resolved relative telemetry path to: {telemetry_log_path}"
                )
            except Exception:
                logger.warning(
                    "Could not resolve relative telemetry path relative to runtime. Using path as is."
                )

    except Exception as config_e:
        logger.error(
            f"Error getting telemetry_log_file path from config: {config_e}. Using default: {default_log_path}"
        )
        telemetry_log_path = default_log_path

    try:
        telemetry_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(telemetry_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(telemetry_data) + "\n")
        logger.info(
            f"Pushed telemetry event: {telemetry_data.get('event')} to {telemetry_log_path}"
        )
    except Exception as e:
        logger.error(f"Failed to push telemetry to {telemetry_log_path}: {e}")


# --- Demonstration Scenario Harness (Module 6) --- #


def simulate_gpt_call(task_description: str) -> dict:
    """Placeholder function simulating a call to GPT."""
    logger.info(f"[DEMO] Simulating GPT call for task: '{task_description}'")
    # Based on task, return mock code or text payload
    if "code" in task_description.lower() or "python" in task_description.lower():
        mock_content = f'# Mock code response for: {task_description}\nprint("Task completed: {task_description}")\n'
        payload = {"type": "code", "content": mock_content}
    else:
        mock_content = f"Mock text response for task: {task_description}. The key is to understand the core requirements."
        payload = {"type": "text", "content": mock_content}
    logger.info(f"[DEMO] Mock GPT returned payload: {payload['type']}")
    return payload


def run_demo_scenario(task: str, config: Optional[AppConfig] = None):
    """Runs a demo scenario: simulate GPT -> inject to Cursor -> optionally extract response."""
    logger.info(f"\n--- Running Demo Scenario: '{task}' ---")
    try:
        # 1. Simulate getting payload from GPT
        gpt_payload = simulate_gpt_call(task)

        # 2. Inject into Cursor via bridge
        handle_gpt_payload(gpt_payload, config)
        logger.info("[DEMO] Payload injection initiated.")

        # 3. Optionally wait and extract response (can be slow/error-prone)
        extract_response = _get_bridge_config(
            "demo_extract_response", False, config
        )  # Add config option
        if extract_response:
            logger.info("[DEMO] Attempting to extract response from Cursor...")
            time.sleep(2)  # Give Cursor some time to respond
            cursor_response = monitor_and_extract_response(config)
            logger.info(
                f"[DEMO] Extracted Cursor response (length: {len(cursor_response)}):\n{cursor_response[:200]}..."
            )  # Log truncated response
        else:
            logger.info("[DEMO] Skipping response extraction based on config.")

    except (CursorBridgeError, ValueError, pyautogui.PyAutoGUIException) as e:
        logger.error(f"[DEMO] Scenario failed: {e}")
    except Exception as e:
        logger.error(f"[DEMO] Unexpected error in scenario: {e}", exc_info=True)


# --- Final Integration Validator (Module 8) --- #


def validate_full_cycle(task: str, config: Optional[AppConfig] = None):
    """Runs the full demo cycle and logs the outcome for validation."""
    logger.info(f"\n=== Validating Full Cycle for Task: '{task}' ===")
    final_result = None
    error = None
    try:
        # The demo scenario now handles the full flow if extraction is enabled
        # We need to capture the return value if interact_with_cursor is modified to return summary
        # Modify run_demo_scenario slightly to return the result for validation

        # --- Re-run Demo Scenario (capturing output conceptually) ---
        # This implicitly calls: simulate_gpt -> handle_payload -> inject -> monitor -> extract -> summarize
        logger.info("Executing demo scenario for validation...")
        # Re-running the demo function implicitly tests the chain
        # We assume run_demo_scenario logs enough info, or modify it to return status/result

        # Simplified approach: Call interact_with_cursor directly for validation purpose
        # if we want the final summarized result explicitly here.
        logger.info("Simulating GPT call for validation...")
        gpt_payload = simulate_gpt_call(task)
        logger.info("Calling handle_gpt_payload for injection...")
        handle_gpt_payload(gpt_payload, config)
        logger.info("Calling monitor_and_extract_response...")
        raw_response = monitor_and_extract_response(config)
        logger.info("Calling summarize_cursor_output...")
        summary_max_len = _get_bridge_config("summary_max_length", 500, config)
        final_result = summarize_cursor_output(raw_response, max_length=summary_max_len)
        logger.info(
            f"Full cycle validation successful. Final Summary (first 100 chars): {final_result[:100]}"
        )

    except CursorBridgeError as e:
        logger.error(f"VALIDATION FAILED: Bridge error during cycle: {e}")
        error = str(e)
    except ValueError as e:
        logger.error(f"VALIDATION FAILED: Value error during cycle: {e}")
        error = str(e)
    except Exception as e:
        logger.error(
            f"VALIDATION FAILED: Unexpected error during cycle: {e}", exc_info=True
        )
        error = f"Unexpected: {e}"

    # Log validation outcome
    validation_log_entry = {
        "event": "full_cycle_validation",
        "task_description": task,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "SUCCESS" if error is None else "FAILURE",
        "final_summary_preview": final_result[:100] if final_result else None,
        "error": error,
    }
    push_telemetry(validation_log_entry, config)  # Log to telemetry file
    logger.info(
        f"=== Full Cycle Validation Complete. Status: {validation_log_entry['status']} ==="
    )
    return error is None  # Return True if successful, False otherwise


# --- Updated RELAY FUNCTION with Telemetry ---
def relay_prompt_via_web_and_gui(
    prompt: str, config: Optional[AppConfig] = None, run_id: str = "standalone_run"
):
    """
    Orchestrates a complex interaction:
    1. Takes a prompt.
    2. Uses ChatGPTScraper to get a response from chatgpt.com.
    3. Injects this response back into the Cursor GUI.
    Logs telemetry at each phase.
    """
    log_telemetry(run_id, "relay_start", "INITIATED", {"prompt_length": len(prompt)})

    ChatGPTScraper_class = None
    CHATGPT_SCRAPER_AVAILABLE = False
    try:
        from dreamos.services.utils.chatgpt_scraper import ChatGPTScraper as Scraper

        ChatGPTScraper_class = Scraper
        CHATGPT_SCRAPER_AVAILABLE = True
        logger.info(
            "Successfully imported ChatGPTScraper for relay_prompt_via_web_and_gui."
        )
    except ImportError as e:
        logger.error(
            f"Failed to import ChatGPTScraper for relay_prompt_via_web_and_gui: {e}. Web relay functionality disabled."
        )
        log_telemetry(
            run_id,
            "scraper_init",
            "ERROR",
            error_message=f"ChatGPTScraper import failed: {e}",
        )
        # Depending on desired behavior, could raise here or try to continue if scraper is optional
        # For this specific relay function, it's essential.
        raise CursorBridgeError(f"ChatGPTScraper failed to import, cannot relay: {e}")

    if (
        not CHATGPT_SCRAPER_AVAILABLE or ChatGPTScraper_class is None
    ):  # Check ChatGPTScraper_class
        error_msg = "ChatGPTScraper class is not available. Cannot perform web relay."
        log_telemetry(
            run_id, "scraper_availability_check", "FAIL", error_message=error_msg
        )
        print(f"[BRIDGE_RELAY {run_id}] FAIL - {error_msg}", file=sys.stderr)
        raise CursorBridgeError(error_msg)
    log_telemetry(run_id, "scraper_availability_check", "SUCCESS")

    # --- Load Config (Does not require GUI lock) ---
    if config is None:
        try:
            log_telemetry(run_id, "config_load_attempt", "START")
            config = AppConfig()  # Or load from file
            log_telemetry(run_id, "config_load_attempt", "SUCCESS")
            logger.info("Loaded default AppConfig for relay.")
        except Exception as e:
            error_msg = f"Configuration (AppConfig) is required for relay. Load attempt failed: {e}"
            log_telemetry(
                run_id, "config_load_attempt", "FAIL", error_message=error_msg
            )
            print(f"[BRIDGE_RELAY {run_id}] FAIL - {error_msg}", file=sys.stderr)
            raise CursorBridgeError(error_msg) from e

    publish_bridge_status("RELAYING_WEB_TO_GUI", {"prompt_length": len(prompt)})
    chatgpt_response = None
    scraper_instance = None
    phase_status = "UNKNOWN"

    try:
        # --- Step 1 & 2: Use ChatGPTScraper (Web interaction - No GUI lock needed yet) ---
        print(f"[BRIDGE_RELAY {run_id}] Initializing ChatGPTScraper...")
        log_telemetry(run_id, "scraper_init", "STARTED")

        # Determine cookie file path from config or default
        # Assuming AppConfig structure: config.tools.chatgpt_scraper.cookie_file
        # Or a more generic config.paths.data_dir / "chatgpt_cookies.json"
        # For now, let's use a placeholder path if config is not robustly providing this
        cookie_file_path_str = _get_bridge_config(
            "cookie_file_path",
            "runtime/config/chatgpt_cookies.json",
            config,
        )
        cookie_file_path = Path(cookie_file_path_str)  # Ensure it's a Path object

        # Instantiate the scraper
        # The original code had ChatGPTScraper(cookie_file=...),
        # but the class __init__ takes (self, config: AppConfig, headless: bool = False)
        # We need to ensure AppConfig is passed or modify scraper, or pass None if it handles it.
        # For now, assuming config object is available and passed. If not, this needs adjustment.
        if config is None:
            logger.warning(
                "AppConfig not provided to relay_prompt_via_web_and_gui, ChatGPTScraper might not initialize correctly."
            )
            # Fallback or raise error depending on scraper's ability to handle missing config
            # scraper_instance = ChatGPTScraper_class() # This would fail if config is mandatory
            raise CursorBridgeError(
                "AppConfig is required for ChatGPTScraper initialization in relay_prompt_via_web_and_gui."
            )

        scraper_instance = ChatGPTScraper_class(
            config=config, headless=True
        )  # Pass config

        # The original logic had a direct cookie_file parameter, which is not in the current scraper __init__
        # scraper_instance = ChatGPTScraper(cookie_file=str(cookie_file_path)) # OLD
        # if not Path(cookie_file_path).exists():
        #     logger.warning(f"Cookie file {cookie_file_path} not found. Scraper may require login.")
        # scraper_instance = ChatGPTScraper(cookie_file="runtime/config/chatgpt_cookies.json") # OLD FALLBACK

        print(f"[BRIDGE_RELAY {run_id}] ChatGPTScraper Initialized.")
        log_telemetry(run_id, "scraper_init", "COMPLETED")

        log_telemetry(
            run_id, "scraper_send_prompt", "STARTED", {"prompt_length": len(prompt)}
        )
        print(
            f"[BRIDGE_RELAY {run_id}] Sending prompt to ChatGPT via web scraper: '{prompt[:50]}...'"
        )
        scraper_instance.send_message_and_wait(prompt)
        print(f"[BRIDGE_RELAY {run_id}] Extracting reply from ChatGPT...")
        chatgpt_response = scraper_instance.extract_latest_reply()

        if not chatgpt_response:
            # ... (error logging, raise error) ...
            raise CursorBridgeError(error_msg)

        log_telemetry(run_id, "scraper_send_prompt", "SUCCESS", {...})
        print(
            f"[BRIDGE_RELAY {run_id}] Received response from ChatGPTScraper (...): '{chatgpt_response[:50]}...'"
        )

        # --- Step 3: Inject the *response* into Cursor GUI (Requires GUI Lock) ---
        log_telemetry(
            run_id, "gui_injection", "START", {"response_length": len(chatgpt_response)}
        )
        print(
            f"[BRIDGE_RELAY {run_id}] Attempting to acquire GUI lock for injection..."
        )
        with gui_interaction_lock:
            print(
                f"[BRIDGE_RELAY {run_id}] GUI lock acquired. Injecting scraped response into Cursor GUI..."
            )
            # Assuming inject_prompt_into_cursor handles its own detailed pyautogui logging/errors
            # It also acquires its own lock, but this outer lock ensures atomicity of this phase
            inject_prompt_into_cursor(chatgpt_response, config)  # Inject the RESPONSE
            log_telemetry(run_id, "gui_injection", "SUCCESS")
            print(
                f"[BRIDGE_RELAY {run_id}] Response injected into Cursor GUI. Releasing lock."
            )
        # Lock released automatically by 'with'

        publish_bridge_status("IDLE", {"last_action": "relay_web_to_gui_success"})
        phase_status = "SUCCESS"
        log_telemetry(run_id, "relay_end", phase_status)
        print(
            f"[BRIDGE_RELAY {run_id}] SUCCESS - Successfully relayed prompt via web and injected response into GUI."
        )

    except CursorBridgeError:
        # ... (error handling) ...
        raise  # Re-raise original error
    except Exception as e:
        # ... (error handling) ...
        raise CursorBridgeError(f"Failed during web/GUI relay: {e}") from e


# --- Telemetry Logging Function ---
def log_telemetry(
    run_id: str,
    phase_id: str,
    status: str,
    metadata: Optional[dict] = None,
    error_message: Optional[str] = None,
):
    """Logs a structured telemetry event to the JSONL file."""
    try:
        TELEMETRY_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        log_entry = {
            "event_id": str(uuid.uuid4()),
            "run_id": run_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "phase_id": phase_id,
            "status": status,  # e.g., START, SUCCESS, FAIL
            "metadata": metadata or {},
            "error_message": error_message,
        }
        with open(TELEMETRY_LOG_FILE, "a", encoding="utf-8") as f:
            json.dump(log_entry, f)
            f.write("\n")
    except Exception as e:
        # Fallback to stderr if telemetry logging fails
        print(f"CRITICAL ERROR: Failed to write telemetry log - {e}", file=sys.stderr)
        print(
            f"Failed Telemetry Data: {log_entry if 'log_entry' in locals() else 'N/A'}",
            file=sys.stderr,
        )


# --- Updated Main execution block with Telemetry ---
if __name__ == "__main__":
    main_run_id = f"test_run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    print(
        f"--- Running Cursor Bridge Web Relay Test (ID: {main_run_id}) (with Config Bypass) ---"
    )
    log_telemetry(main_run_id, "test_start", "START")

    # Configure logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)  # Ensure logger is available

    # Define PROJECT_ROOT simply for the bypass
    # Assumes this script is in src/dreamos/tools/cursor_bridge
    try:
        PROJECT_ROOT = Path(__file__).resolve().parents[3]
    except IndexError:
        PROJECT_ROOT = Path.cwd()  # Fallback if structure is different
        logger.warning(
            f"Could not determine project root via relative path, using CWD: {PROJECT_ROOT}"
        )
    print(f"INFO: Determined PROJECT_ROOT for bypass: {PROJECT_ROOT}")

    # --- CONFIG BYPASS START ---
    print("INFO: Using minimal config bypass for testing.")
    minimal_config = {
        "paths": {
            # Use PROJECT_ROOT defined above
            "runtime": Path(
                os.getenv("DREAMOS_RUNTIME_PATH", PROJECT_ROOT / "runtime")
            ).resolve(),
            "chatgpt_cookie_file": (
                PROJECT_ROOT / "runtime" / "config" / "chatgpt_cookies.json"
            ).resolve(),
        },
        "tools": {
            "cursor_bridge": {
                "window_title_substring": "Cursor",
                "focus_wait_seconds": 0.6,
                "paste_wait_seconds": 0.15,
                "input_coord_x": 100,
                "input_coord_y": 200,
            }
        },
    }
    # ... (ConfigWrapper class remains the same) ...
    from types import SimpleNamespace

    class ConfigWrapper:
        def __init__(self, config_dict):
            self._config = config_dict
            self.paths = SimpleNamespace(**config_dict.get("paths", {}))
            tools_config = config_dict.get("tools", {})
            self.tools = SimpleNamespace(
                **{
                    k: SimpleNamespace(**v) if isinstance(v, dict) else v
                    for k, v in tools_config.items()
                }
            )
            self.chatgpt_scraper = SimpleNamespace(
                **config_dict.get("chatgpt_scraper", {})
            )

        def resolve(self, path_str: str) -> Path:
            if path_str.startswith("runtime/"):
                # Use the runtime path defined within the wrapper
                return self.paths.runtime / path_str[len("runtime/") :]
            # Use the PROJECT_ROOT defined in the main block scope if available
            # This is a bit messy, cleaner way would be to pass PROJECT_ROOT into wrapper
            return PROJECT_ROOT / Path(path_str)

    test_config_obj = None
    try:
        log_telemetry(main_run_id, "config_bypass_init", "START")
        print("INFO: Using minimal config bypass for testing.")
        test_config_obj = ConfigWrapper(minimal_config)
        test_config_obj.paths.chatgpt_cookie_file = minimal_config["paths"][
            "chatgpt_cookie_file"
        ]
        log_telemetry(main_run_id, "config_bypass_init", "SUCCESS")
        print("Config bypass object created.")
    except Exception as cfg_e:
        err_msg = f"Failed to create config bypass object: {cfg_e}"
        log_telemetry(main_run_id, "config_bypass_init", "FAIL", error_message=err_msg)
        print(f"ERROR: {err_msg}", file=sys.stderr)
        import sys

        sys.exit(1)
    # --- CONFIG BYPASS END ---

    # Ensure scraper is available
    if not CHATGPT_SCRAPER_AVAILABLE:
        err_msg = "ChatGPTScraper class not available. Cannot run test."
        log_telemetry(main_run_id, "scraper_check", "FAIL", error_message=err_msg)
        print(f"ERROR: {err_msg}", file=sys.stderr)
        import sys

        sys.exit(1)
    log_telemetry(main_run_id, "scraper_check", "SUCCESS")

    test_prompt = "Explain the difference between HTTP GET and POST requests concisely."

    print(f"Test Prompt: {test_prompt}")
    final_status = "FAIL"
    steps_executed = 0  # Basic step counter
    error_details = None

    try:
        log_telemetry(main_run_id, "relay_call", "START")
        print(
            f"Attempting relay_prompt_via_web_and_gui (ID: {main_run_id}) (using config bypass)..."
        )
        steps_executed = 1  # Mark relay call as started

        relay_prompt_via_web_and_gui(test_prompt, test_config_obj, run_id=main_run_id)

        # If relay completes without exception, mark success
        final_status = "SUCCESS"
        steps_executed = 2  # Mark relay as finished
        log_telemetry(main_run_id, "relay_call", "SUCCESS")
        print("--- Test Relay Completed Successfully ---")

    except CursorBridgeError as e:
        error_details = f"CursorBridgeError: {e}"
        log_telemetry(main_run_id, "relay_call", "FAIL", error_message=error_details)
        print(f"--- Test Relay FAILED --- Error: {e}")
        import traceback

        traceback.print_exc(file=sys.stderr)
    except Exception as e:
        error_details = f"Unexpected Error: {e}"
        log_telemetry(main_run_id, "relay_call", "FAIL", error_message=error_details)
        print(f"--- Test Relay FAILED (Unexpected Error) --- Error: {e}")
        import traceback

        traceback.print_exc(file=sys.stderr)
    finally:
        # Log final summary status
        summary_meta = {
            "steps_executed": steps_executed,
            "success": (final_status == "SUCCESS"),
        }
        log_telemetry(
            main_run_id,
            "test_end",
            final_status,
            metadata=summary_meta,
            error_message=error_details,
        )
        print(f"--- Test Run {main_run_id} Finished. Status: {final_status} ---")

# Ensure this is the absolute end of the file
