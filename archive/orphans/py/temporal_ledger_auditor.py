#!/usr/bin/env python3
"""
Temporal Ledger Auditor

Periodically reviews the UTC Fidelity Ledger, summarizes anomalies over a
rolling 24-hour window, flags repeat offenders, and generates a daily
UTC drift health report.
"""

import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, DefaultDict, Dict

# --- Path Setup ---
# Assuming script is in analytics/
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# --- Configuration ---
UTC_LEDGER_FILE = project_root / "runtime" / "logs" / "utc_fidelity_ledger.log"
REPORTS_DIR = project_root / "runtime" / "reports"
REPORT_FILENAME_TEMPLATE = "utc_drift_health_{}.json"
ANALYSIS_WINDOW_HOURS = 24
ANOMALY_THRESHOLD_PER_SOURCE = 10  # Alert if > this many anomalies per source in window

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TemporalLedgerAuditor")


# --- Helper Functions ---
def parse_iso_utc(timestamp_str: str) -> Optional[datetime]:
    """Parses an ISO format string (potentially without Z) into a UTC datetime object."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            # Should not happen if ledger format is correct, but handle defensively
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        logger.warning(f"Could not parse timestamp string: {timestamp_str}")
        return None


# --- Core Logic ---
def audit_ledger():
    logger.info("Starting Temporal Ledger Audit...")

    if not UTC_LEDGER_FILE.exists():
        logger.error(f"UTC Fidelity Ledger file not found: {UTC_LEDGER_FILE}")
        return

    now_utc = datetime.now(timezone.utc)
    window_start_utc = now_utc - timedelta(hours=ANALYSIS_WINDOW_HOURS)

    # Structure: stats[log_file][anomaly_type] = count
    stats: DefaultDict[str, DefaultDict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    # Structure: latest_anomaly_ts[log_file] = latest_datetime_object
    latest_anomaly_ts: Dict[str, datetime] = {}
    # Track sentinel ID for alerting
    sentinel_ids: Dict[str, str] = {}
    total_anomalies_in_window = 0

    try:
        with open(UTC_LEDGER_FILE, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning(
                        f"Skipping malformed JSON line {i+1} in {UTC_LEDGER_FILE}"
                    )
                    continue

                detection_ts_str = entry.get("detection_timestamp_utc")
                log_file = entry.get("log_file")
                anomaly_type = entry.get("anomaly_type")
                sentinel_id = entry.get("sentinel_id", "UnknownSentinel")

                if not all([detection_ts_str, log_file, anomaly_type]):
                    logger.warning(
                        f"Skipping incomplete ledger entry on line {i+1}: {line}"
                    )
                    continue

                detection_dt = parse_iso_utc(detection_ts_str)
                if not detection_dt:
                    logger.warning(
                        f"Skipping entry with unparseable timestamp on line {i+1}"
                    )
                    continue

                # Filter by time window
                if window_start_utc < detection_dt <= now_utc:
                    total_anomalies_in_window += 1
                    stats[log_file][anomaly_type] += 1
                    sentinel_ids[log_file] = (
                        sentinel_id  # Store last seen sentinel for this source
                    )

                    # Update latest anomaly timestamp for this source
                    current_latest = latest_anomaly_ts.get(
                        log_file, datetime.min.replace(tzinfo=timezone.utc)
                    )
                    if detection_dt > current_latest:
                        latest_anomaly_ts[log_file] = detection_dt

    except Exception as e:
        logger.error(
            f"Error reading or processing ledger file {UTC_LEDGER_FILE}: {e}",
            exc_info=True,
        )
        return

    logger.info(
        f"Processed ledger. Found {total_anomalies_in_window} anomalies in the last {ANALYSIS_WINDOW_HOURS} hours."
    )

    # --- Generate Report ---
    report_data: Dict[str, Any] = {
        "report_generated_utc": now_utc.isoformat().replace("+00:00", "Z"),
        "analysis_window_start_utc": window_start_utc.isoformat().replace(
            "+00:00", "Z"
        ),
        "analysis_window_end_utc": now_utc.isoformat().replace("+00:00", "Z"),
        "total_anomalies_in_window": total_anomalies_in_window,
        "anomaly_summary_by_source": {},
    }

    alert_triggered = False
    for log_file, type_counts in stats.items():
        total_source_anomalies = sum(type_counts.values())
        threshold_exceeded = total_source_anomalies > ANOMALY_THRESHOLD_PER_SOURCE
        latest_ts = latest_anomaly_ts.get(log_file)

        report_data["anomaly_summary_by_source"][log_file] = {
            "total_anomalies": total_source_anomalies,
            "anomaly_types": dict(type_counts),
            "latest_anomaly_utc": latest_ts.isoformat().replace("+00:00", "Z")
            if latest_ts
            else None,
            "threshold_exceeded": threshold_exceeded,
        }

        # --- Check Threshold & Alert ---
        if threshold_exceeded:
            alert_triggered = True
            latest_ts_str = (
                latest_ts.isoformat().replace("+00:00", "Z") if latest_ts else "N/A"
            )
            sentinel_str = sentinel_ids.get(log_file, "UnknownSentinel")
            # Simulate logging to THEA with a high-priority log message
            logger.critical(
                f"ALERT [THEA]: UTC drift anomaly threshold exceeded for source '{log_file}' (Count: {total_source_anomalies}/{ANALYSIS_WINDOW_HOURS}h). Sentinel: {sentinel_str}. Latest Anomaly: {latest_ts_str}"
            )

    # --- Save Report ---
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_filename = REPORT_FILENAME_TEMPLATE.format(now_utc.strftime("%Y-%m-%d"))
        report_path = REPORTS_DIR / report_filename

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        logger.info(f"UTC Drift Health Report saved to: {report_path}")

    except Exception as e:
        logger.error(f"Failed to save drift health report: {e}", exc_info=True)

    if not alert_triggered:
        logger.info(
            f"No sources exceeded the anomaly threshold ({ANOMALY_THRESHOLD_PER_SOURCE}/{ANALYSIS_WINDOW_HOURS}h)."
        )

    logger.info("Temporal Ledger Audit complete.")


if __name__ == "__main__":
    try:
        audit_ledger()
    except Exception as e:
        logger.critical(
            f"Temporal Ledger Auditor encountered a critical error: {e}", exc_info=True
        )
        sys.exit(1)
