#!/usr/bin/env python3
"""
CLI Test Runner - Executes CLI tools for testing and validation.
"""

import subprocess
import sys
from typing import List, Optional


def run_cli_tool(tool_name: str, args: Optional[List[str]] = None) -> bool:
    """
    Run a CLI tool and return True if successful.

    Args:
        tool_name: Name of the CLI tool to run
        args: Optional list of arguments to pass to the tool

    Returns:
        bool: True if tool executed successfully, False otherwise
    """
    cmd = [sys.executable, "-m", "dreamos.cli", tool_name]
    if args:
        cmd.extend(args)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ {tool_name} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {tool_name} failed with exit code {e.returncode}")
        if e.stdout:
            print("Output:", e.stdout)
        if e.stderr:
            print("Error:", e.stderr)
        return False


def test_all_tools() -> bool:
    """Run all available CLI tools with basic arguments."""
    tools = [
        ("edit-task", ["--task-file", "test.json"]),
        ("supervise", ["--log-level", "INFO"]),
    ]

    success = True
    for tool_name, args in tools:
        if not run_cli_tool(tool_name, args):
            success = False

    return success


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific tool
        tool_name = sys.argv[1]
        tool_args = sys.argv[2:] if len(sys.argv) > 2 else None
        sys.exit(0 if run_cli_tool(tool_name, tool_args) else 1)
    else:
        # Run all tools
        sys.exit(0 if test_all_tools() else 1)
