# src/dreamos/tools/analysis/dead_code.py
# MOVED FROM: src/dreamos/tools/code_analysis/dead_code.py by Agent 5 (2025-04-28)
import asyncio
import logging
import re
import shutil

# import subprocess # No longer directly used, use asyncio.create_subprocess_exec
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def find_dead_code(
    target_path: Path | str, min_confidence: int = 80
) -> Optional[List[Dict[str, Any]]]:
    """
    Scans a directory or file for potential dead Python code using Vulture. Async.

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

    if not await asyncio.to_thread(target_path.exists):
        logger.error(f"Target path not found: {target_path}")
        return None

    vulture_cmd_path = await asyncio.to_thread(shutil.which, "vulture")
    if not vulture_cmd_path:
        logger.error("'vulture' command not found. Is it installed and in PATH?")
        return None

    command_args = [
        str(target_path),
        "--min-confidence",
        str(min_confidence),
        "--sort-by-size",
    ]

    logger.debug(f"Running command: {vulture_cmd_path} {' '.join(command_args)}")
    try:
        process = await asyncio.create_subprocess_exec(
            vulture_cmd_path,
            *command_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        stdout_str = stdout.decode("utf-8", errors="ignore") if stdout else ""
        stderr_str = stderr.decode("utf-8", errors="ignore") if stderr else ""

        if process.returncode != 0 and "No dead code found" not in stderr_str:
            if not stdout_str.strip():
                logger.error(
                    f"Vulture command failed. Return code: {process.returncode}. Stderr: {stderr_str.strip()}"  # noqa: E501
                )
                # return None # Optionally return None

        lines = stdout_str.splitlines()
        findings = []
        for line in lines:
            if "% confidence)" not in line:
                continue
            try:
                parts = line.split(":")
                file_path_str = parts[0].strip()
                line_num_str = parts[1].strip()
                message = ":".join(parts[2:]).strip()
                confidence = 0
                if "(" in message and "% confidence)" in message:
                    try:
                        conf_str = message[
                            message.rfind("(") + 1 : message.rfind("% confidence)")
                        ]
                        confidence = int(conf_str)
                    except ValueError:
                        pass
                finding = {
                    "file": file_path_str,
                    "line": int(line_num_str),
                    "confidence": confidence,
                    "message": message,
                    "type": "unknown",
                    "name": "unknown",
                }
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
            f"Vulture command '{vulture_cmd_path}' not found during subprocess run."
        )
        return None
    except Exception as e:
        logger.error(f"Error running Vulture subprocess: {e}", exc_info=True)
        return None


# Example usage (needs to be async now):
# async def main_test():
#     target = "src/dreamos/coordination"
#     dead_code_results = await find_dead_code(target, min_confidence=70)
#     if dead_code_results is None:
#         print("Error running dead code scan.")
#     elif dead_code_results:
#         print("Dead code found:")
#         for item in dead_code_results:
#             print(f"- {item['file']}:{item['line']} ({item['confidence']}%) {item['message']}")  # noqa: E501
#     else:
#         print("No dead code found.")
# if __name__ == "__main__":
#     asyncio.run(main_test())
