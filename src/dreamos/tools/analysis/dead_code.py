# src/dreamos/tools/analysis/dead_code.py
# MOVED FROM: src/dreamos/tools/code_analysis/dead_code.py by Agent 5 (2025-04-28)
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def find_dead_code(
    target_path: Path | str, min_confidence: int = 80
) -> Optional[List[Dict[str, Any]]]:
    """
    Scans a directory or file for potential dead Python code using Vulture.

    Args:
        target_path: The directory or file path to scan.
        min_confidence: Minimum confidence level (0-100) for Vulture findings.

    Returns:
        A list of dictionaries, each representing a dead code finding,
        or None if an error occurred (e.g., vulture not found, path invalid).
        Returns an empty list if no dead code is found.
        Example finding dict:
        {
            'file': 'path/to/file.py',
            'line': 15,
            'type': 'variable', # or function, class, etc. (extracted from message)
            'name': 'unused_variable', # extracted from message
            'confidence': 90, # extracted from message
            'message': 'unused variable unused_variable (90% confidence)' # Raw vulture line
        }
    """  # noqa: E501
    target_path = Path(target_path)
    logger.info(
        f"Scanning for dead code in: {target_path} (min confidence: {min_confidence}%)"
    )

    # Check if target exists
    if not target_path.exists():
        logger.error(f"Target path not found: {target_path}")
        return None

    # Check if vulture command exists
    vulture_cmd = shutil.which("vulture")
    if not vulture_cmd:
        logger.error("'vulture' command not found. Is it installed and in PATH?")
        return None

    command = [
        vulture_cmd,
        str(target_path),
        "--min-confidence",
        str(min_confidence),
        "--sort-by-size",  # Often helpful
    ]

    logger.debug(f"Running command: {' '.join(command)}")
    try:
        # Run Vulture
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, encoding="utf-8"
        )

        if result.returncode != 0 and "No dead code found" not in result.stderr:
            # Vulture might return non-zero even if it just prints findings.
            # Check stderr for actual errors if stdout is empty.
            if not result.stdout.strip():
                logger.error(
                    f"Vulture command failed. Return code: {result.returncode}. Stderr: {result.stderr.strip()}"  # noqa: E501
                )
                # return None # Optionally return None on non-zero exit code if desired

        lines = result.stdout.splitlines()
        findings = []
        for line in lines:
            # Example line: core/utils.py:77: unused function `calculate_mean` (60% confidence)  # noqa: E501
            if "% confidence)" not in line:
                continue  # Skip lines without confidence indication

            try:
                # Basic parsing - might need refinement based on Vulture versions
                parts = line.split(":")
                file_path_str = parts[0].strip()
                line_num_str = parts[1].strip()
                message = ":".join(parts[2:]).strip()  # Rejoin rest of message

                # Extract confidence (simple parsing)
                confidence = 0
                if "(" in message and "% confidence)" in message:
                    try:
                        conf_str = message[
                            message.rfind("(") + 1 : message.rfind("% confidence)")
                        ]
                        confidence = int(conf_str)
                    except ValueError:
                        pass  # Keep confidence 0 if parsing fails

                # Regex parsing handles common cases (function, variable, class, import, property)
                # More complex analysis would require AST parsing or different Vulture output.
                finding = {
                    "file": file_path_str,
                    "line": int(line_num_str),
                    "confidence": confidence,
                    "message": message,
                    # Basic type/name extraction placeholder:
                    "type": "unknown",
                    "name": "unknown",
                }
                # Try regex parsing
                match = re.search(
                    r"unused (function|variable|class|import|property) `([^`]+)`",
                    message,
                )
                if match:
                    finding["type"] = match.group(1)
                    finding["name"] = match.group(2)
                findings.append(finding)
            except (IndexError, ValueError) as parse_error:
                logger.warning(
                    f"Could not parse Vulture line: '{line}'. Error: {parse_error}"
                )
                # Add raw line if parsing fails?
                # findings.append({'file': 'unknown', 'line': 0, 'confidence': 0, 'message': line})  # noqa: E501

        if not findings:
            logger.info(
                f"No unused code found in {target_path} with >= {min_confidence}% confidence."  # noqa: E501
            )
        else:
            logger.info(
                f"Found {len(findings)} potential dead code items in {target_path}."
            )

        return findings

    except FileNotFoundError:
        logger.error(
            f"'{vulture_cmd}' command not found during subprocess run. This shouldn't happen after shutil.which check."  # noqa: E501
        )
        return None
    except Exception as e:
        logger.error(f"Error running Vulture subprocess: {e}", exc_info=True)
        return None


# Example of how an agent might use this:
# from dreamos.tools.analysis.dead_code import find_dead_code # UPDATED EXAMPLE IMPORT PATH  # noqa: E501
#
# target = "src/dreamos/coordination"
# dead_code_results = find_dead_code(target, min_confidence=70)
# if dead_code_results is None:
#     print("Error running dead code scan.")
# elif dead_code_results:
#     print("Dead code found:")
#     for item in dead_code_results:
#         print(f"- {item['file']}:{item['line']} ({item['confidence']}%) {item['message']}")  # noqa: E501
# else:
#     print("No dead code found.")
