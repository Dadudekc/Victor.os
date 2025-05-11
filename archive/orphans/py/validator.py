#!/usr/bin/env python3
"""Module 8: Final Integration Validator Script (Integration Mode with Preflight Checks)"""

import argparse
import json
import os
import subprocess  # For assumed script execution
import time

import requests  # For assumed REST APIs

# --- Configuration (Defaults/Placeholders) ---
DEFAULT_RESULTS_FILE = (
    "sandbox/bridge_validator/validation_results_partial.json"  # Updated output file
)
UNAVAILABLE_MODULES_FILE = (
    "sandbox/bridge_validator/bridge_validator_unavailable_modules.json"
)
SAMPLE_INPUT_FILE = "sandbox/sample_task_input.txt"
SAMPLE_OUTPUT_FILE = "sandbox/sample_task_output.txt"
MAX_WAIT_TIME_SECS = 120  # Max time to wait for bridge task completion
POLL_INTERVAL_SECS = 5
PREFLIGHT_CHECK_TIMEOUT_SECS = 10  # Timeout for individual module check
PREFLIGHT_RETRY_DELAY_SECS = 15
PREFLIGHT_MAX_RETRIES = 4  # Wait up to 1 minute total (4 * 15s)

# --- Assumed Module Interfaces (NEEDS VERIFICATION) ---
MODULE_1_RELAY_API = "http://localhost:8001/relay"
MODULE_1_HEALTH_API = "http://localhost:8001/health"  # Assumed health check
MODULE_2_FEEDBACK_API = "http://localhost:8002/status"
MODULE_2_RESULT_API = "http://localhost:8002/result"
MODULE_2_HEALTH_API = "http://localhost:8002/health"  # Assumed health check
MODULE_3_LOG_FILE = "runtime/logs/bridge_activity.log"  # Needs confirmation
MODULE_5_STATE_API = "http://localhost:8005/state"
MODULE_5_HEALTH_API = "http://localhost:8005/health"  # Assumed health check
MODULE_6_TRIGGER_SCRIPT = "sandbox/demo_harness/trigger.py"  # Needs path
MODULE_6_ENABLED = False  # Default based on previous status
MODULE_7_SUMMARIZE_API = "http://localhost:8007/summarize"
MODULE_7_HEALTH_API = "http://localhost:8007/health"  # Assumed health check


# --- Preflight Check Functions ---
def check_api_endpoint(module_name, health_url):
    """Checks if a REST API endpoint is responsive."""
    print(f"INFO: [Preflight] Checking {module_name} endpoint: {health_url}")
    try:
        response = requests.get(health_url, timeout=PREFLIGHT_CHECK_TIMEOUT_SECS)
        response.raise_for_status()  # Consider 2xx as available
        print(f"INFO: [Preflight] {module_name} is AVAILABLE ({response.status_code}).")
        return True
    except requests.exceptions.RequestException as e:
        print(f"WARNING: [Preflight] {module_name} check failed ({health_url}): {e}")
        return False
    except Exception as e:
        print(f"ERROR: [Preflight] Unexpected error checking {module_name}: {e}")
        return False


def check_file_path(module_name, file_path):
    """Checks if a file path exists."""
    print(f"INFO: [Preflight] Checking {module_name} path: {file_path}")
    if os.path.exists(file_path):
        print(f"INFO: [Preflight] {module_name} path FOUND.")
        return True
    else:
        print(f"WARNING: [Preflight] {module_name} path NOT FOUND: {file_path}")
        return False


# --- Core Validation Functions (Modified check_logs signature) ---
def trigger_bridge_task(task_payload):
    """Triggers the bridge task via Module 1 (Relay) or Module 6 (Harness)."""
    print(f"INFO: Triggering bridge task: {json.dumps(task_payload)}")

    if MODULE_6_ENABLED and check_file_path(
        "Module 6", MODULE_6_TRIGGER_SCRIPT
    ):  # Check if enabled AND exists
        # --- Assumed Module 6 Interaction ---
        print(f"INFO: Using Module 6 Harness: {MODULE_6_TRIGGER_SCRIPT}")
        try:
            # Pass payload as JSON string argument? Needs confirmation.
            result = subprocess.run(
                ["python", MODULE_6_TRIGGER_SCRIPT, json.dumps(task_payload)],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            print(f"INFO: Module 6 Harness Output: {result.stdout}")
            # How does harness signal success/failure? Assume non-zero exit code is failure for now.
            return True
        except FileNotFoundError:
            print(
                f"ERROR: Module 6 Harness script not found at {MODULE_6_TRIGGER_SCRIPT}"
            )
            return False
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Module 6 Harness failed: {e.stderr}")
            return False
        except Exception as e:
            print(f"ERROR: Failed to execute Module 6 Harness: {e}")
            return False
    else:
        # --- Assumed Module 1 Interaction ---
        if not MODULE_6_ENABLED:
            print("INFO: Module 6 not enabled, using Module 1.")
        else:  # Implies file check failed
            print(
                f"WARNING: Module 6 enabled but script not found at {MODULE_6_TRIGGER_SCRIPT}. Falling back to Module 1."
            )

        print(f"INFO: Using Module 1 Relay API: {MODULE_1_RELAY_API}")
        try:
            response = requests.post(MODULE_1_RELAY_API, json=task_payload, timeout=15)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            print(
                f"INFO: Module 1 Relay API Response: {response.status_code} - {response.text}"
            )
            # Assume 2xx status code means success
            return True
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Module 1 Relay API failed: {e}")
            return False
        except Exception as e:
            print(f"ERROR: Unexpected error calling Module 1: {e}")
            return False


def check_bridge_status(task_id):
    """Polls Module 2 (Feedback) or Module 5 (State Sync) for task status."""
    print(f"INFO: Checking bridge status for task {task_id} via Module 2/5...")
    # Prioritize Module 2 if available
    try:
        # Assumed API: GET /status?task_id=<task_id>
        response = requests.get(
            MODULE_2_FEEDBACK_API, params={"task_id": task_id}, timeout=10
        )
        response.raise_for_status()
        status_data = response.json()
        current_status = status_data.get("status", "UNKNOWN")
        print(
            f"INFO: Module 2 Status Response: {current_status} - {status_data.get('detail', '')}"
        )
        # Return values expected: 'PENDING', 'RUNNING', 'COMPLETED', 'ERROR'
        return current_status
    except requests.exceptions.RequestException as e:
        print(
            f"WARNING: Module 2 Feedback API ({MODULE_2_FEEDBACK_API}) failed: {e}. Falling back to Module 5."
        )
    except Exception as e:
        print(
            f"WARNING: Unexpected error calling Module 2 ({MODULE_2_FEEDBACK_API}): {e}. Falling back to Module 5."
        )

    # Fallback to Module 5
    try:
        # Assumed API: GET /state?task_id=<task_id>
        response = requests.get(
            MODULE_5_STATE_API, params={"task_id": task_id}, timeout=10
        )
        response.raise_for_status()
        state_data = response.json()
        # Infer status from Module 5 state (Needs refinement based on actual Module 5 structure)
        active_task = state_data.get("active_task_id")
        bridge_status = state_data.get("bridge_status")
        if active_task == task_id:
            if bridge_status == "ERROR":
                print("INFO: Module 5 State indicates ERROR for task.")
                return "ERROR"
            else:
                print("INFO: Module 5 State indicates RUNNING/PENDING for task.")
                return "RUNNING"  # Or PENDING? Needs clarification
        elif active_task != task_id and bridge_status != "ERROR":
            # Task ID not active, assume completed? Needs verification.
            print("INFO: Module 5 State suggests task might be COMPLETED (not active).")
            return "COMPLETED"  # Highly speculative
        else:
            print(f"INFO: Module 5 State: {state_data}")
            return "UNKNOWN"

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Module 5 State API ({MODULE_5_STATE_API}) failed: {e}.")
        return "UNKNOWN"
    except Exception as e:
        print(f"ERROR: Unexpected error calling Module 5 ({MODULE_5_STATE_API}): {e}")
        return "UNKNOWN"


def get_bridge_result(task_id):
    """Retrieves the final result details from Module 2."""
    print(f"INFO: Getting final result for task {task_id} via Module 2...")
    try:
        # Assumed API: GET /result?task_id=<task_id>
        response = requests.get(
            MODULE_2_RESULT_API, params={"task_id": task_id}, timeout=10
        )
        response.raise_for_status()
        result_data = response.json()
        print(f"INFO: Module 2 Result Response: {result_data}")
        return result_data
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Module 2 Result API ({MODULE_2_RESULT_API}) failed: {e}.")
        return None
    except Exception as e:
        print(f"ERROR: Unexpected error calling Module 2 Result API: {e}")
        return None


def check_output_file():
    """Checks if the output file matches the input file."""
    print("INFO: Checking output file content...")
    try:
        with open(SAMPLE_INPUT_FILE, "r") as infile, open(
            SAMPLE_OUTPUT_FILE, "r"
        ) as outfile:
            input_content = infile.read()
            output_content = outfile.read()
            if input_content == output_content:
                print("INFO: Output file content matches input.")
                return True
            else:
                print("ERROR: Output file content MISMATCH!")
                print(f"--- Expected ---\n{input_content}\n----------------")
                print(f"--- Actual ---\n{output_content}\n----------------")
                return False
    except FileNotFoundError:
        print(f"ERROR: Output file {SAMPLE_OUTPUT_FILE} not found.")
        return False
    except Exception as e:
        print(f"ERROR: Could not compare files: {e}")
        return False


def check_logs(task_id, module3_available):
    """Checks Module 3 logs if available."""
    if not module3_available:
        print("INFO: Module 3 unavailable or log file not found. Skipping log check.")
        return True  # Treat as success if module is known unavailable

    print(f"INFO: Checking Module 3 logs ({MODULE_3_LOG_FILE}) for task {task_id}...")
    try:
        if not os.path.exists(MODULE_3_LOG_FILE):
            print(f"WARNING: Module 3 log file not found at {MODULE_3_LOG_FILE}")
            return False  # Cannot verify if file doesn't exist

        with open(MODULE_3_LOG_FILE, "r") as f:
            log_content = (
                f.read()
            )  # Read whole log for simplicity, might need optimization

        # --- Assumed Log Format Checks (NEEDS REFINEMENT) ---
        # Check for entries indicating start, progress, and end for the task_id
        start_found = (
            f"task_id: {task_id}" in log_content and "status: PENDING" in log_content
        )  # Example
        progress_found = (
            f"task_id: {task_id}" in log_content and "status: RUNNING" in log_content
        )  # Example
        end_found = f"task_id: {task_id}" in log_content and (
            "status: COMPLETED" in log_content or "status: ERROR" in log_content
        )  # Example

        if start_found and progress_found and end_found:
            print("INFO: Found relevant entries in Module 3 logs.")
            return True
        else:
            print(
                f"WARNING: Did not find expected log entries for task {task_id}. Start: {start_found}, Progress: {progress_found}, End: {end_found}"
            )
            return False
    except Exception as e:
        print(f"ERROR: Failed to check Module 3 logs: {e}")
        return False


def call_summarizer(task_id, result_data, module7_available):
    """Calls Module 7 if available."""
    if not module7_available:
        print("INFO: Module 7 unavailable. Skipping summarization.")
        return None  # Return None if module is not available

    print(f"INFO: Calling Module 7 Summarizer for task {task_id}...")
    try:
        # Assumed API: POST /summarize
        payload = {
            "task_id": task_id,
            "final_status": result_data.get("final_status"),
            "result_summary": result_data.get("result_summary"),
            "status_history": result_data.get("status_history"),
        }
        response = requests.post(MODULE_7_SUMMARIZE_API, json=payload, timeout=20)
        response.raise_for_status()
        summary_data = response.json()
        print(f"INFO: Module 7 Summarizer Response: {summary_data}")
        return summary_data  # Return the generated summary
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Module 7 Summarizer API ({MODULE_7_SUMMARIZE_API}) failed: {e}")
        return None
    except Exception as e:
        print(f"ERROR: Unexpected error calling Module 7: {e}")
        return None


# --- Main Execution Logic ---
def run_preflight_checks_only():
    """Runs only the preflight checks for essential modules and returns True if ready."""
    print("--- Running Preflight Checks Only (Modules 1, 2, 5) ---")
    essential_ready = False
    retries = 0
    while retries <= PREFLIGHT_MAX_RETRIES:
        # Check only essential modules
        mod1_ready = check_api_endpoint("Module 1 (Relay)", MODULE_1_HEALTH_API)
        mod2_ready = check_api_endpoint("Module 2 (Feedback)", MODULE_2_HEALTH_API)
        mod5_ready = check_api_endpoint("Module 5 (State Sync)", MODULE_5_HEALTH_API)

        essential_ready = mod1_ready and mod2_ready and mod5_ready

        if essential_ready:
            print("INFO: [Preflight Check Only] Essential modules ARE ready.")
            return True  # Ready
        else:
            print(
                f"WARNING: [Preflight Check Only] Essential modules not ready (Attempt {retries+1}/{PREFLIGHT_MAX_RETRIES+1}). Waiting {PREFLIGHT_RETRY_DELAY_SECS}s..."
            )
            retries += 1
            if retries <= PREFLIGHT_MAX_RETRIES:
                time.sleep(PREFLIGHT_RETRY_DELAY_SECS)

    print(
        "ERROR: [Preflight Check Only] Essential modules did NOT become available after retries."
    )
    return False  # Not ready


def run_validation():
    """Performs preflight checks and then executes the validation test."""
    print(
        "=== Starting Bridge Integration Validation (Integration Mode w/ Preflight) ==="
    )

    # --- Preflight Checks ---
    print("--- Running Preflight Checks ---")
    unavailable_modules = []
    module_status = {}
    essential_ready = False
    retries = 0

    while retries <= PREFLIGHT_MAX_RETRIES:
        module_status = {
            "module1": check_api_endpoint("Module 1 (Relay)", MODULE_1_HEALTH_API),
            "module2": check_api_endpoint("Module 2 (Feedback)", MODULE_2_HEALTH_API),
            "module3": check_file_path("Module 3 (Logging)", MODULE_3_LOG_FILE),
            "module5": check_api_endpoint("Module 5 (State Sync)", MODULE_5_HEALTH_API),
            "module6": check_file_path("Module 6 (Harness)", MODULE_6_TRIGGER_SCRIPT)
            if MODULE_6_ENABLED
            else "DISABLED",
            "module7": check_api_endpoint("Module 7 (Summarizer)", MODULE_7_HEALTH_API),
        }

        # Check if essential modules (1, 2, 5) are ready
        essential_ready = (
            module_status["module1"]
            and module_status["module2"]
            and module_status["module5"]
        )

        if essential_ready:
            print("INFO: [Preflight] Essential modules (1, 2, 5) are ready.")
            break  # Exit retry loop
        else:
            print(
                f"WARNING: [Preflight] Essential modules not ready (Attempt {retries+1}/{PREFLIGHT_MAX_RETRIES+1}). Waiting {PREFLIGHT_RETRY_DELAY_SECS}s..."
            )
            retries += 1
            if retries <= PREFLIGHT_MAX_RETRIES:
                time.sleep(PREFLIGHT_RETRY_DELAY_SECS)

    print("--- Preflight Checks Complete ---")
    unavailable_modules = [
        name for name, status in module_status.items() if status is False
    ]  # Record only unavailable, not disabled

    if unavailable_modules:
        print(f"WARNING: Unavailable modules detected: {unavailable_modules}")
        try:
            os.makedirs(os.path.dirname(UNAVAILABLE_MODULES_FILE), exist_ok=True)
            with open(UNAVAILABLE_MODULES_FILE, "w") as f:
                json.dump(
                    {
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "unavailable": unavailable_modules,
                    },
                    f,
                    indent=2,
                )
            print(f"Unavailable modules logged to {UNAVAILABLE_MODULES_FILE}")
        except Exception as e:
            print(f"ERROR: Failed to log unavailable modules: {e}")

    if not essential_ready:
        print(
            "ERROR: Essential modules (1, 2, 5) did not become available after retries. Aborting validation."
        )
        # Create a minimal results file indicating the preflight failure
        results = {
            "validation_run_id": f"PREFLIGHT_FAIL-{int(time.time())}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mode": "INTEGRATION",
            "status": "BLOCKED",
            "summary": "Validation aborted due to unavailable essential modules.",
            "unavailable_modules": unavailable_modules,
        }
        return results

    # --- Proceed with Validation ---
    validation_run_id = f"VALIDATION-{int(time.time())}"
    results = {
        "validation_run_id": validation_run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "INTEGRATION",
        "status": "FAIL",  # Default to FAIL
        "preflight_status": module_status,
        "steps": {},
        "final_summary": None,
    }

    # 0. Ensure clean state
    try:
        if os.path.exists(SAMPLE_OUTPUT_FILE):
            os.remove(SAMPLE_OUTPUT_FILE)
        results["steps"]["cleanup"] = {
            "status": "SUCCESS",
            "message": "Old output file removed (if existed).",
        }
    except Exception as e:
        results["steps"]["cleanup"] = {
            "status": "ERROR",
            "message": f"Failed to remove old output file: {e}",
        }
        print(f"ERROR: Pre-test cleanup failed: {e}")

    # 1. Define and Trigger Task (using available modules)
    task_payload = {
        "task_id": validation_run_id,  # Use unique run ID as task ID
        "command_type": "file_edit",  # Example task type
        "details": {
            "action": "read_and_write",
            "read_path": os.path.abspath(SAMPLE_INPUT_FILE),  # Use absolute paths
            "write_path": os.path.abspath(SAMPLE_OUTPUT_FILE),
        },
    }
    # Module 6 availability is checked internally by trigger_bridge_task if MODULE_6_ENABLED is True
    trigger_success = trigger_bridge_task(task_payload)
    results["steps"]["trigger"] = {
        "status": "SUCCESS" if trigger_success else "FAIL",
        "task_id": validation_run_id,
        "payload": task_payload,
        "interface_used": f"Module {'6' if (MODULE_6_ENABLED and module_status['module6'] == True) else '1'}",  # Reflect actual used
    }
    if not trigger_success:
        print("ERROR: Failed to trigger bridge task. Aborting validation.")
        return results

    # 2. Poll for Completion (using available modules)
    start_time = time.time()
    final_status = "TIMEOUT"
    while time.time() - start_time < MAX_WAIT_TIME_SECS:
        current_status = check_bridge_status(validation_run_id)
        print(f"INFO: Bridge status poll: {current_status}")
        # Log polling attempts if needed (can get verbose)
        # results["steps"]["polling"] = results["steps"].get("polling", []) + [...]
        if current_status == "COMPLETED":
            final_status = "COMPLETED"
            break
        if current_status == "ERROR":
            final_status = "ERROR"
            break
        # Handle UNKNOWN status? Treat as still running for now.
        if current_status == "UNKNOWN":
            print("WARNING: Bridge status returned UNKNOWN. Continuing poll.")
        time.sleep(POLL_INTERVAL_SECS)

    results["steps"]["completion_check"] = {"status": final_status}

    # Retrieve final result details if completed
    task_result_data = None
    if (
        final_status == "COMPLETED" and module_status["module2"]
    ):  # Only try if Module 2 was available
        task_result_data = get_bridge_result(validation_run_id)
        results["steps"]["result_retrieval"] = {
            "status": "SUCCESS" if task_result_data else "FAIL",
            "data": task_result_data,
        }
        if not task_result_data:
            # If task completed but we can't get result, is that an error?
            print(
                "WARNING: Task reported COMPLETED but failed to retrieve results via Module 2."
            )
            # Keep final_status as COMPLETED for now, but note the retrieval issue
    elif final_status != "COMPLETED":
        print(
            f"ERROR: Bridge task did not complete successfully (Final Status: {final_status}). Aborting further checks."
        )
        return results  # Stop if task didn't complete

    # 3. Verify Output File (Crucial Check)
    output_verified = check_output_file()
    results["steps"]["output_verification"] = {
        "status": "SUCCESS" if output_verified else "FAIL"
    }

    # 4. Verify Logs (Using Module 3 interface, if available)
    logs_verified = check_logs(validation_run_id, module_status["module3"])
    results["steps"]["log_verification"] = {
        "status": "SUCCESS" if logs_verified else "FAIL",
        "log_file": MODULE_3_LOG_FILE,
        "checked": module_status["module3"],
    }

    # 5. Call Summarizer (Module 7, if available)
    summary = call_summarizer(
        validation_run_id, task_result_data, module_status["module7"]
    )
    results["steps"]["summarization"] = {
        "status": "SUCCESS"
        if summary
        else ("SKIPPED" if not module_status["module7"] else "FAIL"),
        "summary_generated": summary,
        "checked": module_status["module7"],
    }
    results["final_summary"] = summary

    # 6. Final Verdict
    # Key success criteria: Task COMPLETED, Output verified.
    if final_status == "COMPLETED" and output_verified:
        print("=== Validation PASSED (Integration Mode) ===")
        results["status"] = "PASS"
    else:
        print(
            f"=== Validation FAILED (Integration Mode) - Status: {final_status}, Output OK: {output_verified}, Logs OK: {logs_verified} ==="
        )
        results["status"] = "FAIL"

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run End-to-End Bridge Validation (Integration Mode w/ Prechecks)."
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_RESULTS_FILE,
        help="JSON file to store validation results.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Run only preflight checks for essential modules and exit.",
    )
    # Add args to override module interfaces
    parser.add_argument(
        "--module1-health-api",
        default=MODULE_1_HEALTH_API,
        help="Module 1 Health API endpoint.",
    )
    parser.add_argument(
        "--module2-health-api",
        default=MODULE_2_HEALTH_API,
        help="Module 2 Health API endpoint.",
    )
    parser.add_argument(
        "--module3-log-file", default=MODULE_3_LOG_FILE, help="Module 3 Log file path."
    )
    parser.add_argument(
        "--module5-health-api",
        default=MODULE_5_HEALTH_API,
        help="Module 5 Health API endpoint.",
    )
    parser.add_argument(
        "--module6-script-path",
        default=MODULE_6_TRIGGER_SCRIPT,
        help="Module 6 Trigger script path.",
    )
    parser.add_argument(
        "--module7-health-api",
        default=MODULE_7_HEALTH_API,
        help="Module 7 Health API endpoint.",
    )
    parser.add_argument(
        "--enable-module6", action="store_true", help="Enable use of Module 6 Harness."
    )

    args = parser.parse_args()

    # Update config based on args
    MODULE_1_HEALTH_API = args.module1_health_api
    MODULE_2_HEALTH_API = args.module2_health_api
    MODULE_3_LOG_FILE = args.module3_log_file
    MODULE_5_HEALTH_API = args.module5_health_api
    MODULE_6_TRIGGER_SCRIPT = args.module6_script_path
    MODULE_7_HEALTH_API = args.module7_health_api
    MODULE_6_ENABLED = args.enable_module6
    if MODULE_6_ENABLED:
        print("INFO: Module 6 Demo Harness execution ENABLED via command line.")

    if args.check_only:
        is_ready = run_preflight_checks_only()
        exit(0 if is_ready else 2)  # Exit 0 if ready, 2 if not ready
    else:
        # --- Normal Execution Path ---
        # Clean up old results file
        try:
            if os.path.exists(args.output):
                os.remove(args.output)
        except Exception as e:
            print(f"Warning: Could not remove old results file {args.output}: {e}")

        # Clean up unavailable modules log
        try:
            if os.path.exists(UNAVAILABLE_MODULES_FILE):
                os.remove(UNAVAILABLE_MODULES_FILE)
        except Exception as e:
            print(
                f"Warning: Could not remove old unavailable modules log {UNAVAILABLE_MODULES_FILE}: {e}"
            )

        validation_results = run_validation()

        # Write results to file
        try:
            os.makedirs(os.path.dirname(args.output), exist_ok=True)
            with open(args.output, "w") as f:
                json.dump(validation_results, f, indent=2)
            print(f"Validation results written to {args.output}")
        except Exception as e:
            print(f"ERROR: Failed to write results to {args.output}: {e}")

        # Exit with non-zero code on failure/blocker for automation
        if validation_results.get("status") not in ["PASS", "BLOCKED"]:
            exit(1)
        elif (
            validation_results.get("status") == "BLOCKED"
        ):  # Exit code 2 if blocked by preflight
            exit(2)
