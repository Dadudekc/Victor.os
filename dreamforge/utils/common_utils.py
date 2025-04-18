import os
import sys
import logging
import json

# Temporarily keep project root finding if CURSOR_OUTPUT_DIR logic remains
# Consider moving CURSOR_OUTPUT_DIR to a config file or constants module
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))

# If CURSOR_OUTPUT_DIR is moved, remove script_dir and project_root above.

# Setup logger for this module specifically
# If parse_cursor_result_file is moved, this logger setup can be removed.
logger = logging.getLogger(__name__)


# --- Cursor Result Parsing (Potentially move to cursor integration) ---

# Define expected output directory (relative to project root)
# TODO: Move this to configuration or a dedicated constants module
CURSOR_OUTPUT_DIR = os.path.join(project_root, "outputs", "social_cursor")

def parse_cursor_result_file(result_filepath: str) -> dict | None:
    """
    Parses a Cursor result JSON file.
    TODO: Re-evaluate if this belongs here or within cursor-specific modules.
    TODO: Replace placeholder log_event calls if that system is removed or refactored.

    Args:
        result_filepath: The full path to the JSON result file.

    Returns:
        A dictionary containing the parsed result data, or None if parsing fails.
    """
    # Placeholder for the potential log_event function if it's needed here
    # This needs to be resolved based on where log_event is defined/used.
    def log_event(event_type, source, details):
        logger.warning(f"Placeholder log_event called: {event_type} from {source} - {details}")
        pass

    log_context = {"filepath": result_filepath}
    logger.info(f"Attempting to parse Cursor result file: {os.path.basename(result_filepath)}")

    if not os.path.exists(result_filepath):
        logger.error(f"Cursor result file not found: {result_filepath}")
        log_event("CURSOR_RESULT_PARSE_ERROR", "CommonUtils", {**log_context, "error": "File not found"})
        return None

    try:
        with open(result_filepath, 'r', encoding='utf-8') as f:
            result_data = json.load(f)

        # Basic validation (adapt based on the actual Cursor output schema)
        # TODO: Make validation more robust based on actual schema
        required_keys = ["result_id", "original_prompt_id", "status", "output"]
        missing_keys = [key for key in required_keys if key not in result_data]
        if missing_keys:
            error_msg = f"Missing required keys in result file: {missing_keys}"
            logger.error(f"{error_msg} in file: {result_filepath}")
            log_event("CURSOR_RESULT_PARSE_ERROR", "CommonUtils", {**log_context, "error": error_msg})
            return None

        # Optional: Deeper validation of sub-structures (e.g., result_data['output'])

        logger.info(f"Successfully parsed Cursor result file: {result_filepath}")
        log_event("CURSOR_RESULT_PARSE_SUCCESS", "CommonUtils", {**log_context, "result_id": result_data.get("result_id")})
        return result_data

    except json.JSONDecodeError as json_e:
        error_msg = f"Invalid JSON in result file: {json_e}"
        logger.error(f"{error_msg} in file: {result_filepath}")
        log_event("CURSOR_RESULT_PARSE_ERROR", "CommonUtils", {**log_context, "error": error_msg})
        return None
    except Exception as e:
        error_msg = f"Failed to read or parse result file: {e}"
        logger.exception(f"{error_msg} - File: {result_filepath}") # Use logger.exception for traceback
        log_event("CURSOR_RESULT_PARSE_ERROR", "CommonUtils", {**log_context, "error": error_msg, "details": str(e)})
        return None

# --- End Cursor Result Parsing ---

# Example usage (can be uncommented for direct testing)
# if __name__ == "__main__":
#     print("Testing Cursor Result Parser...")
#     # Create dummy output dir and file
#     os.makedirs(CURSOR_OUTPUT_DIR, exist_ok=True)
#     dummy_result_filename = f"result_test_{int(time.time())}.json"
#     dummy_result_filepath = os.path.join(CURSOR_OUTPUT_DIR, dummy_result_filename)
#     dummy_result_payload = {
#         "result_id": str(uuid.uuid4()),
#         "original_prompt_id": str(uuid.uuid4()),
#         "timestamp_utc": datetime.now(timezone.utc).isoformat(),
#         "status": "success",
#         "output": {
#             "type": "code_edit_result",
#             "content": "+// Added a new line\n-// Removed a line",
#             "target_file": "test.py"
#         },
#         "metadata": {"execution_time_ms": 123}
#     }
#     try:
#         with open(dummy_result_filepath, 'w') as f:
#             json.dump(dummy_result_payload, f, indent=2)
#         print(f"Created dummy result file: {dummy_result_filepath}")
#         parsed_data = parse_cursor_result_file(dummy_result_filepath)
#         if parsed_data:
#             print("Parsing successful:")
#             print(json.dumps(parsed_data, indent=2))
#         else:
#             print("Parsing failed.")
#     except Exception as e:
#         print(f"Error during test: {e}")
#     finally:
#         # Clean up dummy file
#         if os.path.exists(dummy_result_filepath):
#             try: os.remove(dummy_result_filepath)
#             except: pass
#     print("Test finished.") 