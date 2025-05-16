import json
import logging
import os
from datetime import datetime, timedelta

# --- Configuration ---
LOG_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../logs")
)  # Assume logs are in sandbox/logs
SOURCE_LOG = os.path.join(LOG_DIR, "gpt_to_cursor.jsonl")
SCRAPER_LOG = os.path.join(LOG_DIR, "scraper_log.jsonl")
SUMMARY_LOG = os.path.join(LOG_DIR, "summary_log.jsonl")

OUTPUT_DIR = os.path.abspath(os.path.dirname(__file__))
SUCCESS_LOG = os.path.join(OUTPUT_DIR, "feedback_trace_log.jsonl")
FAILURE_LOG = os.path.join(OUTPUT_DIR, "feedback_trace_failures.jsonl")
ALERT_FLAG = os.path.join(OUTPUT_DIR, "feedback_trace_alert.flag")

TIMESTAMP_TOLERANCE = timedelta(
    seconds=5
)  # How close timestamps need to be for scraper match
CYCLE_TIME = timedelta(seconds=1)  # Define 1 cycle time
SUMMARY_LATENCY_TOLERANCE = (
    2 * CYCLE_TIME
)  # Max time allowed from scraper log to summary log
PROMPT_SUBSTRING_LENGTH = 50  # How many chars of prompt/query to use for matching

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("FeedbackTraceVerifier")


# --- Helper Functions ---
def parse_timestamp(ts_str):
    """Safely parse ISO 8601 timestamps."""
    if not ts_str:
        return None
    try:
        # Handle potential timezone formats (Z, +00:00, etc.)
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        return datetime.fromisoformat(ts_str)
    except ValueError:
        logger.warning(f"Could not parse timestamp: {ts_str}")
        return None


def read_jsonl(file_path):
    """Read a JSON Lines file safely, yielding parsed objects."""
    records = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    if line.strip():
                        records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.error(
                        f"Skipping invalid JSON line in {file_path}: {e} - Line: {line.strip()}"
                    )
    except FileNotFoundError:
        logger.error(f"Log file not found: {file_path}")
    return records


def write_jsonl(file_path, record):
    """Append a record to a JSON Lines file safely."""
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            json.dump(record, f)
            f.write("\n")
    except Exception as e:
        logger.error(f"Failed to write to {file_path}: {e}")


def create_flag_file(file_path):
    """Create an empty flag file."""
    try:
        with open(file_path, "w"):
            pass  # Just create the file
        logger.info(f"Created alert flag file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to create flag file {file_path}: {e}")


# --- Core Verification Logic ---
def verify_traces():
    logger.info("Starting feedback trace verification...")

    # Clean previous run outputs
    for f in [SUCCESS_LOG, FAILURE_LOG, ALERT_FLAG]:
        if os.path.exists(f):
            os.remove(f)

    source_records = read_jsonl(SOURCE_LOG)
    scraper_records = read_jsonl(SCRAPER_LOG)
    summary_records = read_jsonl(SUMMARY_LOG)

    if not source_records:
        logger.warning(
            f"Source log {SOURCE_LOG} is empty or not found. Cannot perform verification."
        )
        return

    # Pre-process records for easier lookup (optional, good for large files)
    # For simplicity here, we iterate and search

    failure_detected = False
    verified_count = 0
    failed_count = 0

    # Autonomy Chain Step 2: Match Source -> Scraper
    for src in source_records:
        src_ts = parse_timestamp(src.get("timestamp"))
        src_id = src.get("request_id", "Unknown Source ID")
        # Use prompt or query field for substring matching
        src_prompt = src.get("prompt") or src.get("parameters", {}).get("query", "")
        src_prompt_sub = src_prompt[:PROMPT_SUBSTRING_LENGTH] if src_prompt else ""

        if not src_ts or not src_prompt_sub:
            logger.warning(
                f"Source record {src_id} missing timestamp or usable prompt/query. Skipping."
            )
            continue

        found_scraper = None
        for scr in scraper_records:
            scr_ts = parse_timestamp(scr.get("timestamp"))
            scr_prompt = scr.get("prompt") or scr.get(
                "query", ""
            )  # Match field in scraper log
            scr_prompt_sub = scr_prompt[:PROMPT_SUBSTRING_LENGTH] if scr_prompt else ""

            if not scr_ts or not scr_prompt_sub:
                continue  # Cannot match this scraper record

            time_match = abs(src_ts - scr_ts) <= TIMESTAMP_TOLERANCE
            prompt_match = src_prompt_sub == scr_prompt_sub

            if time_match and prompt_match:
                found_scraper = scr
                break

        if not found_scraper:
            logger.warning(
                f"Trace broken: No matching scraper log found for source {src_id} ({src_prompt_sub}) around {src_ts}"
            )
            failure_record = {
                "timestamp": datetime.now().isoformat(),
                "failure_point": "source_to_scraper",
                "source_id": src_id,
                "source_timestamp": src.get("timestamp"),
                "reason": "No matching scraper entry found within time/prompt tolerance.",
            }
            write_jsonl(FAILURE_LOG, failure_record)
            failure_detected = True
            failed_count += 1
            continue  # Move to next source record

        # Autonomy Chain Step 3: Match Scraper -> Summary
        scr_id = found_scraper.get("request_id", "Unknown Scraper ID")
        scr_ts = parse_timestamp(
            found_scraper.get("timestamp")
        )  # Re-parse needed timestamp

        found_summary = None
        for smr in summary_records:
            smr_ts = parse_timestamp(smr.get("timestamp"))
            smr_ref_id = smr.get("request_id") or smr.get(
                "scraper_ref"
            )  # Field linking to scraper/source

            if not smr_ts or not smr_ref_id:
                continue  # Cannot match this summary record

            # Check if summary references the same request AND is within latency tolerance
            id_match = (smr_ref_id == src_id) or (
                smr_ref_id == scr_id
            )  # Allow matching either ID
            latency_match = (
                (smr_ts - scr_ts) <= SUMMARY_LATENCY_TOLERANCE
                if scr_ts and smr_ts
                else False
            )

            if id_match and latency_match:
                found_summary = smr
                break

        if not found_summary:
            logger.warning(
                f"Trace broken: No summary log found within {SUMMARY_LATENCY_TOLERANCE} for scraper {scr_id} (Source: {src_id}) from {scr_ts}"
            )
            failure_record = {
                "timestamp": datetime.now().isoformat(),
                "failure_point": "scraper_to_summary",
                "source_id": src_id,
                "scraper_id": scr_id,
                "scraper_timestamp": found_scraper.get("timestamp"),
                "reason": f"No matching summary entry found within latency tolerance ({SUMMARY_LATENCY_TOLERANCE}).",
            }
            write_jsonl(FAILURE_LOG, failure_record)
            failure_detected = True
            failed_count += 1
            continue  # Move to next source record

        # Autonomy Chain Step 4: Log Confirmation
        latency = smr_ts - scr_ts if smr_ts and scr_ts else None
        success_record = {
            "verification_timestamp": datetime.now().isoformat(),
            "source_id": src_id,
            "source_timestamp": src.get("timestamp"),
            "scraper_id": scr_id,
            "scraper_timestamp": found_scraper.get("timestamp"),
            "summary_id": found_summary.get(
                "request_id", "Unknown Summary ID"
            ),  # Or other ID field
            "summary_timestamp": found_summary.get("timestamp"),
            "scraper_to_summary_latency_seconds": (
                latency.total_seconds() if latency else None
            ),
        }
        write_jsonl(SUCCESS_LOG, success_record)
        verified_count += 1

    logger.info(
        f"Verification complete. Verified traces: {verified_count}, Failed traces: {failed_count}"
    )

    # Autonomy Chain Step 5: Trigger Alert Flag
    if failure_detected:
        logger.warning(
            "Failures detected during trace verification. Creating alert flag."
        )
        create_flag_file(ALERT_FLAG)
    else:
        logger.info("No failures detected. Feedback trace integrity maintained.")


# --- Main Execution ---
if __name__ == "__main__":
    # Before running, create mock log files if they don't exist
    mock_files_created = False
    for log_path in [SOURCE_LOG, SCRAPER_LOG, SUMMARY_LOG]:
        if not os.path.exists(log_path):
            logger.warning(f"Creating mock log file: {log_path}")
            # Create very basic mock data
            mock_data = []
            ts_now = datetime.now().isoformat()
            if log_path == SOURCE_LOG:
                mock_data.append(
                    {
                        "request_id": "src-mock-1",
                        "timestamp": ts_now,
                        "parameters": {
                            "query": "This is the first mock query for testing purposes."
                        },
                    }
                )
            elif log_path == SCRAPER_LOG:
                mock_data.append(
                    {
                        "request_id": "scr-mock-1",
                        "timestamp": (
                            datetime.fromisoformat(ts_now) + timedelta(seconds=1)
                        ).isoformat(),
                        "query": "This is the first mock query for testing purposes.",
                    }
                )
            elif log_path == SUMMARY_LOG:
                mock_data.append(
                    {
                        "request_id": "src-mock-1",
                        "timestamp": (
                            datetime.fromisoformat(ts_now) + timedelta(seconds=2)
                        ).isoformat(),
                        "summary": "Mock summary",
                    }
                )

            with open(log_path, "w", encoding="utf-8") as f:
                for item in mock_data:
                    json.dump(item, f)
                    f.write("\n")
            mock_files_created = True
    if mock_files_created:
        logger.info(
            "Mock log files created. Please replace with actual logs for real verification."
        )

    verify_traces()
