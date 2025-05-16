"""
Agent script to monitor THEA replies and inject them as prompts into Cursor.
Supports GUI, Scraper, and Hybrid extraction modes.

Uses:
- gui_utils.copy_thea_reply (GUI mode)
- ChatGPTScraper.extract_latest_reply (Scraper mode)
- cursor_bridge.inject_prompt_into_cursor (Injection)
"""

import json  # Added for mode config
import logging
import sys
import time
import uuid  # Added for UUID tagging
from pathlib import Path
from typing import Literal, Optional  # Added Literal

# Adjust path to import from src
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.dreamos.core.config import AppConfig, load_config

# --- ADDED Scraper Import ---
from src.dreamos.services.utils.chatgpt_scraper import (
    ChatGPTScraper,
    WebDriverException,
)
from src.dreamos.tools.cursor_bridge.cursor_bridge import (
    CursorBridgeError,
    CursorInjectError,
    inject_prompt_into_cursor,
)
from src.dreamos.utils.gui_utils import (  # wait_for_element, # No longer used
    PYAUTOGUI_AVAILABLE,
    PYGETWINDOW_AVAILABLE,
    PYPERCLIP_AVAILABLE,
    copy_thea_reply,
)

# Basic Logging Setup
# Use specific logger for this agent
logger = logging.getLogger("TheaCursorAgent")
# Ensure root logger is configured elsewhere (e.g., by load_config or main entry point)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
POLL_INTERVAL_SECONDS = 10  # How often to check
BRIDGE_MODE_CONFIG_FILE = project_root / "runtime" / "config" / "bridge_mode.json"
EXTRACTION_LOG_FILE = project_root / "runtime" / "logs" / "thea_extraction_relay.md"
BridgeMode = Literal["gui", "scraper", "hybrid"]

# Global state (simple approach)
last_processed_reply_hash = None


def check_dependencies(mode: BridgeMode):
    """Checks if necessary libraries are installed based on the mode."""
    gui_needed = mode in ["gui", "hybrid"]
    scraper_needed = mode in [
        "scraper",
        "hybrid",
    ]  # Requires selenium, undetected-chromedriver

    if gui_needed:
        if not PYAUTOGUI_AVAILABLE:
            logger.critical(
                "PyAutoGUI is required for GUI/Hybrid mode. Please run: pip install pyautogui"
            )
            return False
        if not PYPERCLIP_AVAILABLE:
            logger.critical(
                "Pyperclip is required for GUI/Hybrid mode. Please run: pip install pyperclip"
            )
            return False
        if not PYGETWINDOW_AVAILABLE:
            logger.warning(
                "PyGetWindow is not installed. Window focus checks might be less reliable in GUI/Hybrid mode."
            )

    if scraper_needed:
        # Basic check, ChatGPTScraper init handles detailed WebDriver issues
        try:
            import selenium
            import undetected_chromedriver
        except ImportError as e:
            logger.critical(
                f"Scraper/Hybrid mode requires selenium and undetected-chromedriver: {e}"
            )
            return False

    return True


def load_bridge_mode() -> BridgeMode:
    """Loads the current bridge mode from the config file."""
    try:
        with open(BRIDGE_MODE_CONFIG_FILE, "r") as f:
            data = json.load(f)
        mode = data.get("mode", "gui").lower()
        if mode not in ("gui", "scraper", "hybrid"):
            logger.warning(
                f"Invalid mode '{mode}' in {BRIDGE_MODE_CONFIG_FILE}. Defaulting to 'gui'."
            )
            return "gui"
        logger.info(f"Loaded bridge mode: {mode}")
        return mode
    except FileNotFoundError:
        logger.warning(
            f"{BRIDGE_MODE_CONFIG_FILE} not found. Defaulting to 'gui' mode."
        )
        return "gui"
    except (json.JSONDecodeError, Exception) as e:
        logger.error(
            f"Error reading {BRIDGE_MODE_CONFIG_FILE}: {e}. Defaulting to 'gui' mode.",
            exc_info=True,
        )
        return "gui"


def log_extraction(method: str, text: str, extraction_uuid: uuid.UUID):
    """Appends extracted text info (with UUID) to the relay log file."""
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        # Truncate long text for logging
        preview = text[:150].replace("\n", " ") + ("..." if len(text) > 150 else "")
        log_entry = f"*   **{timestamp}** - **UUID:** `{extraction_uuid}` - **Method:** {method.upper()} - **Payload:** `{preview}`\n"
        with open(EXTRACTION_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"Failed to write to extraction log {EXTRACTION_LOG_FILE}: {e}")


def extract_via_gui(config: AppConfig) -> Optional[str]:
    """Wrapper for GUI extraction with error handling."""
    try:
        logger.debug("Attempting extraction via GUI (copy_thea_reply)...")
        text = copy_thea_reply(config=config)
        if text:
            logger.info("Extraction via GUI successful.")
            return text
        else:
            logger.debug("Extraction via GUI returned no text.")
            return None
    except Exception as e:
        logger.error(
            f"Error during GUI extraction (copy_thea_reply): {e}", exc_info=True
        )
        return None


def extract_via_scraper(scraper: ChatGPTScraper) -> Optional[str]:
    """Wrapper for Scraper extraction with error handling."""
    try:
        logger.debug("Attempting extraction via Scraper (extract_latest_reply)...")
        # Assume scraper is setup and logged in. May need navigation?
        # For now, just try extracting the latest reply from current page.
        # TODO: Add logic to navigate to correct conversation if needed?
        text = scraper.extract_latest_reply()
        if text:
            logger.info("Extraction via Scraper successful.")
            return text
        else:
            logger.debug("Extraction via Scraper returned no text.")
            return None
    except WebDriverException as e:
        logger.error(f"WebDriver error during Scraper extraction: {e}", exc_info=True)
        # Could indicate browser crash, session issue etc.
        # Consider attempting scraper re-init or fallback?
        return None
    except Exception as e:
        logger.error(
            f"Error during Scraper extraction (extract_latest_reply): {e}",
            exc_info=True,
        )
        return None


def main_loop(config: AppConfig):
    """
    Core operational loop for the THEA->Cursor Agent.

    Initializes by loading the bridge mode and setting up the ChatGPTScraper
    if required by the mode (scraper or hybrid).

    Enters a continuous loop that performs the following steps:
    1. Extracts text from THEA based on the current bridge mode (GUI, Scraper, or Hybrid).
       - Hybrid mode attempts Scraper first, then falls back to GUI if no text is extracted.
    2. If text is successfully extracted:
       a. Calculates a hash of the reply to detect if it's new.
       b. If new, generates a UUID for the extraction, logs it, and attempts to inject
          the text as a prompt into Cursor using `inject_prompt_into_cursor`.
       c. Updates `last_processed_reply_hash` upon successful injection.
    3. Sleeps for POLL_INTERVAL_SECONDS before the next cycle.

    Handles KeyboardInterrupt for graceful shutdown and logs other exceptions.
    The loop relies on a global `last_processed_reply_hash` to prevent
    reprocessing identical replies.

    Args:
        config: The application configuration object (AppConfig).
    """
    global last_processed_reply_hash
    current_mode = load_bridge_mode()
    scraper_instance: Optional[ChatGPTScraper] = None

    # --- Scraper Setup (if needed) ---
    if current_mode in ("scraper", "hybrid"):
        try:
            logger.info("Setting up ChatGPTScraper...")
            # Assuming headless=False for potential login needs initially
            scraper_instance = ChatGPTScraper(config=config, headless=False)
            scraper_instance.setup_browser()
            if not scraper_instance.load_cookies():
                logger.warning(
                    "ChatGPT cookies not found or invalid. Requires manual login in the browser window!"
                )
                # Give time for login
                time.sleep(30)
                scraper_instance.save_cookies()
            # Navigate? Load latest? Assume ready for now.
            # scraper_instance.load_latest_conversation() # Add if needed
            logger.info("ChatGPTScraper setup complete.")
        except Exception as e:
            logger.critical(
                f"Failed to initialize ChatGPTScraper: {e}. Cannot run in scraper/hybrid mode.",
                exc_info=True,
            )
            # Fallback? For now, exit if primary mode fails.
            if current_mode == "scraper":
                if scraper_instance:
                    scraper_instance.cleanup()
                return  # Exit if scraper mode fails to init
            else:  # Hybrid mode, fallback to GUI
                logger.warning(
                    "Scraper init failed in Hybrid mode, falling back to GUI only."
                )
                current_mode = "gui"
                scraper_instance = None  # Ensure it's None

    # --- Main Loop ---
    logger.info(f"Starting THEA -> Cursor Agent Loop (Mode: {current_mode.upper()}).")
    try:
        while True:
            # Periodically check mode config file? For now, load once at start.
            extracted_text: Optional[str] = None
            extraction_method: str = "N/A"

            # 1. Extract based on mode
            if current_mode == "gui":
                extracted_text = extract_via_gui(config)
                if extracted_text:
                    extraction_method = "gui"
            elif current_mode == "scraper":
                if scraper_instance:
                    extracted_text = extract_via_scraper(scraper_instance)
                    if extracted_text:
                        extraction_method = "scraper"
                else:
                    logger.error("Scraper mode selected but instance is not available.")
                    time.sleep(
                        POLL_INTERVAL_SECONDS * 2
                    )  # Longer sleep if scraper failed
                    continue
            elif current_mode == "hybrid":
                # Try scraper first
                if scraper_instance:
                    extracted_text = extract_via_scraper(scraper_instance)
                    if extracted_text:
                        extraction_method = "scraper"

                # If scraper didn't find anything, try GUI
                if not extracted_text:
                    logger.debug("Hybrid mode: Scraper yielded no result, trying GUI.")
                    extracted_text = extract_via_gui(config)
                    if extracted_text:
                        extraction_method = "gui"

            # 2. Process if extraction successful
            if extracted_text:
                current_reply_hash = hash(extracted_text)
                # Avoid processing the same reply multiple times
                if current_reply_hash != last_processed_reply_hash:
                    # --- Generate UUID ---
                    extraction_uuid = uuid.uuid4()
                    logger.info(
                        f"Extracted new reply (UUID: {extraction_uuid}) via {extraction_method.upper()} (hash: {current_reply_hash}). Length: {len(extracted_text)} chars."
                    )
                    # --- Pass UUID to logger ---
                    log_extraction(
                        method=extraction_method,
                        text=extracted_text,
                        extraction_uuid=extraction_uuid,
                    )

                    # 3. Inject: Send the extracted text to Cursor
                    # Note: UUID is logged but not currently injected into Cursor itself.
                    # Modify inject_prompt_into_cursor if correlation needed there.
                    try:
                        inject_prompt_into_cursor(prompt=extracted_text, config=config)
                        logger.info(
                            f"Successfully injected prompt (UUID: {extraction_uuid}) into Cursor."
                        )
                        last_processed_reply_hash = (
                            current_reply_hash  # Update state only on success
                        )
                    except CursorInjectError as e:
                        logger.error(f"Failed to inject prompt into Cursor: {e}")
                    except CursorBridgeError as e:
                        logger.error(f"Bridge error during injection: {e}")
                    except Exception as e:
                        logger.exception(f"Unexpected error during injection: {e}")
                else:
                    logger.debug(
                        f"Extracted reply ({extraction_method.upper()}) is the same as the last processed one. Skipping."
                    )
            else:
                logger.debug("No new reply extracted in this cycle.")

            # Wait before next check
            logger.debug(f"Sleeping for {POLL_INTERVAL_SECONDS} seconds.")
            time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logger.info("Agent loop interrupted by user. Exiting.")
    except Exception as e:
        logger.exception(f"Fatal error in main loop: {e}")
    finally:
        # Cleanup scraper browser if it was initialized
        if scraper_instance:
            logger.info("Cleaning up ChatGPTScraper browser...")
            scraper_instance.cleanup()
        logger.info("Agent loop finished.")


if __name__ == "__main__":
    # Load initial mode to check dependencies correctly
    initial_mode = load_bridge_mode()
    if not check_dependencies(initial_mode):
        sys.exit(1)

    # Load configuration
    try:
        app_config = load_config()  # Assumes load_config() finds config
    except Exception as e:
        # Logger might not be fully configured yet if load_config fails early
        print(f"CRITICAL: Failed to load AppConfig: {e}")
        logging.critical(f"Failed to load AppConfig: {e}. Exiting.", exc_info=True)
        sys.exit(1)

    if not app_config:
        logging.critical("Configuration loading returned None. Exiting.")
        sys.exit(1)

    # Setup logging properly *after* config load (load_config should call setup_logging)
    logger.info("AppConfig loaded successfully.")

    # Start the main loop
    main_loop(app_config)
