import os
import re
import sys
from datetime import datetime, timezone

# Ensure the script directory is in the path to import drift_injector
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SANDBOX_DIR = os.path.abspath(
    os.path.join(SCRIPT_DIR, "..")
)  # Go up one level from tests
SCRIPTS_DIR = os.path.join(SANDBOX_DIR, "scripts")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    # Assuming drift_injector.py is in sandbox/scripts/
    from drift_injector import normalize_timestamp_utc
except ImportError as e:
    print(f"Error importing drift_injector: {e}")
    print(f"Ensure drift_injector.py exists in {SCRIPTS_DIR}")
    sys.exit(1)


def parse_expected_utc(line):
    """Extracts the expected UTC timestamp string from a log line comment."""
    match = re.search(r"Expected UTC: (\S+)", line)
    if match:
        expected_str = match.group(1)
        if expected_str == "N/A":
            return None
        # Add microseconds if missing, required for comparison after normalization
        if "." not in expected_str:
            expected_str = expected_str.replace("Z", ".000Z")
        # Standardize Z to +00:00 for parsing
        if expected_str.endswith("Z"):
            expected_str = expected_str[:-1] + "+00:00"
        try:
            # Parse the ISO string into a timezone-aware datetime object
            dt_obj = datetime.fromisoformat(expected_str)
            # Ensure it's UTC
            return dt_obj.astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def calculate_drift(original_ts_str, normalized_ts_str, expected_utc_dt):
    """Calculates the drift between the normalized timestamp and the expected UTC time."""
    if normalized_ts_str is None or expected_utc_dt is None:
        return None, "N/A"

    try:
        # Parse the normalized ISO string (should be UTC)
        normalized_dt = datetime.fromisoformat(normalized_ts_str.replace("Z", "+00:00"))

        # Calculate the difference
        drift = normalized_dt - expected_utc_dt
        drift_seconds = drift.total_seconds()

        # Format drift for readability
        if abs(drift_seconds) < 0.001:
            drift_str = "0s (Correct)"
        else:
            drift_str = f"{drift_seconds:.3f}s"

        return drift_seconds, drift_str

    except Exception as e:
        print(
            f"Error calculating drift for '{normalized_ts_str}' vs '{expected_utc_dt}': {e}"
        )
        return None, "Error"


def run_test(log_file_path):
    """Runs the drift detection test on the given log file."""
    results = []
    print(
        f"--- [DEBUG] Starting Drift Detection Test on {log_file_path} ---"
    )  # DEBUG PRINT
    try:
        print(
            f"--- [DEBUG] Attempting to open file: {log_file_path} ---"
        )  # DEBUG PRINT
        with open(log_file_path, "r") as f:
            print(
                "--- [DEBUG] File opened successfully. Reading lines... ---"
            )  # DEBUG PRINT
            for i, line in enumerate(f):
                # print(f"--- [DEBUG] Processing line {i+1} ---") # Optional: Very verbose
                line = line.strip()
                if (
                    not line
                    or line.startswith("#")
                    or line.startswith("##")
                    or " - " not in line
                ):
                    continue  # Skip empty lines, comments, headers, or lines without delimiter

                parts = line.split(" - ", 1)
                if len(parts) < 2:
                    print(f"Warning: Skipping malformed line {i+1}: {line}")
                    continue

                original_ts_str = parts[0]
                message = parts[1]

                # Get the ground truth expected time
                expected_utc_dt = parse_expected_utc(line)

                # Normalize the timestamp using the function from drift_injector
                normalized_ts_str = normalize_timestamp_utc(original_ts_str)

                # Calculate drift
                drift_seconds, drift_str = calculate_drift(
                    original_ts_str, normalized_ts_str, expected_utc_dt
                )

                results.append(
                    {
                        "line": i + 1,
                        "original": original_ts_str,
                        "normalized_utc": (
                            normalized_ts_str if normalized_ts_str else "Parse Failed"
                        ),
                        "expected_utc": (
                            expected_utc_dt.isoformat(timespec="milliseconds") + "Z"
                            if expected_utc_dt
                            else "N/A"
                        ),
                        "drift_seconds": drift_seconds,
                        "drift_display": drift_str,
                        "message": message.split(". Expected UTC:")[0],  # Clean message
                    }
                )

    except FileNotFoundError:
        print(f"Error: Log file not found at {log_file_path}")
        return None
    except Exception as e:
        print(f"Error processing log file {log_file_path}: {e}")
        return None

    # Print results table
    print("\n--- [DEBUG] Preparing Test Results Table --- --- ---")  # DEBUG PRINT
    print("\n--- Test Results ---")
    # Determine column widths dynamically (simple approach)
    max_orig = max(len(r["original"]) for r in results) if results else 10
    max_norm = max(len(r["normalized_utc"]) for r in results) if results else 15
    max_exp = max(len(r["expected_utc"]) for r in results) if results else 15
    max_drift = max(len(r["drift_display"]) for r in results) if results else 15

    header = f"{'Line':<5} | {'Original Timestamp':<{max_orig}} | {'Normalized UTC':<{max_norm}} | {'Expected UTC':<{max_exp}} | {'Drift':<{max_drift}} | Message"
    print(header)
    print("-" * len(header))

    total_drift_seconds = 0
    max_abs_drift = 0
    drift_count = 0

    print("--- [DEBUG] Iterating through results to print table... ---")  # DEBUG PRINT
    for r in results:
        print(
            f"{r['line']:<5} | {r['original']:<{max_orig}} | {r['normalized_utc']:<{max_norm}} | {r['expected_utc']:<{max_exp}} | {r['drift_display']:<{max_drift}} | {r['message']}"
        )
        if r["drift_seconds"] is not None:
            total_drift_seconds += r["drift_seconds"]
            max_abs_drift = max(max_abs_drift, abs(r["drift_seconds"]))
            if abs(r["drift_seconds"]) > 0.001:  # Count non-zero drifts
                drift_count += 1

    print("\n--- Summary ---")
    print(f"Total lines processed: {len(results)}")
    print(f"Lines with detected drift (>0.001s): {drift_count}")
    print(f"Maximum absolute drift detected: {max_abs_drift:.3f}s")
    # print(f"Total cumulative drift (sum): {total_drift_seconds:.3f}s") # Less useful metric

    print("\nTest Complete.")
    print("--- [DEBUG] run_test function finished. ---")  # DEBUG PRINT
    return results, max_abs_drift


if __name__ == "__main__":
    print("--- [DEBUG] Script execution started (__main__). ---")  # DEBUG PRINT
    # Assumes script is run from workspace root or sandbox/tests
    log_file_rel_path = os.path.join("..", "logs", "fake_bridge_log.md")
    log_file_abs_path = os.path.abspath(os.path.join(SCRIPT_DIR, log_file_rel_path))
    print(
        f"--- [DEBUG] Calculated log file path: {log_file_abs_path} ---"
    )  # DEBUG PRINT

    run_test(log_file_abs_path)
    print("--- [DEBUG] Script execution finished (__main__). ---")  # DEBUG PRINT
