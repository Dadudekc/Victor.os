import json
import os
import re
from datetime import datetime, timezone

# Determine paths relative to the workspace root, assuming script is run from workspace root
WORKSPACE_ROOT = os.getcwd()  # Get current working directory (should be workspace root)
SANDBOX_DIR = os.path.join(WORKSPACE_ROOT, "sandbox")
LOG_FILE_PATH = os.path.join(SANDBOX_DIR, "logs", "hexmire_fault_stream.md")
REPORT_DIR = os.path.join(SANDBOX_DIR, "reports")
REPORT_FILE_PATH = os.path.join(REPORT_DIR, "hexmire_fault_report.json")

# Regex to capture timestamp field, robust to variations
TIMESTAMP_REGEX = re.compile(r"TIMESTAMP:\s*(.*?)\s*\|")

# Known valid formats (expandable)
VALID_FORMATS = [
    "%Y-%m-%dT%H:%M:%SZ",  # ISO 8601 UTC (Zulu)
    "%Y-%m-%dT%H:%M:%S+00:00",  # ISO 8601 UTC (Offset)
]


def parse_timestamp(ts_str):
    """Attempts to parse a timestamp string into a timezone-aware datetime object (UTC)."""
    for fmt in VALID_FORMATS:
        try:
            # Use strptime and ensure it's UTC
            dt = datetime.strptime(ts_str, fmt)
            # If format includes offset, it should be handled directly.
            # If format is Zulu (Z), explicitly set timezone.
            if fmt.endswith("Z"):
                dt = dt.replace(tzinfo=timezone.utc)
            elif dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                # If format was offset +00:00, tzinfo should be set.
                # If somehow still naive, assume UTC but log warning potentially?
                # For now, just assume UTC if format matched but tz is naive
                dt = dt.replace(tzinfo=timezone.utc)

            # Convert to UTC just in case source was offset +00:00
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue  # Try next format
    return None  # Parsing failed for all known formats


def analyze_log_file(log_path):
    """Analyzes the simulated log file for timestamp issues."""
    results = {
        "counts": {
            "valid": 0,
            "malformed": 0,
            "ambiguous": 0,
            "drift-flagged": 0,
            "reverse_chrono_anomaly": 0,
        },
        "flagged_entries": [],
    }
    processed_timestamps = []

    try:
        with open(log_path, "r") as f:
            for i, line in enumerate(f):
                line_num = i + 1
                if not line.strip() or line.startswith("#"):
                    continue  # Skip empty/comment lines

                match = TIMESTAMP_REGEX.search(line)
                if not match:
                    # Could flag lines that don't match expected entry structure
                    continue

                timestamp_str = match.group(1).strip()
                parsed_dt = parse_timestamp(timestamp_str)

                flag_reason = None
                if parsed_dt:
                    results["counts"]["valid"] += 1
                    processed_timestamps.append((line_num, parsed_dt, line.strip()))
                    # Basic ambiguity check (placeholder logic)
                    if (
                        "Zulu" in timestamp_str
                        or "AM" in timestamp_str
                        or "PM" in timestamp_str
                        or "/" in timestamp_str
                    ):
                        # Could be valid if parser handles it, but flag as potentially ambiguous source
                        results["counts"]["ambiguous"] += 1
                        flag_reason = "Ambiguous/Non-standard Format"

                else:
                    results["counts"]["malformed"] += 1
                    flag_reason = "Malformed/Unparseable Timestamp"

                if flag_reason:
                    results["flagged_entries"].append(
                        {
                            "line_number": line_num,
                            "original_entry": line.strip(),
                            "timestamp_string": timestamp_str,
                            "reason": flag_reason,
                        }
                    )

    except FileNotFoundError:
        print(f"ERROR: Log file not found at {log_path}")
        return None

    # --- Add reverse chronology check here (Step 4) --- will add in next edit

    return results, processed_timestamps


def check_reverse_chronology(processed_timestamps, results):
    """Checks for reverse chronological order anomalies."""
    # Sort by line number first to process in original order, then check time
    processed_timestamps.sort(key=lambda x: x[0])
    last_dt = None
    for line_num, dt, original_line in processed_timestamps:
        if last_dt and dt < last_dt:
            results["counts"]["reverse_chrono_anomaly"] += 1
            # Add to flagged entries or update existing if already flagged
            found = False
            for entry in results["flagged_entries"]:
                if entry["line_number"] == line_num:
                    entry["reason"] += "; Reverse Chronology Detected"
                    found = True
                    break
            if not found:
                results["flagged_entries"].append(
                    {
                        "line_number": line_num,
                        "original_entry": original_line,
                        "timestamp_string": dt.isoformat(),  # Use parsed timestamp
                        "reason": "Reverse Chronology Detected",
                    }
                )
        last_dt = dt


def generate_report(report_data, report_path):
    """Generates the JSON report file, creating directory if needed."""
    try:
        # Ensure the report directory exists
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(
                report_data, f, indent=2, default=str
            )  # Add default=str for datetime
        print(f"Report generated successfully at {report_path}")
    except IOError as e:
        print(f"ERROR: Could not write report file {report_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during report generation: {e}")


if __name__ == "__main__":
    analysis_results, timestamps = analyze_log_file(LOG_FILE_PATH)
    if analysis_results:
        check_reverse_chronology(timestamps, analysis_results)
        generate_report(analysis_results, REPORT_FILE_PATH)
