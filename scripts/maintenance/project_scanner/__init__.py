"""
Project Scanner - A modular tool for analyzing project structure and dependencies.
"""

__version__ = "1.0.0"

from .analyzers import FileAnalyzer, ImportAnalyzer, SizeAnalyzer
from .constants import (
    EXCLUDED_DIRS,
    EXCLUDED_FILES,
    LARGE_FILE_THRESHOLD_KB,
    MAX_DIR_SIZE_MB,
    MAX_FILE_SIZE_MB,
    REPORT_DIR,
    SCAN_DIRS,
)
from .reporters import JsonReporter, MarkdownReporter
from .scanner import ProjectScanner

__all__ = [
    "ProjectScanner",
    "FileAnalyzer",
    "ImportAnalyzer",
    "SizeAnalyzer",
    "MarkdownReporter",
    "JsonReporter",
    "REPORT_DIR",
    "SCAN_DIRS",
    "LARGE_FILE_THRESHOLD_KB",
    "MAX_FILE_SIZE_MB",
    "MAX_DIR_SIZE_MB",
    "EXCLUDED_DIRS",
    "EXCLUDED_FILES",
]
