#!/usr/bin/env python3
"""
Minimal Viable Time Normalizer (UTC ISO Only - Stage 1)

Reads lines from a specified input file and attempts to parse
them using the strict '%Y-%m-%dT%H:%M:%SZ' format.
Logs successful parses to a JSONL output file.
"""

import datetime
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Configure logging (basic)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# --- Configuration ---
# Output file for successful parses
DEFAULT_OUTPUT_FILE = Path("sandbox/logs/normalized_test_output.jsonl")
# Strict UTC ISO format required in this stage
UTC_ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def normalize_utc_iso_line(line: str) -> datetime | None:
    """Attempts to parse a string using the strict UTC ISO format."""
    try:
        # Use strptime for exact format matching
        dt_obj = datetime.strptime(line.strip(), UTC_ISO_FORMAT)
        # Ensure it's timezone-aware and set to UTC
        return dt_obj.replace(tzinfo=timezone.utc)
    except ValueError:
        # Format did not match exactly
        return None
    except Exception as e:
        # Handle other potential errors during parsing
        logging.error(f"Unexpected error parsing line '{line.strip()}': {e}")
        return None


def process_file(input_filepath: Path, output_filepath: Path):
    """Reads input file, attempts normalization, logs successes to output file."""
    success_count = 0
    output_filepath.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(input_filepath, "r", encoding="utf-8") as infile, open(
            output_filepath, "w", encoding="utf-8"
        ) as outfile:
            for i, line in enumerate(infile):
                original_line = line.strip()
                normalized_dt = normalize_utc_iso_line(original_line)

                if normalized_dt:
                    success_count += 1
                    log_entry = {
                        "line_number": i + 1,
                        "original": original_line,
                        "normalized_utc": normalized_dt.isoformat(),  # Output standard ISO format
                    }
                    try:
                        outfile.write(json.dumps(log_entry) + "\n")
                    except Exception as e:
                        logging.error(f"Failed to write log entry for line {i+1}: {e}")
                # else: # Optionally log failures/skips
                #     logging.debug(f"Line {i+1} did not match format: {original_line}")

    except FileNotFoundError:
        logging.error(f"Input file not found: {input_filepath}")
        return 0  # Indicate failure
    except Exception as e:
        logging.error(f"Error processing file {input_filepath}: {e}")
        return 0  # Indicate failure

    logging.info(f"Processing complete. Successfully parsed {success_count} lines.")
    return success_count


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <input_log_file>")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = DEFAULT_OUTPUT_FILE

    logging.info("Starting normalization (Stage 1: UTC ISO Only)")
    logging.info(f"Input: {input_file}")
    logging.info(f"Output: {output_file}")

    parsed_count = process_file(input_file, output_file)

    if parsed_count == 0 and not input_file.exists():
        sys.exit(2)  # Exit code for file not found
    elif parsed_count == 0:
        sys.exit(1)  # Generic error or no lines parsed
    else:
        sys.exit(0)  # Success
