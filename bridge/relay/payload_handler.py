import logging
import os
import sys

# --- Add feedback pusher import ---
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../feedback"))
)
from status_pusher import format_feedback, push_feedback

# -----------------------------------

# Configure logging (placeholder - integrate with KNURLSHADE's module later)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Placeholder for Cursor API Interaction ---
# In a real scenario, this would import and call Cursor's actual tool functions.
# For simulation, we'll just log the intended action.


def call_cursor_api(command_type, parameters):
    logger.info(
        f"[SIMULATED CURSOR CALL] Command: {command_type}, Parameters: {parameters}"
    )
    # Simulate potential success/failure or return data if needed
    if command_type == "list_dir":
        return {
            "status": "success",
            "result": {"files": ["SIMULATED_FILE_1.txt", "SIMULATED_DIR/"]},
        }
    elif command_type == "read_file":
        return {
            "status": "success",
            "result": {
                "content": "Simulated file content for "
                + parameters.get("target_file", "unknown")
            },
        }
    elif command_type == "run_terminal" and parameters.get("command") == "echo 'Test'":
        # Simulate specific command success
        return {
            "status": "success",
            "result": {"exit_code": 0, "stdout": "Test\n", "stderr": ""},
        }
    elif command_type == "edit_file":
        # Simulate edit success
        return {
            "status": "success",
            "result": {
                "message": f"File {parameters.get('target_file')} edited successfully (simulated)."
            },
        }
    # Generic simulated success for other commands
    return {"status": "simulated_success", "result": "Generic simulation result"}


# --- Payload Processing Logic ---


def validate_parameters(command_type, parameters):
    """Performs basic validation of required parameters based on command type."""
    required = {
        "edit_file": ["target_file", "code_edit", "instructions"],
        "run_terminal": ["command", "is_background"],
        "codebase_search": ["query"],
        "file_search": ["query"],
        "read_file": [
            "target_file",
            "start_line_one_indexed",
            "end_line_one_indexed_inclusive",
        ],
        "list_dir": ["relative_workspace_path"],
        "grep_search": ["query"],
    }
    if command_type not in required:
        logger.error(f"Unknown command_type for validation: {command_type}")
        return False  # Or raise an error

    missing = [p for p in required[command_type] if p not in parameters]
    if missing:
        logger.error(f"Missing required parameters for {command_type}: {missing}")
        return False

    # Add more specific validation (e.g., types, ranges) here if needed
    logger.info(f"Parameters for {command_type} appear valid.")
    return True


def process_gpt_command(payload: dict):
    """Processes a validated command payload received from GPT and pushes feedback."""
    request_id = payload.get("request_id", "UNKNOWN_ID")
    command_type = payload.get("command_type")
    parameters = payload.get("parameters", {})
    feedback_payload = None  # Initialize feedback payload

    logger.info(f"Processing command {request_id}: Type={command_type}")

    if not command_type or not isinstance(parameters, dict):
        error_message = "Invalid payload structure"
        logger.error(
            f"{error_message} for {request_id}. Missing command_type or parameters."
        )
        feedback_payload = format_feedback(
            request_id, command_type or "unknown", "error", {"message": error_message}
        )
        push_feedback(feedback_payload)
        return  # Return None or the feedback payload itself? Directive implies fire-and-forget push.

    # Validate required parameters for the specific command
    if not validate_parameters(command_type, parameters):
        error_message = "Missing or invalid parameters"
        logger.error(
            f"{error_message} for {request_id}."
        )  # Already logged in validate_parameters
        feedback_payload = format_feedback(
            request_id, command_type, "error", {"message": error_message}
        )
        push_feedback(feedback_payload)
        return

    # --- Add specific sanitization/safety checks here ---
    if command_type == "run_terminal":
        forbidden = ["rm -rf", "shutdown", "> /dev/null"]
        if any(f in parameters.get("command", "") for f in forbidden):
            error_message = "Rejected potentially harmful command"
            logger.error(
                f"{error_message} for {request_id}: {parameters.get('command')}"
            )
            feedback_payload = format_feedback(
                request_id,
                command_type,
                "error",
                {"message": error_message, "command": parameters.get("command")},
            )
            push_feedback(feedback_payload)
            return
        logger.info(f"Terminal command for {request_id} passed basic safety check.")

    # --- Simulate calling the actual Cursor tool/API ---
    try:
        sim_result = call_cursor_api(command_type, parameters)
        exec_status = sim_result.get(
            "status", "error"
        )  # Default to error if status missing
        exec_result = sim_result.get("result", "Unknown simulation result or error")

        logger.info(
            f"Command {request_id} ({command_type}) executed (simulated). Status: {exec_status}"
        )

        feedback_payload = format_feedback(
            request_id, command_type, exec_status, exec_result
        )
        push_feedback(feedback_payload)

    except Exception as e:
        error_message = f"Error executing command: {str(e)}"
        logger.error(
            f"Error executing command {request_id} ({command_type}): {e}", exc_info=True
        )
        feedback_payload = format_feedback(
            request_id, command_type, "error", {"message": error_message}
        )
        push_feedback(feedback_payload)

    # The function now primarily pushes feedback, return value is less critical
    return  # Or return feedback_payload if needed elsewhere immediately


if __name__ == "__main__":
    # Example usage for testing payload handler directly (pushes feedback)
    test_payload_list = [
        {
            "request_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "timestamp": "2023-10-27T10:00:00Z",
            "command_type": "list_dir",
            "parameters": {"relative_workspace_path": "."},
        },
        {
            "request_id": "f47ac10b-58cc-4372-a567-0e02b2c3d480",
            "timestamp": "2023-10-27T10:01:00Z",
            "command_type": "edit_file",
            "parameters": {
                "target_file": "test.py"
                # Missing code_edit and instructions -> should cause error feedback
            },
        },
        {
            "request_id": "f47ac10b-58cc-4372-a567-0e02b2c3d481",
            "timestamp": "2023-10-27T10:02:00Z",
            "command_type": "run_terminal",
            "parameters": {"command": "echo 'Test'", "is_background": False},
        },
    ]

    print("Testing payload handler with direct feedback push:")
    for payload in test_payload_list:
        print(f"\nProcessing test payload: {payload.get('request_id')}")
        process_gpt_command(payload)
        time.sleep(0.1)  # Small delay to avoid filename collision if tests run fast

    print("\nCheck bridge/outgoing_feedback/ for generated JSON files.")

# Cleanup ensure_dir.py as it's no longer needed
# try:
#     os.remove(os.path.abspath(os.path.join(os.path.dirname(__file__), '../feedback/ensure_dir.py'))):
#     logger.info("Removed obsolete ensure_dir.py script.")
# except OSError as e:
#     logger.warning(f"Could not remove ensure_dir.py: {e}")
