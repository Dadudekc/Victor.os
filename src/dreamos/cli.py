"""
Dream.OS Command Line Interface
"""

import argparse
import sys
from pathlib import Path

from .tools.autonomy.resume_autonomy_loop import main as resume_autonomy

def setup_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description='Dream.OS Command Line Interface'
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Resume autonomy command
    resume_parser = subparsers.add_parser(
        'resume-autonomy',
        help='Resume autonomy for all agents'
    )
    resume_parser.add_argument(
        '--strict',
        action='store_true',
        help='Exit with error if any checks fail'
    )
    
    return parser

def main() -> int:
    """Main entry point for the CLI."""
    parser = setup_parser()
    args = parser.parse_args()
    
    if args.command == 'resume-autonomy':
        return resume_autonomy()
    
    parser.print_help()
    return 1

if __name__ == '__main__':
    sys.exit(main()) 