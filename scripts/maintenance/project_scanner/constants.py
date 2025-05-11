"""
Configuration constants for the project scanner.
"""

from pathlib import Path
from typing import Any, Dict, Set

# File extensions supported for analysis
SUPPORTED_EXTENSIONS: Set[str] = {
    ".py",  # Python
    ".rs",  # Rust
    ".js",  # JavaScript
    ".ts",  # TypeScript
    ".jsx",  # React
    ".tsx",  # React TypeScript
    ".vue",  # Vue
    ".svelte",  # Svelte
}

# Default directories to ignore during scanning
DEFAULT_IGNORE_DIRS: Set[str] = {
    ".git",
    ".github",
    ".vscode",
    ".idea",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "build",
    "dist",
    "target",
    "coverage",
    "htmlcov",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

# Cache configuration
CACHE_FILE = ".dreamos_cache/scanner_dependency_cache.json"
CACHE_DIR = ".dreamos_cache"

# Analysis configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_LINES_PER_FILE = 10000

# Report configuration
REPORT_FORMATS = {
    "json": {
        "extension": ".json",
        "mime_type": "application/json",
    },
    "markdown": {
        "extension": ".md",
        "mime_type": "text/markdown",
    },
}

# Language-specific settings
LANGUAGE_SETTINGS: Dict[str, Dict[str, Any]] = {
    "python": {
        "extensions": {".py"},
        "complexity_threshold": 10,
        "max_line_length": 100,
    },
    "rust": {
        "extensions": {".rs"},
        "complexity_threshold": 15,
    },
    "javascript": {
        "extensions": {".js", ".ts"},
        "complexity_threshold": 12,
    },
}

# Performance settings
DEFAULT_NUM_WORKERS = 4
MAX_WORKERS = 16
CHUNK_SIZE = 1024 * 1024  # 1MB for file reading

# Directory paths
REPORT_DIR = Path("runtime/reports")

# Directories to scan
SCAN_DIRS = {
    "src": "Source code",
    "tests": "Test files",
    "docs": "Documentation",
    "scripts": "Utility scripts",
    "runtime": "Runtime data",
    "vendor": "Vendor dependencies",
}

# File size thresholds
LARGE_FILE_THRESHOLD_KB = 100  # Files larger than this will be flagged
MAX_FILE_SIZE_MB = 10  # Files larger than this will be flagged
MAX_DIR_SIZE_MB = 100  # Directories larger than this will be flagged

# Excluded patterns
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "vendor",
    "build",
    "dist",
    "htmlcov",
}

EXCLUDED_FILES = {
    "poetry.lock",
    "package-lock.json",
    "yarn.lock",
    ".coverage",
    "*.pyc",
    "*.pyo",
    "*.pyd",
}

# Report settings
DEFAULT_REPORT_FORMATS = ["markdown", "json"]
DEFAULT_REPORT_TEMPLATE = "templates/project_scan_report.md.j2"
