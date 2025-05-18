"""
Project scanner module for Dream.OS.

This module provides the main ProjectScanner class that orchestrates the project scanning process.
"""

import asyncio
import logging
import threading
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

# Import for type annotations only
from dreamos.core.config import AppConfig

# Import modularized components
from .cache import ProjectCache
from .file_processor import FileProcessor
from .language_analyzer import LanguageAnalyzer
from .report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class ProjectScanner:
    """
    Orchestrates the project scanning process using modular components.
    Responsibilities:
      - Initializes all components (analyzer, processor, reporter, concurrency manager).
      - Loads and saves the file hash cache (if enabled).
      - Discovers files to be scanned.
      - Detects moved files based on hash (if cache enabled).
      - Manages asynchronous file processing.
      - Gathers results and passes them to the ReportGenerator.
      - Provides methods to trigger optional steps like __init__ generation or context export.
    """

    DEFAULT_SCAN_DIRS = ["."]
    DEFAULT_IGNORE_DIRS = FileProcessor.DEFAULT_IGNORE_DIRS
    DEFAULT_IGNORE_FILES = FileProcessor.DEFAULT_IGNORE_FILES
    DEFAULT_SUPPORTED_EXTENSIONS = FileProcessor.SUPPORTED_EXTENSIONS

    def __init__(
        self,
        config: Optional[AppConfig],  # Accept AppConfig instance, can be None
        project_root: Optional[Path] = None,
        additional_ignore_dirs: Optional[Set[str]] = None,
        use_cache: bool = True,
        # Add new args for CLI overrides
        cli_override_cache_file: Optional[Path] = None,
        cli_override_analysis_output_path: Optional[Path] = None,
        cli_override_context_output_path: Optional[Path] = None
    ):
        self.config = config
        self.project_root = (project_root or (Path(config.paths.project_root) if config and hasattr(config, 'paths') and config.paths.project_root else Path.cwd())).resolve()
        logger.info(f"ProjectScanner initialized with project root: {self.project_root}")

        self.use_cache = use_cache  # Assign use_cache parameter to instance attribute
        self.additional_ignore_dirs = additional_ignore_dirs or set()  # Assign additional_ignore_dirs

        # Determine paths: CLI override > AppConfig > Default
        self.cache_file_path = cli_override_cache_file or self._resolve_path_from_config(
            getattr(config, "scanner_cache_file", None) if config else None,
            self.project_root / ".dreamos_cache" / "project_scan_cache.json",
            "Scanner cache file"
        )
        self.analysis_output_path = cli_override_analysis_output_path or self._resolve_path_from_config(
            getattr(config, "scanner_analysis_report_file", None) if config else None,
            self.project_root / "runtime" / "reports" / "project_scan_report.md",
            "Analysis report output file"
        )
        self.context_output_path = cli_override_context_output_path or self._resolve_path_from_config(
            getattr(config, "scanner_chatgpt_context_file", None) if config else None,
            self.project_root / "runtime" / "reports" / "project_context.json",
            "ChatGPT context output file"
        )

        # Ensure cache directory exists
        if self.use_cache:
            self.cache_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Instantiate ProjectCache with resolved path
        self.cache = (
            ProjectCache(cache_path=self.cache_file_path) if self.use_cache else None
        )

        # Initialize LanguageAnalyzer - it now determines grammar paths internally
        self.language_analyzer = LanguageAnalyzer(project_root_for_grammars=self.project_root)

        self.analysis: Dict[str, Dict] = {}
        self._scan_results_lock = threading.Lock()

    def _resolve_path_from_config(
        self,
        config_path_attr: Optional[Union[Path, str]],
        default_path: Path,
        description: str,
    ) -> Path:
        """Resolves a path, prioritizing config, using default, ensuring absolute."""
        path_to_use = None
        if config_path_attr:
            # Handle both Path and string types from config
            path_to_use = Path(config_path_attr)
            logger.debug(f"Using configured path for {description}: {path_to_use}")
        else:
            path_to_use = default_path
            logger.debug(f"Using default path for {description}: {path_to_use}")

        if not path_to_use.is_absolute():
            path_to_use = (self.project_root / path_to_use).resolve()
            logger.debug(f"Resolved relative path for {description} to: {path_to_use}")
        else:
            path_to_use = path_to_use.resolve()

        # Ensure parent directory exists for output files
        try:
            path_to_use.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(
                f"Failed to create parent directory for {description} path {path_to_use}: {e}"
            )
            # Decide if this is critical, maybe raise?

        return path_to_use

    async def _discover_files_async(self) -> List[Path]:
        """Discover all relevant files in the project asynchronously."""
        file_processor = FileProcessor(
            project_root=self.project_root,
            cache={},  # Empty cache for this operation
            cache_lock=threading.Lock(),
            additional_ignore_dirs=self.additional_ignore_dirs,
            use_cache=False,
        )
        
        all_files = []
        for scan_dir in self.DEFAULT_SCAN_DIRS:
            root_dir = self.project_root / scan_dir if scan_dir != "." else self.project_root
            if not root_dir.exists():
                logger.warning(f"Scan directory {root_dir} does not exist, skipping")
                continue
                
            for file_path in root_dir.rglob("*"):
                if file_path.is_file() and not file_processor.should_exclude(file_path):
                    all_files.append(file_path)
                    
        logger.info(f"Discovered {len(all_files)} files to scan")
        return all_files

    async def scan_project(
        self,
        progress_callback: Optional[Callable] = None,
        num_workers: int = 4,
        force_rescan_patterns: Optional[List[str]] = None,
    ):
        """Scan project files, analyze them, and store results."""
        await self.language_analyzer._load_parsers_from_library()
        logger.info(f"Starting project scan in {self.project_root}...")
        
        # Discover files
        files_to_scan = await self._discover_files_async()
        total_files = len(files_to_scan)
        
        if total_files == 0:
            logger.warning("No files found to scan!")
            return
            
        # Create file processor
        file_processor = FileProcessor(
            project_root=self.project_root,
            cache=self.cache.cache if self.cache else {},
            cache_lock=self._scan_results_lock,
            additional_ignore_dirs=self.additional_ignore_dirs,
            use_cache=self.use_cache,
        )
        
        # Process files
        self.analysis = {}
        completed = 0
        
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(num_workers)
        
        async def process_file_task(file_path):
            async with semaphore:
                # This makes the file processing non-blocking
                result = await asyncio.to_thread(
                    file_processor.process_file, file_path, self.language_analyzer
                )
                
                nonlocal completed
                completed += 1
                if progress_callback:
                    percent = (completed / total_files) * 100
                    progress_callback(percent, file_path)
                
                return result
        
        # Create and gather tasks for all files
        tasks = [process_file_task(file_path) for file_path in files_to_scan]
        results = await asyncio.gather(*tasks)
        
        # Collect results
        for result in results:
            if result:
                file_path_str, analysis_data = result
                with self._scan_results_lock:
                    self.analysis[file_path_str] = analysis_data
        
        logger.info(f"Completed analysis of {len(self.analysis)} files")
        
        # Generate reports
        report_generator = ReportGenerator(
            project_root=self.project_root,
            analysis=self.analysis,
            analysis_output_path=self.analysis_output_path,
            context_output_path=self.context_output_path,
        )
        
        report_generator.save_report()
        report_generator.export_chatgpt_context()
        
        logger.info("Project scan completed successfully.")

    def find_name_collisions(self, scan_path: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
        """
        Finds potential name collisions for functions and classes across analyzed files.
        Args:
            scan_path: Optional specific path to limit collision search (not implemented yet, scans all results).
        Returns:
            A list of dictionaries, where each dictionary represents a collided name
            and contains the name and a list of file paths where it's defined.
        """
        if not self.analysis:
            logger.warning("Analysis data not available. Run scan_project() first.")
            return []

        name_definitions = defaultdict(list)  # name -> list of file paths

        for file_path_str, data in self.analysis.items():
            if not data:
                continue
            
            # Collect function names
            if data.get("functions"):
                for func_info in data.get("functions", []):
                    if isinstance(func_info, dict) and func_info.get("name"):
                        name_definitions[func_info["name"]].append(file_path_str)
                    elif isinstance(func_info, str):  # Old format
                         name_definitions[func_info].append(file_path_str)
            
            # Collect class names
            if data.get("classes"):
                for class_name in data.get("classes", {}).keys():
                    name_definitions[class_name].append(file_path_str)

        collisions = []
        for name, paths in name_definitions.items():
            if len(paths) > 1:
                collisions.append({"name": name, "files": sorted(list(set(paths)))})
        
        if collisions:
            logger.info(f"Found {len(collisions)} potential name collisions.")
        else:
            logger.info("No significant name collisions found.")
            
        return sorted(collisions, key=lambda x: x["name"]) 