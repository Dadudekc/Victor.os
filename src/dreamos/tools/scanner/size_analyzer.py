"""
Size analysis module for the project scanner.

This module provides functionality to analyze file and directory sizes.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

logger = logging.getLogger(__name__)


class SizeAnalyzer:
    """Analyzes file and directory sizes."""

    @staticmethod
    def get_directory_size(path: Path, file_processor_should_analyze: Callable[[Path], bool]) -> int:
        """Get total size of a directory in bytes, respecting exclusion rules."""
        total = 0
        try:
            for file_path in path.rglob("*"):
                if file_path.is_file() and not file_processor_should_analyze(file_path):  # Use passed in checker
                    total += file_path.stat().st_size
        except Exception as e:
            logger.error(f"Error calculating directory size for {path}: {e}")
        return total

    @staticmethod
    def find_large_files(analysis_data: Dict[str, Dict[str, Any]], threshold_kb: int) -> List[Tuple[str, int]]:
        """Find files larger than the threshold from analysis data."""
        large_files = []
        for file_path_str, analysis in analysis_data.items():
            size_bytes = analysis.get("size_bytes")  # Assuming size_bytes is stored
            if size_bytes is not None and size_bytes > threshold_kb * 1024:
                large_files.append((file_path_str, size_bytes))
        return sorted(large_files, key=lambda x: x[1], reverse=True)

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format size in bytes to human readable format."""
        if size_bytes is None:
            return "N/A"
        for unit in ["B", "KB", "MB", "GB"]:
            if abs(size_bytes) < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB" 