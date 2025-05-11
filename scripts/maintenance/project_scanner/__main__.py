"""
Command-line entry point for the project scanner.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .scanner import ProjectScanner
from .utils import HealthMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Project scanner with agent categorization and incremental caching."
    )
    parser.add_argument(
        "--project-root", type=Path, default=Path("."), help="Root directory to scan."
    )
    parser.add_argument(
        "--ignore", nargs="*", default=[], help="Additional directories to ignore."
    )
    parser.add_argument(
        "--categorize-agents",
        action="store_true",
        help="Categorize Python classes into maturity level and agent type.",
    )
    parser.add_argument(
        "--no-chatgpt-context",
        action="store_true",
        help="Skip exporting ChatGPT context.",
    )
    parser.add_argument(
        "--generate-init",
        action="store_true",
        help="Enable auto-generating __init__.py files.",
    )
    parser.add_argument(
        "--markdown", action="store_true", help="Generate markdown report."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging."
    )
    return parser.parse_args()


def get_base_dir() -> Optional[Path]:
    """Get the base directory from command line args or current directory."""
    if len(sys.argv) > 1:
        base_dir = Path(sys.argv[1])
        if not base_dir.exists():
            logger.error(f"Directory does not exist: {base_dir}")
            return None
        return base_dir
    return Path.cwd()


def main():
    """Main entry point."""
    try:
        # Get base directory
        base_dir = get_base_dir()
        if base_dir is None:
            sys.exit(1)

        # Check system health
        health = HealthMonitor()
        memory = health.get_memory_usage()
        cpu = health.get_cpu_usage()
        disk = health.get_disk_usage(base_dir)

        logger.info("System health check:")
        logger.info(f"Memory usage: {memory.get('rss', 0):.1f} MB")
        logger.info(f"CPU usage: {cpu:.1f}%")
        logger.info(f"Disk usage: {disk.get('percent', 0):.1f}%")

        # Create scanner
        scanner = ProjectScanner(base_dir)

        # Run scan
        results = scanner.scan()

        # Print summary
        logger.info("\nScan complete!")
        logger.info(f"Total files: {results.get('file_count', 0)}")
        logger.info(f"Total size: {results.get('total_size', 0) / 1024 / 1024:.1f} MB")
        logger.info(f"Total lines: {results.get('total_lines', 0)}")

        # Print language stats
        logger.info("\nLanguage statistics:")
        for lang, stats in results.get("languages", {}).items():
            logger.info(f"{lang}:")
            logger.info(f"  Files: {stats['count']}")
            logger.info(f"  Size: {stats['size'] / 1024 / 1024:.1f} MB")
            logger.info(f"  Lines: {stats['lines']}")
            logger.info(f"  Complexity: {stats['complexity']}")

        # Print large files
        logger.info("\nLarge files:")
        for file in results.get("large_files", []):
            logger.info(f"{file['path']}: {file['size'] / 1024 / 1024:.1f} MB")

        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("\nScan interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during scan: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
