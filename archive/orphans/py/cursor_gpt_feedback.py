import json
import sys

# Assume input JSON (from Module 1) is passed via stdin or file path argument
# Output will be the standardized feedback payload (JSON) for GPT


def determine_result_type(data):
    """Infers the original command type based on the structure of the success response."""
    # This relies on the distinct structures returned by SimulatedCursorTools in Module 1
    if "message" in data and "applied" in data["message"]:
        return "edit_file"
    if "message" in data and "proposed" in data["message"]:
        return "run_terminal"
    if "results" in data and isinstance(data["results"], list):
        # Could be search or grep, need more info if distinction is critical
        # For now, assume codebase_search if result format is generic list
        # Grep results often have line numbers/file paths, but Module 1 sim is basic
        if "grep match" in data["results"][0] if data["results"] else False:
            return "grep_search"
        else:
            return "codebase_search"  # Default search type
    if "content" in data:
        return "read_file"
    # Add more specific checks if Module 1 simulation output becomes more detailed
    return "unknown"  # Fallback


def format_feedback(input_payload):
    correlation_id = input_payload.get("correlation_id", "unknown_id")
    status = input_payload.get("status", "error")  # Default to error if status missing
    output_payload = {
        "correlation_id": correlation_id,
        "status": status,
        "result_type": "unknown",
        "data": {},
    }

    if status == "success":
        result_type = determine_result_type(input_payload)
        output_payload["result_type"] = result_type
        # Populate data based on type (Cycles 11-15)
        if result_type == "edit_file" or result_type == "run_terminal":
            output_payload["data"]["message"] = input_payload.get("message")
        elif result_type == "codebase_search" or result_type == "grep_search":
            output_payload["data"]["results"] = input_payload.get("results")
            output_payload["data"]["message"] = input_payload.get(
                "message"
            )  # Optional message
        elif result_type == "read_file":
            output_payload["data"]["content"] = input_payload.get("content")
            output_payload["data"]["message"] = input_payload.get("message")
        else:  # Unknown success type
            output_payload["data"] = input_payload  # Pass through raw data
            output_payload["data"].pop("status", None)  # Remove redundant fields
            output_payload["data"].pop("correlation_id", None)

    elif status == "error":
        output_payload["result_type"] = "error"
        output_payload["data"]["error_message"] = input_payload.get(
            "message", "Unknown error details."
        )
    else:
        # Handle unexpected status values
        output_payload["result_type"] = "error"
        output_payload["status"] = "error"
        output_payload["data"]["error_message"] = (
            f"Invalid status '{status}' received in input."
        )

    return output_payload


if __name__ == "__main__":
    input_data = None
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], "r") as f:
                input_data = json.load(f)
        except Exception as e:
            print(
                json.dumps(
                    {
                        "correlation_id": "file_read_error",
                        "status": "error",
                        "result_type": "error",
                        "data": {
                            "error_message": f"Error reading file {sys.argv[1]}: {e}"
                        },
                    }
                )
            )
            sys.exit(1)
    else:
        try:
            input_data = json.load(sys.stdin)
        except Exception as e:
            print(
                json.dumps(
                    {
                        "correlation_id": "stdin_read_error",
                        "status": "error",
                        "result_type": "error",
                        "data": {"error_message": f"Error reading stdin: {e}"},
                    }
                )
            )
            sys.exit(1)

    if input_data:
        feedback = format_feedback(input_data)
        print(json.dumps(feedback, indent=2))  # Pretty print for readability
    else:
        print(
            json.dumps(
                {
                    "correlation_id": "no_input_error",
                    "status": "error",
                    "result_type": "error",
                    "data": {"error_message": "No input data received."},
                }
            )
        )
        sys.exit(1)
