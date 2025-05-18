"""
Main entry point for Dream.OS Universal Agent Bootstrap Runner.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List
import json
import os

# --- Add project root to sys.path ---
# This is to ensure that imports like src.dreamos.utils.gui work correctly
# when this script is run directly.
# It assumes this __main__.py is at src/dreamos/tools/agent_bootstrap_runner/__main__.py
try:
    SCRIPT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = SCRIPT_DIR.parents[3] # Navigate up to 'src' then one more for project root if src is not root
    # If your project root is the parent of 'src', then it's SCRIPT_DIR.parents[3]
    # If 'src' is the project root, it might be SCRIPT_DIR.parents[2]
    # Adjust based on your actual project structure where 'src' is located.
    # Assuming 'src' is a top-level dir in the project, and this file is in src/dreamos/tools/agent_bootstrap_runner
    # Path: /project_root/src/dreamos/tools/agent_bootstrap_runner/__main__.py
    # So, project_root = __file__.parent.parent.parent.parent
    # Let's try to be robust: search for a known marker like a root .git folder or a specific file.
    # For now, using fixed parent count, assuming /src/ is one level below project root.
    # If /Dream.os/ is the workspace root, and this is /Dream.os/src/dreamos/..., then project root is 3 parents up from src.
    # And 4 parents up from this file's directory.

    # Let current_dir be this file's directory: /D:/Dream.os/src/dreamos/tools/agent_bootstrap_runner
    # parent 1: /D:/Dream.os/src/dreamos/tools
    # parent 2: /D:/Dream.os/src/dreamos
    # parent 3: /D:/Dream.os/src/
    # parent 4: /D:/Dream.os/  <- This should be the workspace root added to sys.path
    WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
    SRC_ROOT = WORKSPACE_ROOT / "src"
    if str(WORKSPACE_ROOT) not in sys.path:
        sys.path.insert(0, str(WORKSPACE_ROOT))
    if str(SRC_ROOT) not in sys.path:
         sys.path.insert(0, str(SRC_ROOT)) # if modules are imported as dreamos.utils... directly

    # Attempt to import after path modification
    from dreamos.utils.gui.injector import CursorInjector, DEFAULT_COORDS_FILE as INJECTOR_DEFAULT_COORDS_FILE
    from dreamos.utils.gui.retriever import ResponseRetriever, PYPERCLIP_AVAILABLE

except ImportError as e:
    print(f"Error during initial import: {e}")
    print("Please ensure that the script is run from a context where 'dreamos.utils.gui' can be imported.")
    print(f"Current sys.path: {sys.path}")
    print(f"Attempted to add WORKSPACE_ROOT: {WORKSPACE_ROOT} and SRC_ROOT: {SRC_ROOT}")
    sys.exit(1)
except IndexError as e:
    print(f"Error determining project structure for sys.path: {e}")
    print("Failed to calculate WORKSPACE_ROOT. Please check the script's location relative to the project root.")
    sys.exit(1)

# --- Configuration ---
LOG_LEVEL = logging.INFO
AGENT_ID_TO_TEST = "Agent-1"
COORDS_CONFIG_FILE = INJECTOR_DEFAULT_COORDS_FILE # Use the same default as CursorInjector

# Define required directories relative to WORKSPACE_ROOT
REQUIRED_DIRS = [
    "runtime/config",
    "runtime/debug_screenshots",
    f"runtime/agent_comms/agent_mailboxes/{AGENT_ID_TO_TEST}",
    "runtime/bus/events"
]

AGENT_INBOX_FILE = WORKSPACE_ROOT / f"runtime/agent_comms/agent_mailboxes/{AGENT_ID_TO_TEST}/inbox.json"

# --- Logging Setup ---
def setup_logging():
    logging.basicConfig(level=LOG_LEVEL,
                        format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
                        handlers=[logging.StreamHandler(sys.stdout)])
    return logging.getLogger(__name__)

log = setup_logging()

# --- Main Functions ---
def create_required_directories():
    log.info("Checking and creating required directories...")
    for rel_dir_path in REQUIRED_DIRS:
        abs_dir_path = WORKSPACE_ROOT / rel_dir_path
        try:
            abs_dir_path.mkdir(parents=True, exist_ok=True)
            log.info(f"Ensured directory exists: {abs_dir_path}")
        except OSError as e:
            log.error(f"Error creating directory {abs_dir_path}: {e}", exc_info=True)
            # Depending on severity, might want to exit
    log.info("Directory check complete.")

def initialize_agent_inbox():
    log.info(f"Checking and initializing agent inbox: {AGENT_INBOX_FILE}")
    if not AGENT_INBOX_FILE.exists():
        try:
            # Ensure parent directory exists (should be covered by create_required_directories)
            AGENT_INBOX_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(AGENT_INBOX_FILE, 'w') as f:
                json.dump([], f) # Initialize with an empty list or dict as preferred
            log.info(f"Initialized dummy agent inbox: {AGENT_INBOX_FILE}")
        except OSError as e:
            log.error(f"Error initializing agent inbox {AGENT_INBOX_FILE}: {e}", exc_info=True)
    else:
        log.info(f"Agent inbox already exists: {AGENT_INBOX_FILE}")

def check_coordinate_config():
    log.info(f"Checking for coordinate config file: {COORDS_CONFIG_FILE}")
    abs_coords_file = WORKSPACE_ROOT / COORDS_CONFIG_FILE 
    if not abs_coords_file.exists():
        log.warning(f"Coordinate config file NOT FOUND: {abs_coords_file}")
        log.warning("CursorInjector might use default/fallback coordinates or fail if it requires specific agent coords.")
        # The user stated cursor_agent_coords.json is already populated, so we won't create a dummy one here.
        # The CursorInjector itself has a fallback if the file is missing or malformed.
    else:
        log.info(f"Coordinate config file found: {abs_coords_file}")

async def run_agent1_dry_cycle():
    log.info(f"--- Starting Dry Run for Agent: {AGENT_ID_TO_TEST} ---")

    # 1. Initialize CursorInjector for Agent-1
    log.info(f"Initializing CursorInjector for agent '{AGENT_ID_TO_TEST}'...")
    # Pass the absolute path to the coordinates file, resolved from WORKSPACE_ROOT
    abs_coords_file_path = WORKSPACE_ROOT / COORDS_CONFIG_FILE
    injector = CursorInjector(agent_id=AGENT_ID_TO_TEST, coords_file_path=abs_coords_file_path)

    # 2. Inject a dummy prompt using the hybrid method
    dummy_prompt = f"This is a dummy prompt for {AGENT_ID_TO_TEST} from the self-check script."
    log.info(f"Injecting prompt using hybrid method: '{dummy_prompt[:60]}...'")
    try:
        # Using is_initial_prompt=True to target "input_box_initial" for the agent
        # Use the new hybrid injection method for more reliable text input
        injection_successful = await injector.inject_text_hybrid(dummy_prompt, is_initial_prompt=True, retries=2)
        if injection_successful:
            log.info(f"SUCCESS: Dummy prompt injected for {AGENT_ID_TO_TEST} using hybrid method. Check target GUI.")
        else:
            log.error(f"FAILED: Hybrid prompt injection for {AGENT_ID_TO_TEST}. See injector logs.")
            if hasattr(injector, 'take_screenshot_on_error'):
                injector.take_screenshot_on_error(f"self_check_inject_fail_{AGENT_ID_TO_TEST}")
    except Exception as e:
        log.error(f"Exception during hybrid prompt injection for {AGENT_ID_TO_TEST}: {e}", exc_info=True)
        if hasattr(injector, 'take_screenshot_on_error'):
            injector.take_screenshot_on_error(f"self_check_inject_exception_{AGENT_ID_TO_TEST}")

    # 3. Initialize ResponseRetriever
    log.info("Initializing ResponseRetriever...")
    # The ResponseRetriever class expects agent_id.
    abs_coords_file_path = WORKSPACE_ROOT / COORDS_CONFIG_FILE # Already defined, ensure it's passed if retriever needs it
    retriever = ResponseRetriever(agent_id=AGENT_ID_TO_TEST, coords_file=abs_coords_file_path)

    # 4. Simulate a mock clipboard response
    mock_response = f"This is a mock response for {AGENT_ID_TO_TEST}.".strip()
    log.info(f"Simulating mock response to clipboard: '{mock_response[:60]}...'")
    if PYPERCLIP_AVAILABLE:
        if retriever.simulate_copy_to_clipboard(mock_response):
            log.info("Mock response placed on clipboard.")
            # 5. Retrieve the mock response
            log.info("Attempting to retrieve mock response from clipboard...")
            retrieved_text = retriever.get_response_from_clipboard(timeout=2, interval=0.2)
            if retrieved_text == mock_response:
                log.info(f"SUCCESS: Retrieved mock response correctly: '{retrieved_text[:60]}...'")
            elif retrieved_text is not None:
                log.error(f"FAILED: Retrieved different text. Expected: '{mock_response[:60]}...', Got: '{retrieved_text[:60]}...'")
            else:
                log.error("FAILED: Did not retrieve any text from clipboard (retrieved None).")
        else:
            log.error("FAILED to simulate copy to clipboard. Pyperclip might have issues.")
    else:
        log.warning("Pyperclip not available. Skipping clipboard simulation and retrieval test.")

    log.info(f"--- Dry Run for Agent: {AGENT_ID_TO_TEST} Complete ---")

# --- Main Execution ---
if __name__ == "__main__":
    log.info("====== PyAutoGUI Environment Self-Check & Recovery Script ======")
    
    create_required_directories()
    initialize_agent_inbox()
    check_coordinate_config() # Checks and logs if the main coords file exists
    
    # Check for dependencies before attempting the dry run.
    pygetwindow_is_ok = False
    try:
        # Attempt to get the coords file path for the injector check instance
        # This path needs to be valid for the CursorInjector to initialize without error,
        # even if we're just checking 'pygetwindow_available'.
        # The default path is relative to where injector.py is, so we need to give an absolute path
        # or a path relative to WORKSPACE_ROOT that injector.py can understand if it resolves it.
        # Injector's DEFAULT_COORDS_FILE is "runtime/config/cursor_agent_coords.json"
        coords_path_for_check = WORKSPACE_ROOT / INJECTOR_DEFAULT_COORDS_FILE
        
        # Ensure the directory for the coords file exists for the temp_injector,
        # otherwise its _load_agent_coordinates might log excessive errors if file not found.
        # This should be covered by create_required_directories if INJECTOR_DEFAULT_COORDS_FILE is under runtime/config
        coords_path_for_check.parent.mkdir(parents=True, exist_ok=True)

        temp_injector_for_check = CursorInjector(coords_file_path=coords_path_for_check)
        pygetwindow_is_ok = temp_injector_for_check.pygetwindow_available
        if not pygetwindow_is_ok:
            log.warning("- pygetwindow is not available (needed for window focus during injection). GUI injection might be unreliable.")
    except Exception as e:
        log.error(f"Error while creating temporary CursorInjector for pygetwindow check: {e}", exc_info=True)
        log.warning("- Could not determine pygetwindow availability due to an error. Assuming not available for safety.")

    pyperclip_is_ok = PYPERCLIP_AVAILABLE
    if not pyperclip_is_ok:
        log.warning("- pyperclip is not available (needed for clipboard operations). Clipboard tests will be skipped.")

    if pygetwindow_is_ok and pyperclip_is_ok:
        log.info("Attempting Agent-1 dry run cycle (injection and retrieval simulation)...")
        asyncio.run(run_agent1_dry_cycle())
    else:
        log.warning("Skipping agent dry run cycle due to missing critical dependencies.")
        if not pygetwindow_is_ok : # Explicitly log again if it was the reason
             log.warning("Reason: pygetwindow not available.")
        if not pyperclip_is_ok: # Explicitly log again if it was the reason
            log.warning("Reason: pyperclip not available.")


    log.info("====== Self-Check Script Finished. Review logs for details. ======") 