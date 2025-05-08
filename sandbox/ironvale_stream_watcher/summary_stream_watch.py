import json
import os
import time
import datetime
import hashlib

# --- Configuration ---
# Assume bridge logs are in a central location
GPT_LOG_PATH = "runtime/logs/bridge/gpt_to_cursor.jsonl"
SCRAPER_LOG_PATH = "runtime/logs/bridge/scraper_log.jsonl"

# Output paths within the agent's sandbox
# Define relative to the script location or use absolute paths later
# Let's keep them as filenames and construct paths in main
SUMMARY_LOG_FILENAME = "summary_log.jsonl"
STATUS_LOG_FILENAME = "summary_stream_status.log"
WATCHDOG_FLAG_FILENAME = "summary_watchdog.flag"
HASH_MISMATCH_FLAG_FILENAME = "summary_hash_mismatch.flag"
INTEGRITY_REPORT_FILENAME = "summary_integrity_report.jsonl"
TRUST_HISTOGRAM_FILENAME = "summary_trust_histogram.json"

POLL_INTERVAL_SECONDS = 1 # Simulating 3 cycles with 1 second sleep
MAX_CYCLES_WITHOUT_NEW = 6
STATUS_UPDATE_INTERVAL = 5 # Log progress every 5 entries
MAX_RUNTIME_CYCLES = 25 # Limit script runtime for simulation
SCRAPER_LOOKBACK_LINES = 20 # How many recent scraper lines to check for correlation

# --- State Variables ---
processed_gpt_line_count = 0
last_summary_timestamp = None
cycles_since_last_new = 0
entries_since_last_status = 0
hashes_verified = 0
hash_mismatches = 0
trust_counts = { "1.0": 0, "0.5": 0, "0.0": 0 } # For histogram

def get_current_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def log_status(status_log_path, message):
    timestamp = get_current_timestamp()
    try:
        with open(status_log_path, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
        print(f"[STATUS] {message}")
    except Exception as e:
        print(f"[ERROR] Failed to write to status log {status_log_path}: {e}") # Print error, don't crash watcher

def log_integrity_event(report_path, event_data):
    """Logs an event to the integrity report JSONL file."""
    event_data['event_timestamp'] = get_current_timestamp()
    try:
        with open(report_path, 'a') as f:
            f.write(json.dumps(event_data) + '\n')
    except Exception as e:
        print(f"[ERROR] Failed to write to integrity report {report_path}: {e}")

def read_new_jsonl_lines(file_path, start_line):
    """Reads new lines from a JSONL file, returning lines and new line count."""
    lines = []
    current_line = 0
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                for i, line in enumerate(f):
                    current_line = i + 1
                    if current_line > start_line:
                        try:
                            lines.append(json.loads(line))
                        except json.JSONDecodeError:
                            # Need status_log_path here, will get from main scope or pass it
                            # For now, just print error to console if log_status isn't available easily
                            print(f"WARN: Skipping invalid JSON on line {current_line} in {file_path}")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"ERROR: Failed to read {file_path}: {e}")
    return lines, current_line

def find_correlation(gpt_entry, scraper_log_full_path, status_log_full_path):
    """Attempts to find a matching scraper log entry and its hash."""
    gpt_response = gpt_entry.get('response', '')
    gpt_hash_computed = hashlib.sha256(gpt_response.encode()).hexdigest()

    recent_scraper_entries = []
    try:
        if os.path.exists(scraper_log_full_path):
            with open(scraper_log_full_path, 'r') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-SCRAPER_LOOKBACK_LINES:]
                for line in recent_lines:
                     try:
                         recent_scraper_entries.append(json.loads(line))
                     except json.JSONDecodeError:
                         pass
    except Exception as e:
        log_status(status_log_full_path, f"WARN: Could not read/parse scraper log {scraper_log_full_path} for correlation: {e}")

    # Try correlation: Find scraper entry with matching hash
    for entry in reversed(recent_scraper_entries):
        scraper_id = entry.get('scraper_id', 'unknown')
        # *** ASSUMPTION: Scraper log contains the *computed* GPT response hash ***
        # *** If scraper logs the raw response, it would need to be hashed here for comparison ***
        scraper_logged_hash = entry.get('gpt_response_hash') # Assuming this field name
        if scraper_logged_hash and scraper_logged_hash == gpt_hash_computed:
            return scraper_id, scraper_logged_hash # Return both ID and the hash found

    # Fallback: If no hash match, return first recent ID as before, and None for hash
    if recent_scraper_entries:
        return recent_scraper_entries[-1].get('scraper_id', 'unknown'), None

    return "correlation_not_found", None

# --- Main Loop ---
if __name__ == "__main__":
    workspace_root = os.getcwd()
    script_dir = os.path.join(workspace_root, "sandbox/ironvale_stream_watcher")

    # Construct absolute paths for output files
    summary_log_path_abs = os.path.join(script_dir, SUMMARY_LOG_FILENAME)
    status_log_path_abs = os.path.join(script_dir, STATUS_LOG_FILENAME)
    watchdog_flag_path_abs = os.path.join(script_dir, WATCHDOG_FLAG_FILENAME)
    hash_mismatch_flag_path_abs = os.path.join(script_dir, HASH_MISMATCH_FLAG_FILENAME)
    integrity_report_path_abs = os.path.join(script_dir, INTEGRITY_REPORT_FILENAME)
    trust_histogram_path_abs = os.path.join(script_dir, TRUST_HISTOGRAM_FILENAME)

    # Ensure sandbox directory exists (should already exist from previous step, but good practice)
    os.makedirs(script_dir, exist_ok=True)

    # Pass absolute status log path to log_status function
    log_status(status_log_path_abs, "Ironvale Summary Stream Watcher starting (Enhanced with Trust Scoring).")
    log_integrity_event(integrity_report_path_abs, {"event_type": "watcher_start_trust_scoring"})

    # Construct absolute paths for input files
    gpt_log_path_abs = os.path.join(workspace_root, GPT_LOG_PATH)
    scraper_log_path_abs = os.path.join(workspace_root, SCRAPER_LOG_PATH)

    log_status(status_log_path_abs, f"Monitoring {gpt_log_path_abs}")
    log_status(status_log_path_abs, f"Verifying against {scraper_log_path_abs}")
    log_status(status_log_path_abs, f"Appending summaries to {summary_log_path_abs}")
    log_status(status_log_path_abs, f"Logging integrity to {integrity_report_path_abs}")

    # Simulate creating/ensuring log files exist initially if needed
    for path in [gpt_log_path_abs, scraper_log_path_abs]:
        if not os.path.exists(path):
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                open(path, 'a').close() # Touch file
                log_status(status_log_path_abs, f"Ensured log file exists: {path}")
            except Exception as e:
                 log_status(status_log_path_abs, f"ERROR: Failed to ensure log file {path}: {e}")
                 log_integrity_event(integrity_report_path_abs, {"event_type": "startup_error", "error": str(e), "file": path})
                 exit(1) # Exit if we can't ensure input files

    # Read initial line counts to know where to start
    _, processed_gpt_line_count = read_new_jsonl_lines(gpt_log_path_abs, 0)
    log_status(status_log_path_abs, f"Starting GPT log watch from line {processed_gpt_line_count + 1}")

    for cycle in range(MAX_RUNTIME_CYCLES):
        log_status(status_log_path_abs, f"Cycle {cycle + 1}/{MAX_RUNTIME_CYCLES}")

        new_gpt_entries, new_line_count = read_new_jsonl_lines(gpt_log_path_abs, processed_gpt_line_count)

        if new_gpt_entries:
            log_status(status_log_path_abs, f"Detected {len(new_gpt_entries)} new entries in {gpt_log_path_abs}.")
            cycles_since_last_new = 0
            if os.path.exists(watchdog_flag_path_abs):
                log_status(status_log_path_abs, "Clearing watchdog flag.")
                try:
                    os.remove(watchdog_flag_path_abs)
                except Exception as e:
                    log_status(status_log_path_abs, f"WARN: Failed to remove watchdog flag: {e}")

            for entry in new_gpt_entries:
                response_text = entry.get('response', '')
                if not response_text:
                    log_status(status_log_path_abs, "Skipping entry with empty response.")
                    continue

                # Calculate hash of the response from the GPT log
                computed_hash = hashlib.sha256(response_text.encode()).hexdigest()

                # Find correlation and the expected hash from scraper log
                scraper_id, expected_hash = find_correlation(entry, scraper_log_path_abs, status_log_path_abs)
                hashes_verified += 1
                trust_score = 0.0 # Default score

                if scraper_id != "correlation_not_found":
                    if expected_hash and computed_hash == expected_hash:
                        trust_score = 1.0
                        trust_counts["1.0"] += 1
                        hash_mismatches = 0 # Reset mismatch count on successful verification?
                    elif expected_hash and computed_hash != expected_hash:
                        # Hash mismatch found
                        trust_score = 0.0
                        trust_counts["0.0"] += 1
                        hash_mismatches += 1
                        log_status(status_log_path_abs, f"ALERT: Hash mismatch detected! GPT Log Time: {entry.get('timestamp')}, Scraper ID: {scraper_id}")
                        log_integrity_event(integrity_report_path_abs, {
                            "event_type": "hash_mismatch",
                            "gpt_log_timestamp": entry.get('timestamp'),
                            "scraper_id": scraper_id,
                            "computed_hash": computed_hash,
                            "expected_hash": expected_hash
                        })
                        if not os.path.exists(hash_mismatch_flag_path_abs):
                            try:
                                with open(hash_mismatch_flag_path_abs, 'w') as f:
                                    f.write(f"First mismatch detected at {get_current_timestamp()}\n")
                                log_status(status_log_path_abs, f"Created hash mismatch flag: {hash_mismatch_flag_path_abs}")
                            except Exception as e:
                                log_status(status_log_path_abs, f"ERROR: Failed to create hash mismatch flag: {e}")
                    else: # Correlation found, but no hash in scraper log
                        trust_score = 0.5 # Approximate match score
                        trust_counts["0.5"] += 1
                        log_status(status_log_path_abs, f"WARN: Found correlation ({scraper_id}) but no hash in scraper log for comparison. Score: 0.5")
                        log_integrity_event(integrity_report_path_abs, {
                            "event_type": "hash_missing_in_scraper",
                            "gpt_log_timestamp": entry.get('timestamp'),
                            "scraper_id": scraper_id
                        })
                else: # No correlation found
                    trust_score = 0.0
                    trust_counts["0.0"] += 1
                    log_status(status_log_path_abs, f"WARN: No correlation found for GPT entry {entry.get('timestamp')}. Score: 0.0")
                    log_integrity_event(integrity_report_path_abs, {
                        "event_type": "correlation_failed",
                        "gpt_log_timestamp": entry.get('timestamp')
                    })

                # Log warning if trust score is low
                if trust_score < 0.5:
                    log_integrity_event(integrity_report_path_abs, {
                        "event_type": "low_trust_warning",
                        "gpt_log_timestamp": entry.get('timestamp'),
                        "scraper_id": scraper_id,
                        "computed_hash": computed_hash,
                        "expected_hash": expected_hash,
                        "score": trust_score
                    })

                summary_metadata = {
                    'timestamp': get_current_timestamp(),
                    'gpt_log_timestamp': entry.get('timestamp'),
                    'length': len(response_text),
                    'scraper_id': scraper_id,
                    'response_hash': computed_hash,
                    'summary_trust_score': trust_score,
                    'preview': response_text[:80].replace('\n', ' ') + ('...' if len(response_text) > 80 else '')
                }

                try:
                    with open(summary_log_path_abs, 'a') as f:
                        f.write(json.dumps(summary_metadata) + '\n')
                    last_summary_timestamp = summary_metadata['timestamp']
                    entries_since_last_status += 1
                except Exception as e:
                    log_status(status_log_path_abs, f"ERROR: Failed to write to {summary_log_path_abs}: {e}")

                if entries_since_last_status >= STATUS_UPDATE_INTERVAL:
                    log_status(status_log_path_abs, f"Processed {entries_since_last_status} new entries. Last summary at {last_summary_timestamp}")
                    log_integrity_event(integrity_report_path_abs, {
                        "event_type": "batch_processed",
                        "count": entries_since_last_status,
                        "total_verified": hashes_verified,
                        "total_mismatches": hash_mismatches,
                        "trust_counts": trust_counts
                    })
                    entries_since_last_status = 0

            processed_gpt_line_count = new_line_count

        else:
            log_status(status_log_path_abs, "No new entries detected.")
            cycles_since_last_new += 1
            if cycles_since_last_new >= MAX_CYCLES_WITHOUT_NEW:
                if not os.path.exists(watchdog_flag_path_abs):
                    log_status(status_log_path_abs, f"ALERT: Stream stalled for {cycles_since_last_new} cycles. Creating watchdog flag.")
                    log_integrity_event(integrity_report_path_abs, {"event_type": "stream_stalled", "cycles_stalled": cycles_since_last_new})
                    try:
                        with open(watchdog_flag_path_abs, 'w') as f:
                            f.write(f"Stream stalled at {get_current_timestamp()}\n")
                    except Exception as e:
                         log_status(status_log_path_abs, f"ERROR: Failed to create watchdog flag {watchdog_flag_path_abs}: {e}")
                else:
                    log_status(status_log_path_abs, f"Stream stalled for {cycles_since_last_new} cycles. Watchdog flag already present.")

        log_status(status_log_path_abs, f"Sleeping for {POLL_INTERVAL_SECONDS}s...")
        time.sleep(POLL_INTERVAL_SECONDS)

    log_status(status_log_path_abs, f"Completed {MAX_RUNTIME_CYCLES} monitoring cycles. Exiting.")
    final_integrity_event = {
        "event_type": "watcher_end",
        "total_verified": hashes_verified,
        "total_mismatches": hash_mismatches,
        "final_trust_counts": trust_counts
    }
    log_integrity_event(integrity_report_path_abs, final_integrity_event)

    # Step 5: Write trust distribution histogram to telemetry
    log_status(status_log_path_abs, f"Writing trust histogram to {trust_histogram_path_abs}")
    try:
        with open(trust_histogram_path_abs, 'w') as f:
            json.dump(trust_counts, f, indent=2)
    except Exception as e:
        log_status(status_log_path_abs, f"ERROR: Failed to write trust histogram: {e}")
        log_integrity_event(integrity_report_path_abs, {"event_type": "histogram_write_error", "error": str(e)}) 