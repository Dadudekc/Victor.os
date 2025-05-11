"""
Main project scanner implementation.
"""

import hashlib
import json
import logging
import os
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from .analyzers import FileAnalyzer, ImportAnalyzer, LanguageAnalyzer, SizeAnalyzer
from .constants import (
    CACHE_FILE,
    DEFAULT_IGNORE_DIRS,
    DEFAULT_NUM_WORKERS,
    LARGE_FILE_THRESHOLD_KB,
    SCAN_DIRS,
    SUPPORTED_EXTENSIONS,
)
from .reporters import ReportGenerator
from .utils import FileUtils, HealthMonitor, StateManager

logger = logging.getLogger(__name__)


class FileProcessor:
    """Handles file hashing, ignoring, caching checks, etc."""

    def __init__(
        self,
        project_root: Path,
        cache: Dict,
        cache_lock: threading.Lock,
        additional_ignore_dirs: Set[str],
    ):
        self.project_root = project_root
        self.cache = cache
        self.cache_lock = cache_lock
        self.additional_ignore_dirs = additional_ignore_dirs

    def hash_file(self, file_path: Path) -> str:
        """Calculate MD5 hash of a file."""
        try:
            with file_path.open("rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {e}")
            return ""

    def should_exclude(self, file_path: Path) -> bool:
        """Check if a file or directory should be excluded from analysis."""
        # Check if this is the scanner itself
        try:
            if file_path.resolve() == Path(__file__).resolve():
                return True
        except NameError:
            pass

        # Check additional ignore directories
        for ignore in self.additional_ignore_dirs:
            ignore_path = Path(ignore)
            if not ignore_path.is_absolute():
                ignore_path = (self.project_root / ignore_path).resolve()
            try:
                file_path.resolve().relative_to(ignore_path)
                return True
            except ValueError:
                continue

        # Check for excluded directory names in the path
        if any(excluded in file_path.parts for excluded in DEFAULT_IGNORE_DIRS):
            return True

        # Check for common virtual environment path patterns
        path_str = str(file_path.resolve()).lower()
        venv_patterns = {
            "venv",
            "env",
            ".env",
            ".venv",
            "virtualenv",
            "ENV",
            "VENV",
            ".ENV",
            ".VENV",
            "python-env",
            "python-venv",
            "py-env",
            "py-venv",
            "envs",
            "conda-env",
            ".conda-env",
            ".poetry/venv",
            ".poetry-venv",
        }
        if any(
            f"/{pattern}/" in path_str.replace("\\", "/") for pattern in venv_patterns
        ):
            return True

        return False

    def process_file(
        self, file_path: Path, language_analyzer: LanguageAnalyzer
    ) -> Optional[tuple]:
        """Analyzes a file if not in cache or changed, else returns None."""
        file_hash_val = self.hash_file(file_path)
        relative_path = str(file_path.relative_to(self.project_root))

        with self.cache_lock:
            if (
                relative_path in self.cache
                and self.cache[relative_path].get("hash") == file_hash_val
            ):
                return None

        try:
            with file_path.open("r", encoding="utf-8") as f:
                source_code = f.read()
            analysis_result = language_analyzer.analyze_file(file_path, source_code)
            with self.cache_lock:
                self.cache[relative_path] = {"hash": file_hash_val}
            return (relative_path, analysis_result)
        except Exception as e:
            logger.error(f"❌ Error analyzing {file_path}: {e}")
            return None


class BotWorker(threading.Thread):
    """A background worker that processes files from a queue."""

    def __init__(
        self, task_queue: queue.Queue, results_list: list, scanner, status_callback=None
    ):
        super().__init__()
        self.task_queue = task_queue
        self.results_list = results_list
        self.scanner = scanner
        self.status_callback = status_callback
        self.daemon = True
        self.start()

    def run(self):
        while True:
            file_path = self.task_queue.get()
            if file_path is None:
                break
            result = self.scanner._process_file(file_path)
            if result is not None:
                self.results_list.append(result)
            if self.status_callback:
                self.status_callback(file_path, result)
            self.task_queue.task_done()


class MultibotManager:
    """Manages a pool of BotWorker threads."""

    def __init__(self, scanner, num_workers=DEFAULT_NUM_WORKERS, status_callback=None):
        self.task_queue = queue.Queue()
        self.results_list = []
        self.scanner = scanner
        self.status_callback = status_callback
        self.workers = [
            BotWorker(self.task_queue, self.results_list, scanner, status_callback)
            for _ in range(num_workers)
        ]

    def add_task(self, file_path: Path):
        self.task_queue.put(file_path)

    def wait_for_completion(self):
        self.task_queue.join()

    def stop_workers(self):
        for _ in self.workers:
            self.task_queue.put(None)


class ProjectScanner:
    """
    A universal project scanner that:
      - Identifies Python, Rust, JS, TS files
      - Extracts functions, classes, routes, complexity
      - Caches file hashes to skip unchanged files
      - Detects moved files by matching file hashes
      - Merges new analysis into existing project_analysis.json
      - Exports a merged ChatGPT context if requested
      - Processes files asynchronously with BotWorker threads
      - Auto-generates __init__.py files for Python packages
    """

    def __init__(self, project_root: Path = Path(".")):
        self.project_root = project_root.resolve()
        self.analysis: Dict[str, Dict] = {}
        self.cache = self.load_cache()
        self.cache_lock = threading.Lock()
        self.additional_ignore_dirs = set()
        self.language_analyzer = LanguageAnalyzer()
        self.file_processor = FileProcessor(
            self.project_root, self.cache, self.cache_lock, self.additional_ignore_dirs
        )
        self.report_generator = ReportGenerator(self.project_root, self.analysis)
        self.file_analyzer = FileAnalyzer()
        self.import_analyzer = ImportAnalyzer()
        self.size_analyzer = SizeAnalyzer()
        self.state_manager = StateManager(self.project_root / CACHE_FILE)
        self.health_monitor = HealthMonitor()

    def load_cache(self) -> Dict:
        """Loads JSON cache from disk if present."""
        cache_path = self.project_root / CACHE_FILE
        if cache_path.exists():
            try:
                with cache_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def save_cache(self):
        """Writes the updated cache to disk."""
        cache_path = self.project_root / CACHE_FILE
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=4)

    def scan_project(self, progress_callback: Optional[Callable] = None):
        """
        Orchestrates the project scan:
        - Finds Python, Rust, JS, TS files with os.walk()
        - Excludes certain directories
        - Detects moved files by comparing cached hashes
        - Spawns multibot workers for concurrency
        - Merges new analysis with old project_analysis.json
        - Reports progress via progress_callback(percent)
        """
        logger.info(f"🔍 Scanning project: {self.project_root} ...")

        # Find valid files
        valid_files = []
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)
            if self.file_processor.should_exclude(root_path):
                continue
            for file in files:
                file_path = root_path / file
                if (
                    file_path.suffix.lower() in SUPPORTED_EXTENSIONS
                    and not self.file_processor.should_exclude(file_path)
                ):
                    valid_files.append(file_path)

        total_files = len(valid_files)
        logger.info(f"📝 Found {total_files} valid files for analysis.")

        # Handle moved files
        previous_files = set(self.cache.keys())
        current_files = {str(f.relative_to(self.project_root)) for f in valid_files}
        moved_files = {}
        missing_files = previous_files - current_files

        # Detect moved files by matching file hashes
        for old_path in previous_files:
            old_hash = self.cache.get(old_path, {}).get("hash")
            if not old_hash:
                continue
            for new_path in current_files:
                new_file = self.project_root / new_path
                if self.file_processor.hash_file(new_file) == old_hash:
                    moved_files[old_path] = new_path
                    break

        # Remove truly missing files from cache
        for missing_file in missing_files:
            if missing_file not in moved_files:
                with self.cache_lock:
                    if missing_file in self.cache:
                        del self.cache[missing_file]

        # Update cache for moved files
        for old_path, new_path in moved_files.items():
            with self.cache_lock:
                self.cache[new_path] = self.cache.pop(old_path)

        # Process files asynchronously
        logger.info("⏱️  Processing files asynchronously...")
        num_workers = min(os.cpu_count() or DEFAULT_NUM_WORKERS, DEFAULT_NUM_WORKERS)
        manager = MultibotManager(
            scanner=self,
            num_workers=num_workers,
            status_callback=lambda fp, res: logger.info(f"Processed: {fp}"),
        )
        for file_path in valid_files:
            manager.add_task(file_path)
        manager.wait_for_completion()
        manager.stop_workers()

        # Update progress and collect results
        processed_count = 0
        for result in manager.results_list:
            processed_count += 1
            if progress_callback:
                percent = int((processed_count / total_files) * 100)
                progress_callback(percent)
            if result is not None:
                file_path, analysis_result = result
                self.analysis[file_path] = analysis_result

        # Save results
        self.report_generator.save_report()
        self.save_cache()
        logger.info(
            f"✅ Scan complete. Results merged into {self.project_root / 'project_analysis.json'}"
        )

    def _process_file(self, file_path: Path):
        """Processes a file via FileProcessor."""
        return self.file_processor.process_file(file_path, self.language_analyzer)

    def generate_init_files(self, overwrite: bool = True):
        """Generate __init__.py for python packages."""
        self.report_generator.generate_init_files(overwrite)

    def export_chatgpt_context(
        self, template_path: Optional[str] = None, output_path: Optional[str] = None
    ):
        """Merges new analysis into old chatgpt_project_context.json or uses a Jinja template."""
        self.report_generator.export_chatgpt_context(template_path, output_path)

    def generate_markdown_report(self, output_path: Optional[Path] = None) -> str:
        """Generate a markdown report of the analysis results."""
        return self.report_generator.generate_markdown_report(output_path)

    def scan(self) -> Dict:
        """Run the full scan and return results."""
        logger.info(f"Starting scan of {self.project_root}")

        # Load cached results if available
        cached_results = self.state_manager.load_state()
        if cached_results:
            logger.info("Using cached results")
            return cached_results

        # Collect files
        files = self._collect_files()
        if not files:
            logger.warning("No files found to analyze")
            return {}

        # Analyze statistics
        stats = self._analyze_statistics(files)

        # Save results
        self.state_manager.save_state(stats)

        return stats

    def _collect_files(self) -> List[Dict]:
        """Collect information about all files."""
        files = []

        with ThreadPoolExecutor(max_workers=DEFAULT_NUM_WORKERS) as executor:
            futures = []

            for dir_name, description in SCAN_DIRS.items():
                dir_path = self.project_root / dir_name
                if not dir_path.exists():
                    continue

                for file_path in dir_path.rglob("*"):
                    if not file_path.is_file():
                        continue

                    if not self.file_analyzer.should_analyze(file_path):
                        continue

                    futures.append(executor.submit(self._analyze_file, file_path))

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        files.append(result)
                except Exception as e:
                    logger.error(f"Error analyzing file: {e}")

        return files

    def _analyze_file(self, file_path: Path) -> Optional[Dict]:
        """Analyze a single file."""
        try:
            # Get basic stats
            stats = self.file_analyzer.get_file_stats(file_path)
            if "error" in stats:
                return None

            # Get language-specific analysis
            with FileUtils.safe_read(file_path) as content:
                if content is None:
                    return None

                analysis = self.language_analyzer.analyze_file(file_path, content)
                if "error" in analysis:
                    return None

            return {
                "path": str(file_path.relative_to(self.project_root)),
                "size": stats["size"],
                "lines": stats["lines"],
                "non_empty_lines": stats["non_empty_lines"],
                "language": analysis["language"],
                "imports": analysis["imports"],
                "functions": analysis["functions"],
                "classes": analysis["classes"],
                "complexity": analysis["complexity"],
            }

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return None

    def _analyze_statistics(self, files: List[Dict]) -> Dict:
        """Analyze file statistics."""
        stats = {
            "file_count": len(files),
            "total_size": sum(f["size"] for f in files),
            "total_lines": sum(f["lines"] for f in files),
            "total_non_empty_lines": sum(f["non_empty_lines"] for f in files),
            "languages": {},
            "imports": self.import_analyzer.analyze_imports(files),
            "large_files": self.size_analyzer.find_large_files(
                files, LARGE_FILE_THRESHOLD_KB
            ),
        }

        # Count files by language
        for file in files:
            lang = file["language"]
            if lang not in stats["languages"]:
                stats["languages"][lang] = {
                    "count": 0,
                    "size": 0,
                    "lines": 0,
                    "complexity": 0,
                }

            stats["languages"][lang]["count"] += 1
            stats["languages"][lang]["size"] += file["size"]
            stats["languages"][lang]["lines"] += file["lines"]
            stats["languages"][lang]["complexity"] += file["complexity"]

        # Add health metrics
        stats["health"] = {
            "memory": self.health_monitor.get_memory_usage(),
            "cpu": self.health_monitor.get_cpu_usage(),
            "disk": self.health_monitor.get_disk_usage(self.project_root),
        }

        return stats
