"""Runs the vulture dead code detection tool via subprocess and outputs JSON.

This script provides a pure Python way to invoke vulture, avoiding shell
complexities and parsing its output into a structured format.
"""

import subprocess
import json
import argparse
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_MIN_CONFIDENCE = 60

def run_vulture(target_path: str | Path, min_confidence: int = DEFAULT_MIN_CONFIDENCE) -> dict:
    """Executes vulture on the target path and returns a structured result.

    Args:
        target_path: The directory or file path to scan.
        min_confidence: The minimum confidence level for vulture findings (0-100).

    Returns:
        A dictionary containing the analysis results or error information.
    """
    results = {
        "target_path": str(target_path),
        "min_confidence": min_confidence,
        "success": False,
        "findings": [],
        "error": None,
        "raw_output": None,
        "raw_error": None,
    }

    if not Path(target_path).exists():
        results["error"] = f"Target path does not exist: {target_path}"
        logger.error(results["error"])
        return results

    command = [
        sys.executable, # Use the current Python executable
        "-m",
        "vulture",
        str(target_path),
        "--min-confidence",
        str(min_confidence),
        # Add other vulture arguments as needed, e.g., --ignore-names, --ignore-decorators
    ]

    logger.info(f"Running vulture command: {' '.join(command)}")

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False, # Don't raise exception on non-zero exit code
            encoding='utf-8' # Explicit encoding
        )

        results["raw_output"] = process.stdout
        results["raw_error"] = process.stderr
        results["exit_code"] = process.returncode

        if process.returncode == 0 and not process.stderr:
            logger.info(f"Vulture completed successfully for {target_path}.")
            results["success"] = True
            # Parse findings from stdout
            # Vulture output format example:
            # path/to/file.py:10: unused function 'my_func' (60% confidence)
            for line in process.stdout.strip().split('\n'):
                if not line:
                    continue
                # Very basic parsing - assumes standard format
                # TODO: Improve parsing robustness (regex?)
                parts = line.split(':')
                if len(parts) >= 3:
                    finding = {
                        "file": parts[0].strip(),
                        "line": int(parts[1].strip()),
                        "message": ":".join(parts[2:]).strip()
                    }
                    # Attempt to extract confidence
                    if '(' in finding["message"] and '% confidence)' in finding["message"]:
                        try:
                            conf_str = finding["message"][finding["message"].rfind('(')+1:finding["message"].rfind('% confidence)')]
                            finding["confidence"] = int(conf_str)
                        except ValueError:
                            pass # Ignore if confidence parsing fails
                    results["findings"].append(finding)
                else:
                    logger.warning(f"Could not parse vulture output line: {line}")
        else:
            error_msg = f"Vulture execution failed for {target_path} (Exit Code: {process.returncode})."
            if process.stderr:
                error_msg += f" Stderr: {process.stderr.strip()}"
            results["error"] = error_msg
            logger.error(error_msg)

    except FileNotFoundError:
        results["error"] = f"'vulture' command not found. Is vulture installed in the environment ({sys.executable})?"
        logger.exception(results["error"])
    except Exception as e:
        results["error"] = f"An unexpected error occurred while running vulture: {e}"
        logger.exception(results["error"])

    return results

def main():
    parser = argparse.ArgumentParser(description="Run vulture dead code detection and output JSON.")
    parser.add_argument("target_path", help="Directory or file path to scan.")
    parser.add_argument(
        "-c", "--min-confidence", type=int, default=DEFAULT_MIN_CONFIDENCE,
        help=f"Minimum confidence level for findings (0-100, default: {DEFAULT_MIN_CONFIDENCE})."
    )
    parser.add_argument(
        "-o", "--output-file",
        help="Optional path to save the JSON results."
    )

    args = parser.parse_args()

    analysis_results = run_vulture(args.target_path, args.min_confidence)

    json_output = json.dumps(analysis_results, indent=2)

    if args.output_file:
        try:
            Path(args.output_file).write_text(json_output, encoding='utf-8')
            logger.info(f"Results saved to {args.output_file}")
        except Exception as e:
            logger.exception(f"Failed to write results to {args.output_file}: {e}")
            # Print to stdout as fallback
            print(json_output)
    else:
        # Print to stdout if no output file specified
        print(json_output)

if __name__ == "__main__":
    main() 