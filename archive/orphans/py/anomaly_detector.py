import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# --- Configuration ---
INPUT_LOG_FILE = "env_telemetry_stream.md"
OUTPUT_REPORT_FILE = "env_drift_diagnostics.json"
TEMP_THRESHOLD_CELSIUS = 2.0  # Degrees C change considered an anomaly
HUMIDITY_THRESHOLD_PERCENT = 10.0  # % change considered an anomaly

# === MODULE 1: Timestamp Normalization ===


class TimestampNormalizer:
    """Handles parsing and normalization of various timestamp formats to UTC datetime objects."""

    @staticmethod
    def normalize(ts_string: str) -> Optional[datetime]:
        """Attempts to parse a timestamp string using multiple known formats."""
        parsers = [
            TimestampNormalizer._try_unix,
            TimestampNormalizer._try_iso_format,
            TimestampNormalizer._try_log_format,
        ]

        for parser in parsers:
            result = parser(ts_string)
            if result:
                return result
        return None  # Failed all parsers

    @staticmethod
    def _try_unix(ts_string: str) -> Optional[datetime]:
        try:
            unix_ts = float(ts_string)
            return datetime.fromtimestamp(unix_ts, tz=timezone.utc)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _try_iso_format(ts_string: str) -> Optional[datetime]:
        try:
            if ts_string.endswith("Z"):
                ts_string = ts_string[:-1] + "+00:00"
            dt_obj = datetime.fromisoformat(ts_string)
            return dt_obj.astimezone(timezone.utc)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _try_log_format(ts_string: str) -> Optional[datetime]:
        possible_formats = [
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S,%f",
            "%Y-%m-%d %H:%M:%S",
        ]
        for fmt in possible_formats:
            try:
                dt_obj = datetime.strptime(ts_string, fmt)
                # CRITICAL ASSUMPTION: Treat as UTC if no offset info
                return dt_obj.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
        return None


# === MODULE 2: Telemetry Data Parsing ===


class TelemetryParser:
    """Parses raw log lines into structured telemetry records."""

    @staticmethod
    def parse_line(
        line_num: int, line: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Parses a single log line procedurally. Returns (record, error)."""
        line_content = line.split("#")[0].strip()  # Remove comments first

        # Skip headers, comments, empty lines
        if (
            not line_content
            or line_content.startswith("##")
            or line_content.startswith("---")
            or "Timestamp," in line_content
        ):
            return None, None  # Skip silently

        # // EDIT START: Procedural parsing based on splitting by comma
        parts = [
            p.strip() for p in line_content.split(",")
        ]  # Split and strip whitespace

        if len(parts) < 3:
            # Not enough parts for TS, Temp, Humidity
            error = {
                "line": line_num,
                "issue": "Malformed line, expected at least 3 CSV parts",
                "raw_line": line,
            }
            return None, error

        # Assume last two parts are humidity and temperature
        humidity_str = parts[-1]
        temp_str = parts[-2]
        # Reconstruct timestamp string from remaining parts
        raw_timestamp = ",".join(parts[:-2]).strip()

        try:
            temp = float(temp_str)
            humidity = float(humidity_str)
        # // EDIT END
        except ValueError:
            # Handle case where temp/humidity parts are not numeric
            error = {
                "line": line_num,
                "issue": "Failed to parse temperature or humidity as float",
                "parsed_temp_str": temp_str,
                "parsed_humidity_str": humidity_str,
                "raw_line": line,
            }
            return None, error
        except IndexError:  # Should be caught by len(parts) < 3, but for safety
            error = {
                "line": line_num,
                "issue": "Indexing error during parsing, likely < 3 parts",
                "raw_line": line,
            }
            return None, error

        # Normalize timestamp using the dedicated class
        normalized_dt = TimestampNormalizer.normalize(raw_timestamp)

        record = {
            "line": line_num,
            "raw_timestamp": raw_timestamp,
            "normalized_utc_dt": normalized_dt,  # Store as datetime object
            "normalized_utc_str": normalized_dt.isoformat() if normalized_dt else None,
            "temperature_c": temp,
            "humidity_percent": humidity,
            "raw_line": line,  # Keep original line in record
        }

        if normalized_dt is None:
            error = {
                "line": line_num,
                "issue": "Timestamp parsing failed",
                "raw_timestamp": raw_timestamp,
            }
            # Return the record *and* the timestamp error
            return record, error

        return record, None  # Record parsed successfully, no error


# === MODULE 3: Anomaly Detection ===


class AnomalyDetector:
    """Identifies environmental shifts and timestamp inconsistencies."""

    def __init__(self, temp_threshold: float, humidity_threshold: float):
        self.temp_threshold = temp_threshold
        self.humidity_threshold = humidity_threshold
        self.timestamp_issues = []
        self.env_anomalies = []
        self.last_valid_record = None

    def check_record(self, record: Dict[str, Any]):
        """Checks a single parsed record for anomalies against the previous one."""
        # Timestamp check already handled if record["normalized_utc_dt"] is None
        # So we only proceed if the current timestamp is valid.
        if record["normalized_utc_dt"] is None:
            self.last_valid_record = None  # Reset comparison baseline
            return

        if self.last_valid_record and self.last_valid_record["normalized_utc_dt"]:
            last_dt = self.last_valid_record["normalized_utc_dt"]
            current_dt = record["normalized_utc_dt"]

            # 1. Check non-monotonic timestamps
            if current_dt < last_dt:
                self.timestamp_issues.append(
                    {
                        "line": record["line"],
                        "issue": "Timestamp out of order (non-monotonic)",
                        "current_timestamp": current_dt.isoformat(),
                        "previous_timestamp": last_dt.isoformat(),
                    }
                )

            # 2. Check environmental anomalies
            temp_diff = abs(
                record["temperature_c"] - self.last_valid_record["temperature_c"]
            )
            humidity_diff = abs(
                record["humidity_percent"] - self.last_valid_record["humidity_percent"]
            )

            if temp_diff > self.temp_threshold:
                self.env_anomalies.append(
                    {
                        "line": record["line"],
                        "type": "Temperature Shift",
                        "current_value": record["temperature_c"],
                        "previous_value": self.last_valid_record["temperature_c"],
                        "change": round(temp_diff, 3),
                        "threshold": self.temp_threshold,
                    }
                )

            if humidity_diff > self.humidity_threshold:
                self.env_anomalies.append(
                    {
                        "line": record["line"],
                        "type": "Humidity Shift",
                        "current_value": record["humidity_percent"],
                        "previous_value": self.last_valid_record["humidity_percent"],
                        "change": round(humidity_diff, 3),
                        "threshold": self.humidity_threshold,
                    }
                )

        # Update last valid record for next comparison
        self.last_valid_record = record

    def get_results(self) -> Dict[str, List[Dict[str, Any]]]:
        """Returns the collected anomalies and issues."""
        return {
            "timestamp_issues": self.timestamp_issues,
            "environment_anomalies": self.env_anomalies,
        }


# === MODULE 4: Orchestration and Reporting ===


class TelemetryAnalyzer:
    """Orchestrates parsing, analysis, and reporting."""

    def __init__(
        self,
        input_path: str,
        output_path: str,
        summary_output_path: str,
        temp_thresh: float,
        humid_thresh: float,
    ):
        self.input_path = input_path
        self.output_path = output_path
        self.summary_output_path = summary_output_path
        self.parser = TelemetryParser()
        self.detector = AnomalyDetector(temp_thresh, humid_thresh)
        self.all_records = []
        self.all_parse_errors = []
        self.max_temp_deviation = 0.0

    def run_analysis(self) -> bool:
        """Executes the full analysis pipeline."""
        print(f"Analyzing telemetry data from: {self.input_path}")
        try:
            with open(self.input_path, "r") as f:
                lines_processed_count = 0  # Count relevant lines processed
                for i, line in enumerate(f):
                    line_num = i + 1
                    record, error = self.parser.parse_line(line_num, line)

                    # Skip lines that parse_line ignores (comments, headers etc)
                    if record is None and error is None:
                        continue

                    lines_processed_count += 1

                    if error:
                        self.all_parse_errors.append(error)
                        if record:
                            self.all_records.append(record)
                            self.detector.check_record(record)
                    elif record:
                        self.all_records.append(record)
                        self.detector.check_record(record)

            analysis_results = self.detector.get_results()
            all_timestamp_issues = (
                self.all_parse_errors + analysis_results["timestamp_issues"]
            )
            env_anomalies = analysis_results["environment_anomalies"]

            # Calculate max temp deviation for summary
            for anomaly in env_anomalies:
                if anomaly["type"] == "Temperature Shift":
                    self.max_temp_deviation = max(
                        self.max_temp_deviation, anomaly["change"]
                    )

            print(f"Analysis complete. Writing full report to: {self.output_path}")
            self._generate_report(all_timestamp_issues, env_anomalies)
            print("Full report generated successfully.")

            # Generate summary report
            print(f"Generating summary report: {self.summary_output_path}")
            self._generate_summary_report(
                all_timestamp_issues, env_anomalies, lines_processed_count
            )
            print("Summary report generated successfully.")
            return True

        except FileNotFoundError:
            print(f"Error: Input log file not found at {self.input_path}")
            return False
        except Exception as e:
            print(f"Error during analysis or reporting: {e}")
            return False

    def _generate_report(self, timestamp_issues: List[Dict], env_anomalies: List[Dict]):
        """Creates the final detailed JSON report file."""
        summary = {
            "total_timestamp_issues": len(timestamp_issues),
            "total_environment_anomalies": len(env_anomalies),
            "potential_drift_zones (lines with parse failures or non-monotonic)": sorted(
                list(set([item["line"] for item in timestamp_issues if "line" in item]))
            ),
        }

        # Convert datetime objects back to strings for JSON serialization in records
        serializable_records = []
        for rec in self.all_records:
            # Shallow copy is fine here
            s_rec = rec.copy()
            # Replace datetime object with its string representation
            s_rec["normalized_utc_dt"] = None  # Remove dt object
            serializable_records.append(s_rec)

        report_data = {
            "analysis_summary": summary,
            "details": {
                "timestamp_issues": timestamp_issues,
                "environment_anomalies": env_anomalies,
            },
            # "processed_records": serializable_records # Optional: include all processed records
        }

        try:
            with open(self.output_path, "w") as f:
                json.dump(report_data, f, indent=4)
        except IOError as e:
            print(f"Error writing report file {self.output_path}: {e}")
            raise  # Re-raise exception to be caught by run_analysis

    def _generate_summary_report(
        self,
        timestamp_issues: List[Dict],
        env_anomalies: List[Dict],
        processed_line_count: int,
    ):
        """Creates the simplified JSON summary report file."""
        total_timestamp_errors = len(timestamp_issues)
        total_env_anomalies = len(env_anomalies)

        status = (
            "Complete"
            if total_timestamp_errors == 0 and total_env_anomalies == 0
            else "IssuesFound"
        )

        summary_data = {
            "module": "EnvironmentDriftDiagnostics",
            "agent": "Veindrill",
            "status": status,
            "metrics": {
                "max_temperature_deviation_c": round(self.max_temp_deviation, 3),
                "total_timestamp_errors": total_timestamp_errors,
                "total_environmental_anomalies": total_env_anomalies,
                "processed_log_lines": processed_line_count,
            },
            # Provide relative paths assuming reports are in the same directory
            "summary_report_path": os.path.basename(self.summary_output_path),
            "full_report_path": os.path.basename(self.output_path),
        }

        try:
            with open(self.summary_output_path, "w") as f:
                json.dump(summary_data, f, indent=4)
        except IOError as e:
            print(f"Error writing summary report file {self.summary_output_path}: {e}")
            raise


# --- Main Execution --- (Entry point)
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file_path = os.path.join(script_dir, INPUT_LOG_FILE)
    output_file_path = os.path.join(script_dir, OUTPUT_REPORT_FILE)
    summary_output_file_path = os.path.join(script_dir, "env_drift_summary.json")

    analyzer = TelemetryAnalyzer(
        input_path=input_file_path,
        output_path=output_file_path,
        summary_output_path=summary_output_file_path,
        temp_thresh=TEMP_THRESHOLD_CELSIUS,
        humid_thresh=HUMIDITY_THRESHOLD_PERCENT,
    )

    if not analyzer.run_analysis():
        print("Analysis failed.")
        # Consider exiting with non-zero status code if needed
        # sys.exit(1)
