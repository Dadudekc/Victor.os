#!/usr/bin/env python3
"""
Analyze Latency Trends from Bridge Stress Tests

Parses stress test result logs to calculate latency statistics over time
and flags potential regressions.
"""

import logging
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# --- Path Setup ---
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# --- Constants ---
STRESS_TEST_LOG_FILE = project_root / "runtime" / "logs" / "stress_test_results.md"
LATENCY_REGRESSION_THRESHOLD_PERCENT = 15.0  # Flag if weekly avg increases > 15%
# Define how many past runs to compare (e.g., compare latest to average of previous N)
COMPARISON_WINDOW_RUNS = 5

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("LatencyTrendAnalyzer")

# --- Regex Patterns ---
RUN_HEADER_PATTERN = re.compile(
    r"^##\s+Stress\s+Test\s+Run\s+-\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+##$"
)
RESULT_ROW_PATTERN = re.compile(
    r"^\|\s*\d+\s*\|\s*`(.+?)`\s*\|.+?\|.+?\|.+?\|.+?\|\s*(\d+)\s*\|.*?\|$"
)  # Extracts UUID (1) and Latency (2)


# --- Data Structures ---
class StressRunStats:
    def __init__(self, timestamp: datetime):
        self.timestamp = timestamp
        self.latencies_ms: List[int] = []
        self.average_latency_ms: Optional[float] = None
        self.max_latency_ms: Optional[int] = None

    def calculate_stats(self):
        if not self.latencies_ms:
            return
        try:
            self.average_latency_ms = statistics.mean(self.latencies_ms)
            self.max_latency_ms = max(self.latencies_ms)
        except statistics.StatisticsError:
            logger.warning(
                f"Could not calculate latency stats for run {self.timestamp} (empty list?)."
            )
        except Exception as e:
            logger.error(
                f"Error calculating latency stats for run {self.timestamp}: {e}"
            )


# --- Parsing Logic ---
def parse_stress_logs() -> List[StressRunStats]:
    """Parses all stress test runs from the log file."""
    runs: List[StressRunStats] = []
    current_run: Optional[StressRunStats] = None

    if not STRESS_TEST_LOG_FILE.exists():
        logger.error(f"Stress test log file not found: {STRESS_TEST_LOG_FILE}")
        return runs

    try:
        with open(STRESS_TEST_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                header_match = RUN_HEADER_PATTERN.match(line)
                if header_match:
                    # Finalize stats for the previous run before starting a new one
                    if current_run:
                        current_run.calculate_stats()
                        runs.append(current_run)

                    # Start a new run
                    ts_str = header_match.group(1)
                    try:
                        # Handle optional Z and fractional seconds
                        ts_str = ts_str.replace("Z", "+00:00").split(".")[0]
                        run_timestamp = datetime.fromisoformat(ts_str)
                        current_run = StressRunStats(timestamp=run_timestamp)
                        logger.debug(f"Found stress run header: {run_timestamp}")
                    except ValueError:
                        logger.warning(
                            f"Could not parse timestamp from run header: {line}"
                        )
                        current_run = None  # Skip this run if header TS is bad
                elif current_run and line.startswith("|"):
                    result_match = RESULT_ROW_PATTERN.match(line)
                    if result_match:
                        uuid_str, latency_ms_str = result_match.groups()
                        if latency_ms_str.isdigit():
                            current_run.latencies_ms.append(int(latency_ms_str))

            # Finalize the last run in the file
            if current_run:
                current_run.calculate_stats()
                runs.append(current_run)

    except Exception as e:
        logger.error(
            f"Error reading or parsing {STRESS_TEST_LOG_FILE}: {e}", exc_info=True
        )

    # Sort runs by timestamp, most recent first
    runs.sort(key=lambda r: r.timestamp, reverse=True)
    logger.info(f"Parsed data for {len(runs)} stress test runs.")
    return runs


# --- Analysis Logic ---
def analyze_latency_trends(runs: List[StressRunStats]):
    """Analyzes latency trends and flags regressions."""
    if len(runs) < 2:
        logger.info("Insufficient data for trend analysis (need at least 2 runs).")
        return

    latest_run = runs[0]
    previous_runs = runs[1 : 1 + COMPARISON_WINDOW_RUNS]  # Get up to N previous runs

    if not previous_runs:
        logger.info("No previous runs found within the comparison window.")
        return

    if latest_run.average_latency_ms is None:
        logger.warning(
            "Latest run has no average latency data, cannot perform trend analysis."
        )
        return

    # Calculate average latency of the previous window
    previous_latencies = [
        r.average_latency_ms for r in previous_runs if r.average_latency_ms is not None
    ]
    if not previous_latencies:
        logger.info("Previous runs in the window have no average latency data.")
        return

    previous_avg_latency = statistics.mean(previous_latencies)

    # Compare latest run average to previous window average
    percent_increase = (
        (latest_run.average_latency_ms - previous_avg_latency) / previous_avg_latency
    ) * 100

    logger.info(
        f"Latest Run Avg Latency ({latest_run.timestamp.date()}): {latest_run.average_latency_ms:.0f} ms"
    )
    logger.info(
        f"Previous Window Avg Latency (Last {len(previous_runs)} runs): {previous_avg_latency:.0f} ms"
    )
    logger.info(f"Percentage Change: {percent_increase:+.1f}%")

    if percent_increase > LATENCY_REGRESSION_THRESHOLD_PERCENT:
        logger.warning(
            f"LATENCY REGRESSION DETECTED: Average latency increased by {percent_increase:.1f}% (Threshold: >{LATENCY_REGRESSION_THRESHOLD_PERCENT:.1f}%)"
        )
    else:
        logger.info("Latency trend within acceptable threshold.")

    # Basic Charting Placeholder (requires libraries like matplotlib/seaborn)
    print("\n--- Latency Trend (Placeholder Chart) ---")
    print("Timestamp           | Avg Latency (ms) | Max Latency (ms)")
    print("--------------------|------------------|-----------------")
    # Print data for the last few runs (e.g., 10)
    for run in reversed(runs[:10]):  # Show oldest first
        avg_str = (
            f"{run.average_latency_ms:.0f}"
            if run.average_latency_ms is not None
            else "N/A"
        )
        max_str = str(run.max_latency_ms) if run.max_latency_ms is not None else "N/A"
        print(
            f"{run.timestamp.strftime('%Y-%m-%d %H:%M')} | {avg_str:>16} | {max_str:>15}"
        )
    print("--------------------------------------------------------")
    print(
        "(Note: This is a basic text representation. Implement charting for visualization.)"
    )
    print("--------------------------------------------------------\n")


# --- Main Execution ---
if __name__ == "__main__":
    logger.info("Starting Latency Trend Analysis...")
    all_runs = parse_stress_logs()
    if all_runs:
        analyze_latency_trends(all_runs)
    else:
        logger.info("No stress test run data found to analyze.")
    logger.info("Latency Trend Analysis finished.")
