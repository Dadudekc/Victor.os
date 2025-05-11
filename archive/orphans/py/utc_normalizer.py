import re
import datetime
from dateutil import parser as date_parser
from dateutil.tz import UTC, gettz

# Configuration
LOG_FILE_PATH = "../logs/sim_bridge_fault.md"
OUTPUT_LOG_PATH = "../logs/sim_drift_analysis.log"
DRIFT_THRESHOLD_SECONDS = 1.0  # Threshold to flag significant drift

# Define known timezones for nodes providing local time without offset
# In a real scenario, this might come from a configuration database
NODE_TIMEZONES = {
    "NodeC-Edge-1": gettz("America/Los_Angeles"),  # PST/PDT
    "NodeG-West": gettz("America/Denver"),        # MST/MDT
    # NodeE-Legacy has internal drift, not timezone issue primarily
}

# Regex to extract timestamp and node ID
# Handles formats like 'YYYY-MM-DD HH:MM:SS,fff' and ISO 8601 variations
LOG_PATTERN = re.compile(r"^([0-9TZ.:+-,\s]+?)\s+\|\s+([^\s|]+)\s+\|")

# Regex to find 'Reported time: YYYY-MM-DD HH:MM:SS,fff' for NodeE drift simulation
DEVICE_DRIFT_PATTERN = re.compile(r"Reported time: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})")

drift_records_processed = 0
max_drift_observed = 0.0
affected_nodes = set()
drift_examples = []

print(f"Starting UTC Normalization Analysis for {LOG_FILE_PATH}")
print(f"Detailed results will be logged to {OUTPUT_LOG_PATH}")

with open(LOG_FILE_PATH, 'r') as infile, open(OUTPUT_LOG_PATH, 'w') as outfile:
    outfile.write("""Line # | Original Timestamp | Node ID       | Assumed UTC        | Expected UTC       | Drift (s) | Category
-------|--------------------|---------------|--------------------|--------------------|-----------|----------
""")

    for line_num, line in enumerate(infile, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        match = LOG_PATTERN.match(line)
        if not match:
            outfile.write(f"{line_num:<7}| N/A                | N/A           | N/A                | N/A                | N/A       | ParseError
")
            continue

        original_ts_str = match.group(1).strip()
        node_id = match.group(2).strip()
        normalized_utc = None
        expected_utc = None
        drift_seconds = 0.0
        category = "OK"

        try:
            # Attempt parsing using dateutil.parser (handles ISO 8601 well)
            # Default to UTC if no timezone info is present (THE FLAW WE ARE SIMULATING)
            parsed_dt = date_parser.parse(original_ts_str)

            if parsed_dt.tzinfo is None or parsed_dt.tzinfo.utcoffset(parsed_dt) is None:
                # --- This is the flawed assumption: Treat naive timestamps as UTC ---
                normalized_utc = parsed_dt.replace(tzinfo=UTC)
                # Determine the *actual* expected UTC based on our simulation rules
                if node_id in NODE_TIMEZONES:
                    # Assume the naive timestamp was in the node's local time
                    local_dt = NODE_TIMEZONES[node_id].localize(parsed_dt)
                    expected_utc = local_dt.astimezone(UTC)
                    category = "NaiveSkew" # Incorrectly treated local time as UTC
                else:
                     # For nodes without specific timezone info, assume it *was* intended as UTC
                    expected_utc = normalized_utc
            else:
                # Timestamp had timezone info, normalize correctly
                normalized_utc = parsed_dt.astimezone(UTC)
                expected_utc = normalized_utc # Already correct


            # Handle simulated device clock drift (NodeE)
            drift_match = DEVICE_DRIFT_PATTERN.search(line)
            if node_id == "NodeE-Legacy" and drift_match:
                 # The 'Reported time' is the device's actual (wrong) time.
                 # The timestamp at the start of the line is the *ingestion* time (assumed correct UTC)
                 ingestion_dt = date_parser.parse(original_ts_str).replace(tzinfo=UTC)
                 reported_dt_str = drift_match.group(1)
                 # Assume reported time *should* have been close to ingestion time if not for drift
                 # We parse it as naive and assume it *should* have been UTC for comparison
                 reported_dt_naive = datetime.datetime.strptime(reported_dt_str, "%Y-%m-%d %H:%M:%S,%f")
                 reported_dt_utc = reported_dt_naive.replace(tzinfo=UTC)

                 expected_utc = ingestion_dt # Expected UTC is the correct ingestion time
                 normalized_utc = reported_dt_utc # What the system *thinks* the time was based on device report
                 category = "DeviceDrift"

            # Calculate drift
            if expected_utc and normalized_utc:
                drift_delta = expected_utc - normalized_utc
                drift_seconds = drift_delta.total_seconds()

                if abs(drift_seconds) > max_drift_observed:
                    max_drift_observed = abs(drift_seconds)

                if abs(drift_seconds) >= DRIFT_THRESHOLD_SECONDS:
                    drift_records_processed += 1
                    affected_nodes.add(node_id)
                    if len(drift_examples) < 5: # Keep only a few examples
                         drift_examples.append({
                             "line": line_num,
                             "original": original_ts_str,
                             "node": node_id,
                             "normalized": normalized_utc.isoformat(),
                             "expected": expected_utc.isoformat(),
                             "drift": drift_seconds,
                             "category": category
                         })
                elif category == "NaiveSkew": # Reset category if drift is below threshold but skew was assumed
                    category = "OK (Skew<Thresh)"


            # Format for output log
            norm_utc_str = normalized_utc.isoformat() if normalized_utc else "N/A"
            exp_utc_str = expected_utc.isoformat() if expected_utc else "N/A"
            outfile.write(f"{line_num:<7}| {original_ts_str:<18} | {node_id:<13} | {norm_utc_str:<20} | {exp_utc_str:<20} | {drift_seconds:<9.3f} | {category}
")

        except Exception as e:
            outfile.write(f"{line_num:<7}| {original_ts_str:<18} | {node_id:<13} | ERROR              | ERROR              | N/A       | Exception: {e}
")

print(f"Analysis Complete.")
print(f"Total significant drift records processed: {drift_records_processed}")
print(f"Maximum absolute drift observed: {max_drift_observed:.3f} seconds")
print(f"Affected Nodes with significant drift: {', '.join(sorted(list(affected_nodes))) if affected_nodes else 'None'}")

# Check if rewrite condition is met
REWRITE_THRESHOLD = 10
if drift_records_processed >= REWRITE_THRESHOLD:
    print(f"Processed {drift_records_processed} drift records (>= {REWRITE_THRESHOLD}). Proceeding to rewrite documentation.")
    # In a real agent, this would trigger the next step (calling edit_file for the markdown)
    # For now, just print the data needed for the rewrite.
    print("\n--- Data for Documentation Rewrite ---")
    print(f"SIMULATED_START_DATE: 2024-01-15") # Based on log data
    print(f"SIMULATED_END_DATE: 2024-01-15")   # Based on log data
    print(f"MAX_DRIFT_SECONDS: {max_drift_observed:.3f}")
    print(f"AFFECTED_NODES_LIST: {', '.join(sorted(list(affected_nodes)))}")
    print(f"ROOT_CAUSE_SUMMARY: Implicit UTC assumption for ambiguous timestamps and simulated device clock drift.")
    print("DRIFT_EXAMPLES:")
    for ex in drift_examples:
        print(f"  - Line {ex['line']}: Node {ex['node']}, Orig '{ex['original']}', Norm '{ex['normalized']}', Exp '{ex['expected']}', Drift {ex['drift']:.3f}s ({ex['category']})")
else:
    print(f"Processed only {drift_records_processed} drift records (< {REWRITE_THRESHOLD}). Documentation rewrite deferred.")
