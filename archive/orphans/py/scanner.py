"""
Project Scanner - Analyzes repository structure, dependencies, and health metrics.
Generates a comprehensive report of the project's state.
"""

import asyncio
import hashlib
import logging
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from .analyzers import LanguageAnalyzer
from .constants import (
    CACHE_FILE,
    DEFAULT_IGNORE_DIRS,
    SCAN_DIRS,
    SUPPORTED_EXTENSIONS,
)
from .reporters import ReportGenerator
from .utils import FileUtils, HealthMonitor, StateManager

logger = logging.getLogger(__name__)

# Optional: If tree-sitter grammars are present for Rust/JS/TS
try:
    from tree_sitter import Language, Parser
except ImportError:
    Language, Parser = None, None
    logger.warning(
        "⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled."
    )


class FileProcessor:
    """Handles file processing and caching."""

    def __init__(
        self,
        project_root: Path,
        cache: Dict,
        cache_lock: threading.Lock,
        additional_ignore_dirs: Set[str],
        use_cache: bool = True,
    ):
        self.project_root = project_root
        self.cache = cache
        self.cache_lock = cache_lock
        self.ignore_dirs = DEFAULT_IGNORE_DIRS.union(additional_ignore_dirs or set())
        self.use_cache = use_cache
        self.file_utils = FileUtils()

    def hash_file(self, file_path: Path) -> str:
        """Generate a hash of file contents."""
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to hash file {file_path}: {e}")
            return ""

    def should_exclude(self, file_path: Path) -> bool:
        """Check if a file should be excluded from scanning."""
        if not file_path.is_file():
            return True

        # Check file extension
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return True

        # Check ignore patterns
        for ignore_dir in self.ignore_dirs:
            if ignore_dir in file_path.parts:
                return True

        return False

    def process_file(
        self, file_path: Path, language_analyzer: LanguageAnalyzer
    ) -> Optional[tuple]:
        """Process a single file and return its analysis results."""
        try:
            if self.should_exclude(file_path):
                return None

            file_hash = self.hash_file(file_path)
            cache_key = str(file_path.relative_to(self.project_root))

            # Check cache
            if self.use_cache:
                with self.cache_lock:
                    cached = self.cache.get(cache_key)
                    if cached and cached.get("hash") == file_hash:
                        return file_path, cached.get("analysis", {})

            # Analyze file
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            analysis = language_analyzer.analyze_file(file_path, content)
            analysis["hash"] = file_hash

            # Update cache
            if self.use_cache:
                with self.cache_lock:
                    self.cache[cache_key] = analysis

            return file_path, analysis

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return None


class ProjectScanner:
    """Main project scanner class."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        additional_ignore_dirs: Set[str] = None,
        use_cache: bool = True,
    ):
        self.project_root = project_root or Path.cwd()
        self.additional_ignore_dirs = additional_ignore_dirs or set()
        self.use_cache = use_cache
        self.cache_lock = threading.Lock()
        self.cache = {}
        self.state_manager = StateManager(self.project_root / CACHE_FILE)
        self.health_monitor = HealthMonitor()
        self.file_utils = FileUtils()

        # Initialize components
        self.language_analyzer = LanguageAnalyzer()
        self.file_processor = FileProcessor(
            self.project_root,
            self.cache,
            self.cache_lock,
            self.additional_ignore_dirs,
            self.use_cache,
        )

    async def scan_project(
        self,
        progress_callback: Optional[Callable] = None,
        num_workers: int = 4,
        force_rescan_patterns: Optional[List[str]] = None,
    ):
        """Scan the project and generate reports."""
        try:
            # Load cache
            if self.use_cache:
                self.cache = self.state_manager.load_state()

            # Collect files
            files = await self._discover_files_async()
            total_files = len(files)

            # Process files
            results = {}
            processed = 0

            async def process_file_batch(file_batch):
                batch_results = []
                for file_path in file_batch:
                    result = await asyncio.to_thread(
                        self.file_processor.process_file,
                        file_path,
                        self.language_analyzer,
                    )
                    if result:
                        batch_results.append(result)
                return batch_results

            # Process files in batches
            batch_size = max(1, total_files // num_workers)
            for i in range(0, total_files, batch_size):
                batch = files[i : i + batch_size]
                batch_results = await process_file_batch(batch)
                for file_path, analysis in batch_results:
                    results[str(file_path.relative_to(self.project_root))] = analysis
                processed += len(batch)
                if progress_callback:
                    progress_callback(processed / total_files * 100)

            # Save cache
            if self.use_cache:
                self.state_manager.save_state(self.cache)

            # Generate reports
            report_generator = ReportGenerator(
                self.project_root,
                results,
                self.project_root / "runtime/reports/project_scan_report.md",
                self.project_root / "runtime/reports/chatgpt_project_context.json",
            )
            report_generator.save_report()

            return results

        except Exception as e:
            logger.error(f"Error during project scan: {e}")
            raise

    async def _discover_files_async(self) -> List[Path]:
        """Discover files to scan asynchronously."""
        files = []
        for dir_name in SCAN_DIRS:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                files.extend(
                    [
                        f
                        for f in dir_path.rglob("*")
                        if f.is_file() and not self.file_processor.should_exclude(f)
                    ]
                )
        return files


async def main():
    """Main entry point."""
    try:
        scanner = ProjectScanner()
        print("Starting project scan...")

        def progress_update(percent_complete):
            print(f"Progress: {percent_complete:.1f}%")

        await scanner.scan_project(progress_callback=progress_update)
        print("\nScan completed successfully!")
        print("Results saved to runtime/reports/")

    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
