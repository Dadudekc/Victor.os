#!/usr/bin/env python3
"""
DreamOS CLI - Unified command-line interface for DreamOS tools and utilities.
"""

import argparse
import importlib
import inspect
import sys
from pathlib import Path
from typing import Callable, Dict


def discover_cli_tools() -> Dict[str, Callable]:
    """Dynamically discover CLI tools in the cli package."""
    tools = {}
    cli_dir = Path(__file__).parent

    # Import known tools explicitly first
    from . import command_supervisor, task_editor

    tools.update(
        {
            "edit-task": task_editor.main,
            "supervise": command_supervisor.main,
        }
    )

    # Scan for additional tools
    for py_file in cli_dir.glob("*.py"):
        if py_file.stem in ("__init__", "__main__"):
            continue

        try:
            module = importlib.import_module(f".{py_file.stem}", package="dreamos.cli")
            if hasattr(module, "main"):
                # Use module name as command, or get from docstring
                cmd_name = getattr(
                    module, "COMMAND_NAME", py_file.stem.replace("_", "-")
                )
                tools[cmd_name] = module.main
        except Exception as e:
            print(
                f"Warning: Could not load CLI tool from {py_file}: {e}", file=sys.stderr
            )

    return tools


def main():
    parser = argparse.ArgumentParser(
        description="Dream.OS CLI Interface — Run core tools from the command line."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Discover and register all CLI tools
    tools = discover_cli_tools()
    for cmd_name, cmd_func in tools.items():
        # Get help text from function docstring
        help_text = inspect.getdoc(cmd_func) or f"Run the {cmd_name} tool"
        parser_cmd = subparsers.add_parser(cmd_name, help=help_text)
        parser_cmd.set_defaults(func=cmd_func)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
