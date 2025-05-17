import argparse
import ast
import asyncio
import hashlib
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict

# Internal imports (check these for chains leading back to config)
# EDIT START: Keep AppConfig import ONLY for type hint
from dreamos.core.config import AppConfig  # Need AppConfig for type hint

# EDIT END
# Local imports - use relative imports based on actual file structure
# REMOVE: from .analyzer import LanguageAnalyzer  # noqa: E402
# REMOVE: from .file_processor import FileProcessor  # noqa: E402
# REMOVE: from .report_generator import ReportGenerator  # noqa: E402

logger = logging.getLogger(__name__)

# Optional: If tree-sitter grammars are present for Rust/JS/TS
try:
    from tree_sitter import Language, Parser
except ImportError:
    Language, Parser = None, None  # Indicate tree-sitter is unavailable
    logger.warning(
        "⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled."  # noqa: E501
    )

# EDIT START: Define grammar base path relative to project root

# --- REMOVE HELPER AND MODULE-LEVEL PATHS ---
# _PROJECT_ROOT_CACHE: Optional[Path] = None
# def _get_project_root() -> Path:
#     ...
# GRAMMAR_BASE_DIR = _get_project_root() / "runtime" / "tree-sitter-grammars"
# BUILD_LIB_PATH = GRAMMAR_BASE_DIR / "languages.so"
# --- END REMOVE ---

# EDIT END

# ---------------------------------
# Project Config / Cache File Setup
# ---------------------------------
# EDIT START: Remove hardcoded cache file name - will derive from config in main/init\n# CACHE_FILE = \"dependency_cache.json\"  # Original cache name\n# # Define cache path relative to project root\n# CACHE_PATH = PROJECT_ROOT / \".dreamos_cache\" / CACHE_FILE\n# EDIT END


# --- ProjectCache Class --- (Assuming ProjectCache was in utils.py, defining it here temporarily)  # noqa: E501
class ProjectCache:
    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self.cache_lock = threading.Lock()
        self.cache = self._load()

    def _load(self) -> Dict:
        with self.cache_lock:
            if self.cache_path.exists():
                try:
                    with open(self.cache_path, "r") as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(
                        f"Failed to load cache file {self.cache_path}: {e}. Starting fresh."  # noqa: E501
                    )
                    return {}
            return {}

    def _save(self):
        with self.cache_lock:
            try:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_path, "w") as f:
                    json.dump(self.cache, f, indent=2)
            except IOError as e:
                logger.error(f"Failed to save cache file {self.cache_path}: {e}")

    def get(self, key: str) -> Optional[Any]:
        with self.cache_lock:
            return self.cache.get(key)

    def set(self, key: str, value: Any):
        with self.cache_lock:
            self.cache[key] = value
            # Consider debounced/throttled save later if performance is an issue
            self._save()

    def remove(self, key: str):
        with self.cache_lock:
            self.cache.pop(key, None)
            self._save()

    def clear(self):
        with self.cache_lock:
            self.cache = {}
            if self.cache_path.exists():
                try:
                    self.cache_path.unlink()
                    logger.info(f"Cleared cache file: {self.cache_path}")
                except OSError as e:
                    logger.error(f"Failed to delete cache file {self.cache_path}: {e}")

    def analyze_scan_results(self) -> Dict[str, Any]:
        # Implementation here
        # TODO: This method was empty. Consider what analysis it should perform
        # or if it should be removed/repurposed.
        logger.info("ProjectCache.analyze_scan_results called, but not yet implemented.")
        return {}


# ---------------------------------
# Size Analyzer (Integrated from analyzers.py)
# ---------------------------------
class SizeAnalyzer:
    """Analyzes file and directory sizes."""

    @staticmethod
    def get_directory_size(path: Path, file_processor_should_analyze: Callable[[Path], bool]) -> int:
        """Get total size of a directory in bytes, respecting exclusion rules."""
        total = 0
        try:
            for file_path in path.rglob("*"):
                if file_path.is_file() and not file_processor_should_analyze(file_path): # Use passed in checker
                    total += file_path.stat().st_size
        except Exception as e:
            logger.error(f"Error calculating directory size for {path}: {e}")
        return total

    @staticmethod
    def find_large_files(analysis_data: Dict[str, Dict[str, Any]], threshold_kb: int) -> List[Tuple[str, int]]:
        """Find files larger than the threshold from analysis data."""
        large_files = []
        for file_path_str, analysis in analysis_data.items():
            size_bytes = analysis.get("size_bytes") # Assuming size_bytes is stored
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


# ---------------------------------
# Language Analyzer
# ---------------------------------
class LanguageAnalyzer:  # noqa: F811
    """Handles language-specific code analysis for different programming languages."""

    def __init__(self, project_root_for_grammars: Path):
        """Initialize language analyzers and parsers."""
        # EDIT START: Define grammar locations and build library
        # --- MOVED PATH DEFINITION LOGIC HERE ---
        # Determine project root (e.g., pass it in or use find_project_root utility)
        # Using a simple fallback for now, should ideally come from config passed to ProjectScanner
        # REMOVED: try/except block for dreamos.utils.project_root

        # Use the project_root passed from ProjectScanner
        self.grammar_base_dir = (
            project_root_for_grammars / "runtime" / "tree-sitter-grammars"
        )
        self.build_lib_path = (
            self.grammar_base_dir / "languages.so"
        )  # Or .dll on Windows
        # --- END MOVED LOGIC ---

        self.grammar_sources = {
            "python": self.grammar_base_dir / "tree-sitter-python",
            "rust": self.grammar_base_dir / "tree-sitter-rust",
            "javascript": self.grammar_base_dir / "tree-sitter-javascript",
        }
        self.parsers = {}

        if Language and Parser:
            # Ensure the build directory exists
            self.grammar_base_dir.mkdir(parents=True, exist_ok=True)

            # Filter to existing source directories
            available_grammar_paths = [
                str(path) for path in self.grammar_sources.values() if path.is_dir()
            ]

            if available_grammar_paths:
                logger.info(
                    f"Attempting to build tree-sitter library for: {list(self.grammar_sources.keys())}"
                )
                try:
                    Language.build_library(
                        # Store the library in the grammars directory
                        str(self.build_lib_path),
                        # Include paths to the grammar source directories
                        available_grammar_paths,
                    )
                    logger.info(
                        f"Successfully built tree-sitter library at {self.build_lib_path}"
                    )
                    # _load_parsers_from_library is now async, so cannot be directly awaited in sync __init__
                    # This implies it should be part of an async initialization step.
                    # For now, we can schedule it if an event loop is running, or call it from an async method.
                    # Simplest for now: if an event loop is running, create a task.
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(self._load_parsers_from_library())
                        logger.debug(
                            "Scheduled _load_parsers_from_library in __init__."
                        )
                    except RuntimeError:  # No running event loop
                        logger.warning(
                            "No running asyncio event loop in LanguageAnalyzer.__init__ to schedule parser loading."
                        )
                        # Parsers will need to be loaded explicitly via an async method later.
                except Exception as e:
                    logger.error(
                        f"⚠️ Failed to build or load tree-sitter library: {e}",
                        exc_info=True,
                    )
                    logger.warning("Falling back to AST-based parsing where available.")
            else:
                logger.warning(
                    "No tree-sitter grammar source directories found. AST parsing disabled."
                )
        else:
            logger.warning("tree-sitter package not found. AST parsing disabled.")

    async def _load_parsers_from_library(self):
        """Loads parsers for available languages from the built library. Async path check."""
        if (
            not await asyncio.to_thread(self.build_lib_path.exists)
            or not Language
            or not Parser
        ):
            if not Language or not Parser:
                logger.debug(
                    "tree-sitter Language or Parser not available for _load_parsers_from_library."
                )
            else:
                logger.debug(
                    f"Built library path {self.build_lib_path} does not exist. Cannot load parsers."
                )
            return

        for lang_name in self.grammar_sources.keys():
            try:
                lang_lib = Language(str(self.build_lib_path), lang_name)
                parser = Parser()
                parser.set_language(lang_lib)
                self.parsers[lang_name] = parser
                logger.info(f"Initialized tree-sitter parser for {lang_name}.")
            except Exception as e:
                logger.warning(
                    f"⚠️ Failed to load {lang_name} grammar from library {self.build_lib_path}: {e}"
                )

    def analyze_file(self, file_path: Path, source_code: str) -> Dict:
        """
        Analyzes source code based on file extension.

        Args:
            file_path: Path to the source file
            source_code: Contents of the source file

        Returns:
            Dict with structure {language, functions, classes, routes, complexity}
        """
        suffix = file_path.suffix.lower()

        # Prioritize tree-sitter if available
        if suffix == ".py" and "python" in self.parsers:
            return self._analyze_with_tree_sitter("python", source_code)
        elif suffix == ".rs" and "rust" in self.parsers:
            return self._analyze_with_tree_sitter("rust", source_code)
        elif (
            suffix in [".js", ".ts"] and "javascript" in self.parsers
        ):  # Added tsx, jsx
            # Use JS parser for TS/JSX as well (common practice)
            return self._analyze_with_tree_sitter("javascript", source_code)

        # Fallback to AST or basic analysis
        elif suffix == ".py":
            return self._analyze_python_ast(source_code)  # Renamed original method
        else:
            return {
                "language": suffix.lstrip("."),  # Store lang name without dot
                "functions": [],
                "classes": {},
                "routes": [],
                "complexity": 0,
                "parser_used": "basic",
            }

    def _analyze_python_ast(
        self, source_code: str
    ) -> Dict:  # Renamed from _analyze_python
        """
        Analyzes Python source code using the builtin `ast` module.
        Extracts a naive list of function defs, classes, routes, complexity, etc.
        """
        functions = []
        classes = {}
        routes = [] # For web framework route detection
        imports = [] # Enhanced import tracking
        complexity = 0

        try:
            tree = ast.parse(source_code)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            "type": "import",
                            "name": alias.name,
                            "asname": alias.asname,
                            "line": node.lineno
                        })
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module if node.module else ""
                    for alias in node.names:
                        imports.append({
                            "type": "from_import",
                            "module": module_name,
                            "name": alias.name,
                            "asname": alias.asname,
                            "level": node.level,
                            "line": node.lineno
                        })
                elif isinstance(node, ast.FunctionDef):
                    # Basic function info
                    func_info = {
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "returns": ast.unparse(node.returns) if node.returns else None,
                        "decorators": [d.id for d in node.decorator_list if isinstance(d, ast.Name)], # Simplified
                        "line": node.lineno
                    }
                    functions.append(func_info)
                    complexity += 1 # Simple complexity: count functions

                    # Basic route detection (example for Flask/FastAPI style)
                    for decorator in node.decorator_list:
                        # Check for @app.route('/path') or @router.get('/path') patterns
                        if isinstance(decorator, ast.Call):
                            call_func = decorator.func
                            # @app.route(), @blueprint.route()
                            if isinstance(call_func, ast.Attribute) and call_func.attr in ["route", "get", "post", "put", "delete", "patch"]:
                                route_path = "/unknown"
                                route_methods = [call_func.attr.upper()] if call_func.attr != "route" else ["GET"] # Default for .route

                                if decorator.args: # First arg is usually path
                                    path_arg_node = decorator.args[0]
                                    if isinstance(path_arg_node, ast.Constant) and isinstance(path_arg_node.value, str):
                                        route_path = path_arg_node.value
                                
                                # Check for 'methods' keyword argument
                                for kw in decorator.keywords:
                                    if kw.arg == 'methods' and isinstance(kw.value, (ast.List, ast.Tuple)):
                                        current_methods = []
                                        for elt in kw.value.elts:
                                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                                current_methods.append(elt.value.upper())
                                        if current_methods: route_methods = current_methods
                                
                                for method in route_methods:
                                    routes.append({
                                        "function": node.name,
                                        "method": method,
                                        "path": route_path,
                                        "line": decorator.lineno
                                    })
                elif isinstance(node, ast.ClassDef):
                    class_methods = []
                    for body_item in node.body:
                        if isinstance(body_item, ast.FunctionDef):
                            class_methods.append(body_item.name)
                            complexity +=1 # Add methods to complexity
                    
                    classes[node.name] = {
                        "methods": class_methods,
                        "bases": [ast.unparse(b) for b in node.bases],
                        "decorators": [d.id for d in node.decorator_list if isinstance(d, ast.Name)],
                        "docstring": ast.get_docstring(node),
                        "line": node.lineno
                    }
            
            # More sophisticated complexity (e.g. McCabe) could be added here
            # For now, simple sum of functions and methods
            
        except SyntaxError as e:
            logger.warning(f"Syntax error parsing Python AST: {e}")
            return {
                "language": "python",
                "error": str(e),
                "functions": [],
                "classes": {},
                "imports": [],
                "routes": [],
                "complexity": 0,
            }

        return {
            "language": "python",
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "routes": routes,
            "complexity": complexity,
        }

    def _analyze_with_tree_sitter(self, lang_name: str, source_code: str) -> Dict:
        """Analyzes code using the appropriate tree-sitter parser."""
        parser = self.parsers.get(lang_name)
        if not parser:
            return {  # Should not happen if called correctly, but safeguard
                "language": lang_name,
                "functions": [],
                "classes": {},
                "routes": [],
                "complexity": 0,
                "parser_used": "treesitter_unavailable",
            }

        try:
            tree = parser.parse(bytes(source_code, "utf8"))
            # TODO: Implement actual analysis based on tree-sitter nodes
            # This requires language-specific queries or traversal logic
            # Placeholder implementation:
            functions = []  # Extract functions using queries/traversal
            classes = {}  # Extract classes
            routes = []  # Extract routes (if applicable to lang)
            complexity = tree.root_node.descendant_count  # Example complexity metric

            return {
                "language": lang_name,
                "functions": functions,  # Placeholder
                "classes": classes,  # Placeholder
                "routes": routes,  # Placeholder
                "complexity": complexity,
                "parser_used": "treesitter",
            }
        except Exception as e:
            logger.warning(
                f"Tree-sitter parsing failed for {lang_name}: {e}", exc_info=True
            )
            return {
                "language": lang_name,
                "functions": [],
                "classes": {},
                "routes": [],
                "complexity": 0,
                "parser_used": "treesitter_failed",
                "error": str(e),
            }


# ---------------------------------
# FileProcessor
# ---------------------------------
class FileProcessor:  # noqa: F811
    SUPPORTED_EXTENSIONS = {".py", ".rs", ".js", ".ts", ".tsx", ".jsx", ".md", ".json", ".yaml", ".yml", ".toml", ".sh", ".rst"} # Example, make configurable
    DEFAULT_IGNORE_DIRS = {
        ".git",
        "__pycache__",
        "node_modules",
        "venv",
        "target", # Rust build artifacts
        "build", "dist", # Python build artifacts
        ".DS_Store",
        ".pytest_cache",
        ".mypy_cache",
        "htmlcov", # Coverage reports
        # Common data/log folders that might be in project root
        "data", "logs", "output", "results", "temp", "tmp",
        "static", "media", # Django/Flask static/media folders
        "docs", # Often build artifacts or large generated docs
        "examples", # Sometimes can be excluded
        "tests", # Depending on scan purpose, might be excluded
        ".vscode", ".idea", ".devcontainer", # IDE specific
    }
    DEFAULT_IGNORE_FILES = {
        "poetry.lock", "package-lock.json", "yarn.lock", # Lock files
        # Large data files that might be accidentally committed
        # Add specific large data file names if necessary
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
        self.additional_ignore_dirs = additional_ignore_dirs
        self.use_cache = use_cache

    def hash_file(self, file_path: Path) -> str:
        try:
            with file_path.open("rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def should_exclude(self, file_path: Path) -> bool:
        # Normalize path for consistent comparisons
        fp_norm = file_path.resolve()
        project_root_norm = self.project_root.resolve()

        # Ignore if outside project root (e.g. symlinks pointing out)
        try:
            fp_norm.relative_to(project_root_norm)
        except ValueError:
            logger.debug(f"Excluding file outside project root: {file_path}")
            return True
            
        name = file_path.name
        path_str = str(file_path) # For substring checks if needed

        # 1. Check explicit ignore_files set
        if name in self.ignore_files:
            logger.debug(f"Excluding by ignore_files set: {file_path}")
            return True

        # 2. Check explicit ignore_dirs set (any part of the path)
        # Convert to strings for 'in' check against parts
        str_ignore_dirs = {str(d) for d in self.additional_ignore_dirs}
        # Also check default ignore dirs by name
        str_default_ignore_dirs_names = self.DEFAULT_IGNORE_DIRS

        for part in file_path.parts:
            if part in str_ignore_dirs or part in str_default_ignore_dirs_names:
                logger.debug(f"Excluding by ignore_dirs (part: {part}): {file_path}")
                return True
        
        # 3. Check .gitignore (if AppConfig provides it)
        # This part needs AppConfig to be available or a gitignore parser
        # For now, skipping direct .gitignore parsing here for simplicity in this standalone class.
        # This functionality is often better handled by the ProjectScanner class that has config access.

        # 4. Check file extension (allowlist)
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            logger.debug(f"Excluding by unsupported extension: {file_path}")
            return True
            
        # 5. Check if it's a directory (we only process files)
        if not file_path.is_file():
            logger.debug(f"Excluding non-file: {file_path}")
            return True

        return False

    def process_file(
        self, file_path: Path, language_analyzer: LanguageAnalyzer
    ) -> Optional[tuple]:
        if self.should_exclude(file_path):
            return None

        file_hash = self.hash_file(file_path)
        # Use relative path for cache key for portability
        try:
            cache_key = str(file_path.relative_to(self.project_root))
        except ValueError: # Should not happen if should_exclude checks for outside project root
             logger.warning(f"File {file_path} seems outside project root {self.project_root}, skipping.")
             return None

        # Check cache
        with self.cache_lock:
            cached_entry = self.cache.get(cache_key)
            if (
                isinstance(cached_entry, dict)
                and cached_entry.get("hash") == file_hash
            ):
                # File is in cache and hash matches.
                # If analysis is also in cache, we could return it.
                # For now, mirroring original logic: if hash matches, skip reprocessing.
                # The calling ProjectScanner._determine_files_to_process_sync will load analysis from cache.
                return None  # Indicates file is cached and unchanged

        # Process the file if cache is disabled, or if enabled and file not cached/changed, or hash failed
        try:
            # Ensure file_path is absolute for opening
            abs_file_path = (self.project_root / cache_key).resolve()
            with abs_file_path.open("r", encoding="utf-8") as f:
                source_code = f.read()
        except UnicodeDecodeError:
            logger.warning(f"Skipping file due to decoding error: {file_path}")
            return (cache_key, {"error": "UnicodeDecodeError"})
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
            return (cache_key, {"error": f"FileReadError: {e}"})

        analysis_result = language_analyzer.analyze_file(file_path, source_code)

        if (
            self.use_cache and file_hash
        ):  # Only update cache if enabled and hashing was successful
            with self.cache_lock:
                # Store hash and analysis result
                self.cache[cache_key] = {
                    "hash": file_hash,
                    "analysis": analysis_result,
                    "size_bytes": abs_file_path.stat().st_size,
                    "line_count": len(source_code.splitlines()),
                }

        return (cache_key, self.cache[cache_key]["analysis"])


# ---------------------------------
# ReportGenerator (Merges Old + New)
# ---------------------------------
class ReportGenerator:  # noqa: F811
    """Handles merging new analysis into existing project_analysis.json and chatgpt context."""  # noqa: E501

    def __init__(
        self,
        project_root: Path,
        analysis: Dict[str, Dict],
        analysis_output_path: Path,
        context_output_path: Path,
    ):
        self.project_root = project_root
        self.analysis = (
            analysis  # e.g., { 'subdir/file.py': {language:..., classes:...}, ... }
        )
        # Store paths
        self.report_path = analysis_output_path
        self.context_path = context_output_path

    def load_existing_report(self, report_path: Path) -> Dict[str, Any]:
        """Loads any existing project_analysis.json to preserve old entries."""
        # Use the passed path directly
        if report_path.exists():
            try:
                with report_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading existing report {report_path}: {e}")
        return {}

    def save_report(self):
        """
        Merge new analysis results into old project_analysis.json, then write it out.
        Old data is kept; new files are added or updated.
        Uses self.report_path.
        """
        # Use stored path
        report_path = self.report_path
        existing = self.load_existing_report(report_path)

        # Merge logic: new data overrides old entries with the same filename,
        # but preserves any old entries for files not in the current scan.
        merged = {**existing, **self.analysis}

        # Ensure parent directory exists
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(merged, f, indent=4)

        logger.info(f"✅ Project analysis updated and saved to {report_path}")

    def generate_init_files(self, overwrite: bool = True):
        """Auto-generate __init__.py for all Python packages based on self.analysis."""
        from collections import defaultdict

        package_modules = defaultdict(list)
        for rel_path in self.analysis.keys():
            if rel_path.endswith(".py"):
                file_path = Path(rel_path)
                if file_path.name == "__init__.py":
                    continue
                package_dir = file_path.parent
                module_name = file_path.stem
                package_modules[str(package_dir)].append(module_name)

        for package, modules in package_modules.items():
            package_path = self.project_root / package
            init_file = package_path / "__init__.py"
            package_path.mkdir(parents=True, exist_ok=True)

            lines = [
                "# AUTO-GENERATED __init__.py",
                "# DO NOT EDIT MANUALLY - changes may be overwritten\n",
            ]
            for module in sorted(modules):
                lines.append(f"from . import {module}")
            lines.append("\n__all__ = [")
            for module in sorted(modules):
                lines.append(f"    '{module}',")
            lines.append("]\n")
            content = "\n".join(lines)

            if overwrite or not init_file.exists():
                with init_file.open("w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"✅ Generated __init__.py in {package_path}")
            else:
                logger.info(f"ℹ️ Skipped {init_file} (already exists)")

    def load_existing_chatgpt_context(
        self,
    ) -> Dict[str, Any]:  # REMOVED context_path argument
        """Load any existing chatgpt_project_context.json using self.context_path."""
        # Use stored path
        context_path = self.context_path
        if context_path.exists():
            try:
                with context_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading existing ChatGPT context: {e}")
        return {}

    def export_chatgpt_context(self, template_path: Optional[str] = None):
        """
        Merges current analysis details with old chatgpt_project_context.json.
        Uses self.context_path.
        If no template, write JSON. Else use Jinja to render a custom format.
        """
        # Use stored path
        context_path = self.context_path
        context_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"💾 Writing ChatGPT context to: {context_path}")

        # If no template, do direct JSON merging
        if not template_path:
            existing_context = self.load_existing_chatgpt_context()
            payload = {
                "project_root": str(self.project_root),
                "num_files_analyzed": len(self.analysis),
                "analysis_details": self.analysis,
            }
            # New data overrides same keys, but preserves everything else.
            merged_context = {**existing_context, **payload}
            try:
                with context_path.open("w", encoding="utf-8") as f:
                    json.dump(merged_context, f, indent=4)
                logger.info(f"✅ Merged ChatGPT context saved to: {context_path}")
            except Exception as e:
                logger.error(f"❌ Error writing ChatGPT context: {e}")
            return

        # If we do have a template, we can still load old data, but we'll not attempt JSON merging.  # noqa: E501
        # We'll just produce a final rendered template containing the new analysis.
        try:
            from jinja2 import Template

            with open(template_path, "r", encoding="utf-8") as tf:
                template_content = tf.read()
            t = Template(template_content)

            # Could load existing context if you want. We'll skip that for Jinja scenario.  # noqa: E501
            context_dict = {
                "project_root": str(self.project_root),
                "analysis": self.analysis,
                "num_files_analyzed": len(self.analysis),
            }
            rendered = t.render(context=context_dict)
            with context_path.open("w", encoding="utf-8") as outf:
                outf.write(rendered)
            logger.info(f"✅ Rendered ChatGPT context to: {context_path}")
        except ImportError:
            logger.error("⚠️ Jinja2 not installed. Run `pip install jinja2` and re-try.")
        except Exception as e:
            logger.error(f"❌ Error rendering Jinja template: {e}")

    def categorize_agents(self):
        """Placeholder method for agent categorization logic.

        TODO: Implement logic to analyze self.analysis data
              and identify/categorize potential agents.
              Update self.analysis with categorization results if desired.
        """
        logger.warning(
            "Agent categorization logic is not yet implemented in ReportGenerator.categorize_agents."  # noqa: E501
        )
        # Example placeholder logic (does nothing useful yet):
        agent_count = 0
        for file_path, data in self.analysis.items():
            if "agent" in file_path.lower():  # Very naive check
                agent_count += 1
        logger.info(
            f"Placeholder categorization: Found {agent_count} potential agent files (naive check)."  # noqa: E501
        )
        # Ensure report is saved even if categorization does nothing yet
        self.save_report()


# ---------------------------------
# ProjectScanner
# ---------------------------------
class ProjectScanner:
    """
    Orchestrates the project scanning process using modular components.
    Responsibilities:
      - Initializes all components (analyzer, processor, reporter, concurrency manager).
      - Loads and saves the file hash cache (if enabled).
      - Discovers files to be scanned.
      - Detects moved files based on hash (if cache enabled).
      - Manages asynchronous file processing via MultibotManager.
      - Gathers results and passes them to the ReportGenerator.
      - Provides methods to trigger optional steps like __init__ generation or context export.
    """  # noqa: E501

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
        self.additional_ignore_dirs = additional_ignore_dirs or set() # Assign additional_ignore_dirs

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

    # EDIT START: Add helper for path resolution
    def _resolve_path_from_config(
        self,
        config_path_attr: Optional[Path | str],
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

    # EDIT END

    async def _discover_files_async(self) -> List[Path]:
        """Discover all relevant files in the project asynchronously."""
        # ... implementation uses self.project_root ...
        pass

    async def scan_project(
        self,
        progress_callback: Optional[Callable] = None,
        num_workers: int = 4,
        force_rescan_patterns: Optional[List[str]] = None,
    ):
        """Scan project files, analyze them, and store results."""
        await self.language_analyzer._load_parsers_from_library()
        logger.info(f"Starting project scan in {self.project_root}...")
        # ... rest of implementation ...
        pass

    # ... other methods ...

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

        name_definitions = defaultdict(list) # name -> list of file paths

        for file_path_str, data in self.analysis.items():
            if not data:
                continue
            
            # Collect function names
            if data.get("functions"):
                for func_info in data.get("functions", []):
                    if isinstance(func_info, dict) and func_info.get("name"):
                        name_definitions[func_info["name"]].append(file_path_str)
                    elif isinstance(func_info, str): # Old format
                         name_definitions[func_info].append(file_path_str)
            
            # Collect class names
            if data.get("classes"):
                for class_name in data.get("classes", {}).keys():
                    name_definitions[class_name].append(file_path_str)

        collisions = []
        for name, paths in name_definitions.items():
            if len(paths) > 1:
                collisions.append({"name": name, "files": sorted(list(set(paths)))}
        )
        
        if collisions:
            logger.info(f"Found {len(collisions)} potential name collisions.")
            # Optionally log collisions to the report
            # self.report_generator.add_collisions_to_report(collisions) # If such method exists
        else:
            logger.info("No significant name collisions found.")
            
        return sorted(collisions, key=lambda x: x["name"])


async def main():
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
        help='Directory or file patterns to exclude (can be used multiple times). Example: --exclude node_modules --exclude "*.log"',  # noqa: E501
    )
    parser.add_argument(
        "--force-rescan",
        action="append",
        default=[],
        help='Glob patterns for files to forcibly rescan even if unchanged (e.g., "**/config.py").',  # noqa: E501
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
    start_time = asyncio.get_event_loop().time() if hasattr(asyncio, 'get_event_loop') else time.time() # time module needs import

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
            # force_rescan_patterns=args.force_rescan # If you add this arg
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


# EDIT START: Remove duplicate find_project_root if no longer needed
# def find_project_root(marker: str = ".git") -> Path:
#     """Finds the project root by searching upwards for a marker file/directory.""" # noqa
#     current_path = Path(__file__).resolve()
#     while current_path != current_path.parent:
#         if (current_path / marker).exists():
#             return current_path
#         current_path = current_path.parent
#     raise FileNotFoundError(f"Project root marker '{marker}' not found.")
# EDIT END

if __name__ == "__main__":
    # If main is async, it needs to be run with asyncio.run()
    asyncio.run(main())
