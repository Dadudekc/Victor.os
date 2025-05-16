"""Utilities for validation logging and metrics. (Reconstructed)"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union  # Added Union


class ValidationLogger:
    """Logs validation results and metrics. (Reconstructed Skeleton)"""

    def __init__(self, log_file: Union[str, Path] = "runtime/logs/validation_log.json"):
        """Initialize validation logger.

        Args:
            log_file: Path to the validation log JSON file.
        """
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_file.exists():
            with open(self.log_file, "w") as f:
                json.dump([], f)  # Initialize with an empty list
        print(f"ValidationLogger initialized. Log file: {self.log_file}")

    def _read_logs(self) -> List[Dict[str, Any]]:
        """Read all logs from the file."""
        try:
            with open(self.log_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []  # Return empty list if file not found or corrupt

    def _write_logs(self, logs: List[Dict[str, Any]]) -> None:
        """Write all logs to the file."""
        with open(self.log_file, "w") as f:
            json.dump(logs, f, indent=2)

    def log_validation(
        self,
        utility_name: str,
        test_name: str,
        passed: bool,
        score: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        version: Optional[str] = "1.0.0",
        timestamp: Optional[str] = None,
    ) -> None:
        """Log a single validation event."""
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()

        log_entry = {
            "timestamp": timestamp,
            "utility_name": utility_name,
            "test_name": test_name,
            "passed": passed,
            "score": score,
            "details": details or {},
            "version": version,
        }

        logs = self._read_logs()
        logs.append(log_entry)
        self._write_logs(logs)
        # print(f"Logged validation for {utility_name} - {test_name}: Passed={passed}") # Optional: too verbose for normal ops

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of validation results."""
        logs = self._read_logs()
        total_validations = len(logs)
        passed_count = sum(1 for log in logs if log["passed"])
        failed_count = total_validations - passed_count

        # This is a simplified summary. A real one might calculate scores, trends, etc.
        return {
            "total_validations": total_validations,
            "passed": passed_count,
            "failed": failed_count,
            "pass_rate": (
                (passed_count / total_validations * 100) if total_validations > 0 else 0
            ),
        }

    def get_recent_failures(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get the most recent N failed validation logs."""
        logs = self._read_logs()
        failed_logs = [log for log in logs if not log["passed"]]
        return sorted(failed_logs, key=lambda x: x["timestamp"], reverse=True)[:count]


# Note: This is a reconstructed file. Review and restoration from backup/VCS is preferred.
