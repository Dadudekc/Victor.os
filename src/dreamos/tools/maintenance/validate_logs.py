import argparse
import glob
import json
import logging
import os
import sys
from typing import Dict, List

# EDIT START: Import AppConfig
from dreamos.core.config import load_app_config
# EDIT END

# Ensure log_validator exists and jsonschema is available (handled internally by validator)  # noqa: E501
try:
    from src.dreamos.utils.log_validator import LOG_SCHEMAS, validate_log_file
except ImportError as e:
    print(
        f"Error: Failed to import log validator. Ensure src/dreamos/utils/log_validator.py exists and necessary dependencies (like jsonschema) are installed. Details: {e}"  # noqa: E501
    )
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("validate_logs")


# EDIT START: Load Schema Map from config, with fallback
def load_schema_map(config_path: str, default_map: Dict[str, str]) -> Dict[str, str]:
    """Loads the filename-to-schemaID map from a JSON config file."""
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded_map = json.load(f)
                if isinstance(loaded_map, dict):
                    logger.info(f"Successfully loaded schema map from {config_path}")
                    # Optionally merge with default? For now, override.
                    return loaded_map
                else:
                    logger.warning(
                        f"Schema map config ({config_path}) is not a valid JSON dictionary. Using default map."  # noqa: E501
                    )
        except json.JSONDecodeError:
            logger.warning(
                f"Failed to decode JSON from schema map config ({config_path}). Using default map."  # noqa: E501
            )
        except Exception as e:
            logger.warning(
                f"Error reading schema map config ({config_path}): {e}. Using default map."  # noqa: E501
            )
    else:
        logger.info(f"Schema map config not found at {config_path}. Using default map.")
    return default_map


# Default map used if config file is missing or invalid
DEFAULT_SCHEMA_MAP = {
    "cursor_activity_log.jsonl": "cursor_activity",
    "task_events.jsonl": "task_event",
}
# EDIT START: Remove hardcoded path construction - will be determined via AppConfig in main
# SCHEMA_MAP_CONFIG_PATH = os.path.join(\
#     project_root, "runtime", "config", "log_schema_map.json"\
# )\
# SCHEMA_MAP = load_schema_map(SCHEMA_MAP_CONFIG_PATH, DEFAULT_SCHEMA_MAP)\
# EDIT END


def find_jsonl_files(log_dir: str, recursive: bool = False) -> List[str]:
    """Finds all .jsonl files within the specified log directory."""
    pattern = (
        os.path.join(log_dir, "**", "*.jsonl")
        if recursive
        else os.path.join(log_dir, "*.jsonl")
    )
    logger.debug(f"Searching for log files using pattern: {pattern}")
    # Use recursive=True with glob for **/ pattern
    found_files = glob.glob(pattern, recursive=recursive)
    logger.debug(f"Found {len(found_files)} potential files.")
    return found_files


if __name__ == "__main__":
    # EDIT START: Load AppConfig first
    config = load_app_config()
    default_log_dir = config.paths.logs_dir # Assuming logs_dir is defined in config paths
    default_schema_map_config_path = config.paths.runtime / "config" / "log_schema_map.json"
    # EDIT END

    parser = argparse.ArgumentParser(
        description="Validate JSONL log files in runtime/logs against predefined schemas."  # noqa: E501
    )
    parser.add_argument(
        "--log-dir",
        # EDIT START: Use config path as default
        default=str(default_log_dir),
        # EDIT END
        help="Directory containing the log files to validate.",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Search for log files recursively in subdirectories.",
    )
    parser.add_argument(
        "--schema-map-config",
        # EDIT START: Use config path as default
        default=str(default_schema_map_config_path),
        # EDIT END
        help="Path to the JSON config file mapping log filenames to schema IDs.",
    )

    args = parser.parse_args()

    # EDIT START: Load schema map using the path from args (which defaults to config path)
    SCHEMA_MAP = load_schema_map(args.schema_map_config, DEFAULT_SCHEMA_MAP)
    # EDIT END

    log_directory = args.log_dir
    logger.info(
        f"Starting JSONL log validation in directory: {log_directory} (Recursive: {args.recursive})"  # noqa: E501
    )

    if not os.path.isdir(log_directory):
        logger.error(f"Log directory not found: {log_directory}")
        sys.exit(1)

    jsonl_files = find_jsonl_files(log_directory, recursive=args.recursive)

    if not jsonl_files:
        logger.info("No *.jsonl files found to validate.")
        sys.exit(0)

    overall_success = True
    validation_reports = []

    for file_path in jsonl_files:
        filename = os.path.basename(file_path)
        relative_path = os.path.relpath(file_path, log_directory)
        logger.info(f"--- Validating: {relative_path} ---")

        # Determine schema ID based on filename mapping
        schema_id_to_use = SCHEMA_MAP.get(filename)

        if schema_id_to_use:
            if schema_id_to_use not in LOG_SCHEMAS:
                logger.error(
                    f"Schema ID '{schema_id_to_use}' mapped for {filename} but not defined in log_validator.py. Skipping schema check."  # noqa: E501
                )
                schema_id_to_use = None  # Fallback to JSON check only
            else:
                logger.info(f"Using schema: '{schema_id_to_use}'")
        else:
            logger.info(
                "No specific schema mapped. Checking for valid JSON structure only."
            )

        # Perform validation
        is_valid, summary, errors = validate_log_file(
            file_path, schema_id=schema_id_to_use
        )
        validation_reports.append(
            {
                "file": relative_path,
                "is_valid": is_valid,
                "summary": summary,
                "errors": errors,
            }
        )

        if not is_valid:
            overall_success = False
            logger.error(f"Validation FAILED for {relative_path}. Summary: {summary}")
            for err in errors[:5]:  # Log first few errors for brevity
                logger.error(
                    f"  - Line {err['line_number']}: [{err['error_type']}] {err['message']}"  # noqa: E501
                )
            if len(errors) > 5:
                logger.error(f"  ... and {len(errors) - 5} more errors.")
        else:
            logger.info(f"Validation SUCCEEDED for {relative_path}. Summary: {summary}")

        logger.info("---------------------------------")

    # --- Final Summary ---
    logger.info("=== Overall Validation Summary ===")
    total_files = len(validation_reports)
    failed_files = sum(1 for report in validation_reports if not report["is_valid"])

    if failed_files > 0:
        logger.error(f"{failed_files} out of {total_files} files failed validation.")
        # Optionally list failed files again
        for report in validation_reports:
            if not report["is_valid"]:
                logger.error(f"  - {report['file']}")
    else:
        logger.info(
            f"All {total_files} checked *.jsonl files passed validation successfully."
        )

    if not overall_success:
        sys.exit(1)

    sys.exit(0)
