"""
Script to search for potentially interesting scripts ('gold mine') within a directory.

Searches for files with specified extensions, checks their content for keywords,
and excludes common directories.
"""

import os
import argparse
import logging
from pathlib import Path
from typing import List, Set

# --- Configuration ---

# File extensions to consider as scripts
SCRIPT_EXTENSIONS = {'.py', '.js', '.sh', '.ps1', '.ipynb'}

# Keywords that might indicate interesting logic
# (Case-insensitive matching will be used)
KEYWORDS = {
    'api', 'key', 'secret', 'token', 'auth', 'login', 'password',
    'scrape', 'crawl', 'automation', 'strategy', 'trading', 'backtest',
    'analysis', 'analyze', 'model', 'train', 'predict', 'llm', 'openai',
    'controller', 'service', 'util', 'helper', 'pipeline', 'process',
    'coordinate', 'manage', 'state_machine', 'agent', 'bus', 'database',
    'sql', 'query', 'queue', 'monitor', 'alert', 'exploit', 'vulnerability'
}

# Directories to completely ignore during the search
EXCLUDED_DIRS = {
    '.git', '.venv', 'venv', '__pycache__', '.pytest_cache', 'node_modules',
    'dist', 'build', 'env', '.env', 'site-packages', 'migrations', 'logs',
    'static', 'media', 'data', 'output', 'reports', '.idea', '.vscode',
    '_archive', 'archive', 'bak', 'core_bak', 'examples', 'tests', 'test' 
    # Add more specific project archive/test dirs if needed
}

# Maximum file size to read (in bytes) to avoid reading huge files
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024 # 5 MB

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Functions ---

def is_excluded(path: Path, excluded_dirs: Set[str]) -> bool:
    """Check if a path should be excluded based on directory names."""
    return any(part in excluded_dirs for part in path.parts)

def file_contains_keywords(file_path: Path, keywords: Set[str]) -> bool:
    """Check if a file contains any of the specified keywords (case-insensitive)."""
    try:
        # Check file size first
        if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
            logger.warning(f"Skipping large file: {file_path} (> {MAX_FILE_SIZE_BYTES / 1024 / 1024:.1f} MB)")
            return False
            
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower() # Read and convert to lower case once
            for keyword in keywords:
                if keyword.lower() in content:
                    logger.debug(f"Found keyword '{keyword}' in {file_path}")
                    return True
    except OSError as e:
        logger.error(f"Error reading file {file_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing file {file_path}: {e}")
    return False

def find_scripts(search_dir: Path, extensions: Set[str], keywords: Set[str], excluded_dirs: Set[str]) -> List[Path]:
    """Walk through directories and find matching script files."""
    potential_files: List[Path] = []
    processed_count = 0
    
    logger.info(f"Starting search in: {search_dir}")
    logger.info(f"Looking for extensions: {extensions}")
    logger.info(f"Excluding directories containing: {excluded_dirs}")
    logger.info(f"Scanning for keywords (case-insensitive)...")

    for root, dirs, files in os.walk(search_dir, topdown=True):
        current_path = Path(root)

        # --- Directory Exclusion Logic ---
        # Check if the current directory itself should be excluded
        if is_excluded(current_path, excluded_dirs):
            logger.debug(f"Excluding directory: {current_path}")
            # Prevent os.walk from descending into excluded directories
            dirs[:] = [] 
            continue 

        # Filter subdirectories to prevent descending further if needed
        # (This is redundant if top-level check works, but provides fine control)
        dirs[:] = [d for d in dirs if not is_excluded(current_path / d, excluded_dirs)]
        # --- End Exclusion ---

        for filename in files:
            file_path = current_path / filename
            processed_count += 1
            if processed_count % 500 == 0:
                 logger.info(f"Processed {processed_count} files...")

            # Check extension
            if file_path.suffix.lower() in extensions:
                # Check keywords
                if file_contains_keywords(file_path, keywords):
                    logger.info(f"Potential gold mine found: {file_path}")
                    potential_files.append(file_path)

    logger.info(f"Search complete. Processed {processed_count} files.")
    return potential_files

# --- Main Execution ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find potentially valuable scripts.")
    parser.add_argument(
        "search_directory",
        nargs='?',
        default=os.getcwd(), # Default to current working directory
        help="The root directory to start searching from."
    )
    args = parser.parse_args()

    search_root = Path(args.search_directory).resolve()

    if not search_root.is_dir():
        logger.error(f"Error: Search directory '{search_root}' not found or is not a directory.")
        exit(1)

    found_files = find_scripts(
        search_dir=search_root,
        extensions=SCRIPT_EXTENSIONS,
        keywords=KEYWORDS,
        excluded_dirs=EXCLUDED_DIRS
    )

    print("\n--- Potential Gold Mine Scripts Found ---")
    if found_files:
        for file in found_files:
            # Print relative path from search root for cleaner output
            try:
                relative_path = file.relative_to(search_root)
                print(relative_path)
            except ValueError:
                 print(file) # Print absolute if relative fails (shouldn't happen often)
    else:
        print("No potential scripts found matching the criteria.")
    print("-----------------------------------------") 
