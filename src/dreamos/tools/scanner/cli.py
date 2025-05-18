"""
Command line interface for the project scanner.

This module provides a command line interface to run the project scanner.
"""

import argparse
import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

# Import for type annotations only
from dreamos.core.config import AppConfig

from .project_scanner import ProjectScanner

logger = logging.getLogger(__name__)


async def main():
    """
    Main entry point for the command line interface.
    """
    parser = argparse.ArgumentParser(description="Dream.OS Project Scanner")
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,  # Set default to None, determination logic is later
        help="Root directory of the project to scan. Overrides AppConfig if set.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help='Directory or file patterns to exclude (can be used multiple times). Example: --exclude node_modules --exclude "*.log"',
    )
    parser.add_argument(
        "--force-rescan",
        action="append",
        default=[],
        help='Glob patterns for files to forcibly rescan even if unchanged (e.g., "**/config.py").',
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the dependency cache before scanning.",
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable using the cache entirely."
    )
    parser.add_argument(
        "--analysis-output",
        type=str,
        default=None, # Let ProjectScanner determine default from AppConfig/itself
        help="Path to save the main analysis report (e.g., project_scan_report.md).",
    )
    parser.add_argument(
        "--context-output",
        type=str,
        default=None, # Let ProjectScanner determine default
        help="Path to save the ChatGPT context export (e.g., project_context.json).",
    )
    parser.add_argument(
        "--cache-file",
        type=str,
        default=None, # Let ProjectScanner determine default
        help="Path to the dependency cache file (e.g., dependency_cache.json).",
    )
    parser.add_argument(
        "--workers", type=int, default=4, help="Number of worker threads for analysis."
    )
    # Add template path argument
    parser.add_argument(
        "--template-path",
        type=str,
        default=None,
        help="Path to a custom template file for ChatGPT context generation.",
    )
    # Add debug flag
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument(
        "--log-level",
        type=str,
        default=None, # Default to None, will be handled by AppConfig or fallback
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (e.g., DEBUG, INFO). Overrides AppConfig."
    )

    args = parser.parse_args()

    config: Optional[AppConfig] = None
    try:
        config = AppConfig()
    except Exception as e:
        # Basic fallback if AppConfig fails. Config will remain None.
        logging.basicConfig(level=logging.INFO) # Ensure basic logging is set up
        logger.error(f"Error initializing AppConfig: {e}. CLI args or defaults will be critical.")

    # Determine the effective project root
    if args.project_root:
        project_root_to_scan = Path(args.project_root).resolve()
        logger.info(f"Using command-line --project-root: {project_root_to_scan}")
    elif config and hasattr(config, 'paths') and hasattr(config.paths, 'project_root') and config.paths.project_root:
        project_root_to_scan = Path(config.paths.project_root).resolve()
        logger.info(f"Using project root from AppConfig: {project_root_to_scan}")
    else:
        project_root_to_scan = Path.cwd().resolve()
        logger.warning(f"No --project-root specified and AppConfig project_root not found. Defaulting to CWD: {project_root_to_scan}")

    # Setup logging based on AppConfig or args
    log_level_to_set = logging.INFO # Default log level
    if args.log_level:
        log_level_to_set = getattr(logging, args.log_level.upper(), logging.INFO)
        logger.info(f"Using command-line --log-level: {args.log_level.upper()}")
    elif config and hasattr(config, 'logging') and hasattr(config.logging, 'level'):
        log_level_to_set = getattr(logging, config.logging.level.upper(), logging.INFO)
        logger.info(f"Using log level from AppConfig: {config.logging.level.upper()}")
    else:
        logger.info(f"Using default log level: INFO")
    
    # Assuming a global logger or a way to set level for the module's logger
    logging.basicConfig(level=log_level_to_set, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.setLevel(log_level_to_set) # Ensure our specific logger is also set

    # Handle other CLI arguments for paths, overriding AppConfig or ProjectScanner defaults
    # These will be passed to ProjectScanner.__init__ which then uses its _resolve_path_from_config
    # The None default in argparse means if not provided, ProjectScanner will use its internal logic.

    logger.info(f"Starting project scan for: {project_root_to_scan}")
    start_time = asyncio.get_event_loop().time() if hasattr(asyncio, 'get_event_loop') else time.time()

    def progress_update(percent_complete, current_file=None):
        msg = f"Scan Progress: {percent_complete:.1f}%"
        if current_file:
            msg += f" (Processing: {current_file})"
        # Basic print, or use a more advanced progress bar library if available
        print(msg, end='\r') # Overwrite previous line
        if percent_complete >= 100:
            print() # Newline at the end

    scanner = ProjectScanner(
        config=config,
        project_root=project_root_to_scan,
        use_cache=not args.no_cache,
        additional_ignore_dirs=set(args.exclude) if args.exclude else None,
        cli_override_cache_file=Path(args.cache_file) if args.cache_file else None,
        cli_override_analysis_output_path=Path(args.analysis_output) if args.analysis_output else None,
        cli_override_context_output_path=Path(args.context_output) if args.context_output else None
    )

    try:
        await scanner.scan_project(
            progress_callback=progress_update,
            num_workers=args.workers,
            force_rescan_patterns=args.force_rescan
        )
        logger.info("Project scan completed successfully.")
        logger.info(f"Reports generated in: {scanner.analysis_output_path.parent if scanner.analysis_output_path else 'N/A'}")
        # Optionally print summary of collisions or large files
        # collisions = scanner.find_name_collisions()
        # if collisions:
        #     logger.info(f"Found {len(collisions)} name collisions. See report for details.")

    except Exception as e:
        logger.error(f"Error during project scan: {e}", exc_info=True)
    finally:
        end_time = asyncio.get_event_loop().time() if hasattr(asyncio, 'get_event_loop') else time.time()
        logger.info(f"Total scan time: {end_time - start_time:.2f} seconds.")
        print("\nScan finished.") # Ensure this prints on a new line after progress 