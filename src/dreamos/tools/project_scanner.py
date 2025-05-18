"""
Project scanner module for Dream.OS.

This module serves as the main entry point for the project scanner functionality.
It has been refactored into a modular package structure for better maintainability.
"""

import asyncio
import sys

from dreamos.tools.scanner.cli import main

# Re-export the ProjectScanner class
from dreamos.tools.scanner.project_scanner import ProjectScanner

__all__ = ["ProjectScanner"]


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScan canceled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1) 