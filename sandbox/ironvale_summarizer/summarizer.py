import datetime
import json
import os

# Define expected input artifact locations (simulated)
INPUT_PATHS = {
    "module1_injector": "../module1_injector/report.json",
    "module2_telemetry": "../module2_telemetry/report.json",
    "module3_logging": "../module3_logging/report.json",  # Knurlshade
    # Module 4 (Veindrill) likely produces specific diagnostics, not directly summarized here
    "module5_sync": "../module5_sync/report.json",
    "module6_harness": "../module6_harness/report.json",
    "module8_validator": "../module8_validator/report.json",
}

# Corrected: Specify output path relative to the script's directory
# Assuming script is run from workspace root, this will place it inside the sandbox folder
OUTPUT_REPORT_PATH = "sandbox/ironvale_summarizer/final_bridge_report.json"


def read_json_artifact(file_path, module_name):
    """Safely reads and parses a JSON artifact file."""
    # Adjust input paths to be relative to workspace root if script is run from there
    full_path = (
        os.path.join(os.path.dirname(__file__), file_path)
        if not os.path.isabs(file_path)
        else file_path
    )
    # Simplified for sandbox structure: Assume paths are relative to sandbox root
    # Example adjustment - needs refinement based on actual execution context
    # Let's assume execution from D:\Dream.os and paths are relative to that
    full_path = file_path.lstrip("../")  # Basic attempt to fix relative path

    try:
        if os.path.exists(full_path):
            with open(full_path, "r") as f:
                return json.load(f)
        else:
            return {
                "status": "MISSING",
                "error": f"Artifact file not found: {full_path}",
            }
    except json.JSONDecodeError as e:
        return {
            "status": "ERROR",
            "error": f"Failed to parse JSON from {full_path}: {e}",
        }
    except Exception as e:
        return {"status": "ERROR", "error": f"Failed to read {full_path}: {e}"}


def generate_summary_report(inputs):
    """Generates the final summary report from individual module inputs."""
    report = {
        "mission_id": "PRIORITY_ALPHA_BRIDGE_CONSTRUCTION",
        "report_generated_by": "Agent 7 (Ironvale)",
        "report_timestamp_utc": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        "overall_status": "IN_PROGRESS",  # Default, update based on inputs
        "modules": {},
    }

    all_completed = True
    any_errors = False

    for module_key, data in inputs.items():
        report["modules"][module_key] = data
        module_status = data.get("status", "UNKNOWN").upper()
        if module_status != "COMPLETED":
            all_completed = False
        if module_status == "ERROR" or module_status == "FAILED":
            any_errors = True

    # Determine overall status
    if any_errors:
        report["overall_status"] = "ERROR"
    elif all_completed:
        report["overall_status"] = "COMPLETED"
    else:
        # If not all completed and no errors, could be IN_PROGRESS or PARTIAL
        # Let's check if *any* module is completed or working
        any_progress = any(
            d.get("status", "").upper() in ["COMPLETED", "WORKING", "IN_PROGRESS"]
            for d in inputs.values()
        )
        if any_progress:
            report["overall_status"] = "PARTIAL_COMPLETION"
        else:  # Likely all MISSING or PENDING
            report["overall_status"] = "PENDING_INPUTS"

    # Add a high-level summary message
    report["summary_message"] = (
        f"Bridge construction status: {report['overall_status']}. {len(inputs)} modules reporting."
    )
    if any_errors:
        report["summary_message"] += " Errors detected in one or more modules."
    elif all_completed:
        report["summary_message"] += " All reporting modules indicate completion."

    return report


if __name__ == "__main__":
    print("Ironvale Summarizer starting...")
    module_inputs = {}
    # Ensure script runs from workspace root or adjust paths accordingly
    # For now, assuming execution from D:\Dream.os based on terminal output
    workspace_root = os.getcwd()  # Should be D:\Dream.os

    for key, path in INPUT_PATHS.items():
        # Construct absolute path assuming INPUT_PATHS are relative to sandbox/
        absolute_input_path = os.path.join(
            workspace_root, "sandbox", path.lstrip("../")
        )
        print(f"Reading input artifact for {key} from {absolute_input_path}...")
        module_inputs[key] = read_json_artifact(absolute_input_path, key)

    print("Generating final summary report...")
    final_report = generate_summary_report(module_inputs)

    # Ensure output path is absolute and correct
    absolute_output_path = os.path.join(workspace_root, OUTPUT_REPORT_PATH)
    print(f"Writing final report to {absolute_output_path}...")
    try:
        # Ensure the directory exists before writing
        os.makedirs(os.path.dirname(absolute_output_path), exist_ok=True)
        with open(absolute_output_path, "w") as f:
            json.dump(final_report, f, indent=2)
        print("Report generation complete.")
    except Exception as e:
        print(f"ERROR: Failed to write final report: {e}")
