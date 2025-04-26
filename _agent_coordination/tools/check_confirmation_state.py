"""
Tool to check if explicit user confirmation is needed.
See: _agent_coordination/onboarding/TOOLS_GUIDE.md

Checks for the existence of a specific flag file in the current directory.
"""

import argparse
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

CONFIRMATION_FLAG_FILE = "CONFIRMATION_REQUIRED.flag"

def check_confirmation(flag_filename: str = CONFIRMATION_FLAG_FILE):
    """Checks if the specified flag file exists in the current directory."""
    flag_path = Path.cwd() / flag_filename
    logger.info(f"Checking for confirmation flag: {flag_path}")
    
    confirmation_required = flag_path.exists()
    
    if confirmation_required:
        logger.warning(f"Result: Confirmation REQUIRED (Flag file found: {flag_filename}).")
        sys.exit(1) # Exit code 1 indicates confirmation needed
    else:
        logger.info(f"Result: Confirmation NOT required (Flag file not found: {flag_filename}).")
        sys.exit(0) # Exit code 0 indicates safe to proceed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check if user confirmation is needed by looking for a flag file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    parser.add_argument(
        "--flag-file", 
        default=CONFIRMATION_FLAG_FILE, 
        help="Name of the flag file to check for in the current directory."
        )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")

    check_confirmation(flag_filename=args.flag_file) 
