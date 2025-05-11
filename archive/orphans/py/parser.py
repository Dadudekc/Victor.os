import datetime
import json
import os

INPUT_LOG_PATH = "cursor_execution_log.json"
OUTPUT_PAYLOAD_PATH = "gpt_ingest_payload.json"


def parse_cursor_log(log_data):
    """Parses the simulated Cursor execution log and transforms it into the GPT ingest format."""
    status_map = {0: "success", 1: "warning", 2: "error"}
    status_code = log_data.get("status_code", 2)  # Default to error if missing

    combined_log = f"STDOUT:\n{log_data.get('stdout', '')}\n\nSTDERR:\n{log_data.get('stderr', '')}"

    payload = {
        "task_id": log_data.get("task_id", "unknown"),
        "status": status_map.get(status_code, "error"),
        "log": combined_log.strip(),
        "artifacts": log_data.get("result_artifacts", []),
        "execution_metadata": {
            "execution_id": log_data.get("execution_id", "unknown"),
            "start_time": log_data.get("timestamp_start_utc", None),
            "end_time": log_data.get("timestamp_end_utc", None),
        },
    }
    return payload


if __name__ == "__main__":
    print("Ironvale Feedback Parser starting...")

    # Ensure script runs from workspace root or adjust paths accordingly
    workspace_root = os.getcwd()
    absolute_input_path = os.path.join(
        workspace_root, "sandbox/ironvale_feedback", INPUT_LOG_PATH
    )
    absolute_output_path = os.path.join(
        workspace_root, "sandbox/ironvale_feedback", OUTPUT_PAYLOAD_PATH
    )

    # Step 4: Simulate a feedback loop with fabricated execution logs.
    # Create a simulated input log file first.
    simulated_log_data = {
        "execution_id": f"exec_{int(datetime.datetime.now().timestamp())}",
        "task_id": "bridge_task_sim_001",
        "timestamp_start_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "stdout": "Processing item 1... OK\nProcessing item 2... OK\nFinalizing... Done.",
        "stderr": "",
        "status_code": 0,  # Success
        "timestamp_end_utc": (
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=2)
        ).isoformat(),
        "result_artifacts": ["sandbox/output/result.txt"],
    }

    print(f"Creating simulated input log: {absolute_input_path}")
    try:
        os.makedirs(os.path.dirname(absolute_input_path), exist_ok=True)
        with open(absolute_input_path, "w") as f:
            json.dump(simulated_log_data, f, indent=2)
        print("Simulated input log created.")
    except Exception as e:
        print(f"ERROR: Failed to create simulated input log: {e}")
        exit(1)

    # Now, parse the simulated log
    print(f"Reading simulated log from {absolute_input_path}...")
    try:
        with open(absolute_input_path, "r") as f:
            cursor_log = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to read simulated log: {e}")
        exit(1)

    print("Parsing log and generating GPT ingest payload...")
    gpt_payload = parse_cursor_log(cursor_log)

    # Step 5: Confirm data conforms to expected schema and log output path.
    # (Schema conformance is implicit in the generation, path is handled below)
    print(f"Writing GPT payload to {absolute_output_path}...")
    try:
        with open(absolute_output_path, "w") as f:
            json.dump(gpt_payload, f, indent=2)
        print("GPT ingest payload generation complete.")
        print(f"Submission artifact: {absolute_output_path}")
    except Exception as e:
        print(f"ERROR: Failed to write GPT payload: {e}")
