"""
Module entry point for executing the project scanner as a module.

This module allows the scanner to be run using 'python -m dreamos.tools.scanner'.
"""

import asyncio
import sys

from .cli import main


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScan canceled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1) 