# src/dreamos/agents/validation/offline_validation_agent.py
"""
Offline Validation Agent - Finalization Phase

Scans for toolchain deviations and file state inconsistencies in isolation.
Monitors expected tool outputs against actual file states.
Includes basic validation, age/size checks, and auto-repair capabilities.
"""

import logging
import json
import time
import hashlib
import os
import shutil
import argparse # Added for CLI flags
from pathlib import Path
from datetime import datetime, timezone, timedelta # Added for timestamps

# Attempt jsonschema import - will fail if not installed, handled in check logic
try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

# --- Placeholder Imports (Replace with actual core components) ---
# from dreamos.core.coordination.base_agent import BaseAgent
# from dreamos.core.config import Config
# from dreamos.core.tools import ToolRegistry # Hypothetical tool registry
# from dreamos.utils.file_io import read_file_safe # Hypothetical safe reader

logger = logging.getLogger("OfflineValidationAgent")

# --- Constants ---
DEFAULT_MAX_FILE_AGE_MINUTES = 5
DEFAULT_MAX_FILE_SIZE_MB = 10
CORRUPTED_DIR = Path("runtime/corrupted")

class OfflineValidationAgent: # Placeholder for BaseAgent inheritance
    """Scans for tool output vs. file state consistency. Includes auto-repair."""
    def __init__(self, agent_id="ValidatorAgent", config=None, dry_run=False, repair=False):
        self.agent_id = agent_id
        # self.config = config or Config()
        self.validation_matrix_path = Path("runtime/governance/protocols/tool_validation_matrix.md")
        self.validation_results_log = Path("runtime/logs/validation_agent_results.md")
        # self.scan_interval_seconds = 300 # Removed, runs manually or via external trigger now
        self.dry_run = dry_run
        self.repair_mode = repair
        self.current_scan_failures = [] # Track failures for summary

        logger.info(f"{self.agent_id} initialized. Dry Run: {self.dry_run}, Repair Mode: {self.repair_mode}")
        CORRUPTED_DIR.mkdir(parents=True, exist_ok=True)

    # --- Helper: Calculate SHA256 (moved inside class) ---
    def _calculate_sha256(self, filepath: Path) -> str:
        """Calculates the SHA256 hash of a file."""
        hasher = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(4096):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except FileNotFoundError:
            return ""
        except Exception as e:
            logger.error(f"Error hashing {filepath}: {e}")
            return ""

    def load_validation_matrix(self):
        """Loads the validation matrix (placeholder - needs actual parsing)."""
        logger.info(f"Loading validation matrix from: {self.validation_matrix_path} (Placeholder)")
        # --- Placeholder Matrix --- 
        # TODO: Implement actual parsing of the markdown file
        matrix = {
            "edit_file": [
                {"target_pattern": "*.json", "assertion": "is_valid_json"},
                {"target_pattern": "*.py", "assertion": "compiles_ok"},
                {"target_pattern": "runtime/logs/*.md", "assertion": "age_check"}, # Added age check for logs
                {"target_pattern": "runtime/tasks/task_backlog.json", "assertion": "size_check"} # Added size check example
            ],
            # ... (existing placeholders)
        }
        logger.warning("Using hardcoded validation matrix placeholder.")
        return matrix

    def _check_file_age(self, filepath: Path) -> tuple[bool, str]:
        """Checks if a file is older than the configured limit."""
        try:
            stat_result = filepath.stat()
            modified_time = datetime.fromtimestamp(stat_result.st_mtime, timezone.utc)
            age = datetime.now(timezone.utc) - modified_time
            max_age = timedelta(minutes=DEFAULT_MAX_FILE_AGE_MINUTES)
            if age > max_age:
                details = f"File age ({age}) exceeds limit ({max_age}). Last modified: {modified_time.isoformat()}"
                logger.warning(details)
                return False, details
            else:
                return True, f"File age OK ({age})."
        except FileNotFoundError:
            return True, "File not found, age check skipped."
        except Exception as e:
            details = f"Error checking file age for {filepath}: {e}"
            logger.error(details)
            return False, details

    def _check_file_size(self, filepath: Path) -> tuple[bool, str]:
        """Checks if a file is larger than the configured limit."""
        try:
            stat_result = filepath.stat()
            size_bytes = stat_result.st_size
            max_size_bytes = DEFAULT_MAX_FILE_SIZE_MB * 1024 * 1024
            if size_bytes > max_size_bytes:
                details = f"File size ({size_bytes / 1024 / 1024:.2f} MB) exceeds limit ({DEFAULT_MAX_FILE_SIZE_MB} MB)."
                logger.warning(details)
                return False, details
            else:
                return True, f"File size OK ({size_bytes / 1024 / 1024:.2f} MB)."
        except FileNotFoundError:
             return True, "File not found, size check skipped."
        except Exception as e:
            details = f"Error checking file size for {filepath}: {e}"
            logger.error(details)
            return False, details

    def _check_json_validity(self, filepath: Path) -> tuple[bool, str]:
        """Checks if a file contains valid JSON."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json.load(f)
            return True, "JSON is valid."
        except FileNotFoundError:
            return True, "File not found, JSON check skipped."
        except json.JSONDecodeError as e:
            details = f"Invalid JSON: {e}"
            logger.warning(details)
            return False, details
        except Exception as e:
            details = f"Error checking JSON validity for {filepath}: {e}"
            logger.error(details)
            return False, details

    def _check_python_compilation(self, filepath: Path) -> tuple[bool, str]:
        """Checks if a Python file compiles."""
        try:
            import py_compile
            py_compile.compile(str(filepath), doraise=True)
            return True, "Python compiles OK."
        except FileNotFoundError:
             return True, "File not found, compilation check skipped."
        except ImportError:
             return True, "`py_compile` module not found, skipping check."
        except Exception as e: # Catches py_compile.PyCompileError and others
            details = f"Python compilation failed: {e}"
            logger.warning(details)
            return False, details

    def _attempt_repair(self, filepath: Path) -> bool:
        """Moves the corrupted file and attempts restore from .bak."""
        if self.dry_run or not self.repair_mode:
            logger.info(f"Repair skipped for {filepath} (Dry Run: {self.dry_run}, Repair Mode: {self.repair_mode})" )
            return False

        bak_filepath = filepath.with_suffix(filepath.suffix + ".bak")
        corrupted_filepath = CORRUPTED_DIR / f"{filepath.name}.{datetime.now().strftime('%Y%m%d%H%M%S')}.corrupted"
        
        logger.warning(f"Attempting auto-repair for {filepath}")
        
        # 1. Move corrupted file
        try:
            shutil.move(str(filepath), str(corrupted_filepath))
            logger.info(f"Moved corrupted file to {corrupted_filepath}")
        except Exception as e:
            logger.error(f"Failed to move corrupted file {filepath}: {e}", exc_info=True)
            # Continue to attempt restore anyway, original might still be there
            pass
        
        # 2. Check for backup
        if not bak_filepath.exists():
            logger.error(f"Repair failed: Backup file not found: {bak_filepath}")
            # Log this specific failure type
            self.log_specific_failure("repair_failure_no_bak", str(filepath), f"Backup {bak_filepath.name} missing")
            return False

        # 3. Restore from backup
        try:
            shutil.copy2(bak_filepath, filepath)
            logger.info(f"Successfully restored {filepath} from {bak_filepath}. Verifying hash...")
            # 4. Verify restoration
            restored_hash = self._calculate_sha256(filepath)
            backup_hash = self._calculate_sha256(bak_filepath)
            if restored_hash == backup_hash and restored_hash != "":
                logger.info(f"Repair successful and verified for {filepath}.")
                return True
            else:
                 details = f"Restored file hash ({restored_hash}) does not match backup hash ({backup_hash})."
                 logger.error(f"Repair verification failed for {filepath}. {details}")
                 self.log_specific_failure("repair_failure_hash_mismatch", str(filepath), details)
                 return False
        except Exception as e:
            details = f"Error during restoration from {bak_filepath}: {e}"
            logger.error(f"Repair failed for {filepath}: {details}", exc_info=True)
            self.log_specific_failure("repair_failure_exception", str(filepath), details)
            return False

    def run_validation_check(self, tool_name, check_config):
        """Runs a single validation check based on the matrix config."""
        target_pattern = check_config.get('target_pattern')
        # command_pattern = check_config.get('command_pattern') # TODO: Implement command checks
        assertion = check_config.get('assertion')

        if not target_pattern or not assertion:
            logger.error(f"Invalid check config for tool {tool_name}: {check_config}")
            return True # Skip invalid check

        logger.info(f"Running check - Target: '{target_pattern}', Assertion: '{assertion}'")
        
        # Find matching files
        try:
             # Using rglob to search recursively from workspace root
             # Adjust base path if needed, e.g., Path("runtime")
             matching_files = list(Path(".").rglob(target_pattern))
             if not matching_files:
                  logger.debug(f"No files found matching pattern: {target_pattern}")
                  return True # No files to check
        except Exception as e:
             logger.error(f"Error during file globbing for pattern '{target_pattern}': {e}")
             self.log_specific_failure("validation_glob_error", target_pattern, str(e))
             return False # Treat glob error as failure

        overall_result = True
        for filepath in matching_files:
            if not filepath.is_file(): continue # Skip directories
            
            logger.debug(f"Checking file: {filepath}")
            passed = True
            details = ""

            # Perform assertion
            if assertion == "is_valid_json":
                passed, details = self._check_json_validity(filepath)
            elif assertion == "compiles_ok":
                passed, details = self._check_python_compilation(filepath)
            elif assertion == "age_check":
                 passed, details = self._check_file_age(filepath)
            elif assertion == "size_check":
                 passed, details = self._check_file_size(filepath)
            # TODO: Add more assertions from matrix (contains_recent_timestamp, file_matches_content, etc.)
            else:
                logger.warning(f"Unknown assertion type '{assertion}' for {filepath}, skipping.")
                continue

            if not passed:
                overall_result = False
                self.log_validation_failure(tool_name, str(filepath), assertion, details)
                # Attempt repair if enabled and failed
                if not self._attempt_repair(filepath):
                     logger.warning(f"Auto-repair failed or skipped for {filepath}. Inconsistency remains.")
                     # Keep overall_result as False
                else:
                     # If repair successful, we can consider this specific file 'handled'
                     # but the overall check for this pattern still failed initially
                     logger.info(f"File {filepath} inconsistency handled by repair.")
                     # Do not set overall_result back to True here
                     pass 
            else:
                 logger.debug(f"Check passed for {filepath} ({assertion}).")
        
        return overall_result

    def run_scan_cycle(self):
        """Runs a full scan cycle based on the validation matrix."""
        scan_start_time = datetime.now(timezone.utc)
        logger.info(f"Starting validation scan cycle at {scan_start_time.isoformat()}...")
        self.current_scan_failures = [] # Reset failures for this scan
        matrix = self.load_validation_matrix()
        all_passed = True

        for tool_name, checks in matrix.items():
            for check_config in checks:
                if not self.run_validation_check(tool_name, check_config):
                    all_passed = False
                    # No need to break, process all checks to find all failures

        scan_end_time = datetime.now(timezone.utc)
        duration = scan_end_time - scan_start_time
        if all_passed:
            logger.info(f"Validation scan cycle completed at {scan_end_time.isoformat()}. All checks passed. Duration: {duration}")
        else:
            logger.warning(f"Validation scan cycle completed at {scan_end_time.isoformat()}. FAILURES DETECTED. Duration: {duration}")

        self.log_scan_summary(scan_start_time, all_passed)

    def log_specific_failure(self, failure_type: str, target: str, details: str):
         """Helper to log specific operational failures of the validator itself."""
         # This allows tracking issues like backup fails vs. validation fails
         self.current_scan_failures.append({
              "type": failure_type,
              "target": target,
              "details": details,
              "timestamp": datetime.now(timezone.utc).isoformat()
         })
         logger.error(f"Operational Failure: Type={failure_type}, Target={target}, Details={details}")

    def log_validation_failure(self, tool_name, target_file, assertion, details):
        """Logs a specific validation failure detected during checks."""
        self.current_scan_failures.append({
            "type": "validation_failure",
            "tool": tool_name,
            "target_file": target_file,
            "assertion": assertion,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        logger.error(f"Validation Failure: File={target_file}, Tool={tool_name}, Assertion={assertion}, Details={details}")
        # Logging to file happens in log_scan_summary

    def log_scan_summary(self, scan_start_time: datetime, passed: bool):
        """Logs a timestamped summary of the scan cycle including failures."""
        timestamp = datetime.now(timezone.utc)
        status = "PASSED" if passed else "FAILED"
        log_entry = f"\n---\n**Validation Scan Summary**\n- **Scan Start UTC:** {scan_start_time.isoformat()}\n- **Scan End UTC:** {timestamp.isoformat()}\n- **Overall Status:** {status}\n"

        if not passed:
            log_entry += "- **Failures Logged:**\n"
            for failure in self.current_scan_failures:
                 log_entry += f"  - Type: {failure.get('type', 'N/A')}\n"
                 log_entry += f"    Timestamp: {failure.get('timestamp', 'N/A')}\n"
                 log_entry += f"    Tool: {failure.get('tool', 'N/A')}\n"
                 log_entry += f"    Target: {failure.get('target', failure.get('target_file', 'N/A'))}\n"
                 log_entry += f"    Assertion: {failure.get('assertion', 'N/A')}\n"
                 log_entry += f"    Details: {failure.get('details', 'N/A')}\n"

        try:
            with open(self.validation_results_log, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            logger.info(f"Appended scan summary to {self.validation_results_log}")
            if not passed and not self.dry_run:
                 # --- Placeholder for Escalation --- 
                 logger.warning(f"ALERT ESCALATION NEEDED for validation failure summary! (Placeholder)")
                 # --- End Placeholder --- 
        except Exception as e:
            logger.error(f"Failed to write validation scan summary: {e}")

# --- Standalone Execution (for testing scaffold) ---
if __name__ == "__main__":
    import random # Placeholder for validation logic
    parser = argparse.ArgumentParser(description="Offline Validation Agent")
    parser.add_argument("--dry-run", action="store_true", help="Run checks without attempting repairs.")
    parser.add_argument("--repair", action="store_true", help="Enable auto-repair mode (requires backup files)." )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.info("Running OfflineValidationAgent scaffold in standalone mode...")
    agent = OfflineValidationAgent(dry_run=args.dry_run, repair=args.repair)

    # Run one cycle directly
    agent.run_scan_cycle()

    logger.info("Standalone scaffold run complete. Check logs:")
    logger.info(f"- Validation Results: {agent.validation_results_log}")
    logger.info(f"- Corrupted Files Moved To: {CORRUPTED_DIR}")