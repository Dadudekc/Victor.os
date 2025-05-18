"""
File processing module for the project scanner.

This module provides functionality to process files, determining which files to scan
and performing the actual scanning.
"""

import hashlib
import logging
import threading
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

from .language_analyzer import LanguageAnalyzer

logger = logging.getLogger(__name__)


class FileProcessor:
    """
    Processes files for the project scanner, handling file exclusions, caching, and analysis.
    """
    
    SUPPORTED_EXTENSIONS = {
        ".py", ".rs", ".js", ".ts", ".tsx", ".jsx", ".md", ".json", 
        ".yaml", ".yml", ".toml", ".sh", ".rst"
    }
    
    DEFAULT_IGNORE_DIRS = {
        ".git",
        "__pycache__",
        "node_modules",
        "venv",
        ".venv",  # Added explicit .venv
        "vendor",  # Added vendor directory
        "archive",  # Added archive directory
        ".dreamos_cache",  # Added .dreamos_cache
        "target",  # Rust build artifacts
        "build", "dist",  # Python build artifacts
        ".DS_Store",
        ".pytest_cache",
        ".mypy_cache",
        "htmlcov",  # Coverage reports
        # Common data/log folders that might be in project root
        "data", "logs", "output", "results", "temp", "tmp",
        "static", "media",  # Django/Flask static/media folders
        "docs",  # Often build artifacts or large generated docs
        "examples",  # Sometimes can be excluded
        "tests",  # Depending on scan purpose, might be excluded
        ".vscode", ".idea", ".devcontainer",  # IDE specific
    }
    
    DEFAULT_IGNORE_FILES = {
        ".gitignore", ".dockerignore", 
        "LICENSE", "README.md", "CHANGELOG.md", "CONTRIBUTING.md"
    }

    def __init__(
        self,
        project_root: Path,
        cache: Dict,
        cache_lock: threading.Lock,
        additional_ignore_dirs: set,
        use_cache: bool = True,
    ):
        self.project_root = project_root
        self.cache = cache
        self.cache_lock = cache_lock
        self.use_cache = use_cache
        self.ignore_dirs = self.DEFAULT_IGNORE_DIRS.union(additional_ignore_dirs or set())
        # Log the ignored directories to help with debugging
        logger.info(f"Ignoring directories: {sorted(list(self.ignore_dirs))}")

    def hash_file(self, file_path: Path) -> str:
        """Generate a hash of a file's contents for caching."""
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def should_exclude(self, file_path: Path) -> bool:
        """
        Determine if a file should be excluded from analysis.
        
        Args:
            file_path: The path to check
            
        Returns:
            True if the file should be excluded, False otherwise
        """
        # Normalize path for consistent comparisons
        try:
            rel_path = file_path.relative_to(self.project_root)
            path_parts = rel_path.parts
        except ValueError:
            # Path is not relative to project_root
            return True

        # Explicitly check for .venv directory to address potential issues
        if '.venv' in path_parts or any(part == '.venv' for part in path_parts):
            logger.debug(f"Excluding .venv directory file: {file_path}")
            return True

        # Ignore hidden files and directories (starting with .)
        if any(part.startswith(".") for part in path_parts) and not rel_path.suffix == ".py":
            logger.debug(f"Excluding hidden file: {file_path}")
            return True

        # Check if any parent directory or current directory is in ignore_dirs
        for i in range(len(path_parts)):
            dir_name = path_parts[i]
            if dir_name in self.ignore_dirs:
                logger.debug(f"Excluding file in ignored directory '{dir_name}': {file_path}")
                return True
            
            # Also check the full directory path
            partial_path = Path(*path_parts[:i+1]).as_posix()
            for ignore_dir in self.ignore_dirs:
                if partial_path == ignore_dir or partial_path.startswith(f"{ignore_dir}/"):
                    logger.debug(f"Excluding file in composite ignored path '{partial_path}': {file_path}")
                    return True

        # Check file extension
        if file_path.is_file():
            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                logger.debug(f"Excluding unsupported file extension: {file_path}")
                return True
            if file_path.name in self.DEFAULT_IGNORE_FILES:
                logger.debug(f"Excluding ignored file name: {file_path}")
                return True

        # Custom exclusion logic can be added here
        # For example, ignore large files
        if file_path.is_file() and file_path.stat().st_size > 10 * 1024 * 1024:  # 10MB
            logger.warning(f"Skipping large file: {file_path} (> 10MB)")
            return True

        return False

    def process_file(
        self, file_path: Path, language_analyzer: LanguageAnalyzer
    ) -> Optional[Tuple]:
        """
        Process a single file, analyzing its contents if needed.
        
        Args:
            file_path: Path to the file to process
            language_analyzer: The language analyzer to use
            
        Returns:
            Tuple of (file_path_str, analysis_data) if processed, None if skipped
        """
        # Convert to string for logging and relative path handling
        file_path_str = str(file_path.relative_to(self.project_root))
        
        # Check if in exclusion list
        if self.should_exclude(file_path):
            logger.debug(f"Skipping excluded file: {file_path_str}")
            return None
            
        try:
            # Check file cache first if enabled
            file_hash = None
            if self.use_cache:
                file_hash = self.hash_file(file_path)
                with self.cache_lock:
                    cached_result = self.cache.get(file_path_str)
                    if cached_result and cached_result.get("hash") == file_hash:
                        logger.debug(f"Using cached result for {file_path_str}")
                        return (file_path_str, cached_result.get("data", {}))

            # File changed or not in cache, process it
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                
            # Analyze the file
            analysis_data = language_analyzer.analyze_file(file_path, content)
            
            # Update cache
            if self.use_cache and file_hash:
                with self.cache_lock:
                    self.cache[file_path_str] = {"hash": file_hash, "data": analysis_data}
                    
            return (file_path_str, analysis_data)
            
        except Exception as e:
            logger.warning(f"Error processing file {file_path_str}: {e}")
            return (file_path_str, {"error": str(e)})  # Return basic error info 