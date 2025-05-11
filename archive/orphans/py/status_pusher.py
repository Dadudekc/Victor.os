import json
import logging
import os
from datetime import datetime, timezone

# Configure logging (integrate with KNURLSHADE later)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

FEEDBACK_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../outgoing_feedback")
)


def format_feedback(
    request_id: str, command_type: str, status: str, result: any
) -> dict:
    """Constructs the feedback payload dictionary."""
    return {
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command_type": command_type,
        "status": status,
        "result": result,  # Can be complex object, string, etc.
    }


def push_feedback(feedback_payload: dict):
    """Writes the feedback payload as a JSON file to the outgoing directory."""
    request_id = feedback_payload.get("request_id", "unknown_request")
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    # Generate a unique filename to avoid collisions
    filename = f"feedback_{request_id}_{timestamp_str}.json"
    filepath = os.path.join(FEEDBACK_DIR, filename)

    try:
        os.makedirs(FEEDBACK_DIR, exist_ok=True)  # Ensure dir exists
        with open(filepath, "w") as f:
            json.dump(feedback_payload, f, indent=2)
        logger.info(f"Pushed feedback for {request_id} to {filepath}")
        return True
    except Exception as e:
        logger.error(
            f"Failed to push feedback for {request_id} to {filepath}: {e}",
            exc_info=True,
        )
        return False


if __name__ == "__main__":
    # --- Directive Specific Logic ---
    # Ingest simulated log, format, and write to specific file as per autonomy chain.

    SIMULATED_LOG_PATH = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "cursor_execution_log.json")
    )
    TARGET_PAYLOAD_PATH = os.path.abspath(
        os.path.join(FEEDBACK_DIR, "gpt_feedback_payload.json")
    )

    logger.info(f"Starting simulated ingestion from: {SIMULATED_LOG_PATH}")

    try:
        with open(SIMULATED_LOG_PATH, "r") as f:
            sim_log_data = json.load(f)
        logger.info("Successfully read simulated execution log.")

        # Extract necessary fields from the simulated log
        request_id = sim_log_data.get("request_id")
        command_type = sim_log_data.get("command_type")
        status = sim_log_data.get("status")
        result_data = sim_log_data.get("result")

        if not all([request_id, command_type, status, result_data is not None]):
            raise ValueError(
                "Simulated log is missing required fields (request_id, command_type, status, result)"
            )

        # Format the feedback payload using existing function
        feedback_payload = format_feedback(
            request_id=request_id,
            command_type=command_type,
            status=status,  # Use status directly from log
            result=result_data,
        )
        logger.info(f"Formatted feedback payload for {request_id}.")

        # Write to the specific target file
        os.makedirs(FEEDBACK_DIR, exist_ok=True)  # Ensure dir exists
        with open(TARGET_PAYLOAD_PATH, "w") as f:
            json.dump(feedback_payload, f, indent=2)
        logger.info(
            f"Successfully wrote feedback payload to specific file: {TARGET_PAYLOAD_PATH}"
        )

    except FileNotFoundError:
        logger.error(f"Simulated log file not found at {SIMULATED_LOG_PATH}")
    except Exception as e:
        logger.error(
            f"Error during simulated log ingestion and processing: {e}", exc_info=True
        )

    # --- Original example usage (commented out for directive execution) ---
    # test_request_id = str(uuid.uuid4())
    # # Simulate success
    # success_payload = format_feedback(
    #     request_id=test_request_id,
    #     command_type='list_dir',
    #     status='simulated_success',
    #     result={"files": ["file1.txt", "subdir/"]}
    # )
    # print("Testing success feedback push:")
    # push_feedback(success_payload) # Uses timestamped filename

    # # Simulate error
    # error_payload = format_feedback(
    #     request_id=test_request_id, # Same request ID for example
    #     command_type='edit_file',
    #     status='error',
    #     result={"message": "Target file not found", "details": "/path/to/nonexistent.py"}
    # )
    # print("\\nTesting error feedback push:")
    # push_feedback(error_payload) # Uses timestamped filename
