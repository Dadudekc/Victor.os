#!/usr/bin/env python3
"""
Bridge Fault Inspector

Analyzes health reports, stress test results, and potentially other logs
to identify correlated failure patterns (e.g., high latency + duplicates).
"""

import logging
import re
import sys
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any, Dict, List, Optional

# --- Path Setup ---
# Assuming script is in runtime/analytics
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# --- Constants ---
HEALTH_REPORT_SCRIPT = (
    project_root / "scripts" / "bridge_health_report.py"
)  # To potentially import parsing logic
STRESS_TEST_LOG_FILE = project_root / "runtime" / "logs" / "stress_test_results.md"
INTEGRITY_LOG_FILE = project_root / "runtime" / "logs" / "bridge_integrity_monitor.md"
# TODO: Add paths to other relevant logs (e.g., main agent log)
ANALYSIS_TIMESPAN_HOURS = 72  # Look back 3 days for patterns
LATENCY_SPIKE_THRESHOLD_MS = 1000  # Define what constitutes a spike (e.g., > 1 second)
CORRELATION_WINDOW_SECONDS = 60  # Look for other events within 60s of a primary event

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("BridgeFaultInspector")

# --- Regex Patterns ---
STRESS_RUN_HEADER_PATTERN = re.compile(
    r"^##\s+Stress\s+Test\s+Run\s+-\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+##$"
)
# Captures UUID, Start Timestamp, Latency, Notes
STRESS_RESULT_ROW_PATTERN = re.compile(
    r"^\|\s*\d+\s*\|\s*`(.+?)`\s*\|\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)\s*\|.+?\|.+?\|.+?\|\s*(\d+|N/A)\s*\|\s*(.*?)\s*\|$"
)
INTEGRITY_LOG_PATTERN = re.compile(
    r"\*\s+\*\*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\*\*\s+-\s+\*\*Check:\*\*\s+`(.+?)`\s+-\s+\*\*Status:\*\*\s+(FAIL|WARN)\s+-\s+\*\*Details:\*\*(.+)"
)

# --- Data Parsing (Placeholders/Simplified) ---
# In a full implementation, might reuse/refactor parsing from other scripts


def get_local_tz() -> Optional[tzinfo]:
    """Safely retrieves the local system's timezone."""
    try:
        # Attempt to get local timezone information
        return datetime.now().astimezone().tzinfo
    except Exception as e:
        # Handle cases where local timezone cannot be determined (rare)
        logger.error(
            f"Could not determine local timezone: {e}. Timestamps might not be localized correctly.",
            exc_info=True,
        )
        return None


def parse_stress_results(timespan_hours: int) -> List[Dict[str, Any]]:
    """
    Parses stress results, focusing on timestamps, latency, and duplicate notes.
    Ensures all timestamps are timezone-aware and normalized to UTC.
    """
    results = []
    now = datetime.now(timezone.utc)  # Use UTC for comparison
    cutoff_time = now - timedelta(hours=timespan_hours)

    if not STRESS_TEST_LOG_FILE.exists():
        logger.warning(f"Stress test log file not found: {STRESS_TEST_LOG_FILE}")
        return results

    try:  # Outer try for file operations
        with open(STRESS_TEST_LOG_FILE, "r", encoding="utf-8") as f:
            current_run_timestamp: Optional[datetime] = None
            for line in f:
                line = line.strip()
                header_match = STRESS_RUN_HEADER_PATTERN.match(line)
                if header_match:
                    ts_str = header_match.group(1).replace("Z", "+00:00").split(".")[0]
                    try:  # Inner try for header timestamp parsing
                        current_run_timestamp = datetime.fromisoformat(ts_str)
                        # Ensure run timestamp is UTC aware for comparison
                        if current_run_timestamp.tzinfo is None:
                            current_run_timestamp = current_run_timestamp.replace(
                                tzinfo=timezone.utc
                            )
                        else:
                            current_run_timestamp = current_run_timestamp.astimezone(
                                timezone.utc
                            )
                    except ValueError:
                        current_run_timestamp = (
                            None  # Ignore rows until next valid header
                        )
                    continue

                # Check timestamp AFTER potentially setting it above
                if current_run_timestamp and current_run_timestamp < cutoff_time:
                    continue  # Skip runs outside the timespan

                if line.startswith("|"):
                    result_match = STRESS_RESULT_ROW_PATTERN.match(line)
                    if result_match:
                        uuid_str, ts_str, latency_ms_str, notes_str = (
                            result_match.groups()
                        )
                        latency_ms = (
                            int(latency_ms_str) if latency_ms_str.isdigit() else None
                        )
                        is_duplicate_skip = (
                            "duplicate content detected" in notes_str.lower()
                        )
                        try:  # Inner try for result row timestamp parsing
                            # Ensure timestamp has timezone info and convert to UTC
                            event_timestamp_naive_or_aware = datetime.fromisoformat(
                                ts_str.replace("Z", "+00:00")
                            )

                            # If the timestamp is naive, assume UTC (ISO standard implies this if no offset)
                            # If it has an offset, convert it to UTC
                            if event_timestamp_naive_or_aware.tzinfo is None:
                                event_timestamp_utc = (
                                    event_timestamp_naive_or_aware.replace(
                                        tzinfo=timezone.utc
                                    )
                                )
                                logger.debug(
                                    f"Assumed UTC for naive ISO timestamp: {ts_str}"
                                )
                            else:
                                event_timestamp_utc = (
                                    event_timestamp_naive_or_aware.astimezone(
                                        timezone.utc
                                    )
                                )

                            results.append(
                                {
                                    "timestamp": event_timestamp_utc,  # Store UTC timestamp
                                    "uuid": uuid_str,
                                    "latency_ms": latency_ms,
                                    "is_duplicate_skip": is_duplicate_skip,
                                    "notes": notes_str,
                                }
                            )
                        except ValueError:
                            logger.warning(
                                f"Could not parse timestamp in stress result row: {line}"
                            )
    except Exception as e:  # Catch file operation errors
        logger.error(f"Error parsing {STRESS_TEST_LOG_FILE}: {e}", exc_info=True)

    logger.info(f"Parsed {len(results)} stress test result entries within timespan.")
    # Sort by timestamp ascending for easier window analysis
    results.sort(key=lambda x: x["timestamp"])
    return results


def parse_integrity_logs(timespan_hours: int) -> List[Dict[str, Any]]:
    """
    Parses integrity monitor logs, converting local timestamps to UTC.
    Assumes timestamps in the log file are in the system's local timezone if naive.
    Returns timestamps as timezone-aware datetime objects normalized to UTC.
    """
    results = []
    now = datetime.now(timezone.utc)  # Use aware datetime for now
    cutoff_time = now - timedelta(hours=timespan_hours)
    local_tz = get_local_tz()  # Get local timezone once

    if not INTEGRITY_LOG_FILE.exists():
        logger.warning(f"Integrity log file not found: {INTEGRITY_LOG_FILE}")
        return results

    try:  # Outer try for file operations
        with open(INTEGRITY_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                match = INTEGRITY_LOG_PATTERN.match(line.strip())
                if match:
                    ts_str, check_name, status, details = match.groups()
                    try:  # Inner try for timestamp parsing
                        # Parse as naive timestamp
                        naive_timestamp = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")

                        # Make timestamp aware: Assume local timezone if determinable, otherwise UTC
                        if local_tz:
                            aware_timestamp = naive_timestamp.replace(tzinfo=local_tz)
                        else:
                            # Fallback: Assume UTC if local timezone is unknown
                            aware_timestamp = naive_timestamp.replace(
                                tzinfo=timezone.utc
                            )
                            logger.warning(
                                f"Could not determine local timezone for {ts_str}, assuming UTC."
                            )

                        # Convert to UTC for consistency
                        utc_timestamp = aware_timestamp.astimezone(timezone.utc)

                        if utc_timestamp >= cutoff_time:
                            results.append(
                                {
                                    "timestamp": utc_timestamp,  # Store aware UTC timestamp
                                    "check": check_name.strip(),
                                    "status": status.strip(),
                                    "details": details.strip(),
                                }
                            )
                    except ValueError:
                        logger.warning(
                            f"Could not parse timestamp in integrity log: {line.strip()}"
                        )
    except Exception as e:  # Catch file operation errors
        logger.error(f"Error parsing {INTEGRITY_LOG_FILE}: {e}", exc_info=True)

    logger.info(f"Parsed {len(results)} integrity log entries within timespan.")
    results.sort(key=lambda x: x["timestamp"])
    return results


def parse_agent_logs(timespan_hours: int) -> List[Dict[str, Any]]:
    """Simplified parser for main agent logs."""
    results = []
    # TODO: Implement parsing logic for the main bridge agent's log file
    logger.warning("Main agent log parsing not fully implemented in fault inspector.")
    # Example structure: [{'timestamp': datetime, 'level': str, 'message': str}, ...]
    return results


# --- Correlation Logic (Placeholders) ---
def find_latency_spikes_near_duplicates(
    stress_data: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Finds latency spikes occurring near duplicate skip events."""


def find_failure_patterns(stress_data, integrity_data, agent_data) -> List[str]:
    """Identifies potential correlated failure patterns."""
    patterns = []
    logger.info("Analyzing data for failure patterns...")

    # Example Pattern 1: High Latency correlating with Integrity Failures
    # TODO: Implement actual correlation logic
    # - Find time windows with high average latency from stress_data
    # - Check if integrity_data shows FAILs in those windows
    # - Check if agent_data shows specific errors in those windows
    pattern1_found = False  # Placeholder
    if pattern1_found:
        patterns.append(
            "Correlation found: High latency spikes coincide with configuration integrity failures."
        )

    # Example Pattern 2: Duplicate skips correlating with specific agent errors
    # TODO: Implement actual correlation logic
    pattern2_found = False  # Placeholder
    if pattern2_found:
        patterns.append(
            "Correlation found: Duplicate content skips correlate with [Specific Agent Error Message]."
        )

    if not patterns:
        logger.info(
            "No obvious correlated failure patterns found in the analyzed period."
        )
    else:
        logger.warning(f"Potential failure patterns identified: {len(patterns)}")

    return patterns


# --- Main Execution ---
if __name__ == "__main__":
    logger.info("Starting Bridge Fault Inspector...")

    # Parse data from logs
    stress_results = parse_stress_results(ANALYSIS_TIMESPAN_HOURS)
    integrity_results = parse_integrity_logs(ANALYSIS_TIMESPAN_HOURS)
    agent_log_results = parse_agent_logs(ANALYSIS_TIMESPAN_HOURS)

    # Analyze for patterns
    identified_patterns = find_failure_patterns(
        stress_results, integrity_results, agent_log_results
    )

    # Report findings
    print("\n--- Bridge Fault Inspector Report ---")
    print(f"Analysis Period: Last {ANALYSIS_TIMESPAN_HOURS} hours")
    if identified_patterns:
        print("Potential Correlated Failure Patterns Detected:")
        for i, pattern in enumerate(identified_patterns):
            print(f"  {i+1}. {pattern}")
    else:
        print("No significant correlated failure patterns were identified.")
    print("-------------------------------------\n")

    logger.info("Bridge Fault Inspector finished.")
