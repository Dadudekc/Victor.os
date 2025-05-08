#!/usr/bin/env python3
"""
GPT -> Cursor Command Relay Interface (Module 1)

Monitors a command file for payloads originating from ChatGPT and relays them
to the Cursor application using the cursor_bridge tool.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# --- Path Setup ---
# Assuming script is in scripts/
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    # Add relevant paths for importing bridge tools
    sys.path.append(str(project_root / "src"))
    sys.path.append(str(project_root))

# --- Configuration ---
RELAY_ID = "GptCursorRelay-Rustbyte-M1"
COMMAND_FILE_PATH = (
    project_root / "runtime" / "gpt_to_cursor_queue" / "command_input.json"
)
STATE_FILE_PATH = project_root / "runtime" / "gpt_to_cursor_queue" / "relay_state.json"
POLL_INTERVAL_SECONDS = 5

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(RELAY_ID)

# --- Cursor Bridge Integration (Simulation) ---
# Attempt to import the actual function, but handle failure gracefully
# In a real scenario, this import would need to work.
# For this autonomous cycle, we simulate its existence based on prior context.
try:
    # This assumes cursor_bridge.py defines inject_prompt_into_cursor
    from dreamos.tools.cursor_bridge import cursor_bridge

    # Check if the function exists, otherwise use a mock
    if hasattr(cursor_bridge, "inject_prompt_into_cursor") and callable(
        cursor_bridge.inject_prompt_into_cursor
    ):
        inject_prompt_func = cursor_bridge.inject_prompt_into_cursor
        logger.info(
            "Successfully imported inject_prompt_into_cursor from cursor_bridge."
        )
    else:
        raise ImportError("Function not found or not callable")
except ImportError as e:
    logger.warning(
        f"Could not import inject_prompt_into_cursor from dreamos.tools.cursor_bridge: {e}. Using simulation."
    )

    # Define a mock function for simulation purposes
    def simulate_inject_prompt_into_cursor(prompt: str, **kwargs):
        logger.info("SIMULATED call to inject_prompt_into_cursor:")
        logger.info(f"  Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        logger.info(f"  kwargs: {kwargs}")
        # Simulate success or potential failure modes if needed
        time.sleep(0.5)  # Simulate processing time
        return True  # Simulate success

    inject_prompt_func = simulate_inject_prompt_into_cursor


# --- State Management ---
def load_relay_state() -> Dict[str, Any]:
    """Loads the last processed command ID from the state file."""
    if STATE_FILE_PATH.exists():
        try:
            with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
                logger.info(f"Loaded relay state: {state}")
                return state
        except (json.JSONDecodeError, OSError) as e:
            logger.error(
                f"Error loading state file {STATE_FILE_PATH}: {e}. Starting fresh.",
                exc_info=True,
            )
            return {}
    return {}


def save_relay_state(state: Dict[str, Any]):
    """Saves the current state (e.g., last processed ID) to the state file."""
    try:
        STATE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        logger.info(f"Saved relay state: {state}")
    except OSError as e:
        logger.error(f"Error saving state file {STATE_FILE_PATH}: {e}", exc_info=True)


# --- Command Processing ---
def process_command(command_data: Dict[str, Any]) -> bool:
    """Processes a single command payload and injects it into Cursor."""
    command_id = command_data.get("command_id")
    payload_type = command_data.get("payload_type")
    payload = command_data.get("payload")

    # Basic validation
    if not all([command_id, payload_type, payload]):
        logger.error(
            f"Invalid command format received: Missing required fields. Data: {command_data}"
        )
        return False  # Indicate failure, but don't block processing new commands

    logger.info(f"Processing command ID: {command_id}, Type: {payload_type}")

    try:
        success = False
        if payload_type == "code_injection":
            code = payload.get("code")
            language = payload.get("language", "")  # Optional language hint
            if code:
                # Construct the prompt for cursor_bridge if needed, or pass directly
                # Assuming the function takes the code directly
                logger.info(f"Injecting code (lang: {language or 'N/A'})...")
                success = inject_prompt_func(
                    prompt=code, is_code=True, language=language
                )
            else:
                logger.error(
                    f"Missing 'code' in payload for code_injection (ID: {command_id})"
                )

        elif payload_type == "chat_message":
            message = payload.get("message")
            if message:
                logger.info("Injecting chat message...")
                success = inject_prompt_func(prompt=message, is_code=False)
            else:
                logger.error(
                    f"Missing 'message' in payload for chat_message (ID: {command_id})"
                )

        else:
            logger.error(f"Unsupported payload_type: {payload_type} (ID: {command_id})")

        if success:
            logger.info(f"Successfully processed and injected command ID: {command_id}")
            return True
        else:
            logger.error(
                f"Failed to inject command ID: {command_id} via cursor_bridge."
            )
            return False

    except Exception as e:
        logger.error(
            f"Unexpected error processing command ID {command_id}: {e}", exc_info=True
        )
        return False


# --- Main Loop ---
def run_relay():
    """
    Main operational loop for the GPT->Cursor Relay service.

    Initializes by loading any previous relay state. Then, it continuously
    monitors the specified COMMAND_FILE_PATH for modifications.
    If a change is detected, it reads the command file, checks if the
    command_id is new (not processed before), and if so, calls
    process_command().

    If processing is successful, the state (last processed command ID and
    timestamp) is updated and saved. Includes error handling for file
    operations, JSON parsing, and main loop exceptions. Pauses for
    POLL_INTERVAL_SECONDS between checks.
    """
    logger.info(
        f"Starting GPT->Cursor Relay ({RELAY_ID}). Monitoring: {COMMAND_FILE_PATH}"
    )

    state = load_relay_state()
    last_processed_command_id = state.get("last_processed_command_id")
    last_command_file_mtime = 0.0

    while True:
        try:
            if COMMAND_FILE_PATH.exists():
                current_mtime = os.path.getmtime(COMMAND_FILE_PATH)
                # Check if file has been modified since last check
                if current_mtime > last_command_file_mtime:
                    logger.info(
                        f"Detected change in {COMMAND_FILE_PATH}. Checking for new command."
                    )
                    last_command_file_mtime = current_mtime

                    try:
                        with open(COMMAND_FILE_PATH, "r", encoding="utf-8") as f:
                            command_content = json.load(f)

                        current_command_id = command_content.get("command_id")

                        if not current_command_id:
                            logger.error(
                                "Command file is missing 'command_id'. Skipping."
                            )
                        elif current_command_id != last_processed_command_id:
                            logger.info(
                                f"New command ID detected: {current_command_id}"
                            )
                            if process_command(command_content):
                                last_processed_command_id = current_command_id
                                state["last_processed_command_id"] = (
                                    last_processed_command_id
                                )
                                state["last_processed_timestamp_utc"] = datetime.now(
                                    timezone.utc
                                ).isoformat()
                                save_relay_state(state)
                            else:
                                # Optional: Implement retry logic or move to error queue
                                logger.error(
                                    f"Processing failed for command ID: {current_command_id}. Will retry on next file change."
                                )
                        else:
                            logger.info(
                                f"Command ID {current_command_id} already processed. No action needed."
                            )

                    except json.JSONDecodeError:
                        logger.error(
                            f"Command file {COMMAND_FILE_PATH} contains invalid JSON. Skipping."
                        )
                    except Exception as e:
                        logger.error(
                            f"Error reading or processing command file {COMMAND_FILE_PATH}: {e}",
                            exc_info=True,
                        )
                else:
                    logger.debug("No change detected in command file.")
            else:
                logger.debug(f"Command file {COMMAND_FILE_PATH} not found. Waiting...")

        except Exception as e:
            logger.error(f"Relay main loop encountered an error: {e}", exc_info=True)
            # Avoid tight loop on persistent errors

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    # Ensure queue directory exists
    COMMAND_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        run_relay()
    except KeyboardInterrupt:
        logger.info(f"GPT->Cursor Relay ({RELAY_ID}) stopped by user.")
    except Exception as e:
        logger.critical(
            f"GPT->Cursor Relay ({RELAY_ID}) encountered a critical error: {e}",
            exc_info=True,
        )
        sys.exit(1)
