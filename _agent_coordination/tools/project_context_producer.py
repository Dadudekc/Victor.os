"""
Project Context Analyzer
========================
Extracts file paths from log snippets and lists Python files in a project.

See: _agent_coordination/onboarding/TOOLS_GUIDE.md
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Logger Setup
# ─────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(handler)

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ContextConfig:
    OUTPUT_FILENAME: str = "agent_bridge_context.json"
    SUPPORTED_EXTENSIONS: tuple[str, ...] = (
        "py", "md", "json", "txt", "yaml", "yml", "toml", "log", "sh", "bat", "rs", "js", "ts"
    )

# Simplified regex for file paths (relative or absolute-like)
# Looks for sequences with /, \, or drive letters C:, optionally quoted,
# ending in common extensions.
PATH_REGEX = re.compile(
    r'([\'\"]?)((?:[a-zA-Z]:)?[\w\-/\\\\.]+?\.(?:py|md|json|txt|yaml|yml|toml|log|sh|bat|rs|js|ts))\\1'
)

# ─────────────────────────────────────────────────────────────────────────────
# Core Logic
# ─────────────────────────────────────────────────────────────────────────────
def extract_paths_from_log(log: str) -> list[str]:
    """Extracts potential file paths from a log snippet."""
    matches = PATH_REGEX.findall(log)
    paths = {match[1].replace('\\', '/') for match in matches}
    logger.debug(f"Extracted {len(paths)} paths from log.")
    return sorted(paths)


def find_python_files(project_dir: Path) -> list[str]:
    """Recursively finds all .py files in a directory."""
    if not project_dir.exists():
        raise FileNotFoundError(f"Directory does not exist: {project_dir}")
    py_files = {
        str(Path(root).joinpath(f)).replace('\\', '/')
        for root, _, files in os.walk(project_dir)
        for f in files if f.endswith(".py")
    }
    return sorted(py_files)


def produce_project_context(
    log_snippet: str,
    project_dir: Path,
    output_dict: bool = False,
) -> Optional[dict]:
    """Generates and writes (or returns) the project context."""
    logger.info("Analyzing project context...")
    if not project_dir.is_dir():
        raise NotADirectoryError(f"Invalid project directory: {project_dir}")

    context = {
        "analyzed_log_length": len(log_snippet),
        "project_root": str(project_dir),
        "paths_mentioned_in_log": extract_paths_from_log(log_snippet),
        "python_files_in_project": find_python_files(project_dir),
        "potential_stall_reason": "Basic context only. Deeper analysis requires more trace data.",
        "suggested_next_actions": [
            "Review extracted file paths",
            "Check project structure for unresolved dependencies",
        ],
    }

    output_path = project_dir / ContextConfig.OUTPUT_FILENAME

    if output_dict:
        logger.info("Returning context as dictionary (stdout mode).")
        return context

    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(context, f, indent=2)
        logger.info(f"Context written to: {output_path}")
        return None
    except Exception as e:
        logger.error(f"Failed to write context file: {e}", exc_info=True)
        raise

# ─────────────────────────────────────────────────────────────────────────────
# CLI Entrypoint
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Produce a basic project context summary from log + project directory.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "log_snippet",
        help="Log content (or 'stdin' to read from stdin)",
    )
    parser.add_argument(
        "project_dir",
        help="Path to the project root directory",
    )
    parser.add_argument(
        "--output-dict",
        action="store_true",
        help="Print result as JSON to stdout instead of writing to file",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Resolve log content
    if args.log_snippet.strip().lower() == "stdin":
        logger.info("Reading log snippet from stdin...")
        try:
            log_content = sys.stdin.read()
        except Exception as e:
            logger.error(f"Failed to read from stdin: {e}")
            sys.exit(1)
    else:
        log_content = args.log_snippet

    # Resolve project dir
    try:
        project_path = Path(args.project_dir).resolve(strict=True)
    except Exception as e:
        logger.error(f"Invalid project directory: {e}")
        sys.exit(1)

    try:
        result = produce_project_context(
            log_snippet=log_content,
            project_dir=project_path,
            output_dict=args.output_dict,
        )

        if args.output_dict and result:
            print(json.dumps(result, indent=2))
        sys.exit(0)

    except Exception as e:
        logger.error(f"Context analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()