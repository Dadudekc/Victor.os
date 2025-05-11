import argparse
import ast
import asyncio
import hashlib
import json
import logging
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Internal imports (check these for chains leading back to config)
# EDIT START: Keep AppConfig import ONLY for type hint
from dreamos.core.config import AppConfig  # Need AppConfig for type hint

# EDIT END
# Local imports - use relative imports based on actual file structure
from .analyzer import LanguageAnalyzer  # noqa: E402
from .file_processor import FileProcessor  # noqa: E402
from .report_generator import ReportGenerator  # noqa: E402

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
        pass


# ---------------------------------
# Language Analyzer
# ---------------------------------
class LanguageAnalyzer:  # noqa: F811
    """Handles language-specific code analysis for different programming languages."""

    def __init__(self):
        """Initialize language analyzers and parsers."""
        # EDIT START: Define grammar locations and build library
        # --- MOVED PATH DEFINITION LOGIC HERE ---
        # Determine project root (e.g., pass it in or use find_project_root utility)
        # Using a simple fallback for now, should ideally come from config passed to ProjectScanner
        try:
            from dreamos.utils.project_root import find_project_root

            project_root_for_grammars = find_project_root()
        except Exception as e:
            project_root_for_grammars = Path(__file__).resolve().parents[4]  # Fallback
            logger.warning(
                f"Failed to find project root for grammar paths, using fallback: {project_root_for_grammars}, error: {e}"
            )

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
        try:
            tree = ast.parse(source_code)
            functions = []
            classes = {}
            routes = []
            complexity = 0  # Basic complexity count (nodes)

            for node in ast.walk(tree):
                complexity += 1
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)

                    # Route detection (Flask/FastAPI style) from existing logic
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call) and hasattr(
                            decorator.func, "attr"
                        ):
                            func_attr = decorator.func.attr.lower()
                            if func_attr in {
                                "route",
                                "get",
                                "post",
                                "put",
                                "delete",
                                "patch",
                            }:
                                path_arg = "/unknown"
                                methods = [func_attr.upper()]
                                if decorator.args:
                                    arg0 = decorator.args[0]
                                    if isinstance(arg0, ast.Str):
                                        path_arg = arg0.s
                                # Check for "methods" kwarg
                                for kw in decorator.keywords:
                                    if kw.arg == "methods" and isinstance(
                                        kw.value, ast.List
                                    ):
                                        extracted_methods = []
                                        for elt in kw.value.elts:
                                            if isinstance(elt, ast.Str):
                                                extracted_methods.append(elt.s.upper())
                                        if extracted_methods:
                                            methods = extracted_methods
                                for m in methods:
                                    routes.append(
                                        {
                                            "function": node.name,
                                            "method": m,
                                            "path": path_arg,
                                        }
                                    )

                elif isinstance(node, ast.ClassDef):
                    docstring = ast.get_docstring(node)
                    method_names = [
                        n.name for n in node.body if isinstance(n, ast.FunctionDef)
                    ]
                    base_classes = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_classes.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            base_parts = []
                            attr_node = base
                            while isinstance(attr_node, ast.Attribute):
                                base_parts.append(attr_node.attr)
                                attr_node = attr_node.value
                            if isinstance(attr_node, ast.Name):
                                base_parts.append(attr_node.id)
                            base_classes.append(".".join(reversed(base_parts)))
                        else:
                            base_classes.append(None)
                    classes[node.name] = {
                        "methods": method_names,
                        "docstring": docstring,
                        "base_classes": base_classes,
                    }

            return {
                "language": "python",
                "functions": functions,
                "classes": classes,
                "routes": routes,
                "complexity": complexity,
                "parser_used": "ast",
            }
        except SyntaxError as e:
            logger.warning(f"Python AST parsing failed: {e}")
            return {
                "language": "python",
                "functions": [],
                "classes": {},
                "routes": [],
                "complexity": 0,
                "parser_used": "ast_failed",
                "error": str(e),
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
    """Handles file hashing, ignoring, caching checks, etc."""

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
        """Exclude logic for venvs, node_modules, .git, etc."""
        # Common virtual environment patterns
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
            # Common Conda environment locations
            "envs",
            "conda-env",
            ".conda-env",
            # Poetry virtual environments
            ".poetry/venv",
            ".poetry-venv",
        }

        default_exclude_dirs = {
            "__pycache__",
            "node_modules",
            "migrations",
            "build",
            "target",
            ".git",
            "coverage",
            "chrome_profile",
        } | venv_patterns  # Merge with venv patterns

        file_abs = file_path.resolve()

        # Check if this is the scanner itself
        try:
            if file_abs == Path(__file__).resolve():
                return True
        except NameError:
            pass

        # Check additional ignore directories
        for ignore in self.additional_ignore_dirs:
            ignore_path = Path(ignore)
            if not ignore_path.is_absolute():
                ignore_path = (self.project_root / ignore_path).resolve()
            try:
                file_abs.relative_to(ignore_path)
                return True
            except ValueError:
                continue

        # Check for virtual environment indicators
        try:
            # Look for pyvenv.cfg or similar files that indicate a venv
            if any(p.name == "pyvenv.cfg" for p in file_abs.parents):
                return True

            # Look for bin/activate or Scripts/activate.bat
            for parent in file_abs.parents:
                if (parent / "bin" / "activate").exists() or (
                    parent / "Scripts" / "activate.bat"
                ).exists():
                    return True
        except (OSError, PermissionError):
            # Handle permission errors gracefully
            pass

        # Check for excluded directory names in the path
        if any(excluded in file_path.parts for excluded in default_exclude_dirs):
            return True

        # Check for common virtual environment path patterns
        path_str = str(file_abs).lower()
        if any(
            f"/{pattern}/" in path_str.replace("\\", "/") for pattern in venv_patterns
        ):
            return True

        return False

    def process_file(
        self, file_path: Path, language_analyzer: LanguageAnalyzer
    ) -> Optional[tuple]:
        """Analyzes a file. If use_cache is True, checks cache first and updates it."""
        relative_path = str(file_path.relative_to(self.project_root)).replace(
            "\\\\", "/"
        )
        file_hash_val = None

        if self.use_cache:
            file_hash_val = self.hash_file(file_path)
            if not file_hash_val:  # Failed to hash
                logger.warning(
                    f"Could not hash file {file_path}, processing it directly."
                )
            else:
                with self.cache_lock:
                    cached_entry = self.cache.get(relative_path)
                    if (
                        isinstance(cached_entry, dict)
                        and cached_entry.get("hash") == file_hash_val
                    ):
                        # File is in cache and hash matches.
                        # If analysis is also in cache, we could return it.
                        # For now, mirroring original logic: if hash matches, skip reprocessing.
                        # The calling ProjectScanner._determine_files_to_process_sync will load analysis from cache.
                        return None  # Indicates file is cached and unchanged

        # Process the file if cache is disabled, or if enabled and file not cached/changed, or hash failed
        try:
            # Ensure file_path is absolute for opening
            abs_file_path = (self.project_root / relative_path).resolve()
            with abs_file_path.open("r", encoding="utf-8") as f:
                source_code = f.read()
        except UnicodeDecodeError:
            logger.warning(f"Skipping file due to decoding error: {file_path}")
            return (relative_path, {"error": "UnicodeDecodeError"})
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
            return (relative_path, {"error": f"FileReadError: {e}"})

        analysis_result = language_analyzer.analyze_file(file_path, source_code)

        if (
            self.use_cache and file_hash_val
        ):  # Only update cache if enabled and hashing was successful
            with self.cache_lock:
                # Store hash and analysis result
                self.cache[relative_path] = {
                    "hash": file_hash_val,
                    "analysis": analysis_result,
                }

        return (relative_path, analysis_result)


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

    def __init__(
        self,
        config: AppConfig,  # Accept AppConfig instance
        project_root: Optional[Path] = None,
        additional_ignore_dirs: set | None = None,
        use_cache: bool = True,
    ):
        """Initialize the ProjectScanner.

        Args:
            config: The loaded application configuration.
            project_root: Path to the project root directory. Defaults to config.paths.project_root.
            additional_ignore_dirs: Set of directory names to ignore.
            use_cache: Whether to use file hashing cache.
        """
        self.config = config  # Store the passed config
        self.project_root = (project_root or self.config.paths.project_root).resolve()
        self.additional_ignore_dirs = additional_ignore_dirs or set()
        self.use_cache = use_cache

        logger.info(f"Initializing ProjectScanner for root: {self.project_root}")

        # Derive paths from config using helper
        self.cache_path = self._resolve_path_from_config(
            getattr(self.config.paths, "scanner_cache_path", None),
            self.project_root / ".dreamos_cache" / "scanner_dependency_cache.json",
            "scanner cache",
        )
        self.analysis_output_path = self._resolve_path_from_config(
            getattr(self.config.paths, "analysis_output_path", None),
            self.project_root / "project_analysis.json",
            "analysis output",
        )
        self.context_output_path = self._resolve_path_from_config(
            getattr(self.config.paths, "chatgpt_context_output_path", None),
            self.project_root / "chatgpt_project_context.json",
            "ChatGPT context output",
        )

        # Ensure cache directory exists
        if self.use_cache:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Instantiate ProjectCache with resolved path
        self.cache = (
            ProjectCache(cache_path=self.cache_path) if self.use_cache else None
        )

        # Initialize LanguageAnalyzer - it now determines grammar paths internally
        self.language_analyzer = LanguageAnalyzer()

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


def main():
    print("Attempting to import AppConfig...")
    try:
        from dreamos.core.config import AppConfig

        print("AppConfig imported successfully.")
        # config = AppConfig()
        # print("AppConfig instantiated.")
        # project_root = config.paths.project_root
        # print(f"Project root: {project_root}")
    except ImportError as e:
        print(f"ImportError: {e}")
        import traceback

        traceback.print_exc()
    except Exception as e:
        print(f"Other exception: {e}")
        import traceback

        traceback.print_exc()

    parser = argparse.ArgumentParser(
        description="Scan project files, analyze dependencies, and generate reports."
    )
    parser.add_argument(
        "--project-root",
        default=str(project_root),  # Use determined root
        help="Root directory of the project to scan.",
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
        # EDIT START: Use config path as default
        default=str(default_analysis_path),
        # EDIT END
        help=f"Output path for the detailed analysis JSON file (default: {str(default_analysis_path)}).",  # Corrected help f-string
    )
    parser.add_argument(
        "--context-output",
        # EDIT START: Use config path as default
        default=str(default_context_path),
        # EDIT END
        help=f"Output path for the condensed ChatGPT context JSON file (default: {str(default_context_path)}).",  # Corrected help f-string
    )
    parser.add_argument(
        "--cache-file",
        # EDIT START: Use config path as default
        default=str(default_cache_path),
        # EDIT END
        help=f"Path to the dependency cache file (default: {str(default_cache_path)}).",  # Corrected help f-string
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

    args = parser.parse_args()

    # Set logging level
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    # Resolve project root (handle potential relative path from arg)
    # EDIT START: Resolve arg path relative to cwd if provided, otherwise use config root
    resolved_project_root = (
        Path(args.project_root).resolve()
        if args.project_root != str(project_root)
        else project_root
    )
    # EDIT END

    # EDIT START: Resolve output/cache paths relative to the *resolved* project root
    # Use Path() constructor for arguments to ensure they are Path objects
    analysis_output_path = resolved_project_root / Path(args.analysis_output).name
    context_output_path = resolved_project_root / Path(args.context_output).name
    # For cache, ensure the relative path structure is maintained from the project root
    cache_relative_path = (
        Path(args.cache_file).relative_to(project_root)
        if Path(args.cache_file).is_absolute()
        and str(Path(args.cache_file)).startswith(str(project_root))
        else Path(args.cache_file)
    )
    cache_path = resolved_project_root / cache_relative_path
    # EDIT END

    logger.info(f"Project Root: {resolved_project_root}")
    logger.info(f"Cache File: {cache_path}")
    logger.info(f"Analysis Output: {analysis_output_path}")
    logger.info(f"Context Output: {context_output_path}")

    # Initialize scanner with resolved project root
    scanner = ProjectScanner(
        config=AppConfig(),
        project_root=resolved_project_root,
        cache_path=cache_path,
        analysis_output_path=analysis_output_path,
        context_output_path=context_output_path,
        additional_ignore_dirs=set(args.exclude),
        use_cache=(not args.no_cache),
    )

    # EDIT: Define an async function to run scanner operations
    async def run_scanner_operations():
        if args.clear_cache:
            logger.info("Clearing cache...")
            await scanner.clear_cache_async()

        # EDIT: Define progress callback to accept a single percentage argument
        def progress_update(percent_complete):
            print(f"Scan progress: {percent_complete}%...", end="\r")

        logger.info("Starting project scan...")
        await scanner.scan_project(
            progress_callback=progress_update,
            num_workers=args.workers,
            force_rescan_patterns=args.force_rescan,
        )
        print("\nScan complete. Generating reports...")

        # Generate reports using resolved paths
        await scanner.generate_init_files_async(overwrite=True)
        await scanner.export_chatgpt_context_async(template_path=args.template_path)

        # categorize_agents was called without await and its result printed.
        # Assuming categorize_agents_async might update internal state or return something.
        # Based on its implementation, it updates self.analysis and calls save_report.
        # It doesn't seem to return a value that was printed before.
        await scanner.categorize_agents_async()
        # The old code printed json.dumps(agent_categories, indent=2) - this return value is gone.
        # The categorize_agents_async now logs its findings.

        analysis_summary = await scanner.analyze_scan_results_async()
        print("\n--- Analysis Summary ---")
        print(json.dumps(analysis_summary, indent=2))

        print("Done.")

    # EDIT: Run the async operations
    asyncio.run(run_scanner_operations())


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
    main()
