#!/usr/bin/env python3
"""
Chrono Drift Sentinel

Monitors specified log files for timestamp anomalies (skew, significant staleness)
against the sentinel's reference clock (host system UTC time) and logs findings
to the UTC Fidelity Ledger.
"""

import logging
import sys
import re
import json
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone, tzinfo
from typing import List, Dict, Any, Optional

# --- Path Setup --- 
# Assuming script is in analytics/
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# --- Configuration --- 
# Potential future external config file
SENTINEL_ID = "ChronoSentinel-Alpha"
MONITOR_INTERVAL_SECONDS = 60 # Check logs every 60 seconds
LOG_SOURCES = {
    # File path relative to project_root: parser_function
    "runtime/logs/bridge_integrity_monitor.md": "parse_integrity_log_entry",
    "runtime/logs/stress_test_results.md": "parse_stress_log_entry",
    # Add other log sources here
}
UTC_LEDGER_FILE = project_root / "runtime" / "logs" / "utc_fidelity_ledger.log"
# Thresholds for anomaly detection
STALENESS_THRESHOLD_MINUTES = 15 # Log entries older than this might indicate issues
FUTURE_SKEW_THRESHOLD_SECONDS = 10 # Timestamps this far in the future indicate clock skew
LOCAL_TIMEZONE_ASSUMPTION = timezone.utc # Default assumption if system TZ fails

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("ChronoSentinel")

# --- UTC Fidelity Ledger Setup ---
def log_to_ledger(anomaly_details: Dict[str, Any]):
    """Appends a JSON record of the detected anomaly to the ledger file."""
    try:
        with open(UTC_LEDGER_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(anomaly_details) + '\n')
    except Exception as e:
        logger.error(f"Failed to write to UTC Fidelity Ledger {UTC_LEDGER_FILE}: {e}", exc_info=True)

# --- Timezone Handling (Adapted from bridge_fault_inspector) ---
_local_tz: Optional[tzinfo] = None
def get_local_tz_cached() -> tzinfo:
    """Safely retrieves and caches the local system's timezone."""
    global _local_tz
    if _local_tz is None:
        try:
            _local_tz = datetime.now().astimezone().tzinfo
            if _local_tz is None: # Handle rare cases where it might still be None
                logger.warning("Could not determine local timezone, defaulting to UTC.")
                _local_tz = LOCAL_TIMEZONE_ASSUMPTION
        except Exception as e:
            logger.error(f"Could not determine local timezone: {e}. Defaulting to UTC.", exc_info=True)
            _local_tz = LOCAL_TIMEZONE_ASSUMPTION
    return _local_tz

# --- Log Parsing Logic (Simplified - focus on timestamp) ---
# Regex patterns adapted/simplified from bridge_fault_inspector
INTEGRITY_LOG_PATTERN = re.compile(r"\*\s+\*\*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\*\*.*")
STRESS_RESULT_ROW_PATTERN = re.compile(r"^\|.*?\|.*?\|\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)\s*\|.*")

def parse_integrity_log_entry(line: str) -> Optional[datetime]:
    """Parses a line from integrity log, returns UTC timestamp if found."""
    match = INTEGRITY_LOG_PATTERN.match(line.strip())
    if match:
        ts_str = match.group(1)
        try:
            naive_timestamp = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            local_tz = get_local_tz_cached()
            aware_timestamp = naive_timestamp.replace(tzinfo=local_tz)
            utc_timestamp = aware_timestamp.astimezone(timezone.utc)
            return utc_timestamp
        except ValueError:
            logger.debug(f"Could not parse timestamp in integrity log line: {line.strip()}")
            return None
    return None

def parse_stress_log_entry(line: str) -> Optional[datetime]:
    """Parses a line from stress log, returns UTC timestamp if found."""
    match = STRESS_RESULT_ROW_PATTERN.match(line.strip())
    if match:
        ts_str = match.group(1)
        try:
            # Handle ISO format, converting to UTC
            ts_str_tz = ts_str.replace('Z', '+00:00') # Ensure Z is handled by fromisoformat
            event_timestamp_naive_or_aware = datetime.fromisoformat(ts_str_tz)
            if event_timestamp_naive_or_aware.tzinfo is None:
                # Assume naive ISO timestamp represents UTC
                utc_timestamp = event_timestamp_naive_or_aware.replace(tzinfo=timezone.utc)
            else:
                utc_timestamp = event_timestamp_naive_or_aware.astimezone(timezone.utc)
            return utc_timestamp
        except ValueError:
            logger.debug(f"Could not parse timestamp in stress log line: {line.strip()}")
            return None
    return None

# --- Monitoring Logic ---
def check_log_file(file_path: Path, parser_func_name: str):
    """Checks a single log file for timestamp anomalies."""
    if not file_path.exists():
        logger.warning(f"Monitored log file not found: {file_path}")
        return

    parser_func = globals().get(parser_func_name)
    if not parser_func:
        logger.error(f"Parser function '{parser_func_name}' not found for {file_path}")
        return

    try:
        # In a real implementation, use more efficient log reading (e.g., tracking position)
        # For simulation, read recent lines or the whole file if small
        logger.info(f"Checking log file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            # Simplified: Check last N lines or implement state tracking
            # Here, just reading all lines for simplicity in this phase
            lines = f.readlines()
            reference_time_utc = datetime.now(timezone.utc)

            for i, line in enumerate(lines):
                original_ts_str = line.strip() # Approximate original string
                event_time_utc = parser_func(line)

                if event_time_utc:
                    # Check for future skew
                    if event_time_utc > reference_time_utc + timedelta(seconds=FUTURE_SKEW_THRESHOLD_SECONDS):
                        deviation = (event_time_utc - reference_time_utc).total_seconds()
                        anomaly = {
                            "detection_timestamp_utc": reference_time_utc.isoformat(),
                            "sentinel_id": SENTINEL_ID,
                            "log_file": str(file_path),
                            "log_entry_ref": f"line_{i+1}",
                            "original_timestamp_str": original_ts_str, # Best effort original
                            "parsed_timestamp_utc": event_time_utc.isoformat(),
                            "reference_time_utc": reference_time_utc.isoformat(),
                            "deviation_seconds": deviation,
                            "anomaly_type": "FutureSkew"
                        }
                        logger.warning(f"Future skew detected in {file_path}: {deviation:.2f}s")
                        log_to_ledger(anomaly)
                    
                    # Check for staleness
                    if event_time_utc < reference_time_utc - timedelta(minutes=STALENESS_THRESHOLD_MINUTES):
                       deviation = (reference_time_utc - event_time_utc).total_seconds()
                       anomaly = {
                            "detection_timestamp_utc": reference_time_utc.isoformat(),
                            "sentinel_id": SENTINEL_ID,
                            "log_file": str(file_path),
                            "log_entry_ref": f"line_{i+1}",
                            "original_timestamp_str": original_ts_str,
                            "parsed_timestamp_utc": event_time_utc.isoformat(),
                            "reference_time_utc": reference_time_utc.isoformat(),
                            "deviation_seconds": -deviation, # Negative indicates past
                            "anomaly_type": "StaleTimestamp"
                        }
                       logger.warning(f"Stale timestamp detected in {file_path}: {deviation/60:.2f} minutes old")
                       log_to_ledger(anomaly)

    except Exception as e:
        logger.error(f"Error checking log file {file_path}: {e}", exc_info=True)

# --- Main Loop ---
def run_sentinel():
    logger.info(f"Starting Chrono Drift Sentinel ({SENTINEL_ID})... Monitoring interval: {MONITOR_INTERVAL_SECONDS}s")
    logger.info(f"UTC Fidelity Ledger: {UTC_LEDGER_FILE}")
    logger.info(f"Monitoring sources: {list(LOG_SOURCES.keys())}")
    
    # Ensure ledger file exists
    try:
        UTC_LEDGER_FILE.touch()
    except Exception as e:
         logger.error(f"Could not create or access ledger file {UTC_LEDGER_FILE}: {e}. Sentinel cannot log findings.")
         # Decide whether to exit or continue without logging
         # return 

    while True:
        logger.debug("Starting monitoring cycle.")
        for log_path_str, parser_name in LOG_SOURCES.items():
            log_file_path = project_root / log_path_str
            check_log_file(log_file_path, parser_name)
        
        logger.debug(f"Monitoring cycle complete. Sleeping for {MONITOR_INTERVAL_SECONDS} seconds.")
        time.sleep(MONITOR_INTERVAL_SECONDS)

if __name__ == "__main__":
    try:
        run_sentinel()
    except KeyboardInterrupt:
        logger.info("Chrono Drift Sentinel stopped by user.")
    except Exception as e:
        logger.critical(f"Chrono Drift Sentinel encountered a critical error: {e}", exc_info=True)
        sys.exit(1) 