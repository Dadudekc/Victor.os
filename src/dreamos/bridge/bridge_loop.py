import asyncio
import datetime
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path

import yaml  # Added for YAML loading

# --- Potentially needed for ChatGPTWebAgent instantiation ---
# from dreamos.core.config import AppConfig # Assuming AppConfig is needed
# from dreamos.core.tasks.nexus.task_nexus import TaskNexus # Assuming TaskNexus is needed
from dreamos.agents.chatgpt_web_agent import ChatGPTWebAgent
from dreamos.core.config import CoreConfigurationError, load_config
from dreamos.core.tasks.nexus.task_nexus import (
    TaskNexus,  # Assuming TaskNexus can be imported
)

# Global or passed-in instance of ChatGPTWebAgent
# This needs to be properly initialized and managed.
chatgpt_agent_instance = None

# --- Configuration ---
POLL_INTERVAL_SECONDS = 5  # Simulate cycle duration
STALL_THRESHOLD_CYCLES = 5
CONSECUTIVE_FAILURE_THRESHOLD = 3

CURSOR_PROMPT_FILE = "src/dreamos/bridge/cursor_to_gpt.jsonl"
BRIDGE_OUTPUT_FILE = "src/dreamos/bridge/gpt_to_cursor.jsonl"
STATUS_LOG_FILE = "src/dreamos/bridge/bridge_loop_status.log"
FAILURE_LOG_FILE = "src/dreamos/bridge/bridge_loop_failures.jsonl"
STALL_ALERT_FLAG = "src/dreamos/bridge/bridge_loop_alert.flag"
RESUME_FLAG = "src/dreamos/bridge/resume.flag"

BRIDGE_CONFIG_FILE = Path(__file__).parent / "bridge_config.yaml"

# --- Logging Setup ---
# Status logger for polling activity
status_logger = logging.getLogger("BridgeStatus")
status_logger.setLevel(logging.INFO)
status_handler = logging.FileHandler(STATUS_LOG_FILE)
status_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
status_handler.setFormatter(status_formatter)
status_logger.addHandler(status_handler)
# Prevent double logging if root logger is configured
status_logger.propagate = False

# --- Scraper Log Import ---
MODULE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "runtime/modules/chatgpt_scraper"
    )
)
if MODULE_PATH not in sys.path:
    sys.path.append(MODULE_PATH)

try:
    from scraper import log_interaction

    print(f"Successfully imported log_interaction from {MODULE_PATH}")
except ImportError as e:
    print(
        f"Error: Could not import log_interaction from {MODULE_PATH}/scraper.py - {e}"
    )
    log_interaction = None  # Ensure it exists even if import fails

if log_interaction is None:
    # Define fallback if import failed, crucial for operation
    def log_interaction(prompt, response, tags=None):
        print(
            "CRITICAL: Fallback logger active. Cannot log interaction to scraper log due to import error."
        )
        return False, None

# --- Core Functions ---


def call_gpt_api(prompt: str) -> str:
    """Calls the actual ChatGPTWebAgent to process the prompt."""
    # Removed HACK initialization. chatgpt_agent_instance is now expected to be initialized by main_loop.
    status_logger.info(
        f"Attempting to call ChatGPTWebAgent for prompt: '{prompt[:50]}...'"
    )

    if not chatgpt_agent_instance:
        status_logger.error(
            "CRITICAL: chatgpt_agent_instance is not initialized. Bridge cannot function."
        )
        raise ConnectionError(
            "Critical: chatgpt_agent_instance is not available. Check main_loop initialization."
        )

    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # No event loop running
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        response = loop.run_until_complete(
            chatgpt_agent_instance.process_external_prompt(prompt)
        )

        if response is None:
            status_logger.error(
                "ChatGPTWebAgent returned None, indicating an error or critical failure during processing."
            )
            raise ConnectionError(
                "Failed to get valid response from ChatGPTWebAgent (returned None)."
            )
        elif response == "":  # Specific marker for no new reply found by agent
            status_logger.warning("ChatGPTWebAgent found no new reply for the prompt.")
            return ""  # Or a specific marker like "[NO_REPLY_FOUND]"

        status_logger.info("Response received from ChatGPTWebAgent.")
        return response
    except Exception as e:
        status_logger.error(
            f"Error calling ChatGPTWebAgent's process_external_prompt: {e}",
            exc_info=True,
        )
        if chatgpt_agent_instance and chatgpt_agent_instance.driver:
            status_logger.info(
                "Attempting to close ChatGPTWebAgent browser due to error..."
            )
            try:
                chatgpt_agent_instance.close()
                status_logger.info("ChatGPTWebAgent browser closed.")
            except Exception as close_e:
                status_logger.error(
                    f"Error closing ChatGPTWebAgent browser: {close_e}", exc_info=True
                )
        raise


def write_bridge_output(prompt_id, log_id, gpt_response):
    """Writes the successful GPT response to the output file."""
    try:
        output_payload = {
            "response_for_prompt_id": prompt_id,
            "gpt_response_id": log_id,
            "response_content": gpt_response,
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        os.makedirs(os.path.dirname(BRIDGE_OUTPUT_FILE), exist_ok=True)
        with open(BRIDGE_OUTPUT_FILE, "a", encoding="utf-8") as f:
            json.dump(output_payload, f)
            f.write("\n")
        status_logger.info(
            f"Successfully wrote response for prompt {prompt_id} to {BRIDGE_OUTPUT_FILE}"
        )
        return True
    except Exception as e:
        status_logger.error(
            f"Error writing bridge output to {BRIDGE_OUTPUT_FILE}: {e}", exc_info=True
        )
        return False


def log_failure_trace(prompt_id, prompt_text, error_details):
    """Logs details of a failed processing attempt."""
    try:
        failure_entry = {
            "failed_prompt_id": prompt_id,
            "failed_prompt_text": prompt_text,
            "error_details": str(error_details),
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        os.makedirs(os.path.dirname(FAILURE_LOG_FILE), exist_ok=True)
        with open(FAILURE_LOG_FILE, "a", encoding="utf-8") as f:
            json.dump(failure_entry, f)
            f.write("\n")
        status_logger.warning(
            f"Logged failure trace for prompt {prompt_id} to {FAILURE_LOG_FILE}"
        )
    except Exception as e:
        status_logger.error(
            f"CRITICAL: Failed to log failure trace: {e}", exc_info=True
        )


def relay_prompt_to_gpt(prompt: str, prompt_id: str = "unknown") -> bool:
    """Relays prompt, logs, writes response. Returns True on full success."""
    status_logger.info(f"Relaying prompt_id: {prompt_id}")
    gpt_response = None
    log_id = None
    try:
        # Step 1: Call GPT
        gpt_response = call_gpt_api(prompt)

        # Step 2: Log interaction using imported function
        logged_ok, log_id = log_interaction(
            prompt, gpt_response, tags=["bridge_loop", f"prompt_{prompt_id}"]
        )
        if not logged_ok:
            status_logger.warning(
                f"Failed to log interaction {prompt_id} to scraper log."
            )
            # Decide if this is a critical failure or just a warning

        # Step 3: Write response for Cursor pickup
        write_ok = write_bridge_output(prompt_id, log_id, gpt_response)
        if not write_ok:
            raise IOError(
                f"Failed to write response for {prompt_id} to {BRIDGE_OUTPUT_FILE}"
            )

        return True  # Full success

    except Exception as e:
        status_logger.error(
            f"Error during relay for prompt {prompt_id}: {e}", exc_info=True
        )
        log_failure_trace(prompt_id, prompt, e)  # Log the failure
        return False  # Indicate failure


def get_file_mtime(file_path):
    """Get last modification time of a file, return 0 if not found."""
    try:
        return os.path.getmtime(file_path)
    except FileNotFoundError:
        return 0


def main_loop():
    """Main sentinel loop."""
    global chatgpt_agent_instance
    status_logger.info("--- Bridge Loop Sentinel Initializing ---")

    # --- Load Bridge Configuration and Initialize ChatGPTWebAgent ---
    try:
        status_logger.info(
            f"Attempting to load bridge configuration from: {BRIDGE_CONFIG_FILE}"
        )
        app_cfg_for_agent = load_config(
            config_path=BRIDGE_CONFIG_FILE
        )  # Use the load_config function
        status_logger.info("Successfully loaded AppConfig via load_config for bridge.")

        # Extract settings needed for TaskNexus and ChatGPTWebAgent from the loaded config
        # These paths/keys might need adjustment based on exact AppConfig structure defined in bridge_config.yaml

        # TaskNexus setup
        nexus_task_file_str = (
            app_cfg_for_agent.paths.task_list_file_for_bridge
        )  # Assuming this path is set in AppConfig via bridge_config.yaml
        if not nexus_task_file_str:
            raise CoreConfigurationError(
                "Path 'task_list_file_for_bridge' not found in loaded AppConfig paths."
            )
        nexus_task_file = Path(nexus_task_file_str)
        nexus_task_file.parent.mkdir(parents=True, exist_ok=True)
        if not nexus_task_file.exists():
            nexus_task_file.write_text("[]")
        agent_task_nexus = TaskNexus(task_file=nexus_task_file)
        status_logger.info(
            f"TaskNexus initialized for bridge agent using: {nexus_task_file}"
        )

        # ChatGPTWebAgent setup - getting settings from bridge_config.yaml via AppConfig
        # We need agent_id, conversation_url, simulate status.
        # These were placed under 'chatgpt_web_agent_settings' in the example bridge_config.yaml.
        # AppConfig needs to make these accessible. If load_config doesn't nest them automatically,
        # we might need to load bridge_config.yaml directly here just for these settings.
        try:
            with open(BRIDGE_CONFIG_FILE, "r") as f_direct_cfg:
                direct_bridge_cfg_data = yaml.safe_load(f_direct_cfg)
                agent_settings = direct_bridge_cfg_data.get(
                    "chatgpt_web_agent_settings"
                )
                if not agent_settings:
                    raise CoreConfigurationError(
                        "'chatgpt_web_agent_settings' section missing in bridge_config.yaml"
                    )
        except Exception as e_direct_load:
            status_logger.error(
                f"Failed to directly load chatgpt_web_agent_settings from {BRIDGE_CONFIG_FILE}: {e_direct_load}. Using defaults or potentially failing."
            )
            # Set defaults or raise - raising is safer
            raise CoreConfigurationError(
                f"Could not extract chatgpt_web_agent_settings from config: {e_direct_load}"
            )

        agent_id = agent_settings.get("agent_id", "bridge_chatgpt_agent_default")
        conversation_url = agent_settings.get("conversation_url")
        simulate_interaction = agent_settings.get("simulate_interaction", False)

        if not conversation_url:
            raise CoreConfigurationError(
                "'conversation_url' missing in chatgpt_web_agent_settings within bridge_config.yaml"
            )

        # Instantiate the agent
        chatgpt_agent_instance = ChatGPTWebAgent(
            config=app_cfg_for_agent,  # Pass the fully loaded AppConfig
            agent_id=agent_id,
            conversation_url=conversation_url,
            task_nexus=agent_task_nexus,
            simulate=simulate_interaction,
        )

        # Ensure external_prompt_delay is available to the agent (set via AppConfig)
        # The previous edit added logic to set app_cfg_for_agent.agents.chatgpt_web.external_prompt_delay
        # This assumes load_config() correctly creates nested structures or they exist.
        # If not, we might need to set it manually on the instance or config AFTER load_config,
        # based on the value from direct_bridge_cfg_data if needed.
        # Verify it's accessible for the agent:
        try:
            delay_val = getattr(
                app_cfg_for_agent.agents.chatgpt_web, "external_prompt_delay"
            )
            status_logger.info(
                f"Agent external_prompt_delay configured via AppConfig: {delay_val}"
            )
        except AttributeError:
            status_logger.warning(
                "Could not verify external_prompt_delay in AppConfig structure. Agent might use default."
            )
            # Optionally set it directly on the instance if AppConfig structure is problematic:
            # chatgpt_agent_instance.config.agents.chatgpt_web.external_prompt_delay = agent_settings.get('external_prompt_delay', 5) # Requires ensuring nested objects exist

        status_logger.info(
            f"ChatGPTWebAgent instance '{agent_id}' initialized successfully for bridge."
        )

    except CoreConfigurationError as e_core_cfg:
        status_logger.critical(
            f"Core configuration error during bridge initialization: {e_core_cfg}. Bridge cannot function.",
            exc_info=True,
        )
        return  # Exit main_loop
    except Exception as e:
        status_logger.critical(
            f"Unexpected error during bridge initialization: {e}. Bridge cannot function.",
            exc_info=True,
        )
        return  # Exit main_loop

    # --- End Initialization ---

    processed_ids = set()  # Track processed prompts within this run
    last_prompt_mtime = get_file_mtime(CURSOR_PROMPT_FILE)
    cycles_since_last_change = 0
    consecutive_failures = 0
    is_suspended = False

    while True:  # Run indefinitely until stopped externally
        cycle_start_time = time.time()
        status_logger.info(f"--- Starting Poll Cycle --- Suspended: {is_suspended}")

        # --- Resumption Logic ---
        if is_suspended:
            if os.path.exists(RESUME_FLAG):
                status_logger.warning(
                    f"Resume flag found ({RESUME_FLAG}). Resuming operation."
                )
                os.remove(RESUME_FLAG)  # Consume the flag
                is_suspended = False
                consecutive_failures = 0
            else:
                # Check if input file changed while suspended
                current_mtime = get_file_mtime(CURSOR_PROMPT_FILE)
                if current_mtime > last_prompt_mtime:
                    status_logger.warning(
                        "Input file changed while suspended. Resuming operation."
                    )
                    last_prompt_mtime = current_mtime
                    is_suspended = False
                    consecutive_failures = 0
                    cycles_since_last_change = 0  # Reset stall counter
                else:
                    status_logger.info(
                        "Suspended. Checking for resume flag or input file change next cycle."
                    )
                    # Sleep and skip rest of the loop while suspended
                    time.sleep(POLL_INTERVAL_SECONDS)
                    continue

        # --- Stall Detection Logic ---
        current_mtime = get_file_mtime(CURSOR_PROMPT_FILE)
        if current_mtime == last_prompt_mtime:
            cycles_since_last_change += 1
            status_logger.info(
                f"Input file unchanged. Cycles since last change: {cycles_since_last_change}"
            )
            if cycles_since_last_change >= STALL_THRESHOLD_CYCLES:
                status_logger.warning(
                    f"Input file ({CURSOR_PROMPT_FILE}) stalled for {cycles_since_last_change} cycles. Creating alert flag."
                )
                # Create or update the alert flag file
                try:
                    with open(STALL_ALERT_FLAG, "w") as f:
                        f.write(
                            f"Stalled since: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n"
                        )
                except Exception as e:
                    status_logger.error(f"Failed to create stall alert flag: {e}")
        else:
            status_logger.info("Input file changed. Resetting stall counter.")
            cycles_since_last_change = 0
            last_prompt_mtime = current_mtime
            # Remove stall flag if it exists
            if os.path.exists(STALL_ALERT_FLAG):
                try:
                    os.remove(STALL_ALERT_FLAG)
                    status_logger.info("Removed stall alert flag.")
                except Exception as e:
                    status_logger.error(f"Failed to remove stall alert flag: {e}")

        # --- Prompt Processing Logic ---
        prompts_processed_this_cycle = 0
        try:
            if not os.path.exists(CURSOR_PROMPT_FILE):
                status_logger.info(f"Input file {CURSOR_PROMPT_FILE} not found.")
            else:
                with open(CURSOR_PROMPT_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            prompt_id = data.get(
                                "prompt_id", f"missing_id_{uuid.uuid4()}"
                            )  # Ensure unique ID
                            prompt_text = data.get("prompt")

                            if prompt_id not in processed_ids and prompt_text:
                                status_logger.info(f"Found new prompt: ID {prompt_id}")
                                success = relay_prompt_to_gpt(prompt_text, prompt_id)
                                processed_ids.add(prompt_id)
                                prompts_processed_this_cycle += 1

                                if success:
                                    consecutive_failures = 0  # Reset on success
                                else:
                                    consecutive_failures += 1
                                    status_logger.warning(
                                        f"Relay failed for prompt {prompt_id}. Consecutive failures: {consecutive_failures}"
                                    )
                                    if (
                                        consecutive_failures
                                        >= CONSECUTIVE_FAILURE_THRESHOLD
                                    ):
                                        status_logger.error(
                                            f"Reached consecutive failure threshold ({CONSECUTIVE_FAILURE_THRESHOLD}). Suspending loop."
                                        )
                                        is_suspended = True
                                        # Log final failure context if needed, maybe the last error from relay?
                                        break  # Stop processing further prompts this cycle

                            elif not prompt_text:
                                status_logger.warning(
                                    f"Skipping entry with missing prompt text: {line.strip()}"
                                )

                        except json.JSONDecodeError as e:
                            status_logger.error(
                                f"Skipping invalid JSON line: {line.strip()} - Error: {e}"
                            )
                        except Exception as e:
                            status_logger.error(
                                f"Error processing line: {line.strip()} - Error: {e}",
                                exc_info=True,
                            )
                    # End of file processing

            if prompts_processed_this_cycle == 0 and not is_suspended:
                status_logger.info("No new, unprocessed prompts found in this cycle.")

        except Exception as e:
            status_logger.error(
                f"Error reading or processing {CURSOR_PROMPT_FILE}: {e}", exc_info=True
            )
            # Consider if this constitutes a failure for suspension purposes

        # --- Cycle End ---
        cycle_end_time = time.time()
        cycle_duration = cycle_end_time - cycle_start_time
        sleep_time = max(0, POLL_INTERVAL_SECONDS - cycle_duration)
        status_logger.info(
            f"--- Poll Cycle End. Duration: {cycle_duration:.2f}s. Sleeping for {sleep_time:.2f}s ---"
        )
        time.sleep(sleep_time)


if __name__ == "__main__":
    main_loop()
