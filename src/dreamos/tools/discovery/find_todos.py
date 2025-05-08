import argparse
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from dreamos.core.config import load_app_config

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("FindTodos")

# Default patterns to search for
DEFAULT_PATTERNS = ["TODO", "FIXME", "BUG"]
# EDIT START: Remove hardcoded log file path - will get from config
# DEFAULT_LOG_FILE = Path("runtime/logs/feedback.jsonl")
# EDIT END
# Default file extensions to scan
DEFAULT_EXTENSIONS = [".py", ".md", ".js", ".ts", ".rs", ".toml", ".yaml", ".yml"]
# Default directories/files to ignore
DEFAULT_IGNORE = [
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    "htmlcov",
    "_archive",
    "build",
    "dist",
    ".log",
    ".jsonl",
    ".json",
    ".lock",
    ".bak",
    ".tmp",
]


def find_todos_in_file(
    file_path: Path, patterns: list[str], base_dir: Path
) -> list[dict]:
    """Scans a single file for lines matching the specified patterns."""
    findings = []
    pattern_regex = re.compile(
        r"#\s*({})[:\s]?\s*(.*?)$".format("|".join(patterns)), re.IGNORECASE
    )

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_num, line in enumerate(f, 1):
                match = pattern_regex.search(line)
                if match:
                    pattern_found = match.group(1).upper()
                    comment_text = match.group(2).strip()
                    relative_path = str(file_path.relative_to(base_dir)).replace(
                        "\\", "/"
                    )  # Normalize path separators

                    level = "INFO"
                    if pattern_found == "FIXME":
                        level = "WARNING"
                    elif pattern_found == "BUG":
                        level = "ERROR"

                    finding = {
                        "timestamp": datetime.now(timezone.utc).isoformat(
                            timespec="milliseconds"
                        )
                        + "Z",
                        "type": "discovery",
                        "source": "find_todos_tool",
                        "level": level,
                        "data": {
                            "pattern": pattern_found,
                            "file": relative_path,
                            "line": line_num,
                            "comment": comment_text,
                        },
                    }
                    findings.append(finding)
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
    return findings


def write_log_entry(log_file: Path, entry: dict):
    """Appends a JSON entry to the log file."""
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
            f.write("\n")
    except Exception as e:
        logger.error(f"Failed to write to log file {log_file}: {e}")


def scan_directory(
    directory: Path,
    patterns: list[str],
    log_file: Path,
    ignore_list: list[str],
    extensions: list[str],
):
    """Scans a directory recursively for TODOs and logs them."""
    logger.info(f"Scanning directory: {directory} for patterns: {patterns}")
    total_findings = 0
    scanned_files = 0

    ignore_set = set(DEFAULT_IGNORE + ignore_list)
    extension_set = set(extensions)

    for root, dirs, files in os.walk(directory, topdown=True):
        # Modify dirs in-place to prevent descending into ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_set]

        for file in files:
            file_path = Path(root) / file

            # Check if the file or its parent directories should be ignored
            if any(part in ignore_set for part in file_path.parts):
                continue

            # Check file extension
            if file_path.suffix.lower() not in extension_set:
                continue

            scanned_files += 1
            findings = find_todos_in_file(file_path, patterns, directory)
            if findings:
                logger.info(
                    f"Found {len(findings)} item(s) in {file_path.relative_to(directory)}"  # noqa: E501
                )
                for finding in findings:
                    write_log_entry(log_file, finding)
                total_findings += len(findings)

    logger.info(
        f"Scan complete. Scanned {scanned_files} files. Found {total_findings} total items."  # noqa: E501
    )


def main():
    # EDIT START: Load AppConfig
    config = load_app_config()
    default_log_file_path = config.paths.logs_dir / "feedback.jsonl" # Construct path using config
    # EDIT END

    parser = argparse.ArgumentParser(
        description="Scan directories for TODO/FIXME/BUG comments and log them."
    )
    parser.add_argument(
        "--dir", type=Path, required=True, help="Directory to scan recursively."
    )
    parser.add_argument(
        "--patterns",
        nargs="+",
        default=DEFAULT_PATTERNS,
        help=f"List of patterns to search for (e.g., TODO FIXME). Default: {DEFAULT_PATTERNS}",  # noqa: E501
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        # EDIT START: Use config path as default
        default=default_log_file_path,
        help=f"Output JSON Lines log file. Default: {default_log_file_path}", # Update help text
        # EDIT END
    )
    parser.add_argument(
        "--ignore",
        nargs="*",
        default=[],
        help=f"Additional directories or file names/extensions to ignore. Default ignores: {DEFAULT_IGNORE}",  # noqa: E501
    )
    parser.add_argument(
        "--ext",
        nargs="*",
        default=DEFAULT_EXTENSIONS,
        help=f"File extensions to scan (include dot). Default: {DEFAULT_EXTENSIONS}",
    )

    args = parser.parse_args()

    if not args.dir.is_dir():
        logger.error(f"Error: Directory not found: {args.dir}")
        return

    scan_directory(args.dir, args.patterns, args.log_file, args.ignore, args.ext)


if __name__ == "__main__":
    main()
