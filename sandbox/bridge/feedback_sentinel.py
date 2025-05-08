import json
import sys
import os
import time
import glob
import hashlib
from datetime import datetime, timedelta

# Configuration
WORKSPACE_ROOT = os.getcwd()
SANDBOX_DIR = os.path.join(WORKSPACE_ROOT, "sandbox", "bridge")
MONITOR_DIR = os.path.join(SANDBOX_DIR, "outgoing_feedback")
QUARANTINE_DIR = os.path.join(SANDBOX_DIR, "feedback", "quarantine")
FEEDBACK_DIR = os.path.join(SANDBOX_DIR, "feedback")
LOG_FILE = os.path.join(FEEDBACK_DIR, "anomaly_log.jsonl")
ALERT_DIR = os.path.join(SANDBOX_DIR, "alerts")
ALERT_FLAG_FILE = os.path.join(SANDBOX_DIR, "feedback_sentinel_breach.flag")
SWARM_STATE_FILE = os.path.join(WORKSPACE_ROOT, "runtime", "state", "swarm_state.json")
STATE_SYNC_LOG_FILE = os.path.join(FEEDBACK_DIR, "sentinel_state_sync.log")

SCAN_INTERVAL_SECONDS = 15 # Simulating 3 cycles (5s/cycle)
ALERT_WINDOW_SECONDS = 50  # Simulating 10 cycles
ALERT_THRESHOLD = 5
PURGE_WINDOW_SECONDS = 500 # Simulating 100 cycles
REQUIRED_FIELDS = ["correlation_id", "status", "result_type"]

def ensure_dir_exists(path):
    os.makedirs(path, exist_ok=True)

def load_log():
    ensure_dir_exists(os.path.dirname(LOG_FILE))
    if not os.path.exists(LOG_FILE):
        return []
    log_data = []
    try:
        with open(LOG_FILE, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        log_data.append(json.loads(line))
                    except json.JSONDecodeError:
                        print(f"ERROR: Skipping corrupted line in log: {line.strip()}", file=sys.stderr)
        return log_data
    except Exception as e:
        print(f"ERROR: Failed to load anomaly log {LOG_FILE}: {e}", file=sys.stderr)
        return [] # Return empty list on error

def save_log(log_data):
    """Saves log data as JSON Lines."""
    ensure_dir_exists(os.path.dirname(LOG_FILE))
    try:
        with open(LOG_FILE, 'w') as f:
            for entry in log_data:
                json.dump(entry, f)
                f.write('\n')
    except Exception as e:
        print(f"ERROR: Failed to save anomaly log {LOG_FILE}: {e}", file=sys.stderr)

def log_anomaly(filename, file_hash, reason):
    """Logs anomaly if hash is not already present."""
    log_data = load_log()
    # Check for duplication
    existing_hashes = {entry.get("file_hash") for entry in log_data}
    if file_hash != "<hash_calculation_failed>" and file_hash in existing_hashes:
        print(f"Duplicate anomaly detected (Hash: {file_hash[:8]}...). Skipping log.", file=sys.stderr)
        return None # Indicate no log update happened

    timestamp = datetime.utcnow().isoformat() + "Z"
    log_entry = {"timestamp": timestamp, "quarantined_file": os.path.basename(filename), "file_hash": file_hash, "reason": reason}
    log_data.append(log_entry)
    save_log(log_data)
    print(f"Anomaly logged: {log_entry}", file=sys.stderr)

    # Update swarm state only for new, unique anomalies
    update_swarm_state(log_entry)

    return log_data # Return updated log for alert check

def check_alert_condition(log_data):
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=ALERT_WINDOW_SECONDS)
    recent_anomalies = 0
    for entry in reversed(log_data): # Check recent entries first
        try:
            entry_ts = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
            if entry_ts >= window_start:
                recent_anomalies += 1
            else:
                break # Log is chronological, no need to check older
        except Exception:
            continue # Skip malformed log entries

    if recent_anomalies >= ALERT_THRESHOLD:
        if not os.path.exists(ALERT_FLAG_FILE):
            ensure_dir_exists(ALERT_DIR)
            try:
                with open(ALERT_FLAG_FILE, 'w') as f:
                    f.write(f"ALERT: {recent_anomalies} anomalies detected within {ALERT_WINDOW_SECONDS}s window. Triggered at {now.isoformat()}Z by Hexmire.")
                print(f"ALERT TRIGGERED: {ALERT_FLAG_FILE} created.", file=sys.stderr)
            except Exception as e:
                print(f"ERROR: Failed to write alert file: {e}", file=sys.stderr)
        else:
             print(f"Alert condition met ({recent_anomalies} anomalies), but alert file already exists.", file=sys.stderr)

def process_file(filepath):
    """Validates file structure and returns (isValid, reason)."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        # Validate required fields
        missing_fields = [field for field in REQUIRED_FIELDS if field not in data]
        if missing_fields:
            reason = f"Missing fields: {', '.join(missing_fields)}"
            print(f"Malformed payload detected: {os.path.basename(filepath)}. {reason}", file=sys.stderr)
            return False, reason # Malformed
        return True, "Valid" # Valid
    except json.JSONDecodeError as e:
        reason = f"Invalid JSON: {e}"
        print(f"Malformed payload detected: {os.path.basename(filepath)}. {reason}", file=sys.stderr)
        return False, reason # Malformed
    except Exception as e:
        reason = f"Error reading/processing: {e}"
        print(f"Error processing file {os.path.basename(filepath)}: {reason}", file=sys.stderr)
        return False, reason # Treat as potentially malformed or unreadable

def quarantine_file(filepath, reason):
    """Reads file, calculates hash, moves to quarantine, and logs anomaly with hash."""
    ensure_dir_exists(QUARANTINE_DIR)
    file_hash = "<hash_calculation_failed>"
    try:
        # Read content for hashing *before* moving
        with open(filepath, 'rb') as f:
            content = f.read()
            file_hash = hashlib.sha256(content).hexdigest()

        destination = os.path.join(QUARANTINE_DIR, os.path.basename(filepath))
        os.replace(filepath, destination) # Atomic move
        print(f"Quarantined: {os.path.basename(filepath)} to {QUARANTINE_DIR}", file=sys.stderr)
        updated_log = log_anomaly(filepath, file_hash, reason)
        if updated_log:
            check_alert_condition(updated_log)
    except Exception as e:
        print(f"ERROR: Failed to quarantine {os.path.basename(filepath)}: {e}", file=sys.stderr)

def purge_old_logs():
    """Removes log entries older than PURGE_WINDOW_SECONDS."""
    log_data = load_log()
    if not log_data: return # Nothing to purge

    now = datetime.utcnow()
    purge_cutoff = now - timedelta(seconds=PURGE_WINDOW_SECONDS)
    original_count = len(log_data)
    purged_log = []

    for entry in log_data:
        try:
            entry_ts = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
            if entry_ts >= purge_cutoff:
                purged_log.append(entry)
        except Exception:
            print(f"Skipping potentially malformed entry during purge: {entry}", file=sys.stderr)
            purged_log.append(entry) # Keep malformed entries for now

    if len(purged_log) < original_count:
        save_log(purged_log)
        print(f"Purged {original_count - len(purged_log)} old log entries.", file=sys.stderr)
    else:
        print("No old log entries found to purge.", file=sys.stderr)

def sentinel_loop():
    print("Hexmire Sentinel Loop Activated.", file=sys.stderr)
    ensure_dir_exists(MONITOR_DIR)
    while True:
        purge_old_logs() # Purge at start of cycle
        print(f"Scanning {MONITOR_DIR}...", file=sys.stderr)
        try:
            found_files = glob.glob(os.path.join(MONITOR_DIR, "*.json"))
            if not found_files:
                 print("No feedback files found.", file=sys.stderr)

            for filepath in found_files:
                is_valid, reason = process_file(filepath)
                if not is_valid:
                    quarantine_file(filepath, reason)
                else:
                     print(f"File {os.path.basename(filepath)} validated.", file=sys.stderr)
                     # Optionally move validated files to a processed directory?
                     # For now, just leaving them - could delete or move.
                     # os.remove(filepath) # Example deletion

        except Exception as e:
            print(f"ERROR during scan cycle: {e}", file=sys.stderr)

        print(f"Scan complete. Sleeping for {SCAN_INTERVAL_SECONDS}s...", file=sys.stderr)
        time.sleep(SCAN_INTERVAL_SECONDS)

def log_state_update(anomaly_entry):
    """Logs the state update event to a separate file."""
    ensure_dir_exists(os.path.dirname(STATE_SYNC_LOG_FILE))
    timestamp = datetime.utcnow().isoformat() + "Z"
    log_message = f"{timestamp} - STATE_UPDATE: Added anomaly hash {anomaly_entry.get('file_hash', 'N/A')[:8]}... to swarm state. Reason: {anomaly_entry.get('reason', 'N/A')}\n"
    try:
        with open(STATE_SYNC_LOG_FILE, 'a') as f:
            f.write(log_message)
    except Exception as e:
        print(f"ERROR: Failed to write to state sync log {STATE_SYNC_LOG_FILE}: {e}", file=sys.stderr)

def update_swarm_state(anomaly_entry):
    """Loads swarm state, appends new anomaly, and saves atomically."""
    state_data = {}
    try:
        # Ensure state directory exists
        ensure_dir_exists(os.path.dirname(SWARM_STATE_FILE))

        # Load existing state
        if os.path.exists(SWARM_STATE_FILE):
            try:
                with open(SWARM_STATE_FILE, 'r') as f:
                    state_data = json.load(f)
            except json.JSONDecodeError:
                print(f"ERROR: Swarm state file {SWARM_STATE_FILE} corrupted. Initializing new state.", file=sys.stderr)
                state_data = {}
            except Exception as e:
                 print(f"ERROR: Failed to read swarm state {SWARM_STATE_FILE}: {e}. Initializing new state.", file=sys.stderr)
                 state_data = {}
        else:
            state_data = {}

        # Ensure feedback_anomalies list exists
        if "feedback_anomalies" not in state_data:
            state_data["feedback_anomalies"] = []
        elif not isinstance(state_data["feedback_anomalies"], list):
             print(f"WARNING: feedback_anomalies in {SWARM_STATE_FILE} is not a list. Overwriting.", file=sys.stderr)
             state_data["feedback_anomalies"] = []

        # Prepare and append new anomaly entry
        swarm_entry = {
            "hash": anomaly_entry.get("file_hash", "<missing_hash>"),
            "timestamp": anomaly_entry.get("timestamp", "<missing_timestamp>"),
            "reason": anomaly_entry.get("reason", "<missing_reason>"),
            "sentinel": "HEXMIRE"
        }
        state_data["feedback_anomalies"].append(swarm_entry)

        # --- Atomic Write Logic (Next Cycle) --- 
        # Placeholder for now, write logic will be added next
        temp_file_path = SWARM_STATE_FILE + ".tmp"
        with open(temp_file_path, 'w') as f_tmp:
             json.dump(state_data, f_tmp, indent=2)
        os.replace(temp_file_path, SWARM_STATE_FILE)
        print(f"Successfully updated swarm state file: {SWARM_STATE_FILE}", file=sys.stderr)
        log_state_update(swarm_entry) # Log after successful write

    except Exception as e:
        print(f"ERROR: Failed during swarm state update: {e}", file=sys.stderr)

if __name__ == "__main__":
    sentinel_loop() 