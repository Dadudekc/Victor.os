#!/usr/bin/env python3
"""
Bridge Health Report Generator

Parses extraction logs, stress test logs, and potentially agent logs to summarize
bridge uptime, extraction success rates, errors, latency, and duplicate detection.
"""

import datetime
import logging
import re
import statistics  # Added for latency calculation
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict  # Added List, Tuple

# Adjust path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Constants
EXTRACTION_LOG_FILE = project_root / "runtime" / "logs" / "thea_extraction_relay.md"
STRESS_TEST_LOG_FILE = project_root / "runtime" / "logs" / "stress_test_results.md"
# TODO: Add path to main agent log if needed for error parsing
# AGENT_LOG_FILE = project_root / "runtime" / "logs" / "thea_cursor_agent.log"
REPORT_TIMESPAN_HOURS = 24

# Logging Setup
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("BridgeHealthReport")

# Regex patterns
EXTRACTION_LOG_PATTERN = re.compile(
    r"\*\s+\*\*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\*\*\s+-\s+\*\*UUID:\*\*\s+`(.+?)`\s+-\s+\*\*Method:\*\*\s+(GUI|SCRAPER)\s+-\s+\*\*Payload:\*\*\s+`(.*?)`"
)
STRESS_RUN_HEADER_PATTERN = re.compile(
    r"^##\s+Stress\s+Test\s+Run\s+-\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+##$"
)
# Captures UUID, Latency, Notes
STRESS_RESULT_ROW_PATTERN = re.compile(
    r"^\|\s*\d+\s*\|\s*`(.+?)`\s*\|.+?\|.+?\|.+?\|.+?\|\s*(\d+|N/A)\s*\|\s*(.*?)\s*\|$"
)

# Define expected file paths (make these configurable or use AppConfig)
# Assuming standard project structure for now
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # Adjust if script moves
LOGS_DIR = PROJECT_ROOT / "runtime" / "logs"
TOOL_DIAG_SUMMARY = LOGS_DIR / "tool_diagnostics_summary.md"
BRIDGE_LOG = LOGS_DIR / "dream_os.log"  # Or a dedicated bridge log?

# --- Health Check Functions ---


def check_tool_stability() -> dict:
    """Checks the tool diagnostics summary for critical blockers."""
    report = {"status": "UNKNOWN", "details": "Tool diagnostics summary not found."}
    if not TOOL_DIAG_SUMMARY.exists():
        return report

    try:
        content = TOOL_DIAG_SUMMARY.read_text()
        # Simple checks for keywords indicating critical issues
        has_edit_blocker = (
            "BUG-EDIT-FILE-OVERWRITE-FAILURE-001" in content
            and "High Priority Blocker" in content
        )
        has_io_blocker = (
            "BUG-TOOLING-LISTDIR-READFILE-TIMEOUT-001" in content
            and "High Priority Blocker" in content
        )

        # --- EDIT START: Escalate Edit File Corruption Risk --- #
        is_corruption_risk_flagged = (
            "file corruption risk" in content.lower()
        )  # Check if already noted

        if has_edit_blocker and not is_corruption_risk_flagged:
            # This check adds the explicit note if the blocker is present but risk isn't mentioned
            report["status"] = "CRITICAL_RISK"
            report["details"] = (
                "High priority edit_file blocker (BUG-EDIT-FILE-OVERWRITE-FAILURE-001) detected. **IMMEDIATE FILE CORRUPTION RISK.** Needs urgent investigation."
            )
            # Log escalation
            logger.critical(
                "ESCALATION: edit_file overwrite failures pose immediate file corruption risk!"
            )
        elif has_edit_blocker and is_corruption_risk_flagged:
            report["status"] = "ERROR"
            report["details"] = (
                "High priority edit_file blocker (BUG-EDIT-FILE-OVERWRITE-FAILURE-001) persists, file corruption risk noted."
            )
        # --- EDIT END --- #
        elif has_io_blocker:
            report["status"] = "ERROR"
            report["details"] = (
                "High priority file I/O blocker (BUG-TOOLING-LISTDIR-READFILE-TIMEOUT-001) detected."
            )
        elif "Blocker" in content:  # General check
            report["status"] = "WARNING"
            report["details"] = (
                "Potential tool blockers identified in diagnostics summary. Review needed."
            )
        else:
            report["status"] = "OK"
            report["details"] = "No critical tool blockers found in summary."

    except Exception as e:
        logger.error(f"Error checking tool diagnostics summary: {e}")
        report["status"] = "ERROR"
        report["details"] = f"Failed to parse tool diagnostics summary: {e}"

    return report


def check_bridge_logs() -> dict:
    """Placeholder: Checks bridge-specific logs for errors or timeouts."""
    # In a real implementation:
    # - Read BRIDGE_LOG or dedicated logs
    # - Grep for error messages, timeouts, exceptions related to bridge components
    # - Calculate success/failure rates if possible
    logger.warning("Bridge log checking not fully implemented.")
    return {"status": "UNKNOWN", "details": "Bridge log analysis not implemented."}


def check_component_availability() -> dict:
    """Placeholder: Checks if required bridge components/files exist."""
    # Example checks:
    # - Check if cursor_injector.py, response_retriever.py exist
    # - Check if coordinate files exist
    logger.warning("Bridge component availability check not fully implemented.")
    return {
        "status": "UNKNOWN",
        "details": "Component availability check not implemented.",
    }


# --- Main Report Generation ---


def generate_report() -> dict:
    """Generates the overall bridge health report."""
    report = {
        "report_generated_utc": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        "overall_status": "UNKNOWN",
        "checks": {},
    }

    checks_results = {
        "tool_stability": check_tool_stability(),
        "bridge_logs": check_bridge_logs(),
        "component_availability": check_component_availability(),
    }

    report["checks"] = checks_results

    # Determine overall status based on individual checks
    if any(check["status"] == "CRITICAL_RISK" for check in checks_results.values()):
        report["overall_status"] = "CRITICAL_RISK"
    elif any(check["status"] == "ERROR" for check in checks_results.values()):
        report["overall_status"] = "ERROR"
    elif any(check["status"] == "WARNING" for check in checks_results.values()):
        report["overall_status"] = "WARNING"
    elif all(check["status"] == "OK" for check in checks_results.values()):
        report["overall_status"] = "OK"
    # Otherwise remains UNKNOWN

    return report


def parse_extraction_log(timespan_hours: int) -> Dict[str, Any]:  # Return type changed
    """Parses the extraction log for events within the timespan."""
    stats = {
        "success_counts": Counter(),  # Method -> count
        "total_extractions": 0,
    }
    now = datetime.now()
    cutoff_time = now - timedelta(hours=timespan_hours)

    if not EXTRACTION_LOG_FILE.exists():
        logger.warning(f"Extraction log file not found: {EXTRACTION_LOG_FILE}")
        return stats

    try:
        with open(EXTRACTION_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                match = EXTRACTION_LOG_PATTERN.match(line.strip())
                if match:
                    timestamp_str, uuid_str, method, payload = match.groups()
                    try:
                        log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        if log_time >= cutoff_time:
                            stats["success_counts"][method.upper()] += 1
                            stats["total_extractions"] += 1
                    except ValueError:
                        logger.warning(
                            f"Could not parse timestamp in extraction log line: {line.strip()}"
                        )
    except Exception as e:
        logger.error(
            f"Error reading or parsing {EXTRACTION_LOG_FILE}: {e}", exc_info=True
        )

    return stats


def parse_stress_test_data(timespan_hours: int) -> Dict[str, Any]:
    """Parses the stress test log for latency values and duplicate notes within the timespan."""
    results = {"latencies_ms": [], "duplicate_skips": 0, "runs_parsed": 0}
    now = datetime.now()
    cutoff_time = now - timedelta(hours=timespan_hours)

    if not STRESS_TEST_LOG_FILE.exists():
        logger.warning(f"Stress test results file not found: {STRESS_TEST_LOG_FILE}")
        return results

    try:
        with open(STRESS_TEST_LOG_FILE, "r", encoding="utf-8") as f:
            in_relevant_run = False
            run_count_in_period = 0
            for line in f:
                line = line.strip()
                header_match = STRESS_RUN_HEADER_PATTERN.match(line)
                if header_match:
                    ts_str = header_match.group(1)
                    try:
                        ts_str = ts_str.replace("Z", "+00:00").split(".")[0]
                        run_timestamp = datetime.fromisoformat(ts_str)
                        in_relevant_run = run_timestamp >= cutoff_time
                        if in_relevant_run:
                            run_count_in_period += 1
                    except ValueError:
                        in_relevant_run = False
                    continue

                if in_relevant_run and line.startswith("|"):
                    result_match = STRESS_RESULT_ROW_PATTERN.match(line)
                    if result_match:
                        uuid_str, latency_ms_str, notes_str = result_match.groups()
                        if latency_ms_str.isdigit():
                            results["latencies_ms"].append(int(latency_ms_str))
                        if "duplicate content detected" in notes_str.lower():
                            results["duplicate_skips"] += 1
        results["runs_parsed"] = run_count_in_period
    except Exception as e:
        logger.error(
            f"Error reading or parsing {STRESS_TEST_LOG_FILE}: {e}", exc_info=True
        )

    logger.info(
        f"Parsed {len(results['latencies_ms'])} latencies and {results['duplicate_skips']} duplicate skips from {results['runs_parsed']} stress runs in the period."
    )
    return results


def parse_agent_errors(timespan_hours: int) -> int:
    """Parses agent logs for error counts within the timespan (Placeholder)."""
    # TODO: Implement actual error parsing from the main agent log file
    # This would involve defining AGENT_LOG_FILE and searching for ERROR/CRITICAL messages
    logger.warning("Agent error parsing is not yet implemented.")
    return 0  # Placeholder


def calculate_uptime() -> str:
    """Calculates agent uptime (Placeholder)."""
    # TODO: Implement uptime tracking
    # Option 1: Read a start time from a file created when the agent starts.
    # Option 2: Assume 'always up' if this script runs (less accurate).
    # Option 3: Query a process manager if available.
    logger.warning("Uptime calculation is not yet implemented.")
    return "Unknown"  # Placeholder


def generate_report():
    """Generates and prints the health report."""
    logger.info(
        f"Generating Bridge Health Report (Last {REPORT_TIMESPAN_HOURS} hours)..."
    )

    uptime = calculate_uptime()
    extraction_stats = parse_extraction_log(REPORT_TIMESPAN_HOURS)
    stress_data = parse_stress_test_data(REPORT_TIMESPAN_HOURS)
    error_count = parse_agent_errors(REPORT_TIMESPAN_HOURS)

    total_extractions = extraction_stats["total_extractions"]
    gui_success = extraction_stats["success_counts"]["GUI"]
    scraper_success = extraction_stats["success_counts"]["SCRAPER"]

    latency_values_ms = stress_data["latencies_ms"]
    duplicate_skips = stress_data["duplicate_skips"]

    # Calculate latency stats
    avg_latency_ms: Optional[float] = None
    max_latency_ms: Optional[int] = None
    if latency_values_ms:
        try:
            avg_latency_ms = statistics.mean(latency_values_ms)
            max_latency_ms = max(latency_values_ms)
        except statistics.StatisticsError:
            logger.warning("Could not calculate latency statistics (empty list?).")
        except Exception as e:
            logger.error(f"Error calculating latency statistics: {e}")

    # Using standard ASCII and correct newline escapes
    print("\n--- Bridge Health Report ---")
    print(f"Report Period: Last {REPORT_TIMESPAN_HOURS} hours")
    print(f"Agent Uptime: {uptime}")

    print("\nExtraction Summary:")
    print(f"  Total Successful Extractions: {total_extractions}")
    print(f"    - GUI Method: {gui_success} successes")
    print(f"    - Scraper Method: {scraper_success} successes")
    print(
        "  (Note: Success rates require logging attempts, currently showing success counts)"
    )

    print("\nLatency & Stress Test Summary (from recent runs):")
    print(f"  Stress Test Runs Analyzed: {stress_data['runs_parsed']}")
    if avg_latency_ms is not None and max_latency_ms is not None:
        print(f"  Average Extraction-to-Injection Latency: {avg_latency_ms:.0f} ms")
        print(f"  Maximum Extraction-to-Injection Latency: {max_latency_ms} ms")
    else:
        print("  Latency data not available.")
    print(f"  Duplicate Skips Recorded (Stress Test): {duplicate_skips}")

    print("\nError Summary:")
    print(f"  Agent Errors Logged: {error_count}")
    print("  (Note: Requires implementation of agent error log parsing)")
    print("----------------------------\n")


if __name__ == "__main__":
    generate_report()
