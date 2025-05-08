import subprocess
import os
import time
from pathlib import Path
import sys
import json # Added for JSON parsing
import re # Added for regex parsing of timestamp
from datetime import datetime # Added for timestamp comparison
from typing import Optional

# Configuration
AGENT_ID = "1"  # Agent ID to use for the bridge loop
RESPONSE_TIMEOUT = 180  # Timeout for the bridge loop response in seconds
PROMPTS_DIR = Path("prompts")
# Changed to bridge_outbox as per run_bridge_loop.py and Agent-1's protocol doc
BRIDGE_OUTBOX_DIR = Path("runtime/bridge_outbox") 
# Ensure the root of the project is in the Python path for imports like dreamos
PROJECT_ROOT = Path(__file__).resolve().parent.parent 
SRC_DIR = PROJECT_ROOT / "src"

def get_latest_response_file(agent_id: str, outbox_dir: Path, after_timestamp: datetime) -> Optional[Path]:
    """Finds the latest JSON response file for the given agent_id created after a specific timestamp."""
    candidate_files = []
    # Regex to extract timestamp from filename: agent<ID>_<YYYYMMDDTHHMMSSZ>.json
    # Example: agent1_20240730T123456Z.json
    filename_pattern = re.compile(rf"agent{agent_id}_(\d{{8}}T\d{{6}}Z)\.json")

    for f_path in outbox_dir.glob(f"agent{agent_id}_*.json"):
        if f_path.is_file():
            match = filename_pattern.match(f_path.name)
            if match:
                try:
                    file_ts_str = match.group(1)
                    file_dt = datetime.strptime(file_ts_str, "%Y%m%dT%H%M%SZ")
                    if file_dt > after_timestamp:
                        candidate_files.append((file_dt, f_path))
                except ValueError:
                    # Invalid timestamp format in filename
                    print(f"Warning: Could not parse timestamp from {f_path.name}", file=sys.stderr)
                    continue 
    
    if not candidate_files:
        return None
    
    # Sort by datetime (first element of tuple) in descending order and pick the first one
    candidate_files.sort(key=lambda x: x[0], reverse=True)
    return candidate_files[0][1]

def run_self_prompt(prompt_text: str):
    """
    Manages the self-prompting process:
    1. Creates a temporary prompt file.
    2. Executes the dreamos.bridge.run_bridge_loop.
    3. Retrieves and prints the response from the bridge_outbox.
    """
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    BRIDGE_OUTBOX_DIR.mkdir(parents=True, exist_ok=True) # Ensure bridge_outbox dir exists

    # Record time before executing the bridge loop to find responses created *after* this point
    execution_start_time = datetime.utcnow()
    # Add a small delay to ensure file timestamps are likely after this moment
    # This helps in finding the correct response file if multiple exist.
    time.sleep(0.1)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    prompt_file_name = f"self_prompt_agent{AGENT_ID}_{timestamp}.txt"
    prompt_file_path = PROMPTS_DIR / prompt_file_name

    try:
        with open(prompt_file_path, "w", encoding="utf-8") as f:
            f.write(prompt_text)
        print(f"Prompt written to: {prompt_file_path}")

        env = os.environ.copy()
        current_pythonpath = env.get("PYTHONPATH", "")
        new_pythonpath_parts = [str(PROJECT_ROOT), str(SRC_DIR)]
        if current_pythonpath:
            new_pythonpath_parts.append(current_pythonpath)
        new_pythonpath = os.pathsep.join(new_pythonpath_parts)
        env["PYTHONPATH"] = new_pythonpath

        command = [
            sys.executable,
            "-m", "dreamos.bridge.run_bridge_loop",
            "--agent-id", str(AGENT_ID),
            "--prompt-file", str(prompt_file_path.resolve()),
            "--response-timeout", str(RESPONSE_TIMEOUT),
            "--outbox", str(BRIDGE_OUTBOX_DIR.resolve()) # Explicitly pass outbox
        ]

        print(f"Executing command: {' '.join(command)}")
        print(f"With PYTHONPATH: {new_pythonpath}")
        print(f"Working directory: {PROJECT_ROOT}")
        
        process = subprocess.run(command, env=env, capture_output=True, text=True, shell=False, cwd=PROJECT_ROOT)

        if process.returncode != 0:
            print(f"\n--- Error during bridge loop execution ---")
            print(f"Return Code: {process.returncode}")
            print(f"Stdout:\n{process.stdout}")
            print(f"Stderr:\n{process.stderr}")
            print("----------------------------------------\n")
            return

        print("\n--- Bridge loop executed successfully (according to return code) ---")
        if process.stdout:
            print(f"Stdout:\n{process.stdout}")
        if process.stderr:
            print(f"Stderr:\n{process.stderr}")
        print("--------------------------------------------------------------------\n")

        # Attempt to find and read the response JSON file from bridge_outbox
        print(f"Searching for response in: {BRIDGE_OUTBOX_DIR}")
        # Wait a moment for the file system to catch up after the process finishes.
        time.sleep(1) 
        latest_response_path = get_latest_response_file(AGENT_ID, BRIDGE_OUTBOX_DIR, execution_start_time)

        if latest_response_path and latest_response_path.exists():
            print(f"Found potential response file: {latest_response_path}")
            try:
                with open(latest_response_path, "r", encoding="utf-8") as f:
                    response_data = json.load(f)
                
                llm_response = response_data.get("response")
                if llm_response is not None:
                    print(f"--- Response from LLM (from {latest_response_path.name}) ---")
                    print(llm_response)
                    print("----------------------------------------------------------\n")
                else:
                    print(f"Error: 'response' key not found in JSON data in {latest_response_path.name}.")
                    print(f"Full JSON content: {response_data}")

            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from {latest_response_path.name}.")
            except Exception as e_read:
                print(f"Error reading or parsing response file {latest_response_path.name}: {e_read}")
        else:
            print(f"No new response file found for Agent {AGENT_ID} in {BRIDGE_OUTBOX_DIR} created after {execution_start_time.strftime('%Y%m%dT%H%M%SZ')}.")
            print("This might indicate the bridge loop did not produce an output file, or an error occurred before file creation.")
            print("Review the Stdout/Stderr above for clues from the bridge loop itself.")

    except Exception as e:
        print(f"An error occurred in the self-prompter script: {e}")
    finally:
        # Optional: Clean up the prompt file
        # if prompt_file_path.exists():
        #     prompt_file_path.unlink()
        #     print(f"Cleaned up prompt file: {prompt_file_path}")
        pass

if __name__ == "__main__":
    print("Captain AI Self-Prompter")
    print("--------------------------")
    try:
        prompt_from_user = input("Enter your self-prompt: ")
        if prompt_from_user.strip():
            run_self_prompt(prompt_from_user)
        else:
            print("No prompt entered. Exiting.")
    except KeyboardInterrupt:
        print("\nExiting self-prompter.") 