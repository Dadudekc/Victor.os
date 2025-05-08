#!/usr/bin/env python3
# EDIT START: Revert RUN_ID print
# import uuid
# RUN_ID = uuid.uuid4()
# print(f"DEBUG: run_e2e_bridge_test.py EXECUTING - RUN ID: {RUN_ID}")
# EDIT END
"""
run_e2e_bridge_test.py

Performs a full end-to-end test of the Cursor ↔ ChatGPT bridge loop:
1. Ensures prompt file exists (or creates it)
2. Verifies required config file + key
3. Executes `run_bridge_loop.py` as subprocess
4. Validates output JSON structure in `runtime/bridge_outbox`
5. Logs PASS/FAIL status with timestamps
"""

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
import sys
import os
from dotenv import load_dotenv

# EDIT START: Add dotenv import and loading
load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))
# EDIT END

# EDIT START: Explicitly delete log files before redirection
log_files_to_delete = ["test_stdout.log", "test_stderr.log"]
for log_file in log_files_to_delete:
    try:
        if Path(log_file).exists():
            os.remove(log_file)
            print(f"DEBUG: run_e2e_bridge_test.py (parent) - Deleted existing log: {log_file}", file=sys.stderr) # To console
    except OSError as e:
        print(f"DEBUG: run_e2e_bridge_test.py (parent) - Error deleting {log_file}: {e}", file=sys.stderr) # To console
# EDIT END

# EDIT START: PYTHONPATH construction logic (ensure it's early)
print(f"DEBUG: run_e2e_bridge_test.py (parent) sys.path: {sys.path}", file=sys.stderr)

project_root_path_for_env = str(Path(__file__).resolve().parent)
src_dir_path_for_env = str(Path(__file__).resolve().parent / "src")
new_pythonpath_parts_for_env = []
if Path(src_dir_path_for_env).is_dir():
    new_pythonpath_parts_for_env.append(src_dir_path_for_env)
new_pythonpath_parts_for_env.append(project_root_path_for_env)
existing_pythonpath_for_env = os.environ.get("PYTHONPATH")
if existing_pythonpath_for_env:
    new_pythonpath_parts_for_env.extend(existing_pythonpath_for_env.split(os.pathsep))
constructed_pythonpath_for_subprocess = os.pathsep.join(new_pythonpath_parts_for_env)
print(f"DEBUG: run_e2e_bridge_test.py (parent) new constructed PYTHONPATH for subprocess: {constructed_pythonpath_for_subprocess}", file=sys.stderr)
# EDIT END

# EDIT START: Read and print the content of the target script before execution
SCRIPT_TO_EXECUTE = Path("src") / "dreamos" / "bridge" / "run_bridge_loop.py"
print(f"--- Content of {SCRIPT_TO_EXECUTE} as seen by parent script (console): ---", file=sys.stderr)
try:
    with open(SCRIPT_TO_EXECUTE, 'r', encoding='utf-8') as f_read: # Added encoding
        print(f_read.read(), file=sys.stderr)
except Exception as e_read:
    print(f"Error reading {SCRIPT_TO_EXECUTE}: {e_read}", file=sys.stderr)
print("--- End of content (console) ---", file=sys.stderr)
# EDIT END

# --- Define constants AFTER path logic and script checks but BEFORE redirection for subprocess use ---
PROMPT_PATH = Path("prompts/test_prompt.txt")
CONFIG_PATH = Path("runtime/config/cursor_agent_coords.json") # Defined but not used by COMMAND_TO_RUN currently
OUTBOX_PATH = Path("runtime/bridge_outbox") # Defined but not used by COMMAND_TO_RUN currently
# MODIFIED: Define module name for -m execution
MODULE_TO_EXECUTE = "dreamos.bridge.run_bridge_loop"
# SCRIPT_TO_EXECUTE = Path("src") / "dreamos" / "bridge" / "run_bridge_loop.py"
# MODULE_NAME_ORIG = "dreamos.bridge.run_bridge_loop" # Not needed for direct script exec
# MODULE_NAME = MODULE_NAME_ORIG # Not needed

EXPECTED_AGENT_ID = 1
RESPONSE_TIMEOUT = 90
# --- End constants definition ---

# Redirect stdout and stderr for run_e2e_bridge_test.py itself
# This MUST happen AFTER all prints to console that we want to see in the console
# MODIFIED: Add try-except around stream redirection for debugging
original_stderr = sys.stderr # Keep a reference to original stderr
# try:
#     print("DEBUG_REDIR: Attempting to redirect stdout to test_stdout.log", file=original_stderr)
#     sys.stdout = open('test_stdout.log', 'w', encoding='utf-8')
#     print("DEBUG_REDIR: Successfully redirected stdout.", file=original_stderr)
#     
#     print("DEBUG_REDIR: Attempting to redirect stderr to test_stderr.log", file=original_stderr)
#     sys.stderr = open('test_stderr.log', 'w', encoding='utf-8')
#     print("DEBUG_REDIR: Successfully redirected stderr.", file=original_stderr)
#     
#     # Test if the new stderr works
#     print("DEBUG_REDIR: This message should now go to test_stderr.log if redirection was successful.", file=sys.stderr)
# 
# except Exception as e_redir:
#     print(f"CRITICAL_REDIR_FAIL: Failed to redirect streams: {e_redir}", file=original_stderr)
#     # Decide if to exit or proceed with potentially broken logging
#     # For now, let it proceed to see if other parts run and where their output goes.
print("INFO: Stream redirection to log files is currently COMMENTED OUT for direct console debugging.", file=original_stderr)

# --- Code that runs AFTER redirection (logs to test_stderr.log or test_stdout.log) ---
# Will now print directly to console

# Print sys.executable and re-check first line of script just before subprocess.run
print(f"DEBUG: run_e2e_bridge_test.py (parent) - sys.executable: {sys.executable}", file=sys.stderr)
try:
    with open(SCRIPT_TO_EXECUTE, 'r', encoding='utf-8') as f_check: # Added encoding
        first_line_check = f_check.readline().strip()
    print(f"DEBUG: run_e2e_bridge_test.py (parent) - First line of {SCRIPT_TO_EXECUTE} before exec: {first_line_check}", file=sys.stderr)
except Exception as e_check:
    print(f"DEBUG: run_e2e_bridge_test.py (parent) - Error re-checking {SCRIPT_TO_EXECUTE}: {e_check}", file=sys.stderr)

# This import is for the main script's validation step.
from dreamos.services.utils.chatgpt_scraper import HybridResponseHandler

# Prepare environment for subprocess
current_env = os.environ.copy()
current_env["PYTHONPATH"] = constructed_pythonpath_for_subprocess

# REVERTED: Define target chat URL back to standard ChatGPT
# CHAT_URL = (
#     "https://chatgpt.com/g/g-6817f1a5d2e88191948898629f7e8d9b-autonomy-enforcer"
# )
CHAT_URL = "https://chat.openai.com/chat"

# EDIT START: Define COMMAND_TO_RUN globally BEFORE function definitions
COMMAND_TO_RUN = [
    sys.executable,
    "-B", # RESTORED: -B flag
    "-m", # ADDED: Use module execution flag
    MODULE_TO_EXECUTE, # Use module path instead of script path
    # str(SCRIPT_TO_EXECUTE), # Removed script path
    "--agent-id", str(EXPECTED_AGENT_ID),
    "--prompt-file", str(PROMPT_PATH),
    "--response-timeout", str(RESPONSE_TIMEOUT),
    "--chat-url", CHAT_URL,
]
print(f"DEBUG: run_e2e_bridge_test.py (parent) - COMMAND_TO_RUN defined: {COMMAND_TO_RUN}", file=sys.stderr)
# EDIT END

# Function definitions
def step(msg):
    print(f"\n🛠️  {msg}") # This will go to test_stdout.log

def assert_file(path: Path, must_contain_key=None):
    if not path.exists():
        raise FileNotFoundError(f"❌ Missing file: {path}")
    if must_contain_key:
        data = json.loads(path.read_text(encoding='utf-8')) # Added encoding
        if must_contain_key not in data:
            raise ValueError(f"❌ `{must_contain_key}` missing from: {path}")

def create_prompt_file():
    PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not PROMPT_PATH.exists():
        PROMPT_PATH.write_text("What is Dream.OS and how does it work?", encoding='utf-8') # Added encoding
        print(f"✅ Prompt created → {PROMPT_PATH}") # This will go to test_stdout.log
    else:
        print(f"✅ Prompt already exists → {PROMPT_PATH}") # This will go to test_stdout.log
        
def run_bridge_loop():
    print(f"▶️  Launching bridge loop (as module: {MODULE_TO_EXECUTE})...") # Modified print
    # COMMAND_TO_RUN should now be visible here
    result = subprocess.run(
        COMMAND_TO_RUN,
        capture_output=True,
        text=True, 
        env=current_env, # RESTORED: Pass constructed environment
        encoding='utf-8', 
        errors='replace'  
    )
    # EDIT START: Always print both stdout and stderr from subprocess for debugging
    print("--- Subprocess STDOUT ---")
    print(result.stdout)
    print("--- Subprocess STDERR ---")
    print(result.stderr)
    print("--- End Subprocess Output ---")
    # EDIT END
    if result.returncode != 0:
        # print(result.stderr) # Already printed above
        raise RuntimeError(f"Bridge loop exited with code {result.returncode}")

def validate_latest_output():
    files = sorted(OUTBOX_PATH.glob(f"agent{EXPECTED_AGENT_ID}_*.json"), reverse=True)
    if not files:
        raise FileNotFoundError("❌ No output file found in bridge_outbox.")
    latest = files[0]
    print(f"Validating output file: {latest}") # This will go to test_stdout.log
    data = json.loads(latest.read_text(encoding='utf-8')) # Added encoding

    assert "prompt" in data, "Missing 'prompt'"
    assert "response" in data and data["response"].strip(), "Empty 'response'"
    assert "timestamp" in data, "Missing 'timestamp'"

    expected_prompt = PROMPT_PATH.read_text(encoding='utf-8').strip() # Added encoding
    assert data["prompt"].strip() == expected_prompt, "Prompt mismatch"

    ts = datetime.strptime(data["timestamp"], "%Y%m%dT%H%M%SZ")
    age = (datetime.utcnow() - ts).total_seconds()
    assert age < 300, f"Timestamp too old: {ts}"
 
    print("Verifying response format using HybridResponseHandler...") # This will go to test_stdout.log
    try:
        response_text = data["response"]
        text_part, memory_update = HybridResponseHandler().parse_hybrid_response(response_text)
        
        assert isinstance(text_part, str), "Parsed text part is not a string."
        assert isinstance(memory_update, dict), "Parsed memory update is not a dict."
        
        print("✅ Response format verified successfully by HybridResponseHandler.") # This will go to test_stdout.log
        if memory_update: 
            print(f"    Found memory_update keys: {list(memory_update.keys())}") # This will go to test_stdout.log
        else:
            print("    No memory_update JSON block found in response (this may be expected).") # This will go to test_stdout.log
            
    except Exception as e:
        print(f"❌ HybridResponseHandler verification failed: {e}") # This will go to test_stdout.log
        raise AssertionError(f"HybridResponseHandler failed to parse response: {e}")

    print(f"✅ Output validated → {latest}") # This will go to test_stdout.log
    return latest

def main():
    print("🔍 Starting E2E Bridge Loop Test") # This will go to test_stdout.log

    try:
        step("Step 1: Ensure prompt file exists")
        create_prompt_file()

        step("Step 2: Verify cursor_agent_coords.json contains Agent-1")
        # ADDED: Granular try-except for debugging Step 2
        config_data_text = "<not read yet>"
        try:
            print("DEBUG_STEP2: Attempting to read CONFIG_PATH...", file=sys.stderr)
            config_data_text = CONFIG_PATH.read_text(encoding='utf-8')
            print("DEBUG_STEP2: Successfully read CONFIG_PATH.", file=sys.stderr)
            
            print("DEBUG_STEP2: Attempting json.loads()...", file=sys.stderr)
            raw = json.loads(config_data_text) 
            print("DEBUG_STEP2: Successfully parsed JSON.", file=sys.stderr)
            
            agent_key = f"Agent-{EXPECTED_AGENT_ID}"
            print(f"DEBUG_STEP2: Checking for agent_key: {agent_key}", file=sys.stderr)
            if agent_key not in raw:
                raise ValueError(f"❌ Missing expected agent key: {agent_key}")
            print("DEBUG_STEP2: Agent key found.", file=sys.stderr)
            
            print("DEBUG_STEP2: Checking for 'input_box'...", file=sys.stderr)
            if "input_box" not in raw[agent_key]:
                raise ValueError(f"❌ Missing 'input_box' in coords for {agent_key}")
            print("DEBUG_STEP2: 'input_box' found.", file=sys.stderr)
            
            print(f"✅ Found {agent_key} with input_box coordinates.") # This goes to test_stdout.log

        except FileNotFoundError as e_fnf:
             print(f"DEBUG_STEP2_FAIL: FileNotFoundError - {e_fnf}", file=sys.stderr)
             # raise # Re-raise to trigger main except block - REMOVED RAISE
             sys.exit(1) # Exit explicitly instead?
        except json.JSONDecodeError as e_json:
             print(f"DEBUG_STEP2_FAIL: JSONDecodeError - {e_json}", file=sys.stderr)
             # print(f"DEBUG_STEP2_FAIL: Text that failed parsing:\n{config_data_text[:500]}...", file=sys.stderr)
             # raise # Re-raise - REMOVED RAISE
             sys.exit(1) # Exit explicitly instead?
        except KeyError as e_key:
             print(f"DEBUG_STEP2_FAIL: KeyError - Likely missing agent key or sub-key - {e_key}", file=sys.stderr)
             # raise # Re-raise - REMOVED RAISE
             sys.exit(1) # Exit explicitly instead?
        except ValueError as e_val:
             print(f"DEBUG_STEP2_FAIL: ValueError - {e_val}", file=sys.stderr)
             # raise # Re-raise - REMOVED RAISE
             sys.exit(1) # Exit explicitly instead?
        except Exception as e_step2:
             # Catch any other unexpected error during Step 2 validation
             print(f"DEBUG_STEP2_FAIL: Unexpected Exception - {type(e_step2).__name__}: {e_step2}", file=sys.stderr)
             # raise # KEEP raise for truly unexpected errors here - NOW COMMENTING OUT
             sys.exit(1) # Exit explicitly if even unexpected error occurs in Step 2

        # END Granular try-except

        # ADDED: Debug print immediately after Step 2 block
        print("DEBUG: Reached point immediately after Step 2 try-except block.", file=sys.stderr)

        step("Step 3: Run bridge loop subprocess")
        
        # ADDED: Debug print just before subprocess call
        print("DEBUG: About to call run_bridge_loop() function.", file=sys.stderr)
        
        run_bridge_loop() # Calls subprocess.run

        step("Step 4: Validate output JSON")
        outfile = validate_latest_output() # <<< RESTORED
        # print("INFO: validate_latest_output() call skipped for this test run.", file=sys.stderr) # Print to stderr log
        # outfile = "N/A (subprocess skipped)"

        # print("\n✅ E2E TEST STRUCTURE COMPLETED (SUBPROCESS SKIPPED)") # This will go to test_stdout.log
        # print(f"📦 Output path would be: {OUTBOX_PATH}") # This will go to test_stdout.log
        print("\n✅ E2E TEST PASSED") # <<< RESTORED
        print(f"📦 Output saved at: {outfile}") # <<< RESTORED
    except Exception as e:
        # CORRECTED: Added missing closing parenthesis for the f-string
        print(f"\n❌ E2E TEST FAILED (during setup/validation):\n{e}") # This will go to test_stdout.log
        sys.exit(1)

if __name__ == "__main__":
    main() 