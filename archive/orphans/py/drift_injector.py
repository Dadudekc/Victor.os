from datetime import datetime, timezone

import pandas as pd


def normalize_timestamp_utc(ts_string):
    """Placeholder: Converts various timestamp formats to UTC ISO 8601."""
    # TODO: Implement robust parsing for different formats (log, ISO, etc.)
    try:
        # Attempt parsing standard log format: YYYY-MM-DD HH:MM:SS,fff
        # CRITICAL ASSUMPTION: This format is treated as implicitly UTC.
        # This is a potential source of error if logs are in local time.
        dt_obj = datetime.strptime(ts_string, "%Y-%m-%d %H:%M:%S,%f")
        dt_obj_utc = dt_obj.replace(tzinfo=timezone.utc)  # Explicitly treat as UTC
        return dt_obj_utc.isoformat(timespec="milliseconds")
    except ValueError:
        # Attempt parsing ISO format (handling Z and offsets)
        try:
            # Handle 'Z' for UTC explicitly
            if ts_string.endswith("Z"):
                ts_string = ts_string[:-1] + "+00:00"
            dt_obj = datetime.fromisoformat(ts_string)
            # Convert to UTC regardless of original offset
            dt_obj_utc = dt_obj.astimezone(timezone.utc)
            return dt_obj_utc.isoformat(timespec="milliseconds")
        except ValueError:
            # Fallback or raise error - return None to indicate failure
            # print(f"DEBUG: Failed to parse timestamp: {ts_string}") # Optional debug
            return None  # Return None if parsing fails completely


def process_log_data(log_file_path):
    """Processes log data from a file, normalizing timestamps."""
    data = []
    try:
        with open(log_file_path, "r") as f:
            for line in f:
                # Basic log parsing assumption: Timestamp is the first part, separated by ' - '
                parts = line.split(" - ", 1)
                if len(parts) < 2:
                    continue  # Skip lines without the expected format

                raw_timestamp_str = parts[0]
                log_message = parts[1].strip()

                normalized_ts = normalize_timestamp_utc(raw_timestamp_str)

                if (
                    normalized_ts
                ):  # Only include entries with valid, normalized timestamps
                    processed_entry = {
                        "original_timestamp": raw_timestamp_str,
                        "normalized_timestamp_utc": normalized_ts,
                        "message": log_message,
                        # Potentially extract other fields if needed
                    }
                    data.append(processed_entry)
                # else: Optional: log skipped entries
                #    print(f"Skipped line due to timestamp parse error: {line.strip()}")

    except FileNotFoundError:
        print(f"Error: Log file not found at {log_file_path}")
        return None
    except Exception as e:
        print(f"Error processing log file {log_file_path}: {e}")
        return None

    df = pd.DataFrame(data)
    # TODO: Implement synthetic drift injection logic if needed here
    # For now, focus is on normalization pipeline testing
    return df


# Example usage (optional, for direct testing)
# if __name__ == "__main__":
#     # Assumes script is run from workspace root or sandbox/scripts
#     test_log = Path("../logs/fake_bridge_log.md") # Adjust path as needed
#     if not test_log.parent.exists():
#         test_log.parent.mkdir(parents=True, exist_ok=True)
#     if not test_log.exists():
#         # Create a dummy log for testing if it doesn't exist
#         with open(test_log, 'w') as f:
#             f.write("2023-11-15 10:00:00,123 - INFO - Dummy log line 1\n")
#             f.write("2023-11-15T10:00:05.456Z - ERROR - Dummy log line 2\n")
#
#     processed_df = process_log_data(test_log)
#     if processed_df is not None:
#         print(processed_df.to_string())
