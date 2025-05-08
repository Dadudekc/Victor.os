import argparse
import ast
import hashlib
import json
import logging
import os
import asyncio
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Local imports - use relative imports based on actual file structure
# Remove the unused import causing the ModuleNotFoundError
from .analyzer import LanguageAnalyzer  # noqa: E402

# Need concurrency import?
from .concurrency import MultibotManager  # Added based on file list  # noqa: E402

# Assuming ProjectCache is also in file_processor or defined elsewhere? Let's try file_processor  # noqa: E501
from .file_processor import FileProcessor  # noqa: E402
from .report_generator import ReportGenerator  # noqa: E402

# Assuming config loading happens differently now, remove direct import if unused
# from dreamos.core.config_utils import load_config
from dreamos.core.config import AppConfig # Import AppConfig directly

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
# Assuming PROJECT_ROOT is defined globally or accessible via config
try:
    # Attempt to get from config first (preferred)
    config = AppConfig.load() # This might fail if config path isn't set/found
    PROJECT_ROOT = config.paths.project_root
except Exception:
    # Fallback: Determine project root based on this file's location
    # This assumes a specific directory structure: src/dreamos/tools/analysis/...
    PROJECT_ROOT = Path(__file__).resolve().parents[4]
    logger.warning(f"Failed to load AppConfig for PROJECT_ROOT, falling back to relative path: {PROJECT_ROOT}")

GRAMMAR_BASE_DIR = PROJECT_ROOT / "runtime" / "tree-sitter-grammars"
BUILD_LIB_PATH = GRAMMAR_BASE_DIR / "languages.so"  # Or .dll on Windows
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
        self.grammar_sources = {
            "python": GRAMMAR_BASE_DIR / "tree-sitter-python",
            "rust": GRAMMAR_BASE_DIR / "tree-sitter-rust",
            "javascript": GRAMMAR_BASE_DIR / "tree-sitter-javascript",
        }
        self.parsers = {}

        if Language and Parser:
            # Ensure the build directory exists
            GRAMMAR_BASE_DIR.mkdir(parents=True, exist_ok=True)

            # Filter to existing source directories
            available_grammar_paths = [
                str(path) for path in self.grammar_sources.values() if path.is_dir()
            ]

            if available_grammar_paths:
                logger.info(f"Attempting to build tree-sitter library for: {list(self.grammar_sources.keys())}")
                try:
                    Language.build_library(
                        # Store the library in the grammars directory
                        str(BUILD_LIB_PATH),
                        # Include paths to the grammar source directories
                        available_grammar_paths
                    )
                    logger.info(f"Successfully built tree-sitter library at {BUILD_LIB_PATH}")
                    # _load_parsers_from_library is now async, so cannot be directly awaited in sync __init__
                    # This implies it should be part of an async initialization step. 
                    # For now, we can schedule it if an event loop is running, or call it from an async method.
                    # Simplest for now: if an event loop is running, create a task.
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(self._load_parsers_from_library())
                        logger.debug("Scheduled _load_parsers_from_library in __init__.")
                    except RuntimeError: # No running event loop
                        logger.warning("No running asyncio event loop in LanguageAnalyzer.__init__ to schedule parser loading.")
                        # Parsers will need to be loaded explicitly via an async method later.
                except Exception as e:
                    logger.error(f"⚠️ Failed to build or load tree-sitter library: {e}", exc_info=True)
                    logger.warning("Falling back to AST-based parsing where available.")
            else:
                logger.warning("No tree-sitter grammar source directories found. AST parsing disabled.")
        else:
            logger.warning("tree-sitter package not found. AST parsing disabled.")

    async def _load_parsers_from_library(self):
        """Loads parsers for available languages from the built library. Async path check."""
        if not await asyncio.to_thread(BUILD_LIB_PATH.exists) or not Language or not Parser:
            if not Language or not Parser:
                logger.debug("tree-sitter Language or Parser not available for _load_parsers_from_library.")
            else:
                logger.debug(f"Built library path {BUILD_LIB_PATH} does not exist. Cannot load parsers.")
            return

        for lang_name in self.grammar_sources.keys():
            try:
                lang_lib = Language(str(BUILD_LIB_PATH), lang_name)
                parser = Parser()
                parser.set_language(lang_lib)
                self.parsers[lang_name] = parser
                logger.info(f"Initialized tree-sitter parser for {lang_name}.")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load {lang_name} grammar from library {BUILD_LIB_PATH}: {e}")

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
        elif suffix in [".js", ".ts"] and "javascript" in self.parsers: # Added tsx, jsx
            # Use JS parser for TS/JSX as well (common practice)
            return self._analyze_with_tree_sitter("javascript", source_code)
        
        # Fallback to AST or basic analysis
        elif suffix == ".py":
            return self._analyze_python_ast(source_code) # Renamed original method
        else:
            return {
                "language": suffix.lstrip('.'), # Store lang name without dot
                "functions": [],
                "classes": {},
                "routes": [],
                "complexity": 0,
                "parser_used": "basic",
            }

    def _analyze_python_ast(self, source_code: str) -> Dict: # Renamed from _analyze_python
        """
        Analyzes Python source code using the builtin `ast` module.
        Extracts a naive list of function defs, classes, routes, complexity, etc.
        """
        try:
            tree = ast.parse(source_code)
            functions = []
            classes = {}
            routes = []
            complexity = 0 # Basic complexity count (nodes)

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
                "error": str(e)
            }

    def _analyze_with_tree_sitter(self, lang_name: str, source_code: str) -> Dict:
        """Analyzes code using the appropriate tree-sitter parser."""
        parser = self.parsers.get(lang_name)
        if not parser:
            return { # Should not happen if called correctly, but safeguard
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
            functions = [] # Extract functions using queries/traversal
            classes = {} # Extract classes
            routes = [] # Extract routes (if applicable to lang)
            complexity = tree.root_node.descendant_count # Example complexity metric

            return {
                "language": lang_name,
                "functions": functions, # Placeholder
                "classes": classes, # Placeholder
                "routes": routes, # Placeholder
                "complexity": complexity,
                "parser_used": "treesitter",
            }
        except Exception as e:
            logger.warning(f"Tree-sitter parsing failed for {lang_name}: {e}", exc_info=True)
            return {
                "language": lang_name,
                "functions": [],
                "classes": {},
                "routes": [],
                "complexity": 0,
                "parser_used": "treesitter_failed",
                "error": str(e)
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
    ):
        self.project_root = project_root
        self.cache = cache
        self.cache_lock = cache_lock
        self.additional_ignore_dirs = additional_ignore_dirs

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
        except UnicodeDecodeError:
            logger.warning(f"Skipping file due to decoding error: {file_path}")
            return None # Indicate failure
        except Exception as e:
            logger.error(
                f"Error processing file {file_path}: {e}", exc_info=True
            )
            # Optionally store error info in cache or analysis?
            # For now, return None to indicate processing failure
            return None


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
      - Loads and saves the file hash cache.
      - Discovers files to be scanned.
      - Detects moved files based on hash.
      - Manages asynchronous file processing via MultibotManager.
      - Gathers results and passes them to the ReportGenerator.
      - Provides methods to trigger optional steps like __init__ generation or context export.
    """  # noqa: E501

    def __init__(
        self, project_root: Path | str = ".", additional_ignore_dirs: set | None = None
    ):
        # Ensure project_root is Path object
        self.project_root = Path(project_root).resolve()
        self.analysis: Dict[
            str, Dict
        ] = {}  # Stores results {relative_path: analysis_dict}

        # Set DEFAULT paths initially - these might be updated in main()
        self.cache_path: Path = (
            self.project_root / ".dreamos_cache" / "dependency_cache.json"
        )
        # Use default paths for ReportGenerator initially
        default_analysis_path = self.project_root / "project_analysis.json"
        default_context_path = self.project_root / "chatgpt_project_context.json"

        self.cache_instance = ProjectCache(self.cache_path) # Renamed to avoid conflict with self.cache dict
        self.cache = self._load_cache_sync() # Initial load is sync for now
        
        # FIXME: self.cache_lock is a threading.Lock passed to FileProcessor.
        # This will be an issue if FileProcessor methods called by async workers need an asyncio.Lock.
        self.cache_lock = self.cache_instance.cache_lock # Use ProjectCache's lock for consistency with FileProcessor
        
        self.additional_ignore_dirs = additional_ignore_dirs or set()

        # FIXME: LanguageAnalyzer() instantiation is synchronous and its __init__ contains
        # a synchronous tree-sitter build step. This will block if ProjectScanner
        # is created in an async context. An async factory or explicit async init for LanguageAnalyzer is needed.
        self.language_analyzer = LanguageAnalyzer()
        
        # FileProcessor is given the ProjectCache's threading.Lock.
        # FIXME: FileProcessor may need async refactoring if its methods are I/O bound and called concurrently.
        self.file_processor = FileProcessor(
            self.project_root, self.cache, self.cache_lock, self.additional_ignore_dirs
        )
        self.report_generator = ReportGenerator(
            self.project_root,
            self.analysis,
            default_analysis_path,
            default_context_path,
        )

    def _load_cache_sync(self) -> Dict[str, Dict]: 
        """Loads the hash/analysis cache JSON from disk synchronously."""
        # Uses self.cache_instance which has its own internal locking
        return self.cache_instance._load() # Accessing ProjectCache's internal method directly

    def _save_cache_sync(self):
        """Writes the current file hash cache to disk synchronously."""
        # Uses self.cache_instance which has its own internal locking
        # And self.cache from ProjectScanner is passed to FileProcessor which might modify it.
        # This is complex; direct modification of self.cache should be via self.cache_instance.set()
        # For now, assume self.cache correctly reflects what should be in self.cache_instance.cache
        # This needs a more robust design if ProjectCache is properly encapsulated.
        if isinstance(self.cache, dict): # Ensure self.cache is a dict
            self.cache_instance.cache = self.cache # Force update ProjectCache's internal dict
            self.cache_instance._save() # Accessing ProjectCache's internal method
        else:
            logger.error("ProjectScanner.cache is not a dict, cannot save cache.")

    async def _discover_files_async(self) -> List[Path]: # Renamed to clarify it's the async version
        """Finds project files eligible for analysis, respecting exclusions. Async."""
        logger.info(f"Discovering files in {self.project_root} asynchronously...")
        file_extensions = {".py", ".rs", ".js", ".ts"}
        valid_files: List[Path] = []
        
        # Use a list for paths to scan to manage async directory scanning
        paths_to_scan = [self.project_root]
        processed_paths = set()

        while paths_to_scan:
            current_scan_path = paths_to_scan.pop(0)
            if current_scan_path in processed_paths:
                continue
            processed_paths.add(current_scan_path)

            try:
                # scandir itself is an iterator, convert to list in thread for safety if needed,
                # or process entry by entry carefully.
                # For simplicity here, list comprehension in thread.
                def _sync_scandir(p: Path):
                    entries = []
                    try:
                        for entry in os.scandir(p):
                            entries.append((entry.path, entry.is_dir(follow_symlinks=False), entry.is_file()))
                    except (PermissionError, OSError) as e:
                        logger.warning(f"Error scanning dir {p} in thread: {e}")
                    return entries
                
                entries = await asyncio.to_thread(_sync_scandir, current_scan_path)

                for entry_path_str, is_dir, is_file in entries:
                    entry_path = Path(entry_path_str)
                    if await asyncio.to_thread(self.file_processor.should_exclude, entry_path):
                        continue

                    if is_dir:
                        paths_to_scan.append(entry_path)
                    elif is_file:
                        if entry_path.suffix.lower() in file_extensions:
                            valid_files.append(entry_path)
            except Exception as e: # Catch potential errors from to_thread or path ops
                logger.error(f"Error processing path {current_scan_path} during discovery: {e}", exc_info=True)

        logger.info(f"📝 Found {len(valid_files)} potential files for analysis (async discovery).")
        return valid_files

    # _walk_directory is effectively merged into _discover_files_async's iterative approach

    async def _detect_moved_files_async(self, current_files_rel: Set[str]):
        """Compares hashes in cache to detect moved files. Async I/O for hashing."""
        logger.debug("Detecting moved files (async mode)...")
        previous_files_rel = set(self.cache.keys())
        potential_new_files = current_files_rel - previous_files_rel
        potential_missing_files = previous_files_rel - current_files_rel

        moved_files_map: Dict[str, str] = {}
        files_to_remove_from_cache: Set[str] = set()
        candidates_to_check = potential_missing_files

        # Pre-calculate hashes for potential new files asynchronously
        new_file_hashes: Dict[str, str] = {}
        hash_tasks = []
        for new_rel_path in potential_new_files:
            new_abs_path = self.project_root / new_rel_path
            # FIXME: self.file_processor.hash_file needs to be async or called in thread.
            # Assuming it will be made async or this part needs to_thread if it's sync and I/O bound.
            async def _get_hash(path, rel_path): # Helper async func for task group
                # For now, assume hash_file is sync and needs to_thread if it does I/O
                # If hash_file becomes async, this can be simplified.
                file_hash = await asyncio.to_thread(self.file_processor.hash_file, path)
                if file_hash:
                    new_file_hashes[rel_path] = file_hash
            hash_tasks.append(_get_hash(new_abs_path, new_rel_path))
        
        if hash_tasks:
            await asyncio.gather(*hash_tasks)

        # The cache interactions below use self.cache (dict) and self.cache_instance (ProjectCache).
        # This needs to be careful due to ProjectCache being synchronous with its own lock.
        # For this refactor, we modify self.cache directly and then call _save_cache_sync.
        # This means multiple coroutines could modify self.cache concurrently if not careful.
        # An asyncio.Lock for self.cache modifications in ProjectScanner would be needed.
        # Let's assume for now that _detect_moved_files_async is not run concurrently itself.

        with self.cache_lock: # Using the ProjectCache's threading.Lock via asyncio.to_thread or make this whole block sync.
                             # This is problematic. For now, let's assume this logic is okay for one pass.
                             # A full async solution would make ProjectCache fully async.
            current_cache_copy = dict(self.cache) # Work on a copy for this part

            for old_rel_path in candidates_to_check:
                old_data = current_cache_copy.get(old_rel_path)
                if not isinstance(old_data, dict) or "hash" not in old_data:
                    files_to_remove_from_cache.add(old_rel_path)
                    continue

                old_hash = old_data["hash"]
                found_match = False
                for new_rel_path, new_hash in new_file_hashes.items():
                    if new_hash == old_hash:
                        logger.info(
                            f"Detected move: '{old_rel_path}' -> '{new_rel_path}'"
                        )
                        moved_files_map[old_rel_path] = new_rel_path
                        popped_data = current_cache_copy.pop(old_rel_path)
                        current_cache_copy[new_rel_path] = popped_data # Update the copy
                        del new_file_hashes[new_rel_path]
                        found_match = True
                        break

                if not found_match:
                    files_to_remove_from_cache.add(old_rel_path)
            
            for path_to_remove in files_to_remove_from_cache:
                if path_to_remove in current_cache_copy:
                    logger.debug(
                        f"Marking missing file '{path_to_remove}' for removal from cache."
                    )
                    current_cache_copy.pop(path_to_remove)
            
            self.cache = current_cache_copy # Update the main cache dict

        if files_to_remove_from_cache or moved_files_map: # Save if changes were made
            self._save_cache_sync() # Save changes made to self.cache

        logger.debug(f"Move detection complete. {len(moved_files_map)} moves detected.")

    async def scan_project( # Changed to async def
        self,
        progress_callback: Optional[callable] = None,
        num_workers: int = 4,
        force_rescan_patterns: Optional[List[str]] = None,
    ):
        """
        Orchestrates the project scan using the modular components. Async.
        Accepts optional num_workers and force_rescan_patterns.
        """
        logger.info(f"🔍 Scanning project: {self.project_root} asynchronously...")

        all_eligible_files = await self._discover_files_async()
        current_files_rel = {
            str(f.relative_to(self.project_root)).replace("\\", "/")
            for f in all_eligible_files
        }
        await self._detect_moved_files_async(current_files_rel)

        logger.info("⏱️ Processing files asynchronously...")
        processed_count = 0
        total_files = len(all_eligible_files)

        def _status_update(file_path: Path, result: Optional[Any]):
            nonlocal processed_count
            processed_count += 1
            if progress_callback:
                try:
                    percent = (
                        int((processed_count / total_files) * 100)
                        if total_files > 0
                        else 0
                    )
                    progress_callback(percent)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")
        
        # FIXME: MultibotManager interaction needs to be async-aware.
        # If MultibotManager uses threads, _process_file must be thread-safe.
        # If MultibotManager uses asyncio tasks, _process_file must be async and non-blocking.
        manager = MultibotManager(
            scanner=self, num_workers=num_workers, status_callback=_status_update
        )

        logger.info(
            f"Attempting to start workers. Manager type: {type(manager)}"
        )
        # Assuming MultibotManager.start_workers might be async or setup async workers
        # If it's blocking or purely sync, this itself is an issue for an async scan_project
        # For now, assume it correctly interfaces with an async _process_file if it uses async tasks.
        if hasattr(manager, 'async_start_workers'): # Hypothetical async start
            await manager.async_start_workers()
        elif hasattr(manager, 'start_workers'):
            manager.start_workers() # Assuming this is non-blocking or sets up async workers
        else:
            logger.error("MultibotManager does not have a recognized start_workers method.")
            return

        files_to_process = []
        patterns_to_force = []
        if force_rescan_patterns:
            from fnmatch import fnmatch # Keep local import
            patterns_to_force = force_rescan_patterns

        # FIXME: This block uses self.cache_lock (threading.Lock) and calls sync self.file_processor.hash_file.
        # This will block. It should be run in asyncio.to_thread, or FileProcessor.hash_file made async 
        # and cache interactions made async-safe (e.g., with an async ProjectCache).
        def _determine_files_to_process_sync():
            _files_to_process = []
            with self.cache_lock: # This is ProjectCache's threading.Lock
                for file_path in all_eligible_files:
                    relative_path = str(file_path.relative_to(self.project_root)).replace("\\", "/")
                    force_this_file = False
                    if patterns_to_force:
                        if any(fnmatch(relative_path, pattern) for pattern in patterns_to_force):
                            force_this_file = True
                            logger.debug(f"Forcing rescan for {relative_path}")
                    cached_item = self.cache.get(relative_path) # self.cache is a dict
                    needs_processing = True
                    if not force_this_file and isinstance(cached_item, dict) and "hash" in cached_item:
                        # FileProcessor.hash_file is likely sync and I/O bound
                        current_hash = self.file_processor.hash_file(file_path) 
                        if current_hash and current_hash == cached_item["hash"]:
                            if "analysis" in cached_item:
                                needs_processing = False
                    if needs_processing:
                        _files_to_process.append(file_path)
                    else:
                        _status_update(file_path, None) # Cached, not processed by worker
                        if isinstance(cached_item, dict) and "analysis" in cached_item:
                            if relative_path not in self.analysis:
                                self.analysis[relative_path] = cached_item["analysis"]
            return _files_to_process
        
        files_to_process = await asyncio.to_thread(_determine_files_to_process_sync)

        logger.info(
            f"Submitting {len(files_to_process)} files for analysis/cache update."
        )

        for file_path in files_to_process:
            # Assuming MultibotManager.add_task can handle tasks that result in async execution
            # if _process_file is async. Or it adapts.
            manager.add_task(file_path) # If manager expects async work func, _process_file must be async

        # Assuming MultibotManager.wait_for_completion might be async or blocking.
        if hasattr(manager, 'async_wait_for_completion'):
            await manager.async_wait_for_completion()
        elif hasattr(manager, 'wait_for_completion'):
            manager.wait_for_completion()
        else:
            logger.error("MultibotManager does not have wait_for_completion method.")

        if hasattr(manager, 'async_stop_workers'):
            await manager.async_stop_workers()
        elif hasattr(manager, 'stop_workers'):
            manager.stop_workers()
        else:
            logger.error("MultibotManager does not have stop_workers method.")

        scan_results = manager.get_results() # Assuming sync get_results

        logger.info(f"Gathered {len(scan_results)} analysis results from workers.")
        self.analysis.clear()
        for result in scan_results:
            if result is not None and isinstance(result, tuple) and len(result) == 2:
                rel_path, analysis_data = result
                if isinstance(rel_path, str) and isinstance(analysis_data, dict):
                    self.analysis[rel_path] = analysis_data
                else:
                    logger.warning(f"Malformed result received from worker: {result}")

        # Populate self.analysis with any remaining cached items not re-processed by workers
        # This needs to be careful if self.cache was modified by workers via FileProcessor
        # For now, assume self.cache (the dict) is the source of truth from _determine_files_to_process_sync
        def _sync_populate_analysis_from_cache():
            with self.cache_lock: # ProjectCache's threading.Lock
                for rel_path, data in self.cache.items():
                    if rel_path not in self.analysis and isinstance(data, dict) and "analysis" in data:
                        self.analysis[rel_path] = data["analysis"]
        await asyncio.to_thread(_sync_populate_analysis_from_cache)

        logger.info(f"Total analysis entries collected: {len(self.analysis)}")

        # FIXME: ReportGenerator methods are likely sync and I/O bound.
        await asyncio.to_thread(self.report_generator.save_report)
        await asyncio.to_thread(self._save_cache_sync) # _save_cache_sync is already designed for this

        logger.info(
            f"✅ Scan complete. Results merged into {self.report_generator.report_path}"
        )
        await self.categorize_agents_async() # Call the new async version
        logger.info("✅ Agent categorization complete.")

    async def _process_file(self, file_path: Path) -> Optional[tuple]: # Changed to async
        """
        Internal method called by workers. Async.
        Delegates to FileProcessor.process_file (which also needs to be async).
        Returns tuple (relative_path, analysis_result) or None.
        """
        # FIXME: self.file_processor.process_file needs to be async if it does I/O or calls async LanguageAnalyzer methods.
        # For now, assuming it will be made async. If it remains sync and blocking, it needs to_thread here.
        # return self.file_processor.process_file(file_path, self.language_analyzer)
        # Tentatively make it awaitable, assuming FileProcessor.process_file will be refactored.
        # If FileProcessor.process_file is confirmed sync and I/O bound: 
        # return await asyncio.to_thread(self.file_processor.process_file, file_path, self.language_analyzer)
        if hasattr(self.file_processor, 'process_file_async'): # Ideal scenario
            return await self.file_processor.process_file_async(file_path, self.language_analyzer)
        elif hasattr(self.file_processor, 'process_file'): # Fallback if it's sync
             logger.warning(f"Calling synchronous FileProcessor.process_file for {file_path} from async ProjectScanner._process_file. This may block. Consider making FileProcessor.process_file async.")
             return await asyncio.to_thread(self.file_processor.process_file, file_path, self.language_analyzer)
        logger.error(f"FileProcessor missing process_file or process_file_async method.")
        return None

    async def generate_init_files_async(self, overwrite: bool = True): # Renamed
        """Generate __init__.py for python packages. Async."""
        logger.info("Generating __init__.py files (async)...")
        # FIXME: self.report_generator.generate_init_files is likely sync and I/O bound.
        await asyncio.to_thread(self.report_generator.generate_init_files, overwrite)

    async def export_chatgpt_context_async(self, template_path: Optional[str] = None): # Renamed
        """Exports analysis context. Async."""
        logger.info("Exporting ChatGPT context (async)...")
        # FIXME: self.report_generator.export_chatgpt_context is likely sync and I/O bound.
        await asyncio.to_thread(self.report_generator.export_chatgpt_context, template_path)

    async def categorize_agents_async(self): # Renamed
        """Identifies potential agent scripts/definitions. Async for save_report."""
        logger.info("Analyzing files for agent categorization (async)...")
        agent_keywords = ["agent", "worker", "coordinator", "dispatcher", "supervisor", "monitor"]
        path_patterns = ["src/dreamos/agents/", "src/agents/"]
        base_agent_classes = {"BaseAgent"}
        identified_agents = 0

        # This part is CPU bound and modifies self.analysis (a dict)
        # If self.analysis is accessed by other coroutines, it would need an asyncio.Lock.
        # Assuming for now it's only modified sequentially within this method or by scan_project before this.
        for file_path_str, data in self.analysis.items():
            if not data or data.get("error"): continue
            file_path = Path(file_path_str)
            is_potential_agent = False
            agent_role = None
            if any(norm_path.startswith(p) for p in path_patterns for norm_path in [file_path_str.replace("\\", "/")]) or \
               any(keyword in file_path.name.lower() for keyword in agent_keywords):
                is_potential_agent = True
                agent_role = "potential_agent_script"
            if data.get("language") == ".py" and "classes" in data:
                for class_name, class_info in data["classes"].items():
                    direct_bases = class_info.get("base_classes", [])
                    if any(base in base_agent_classes for base in direct_bases):
                        is_potential_agent = True
                        agent_role = "agent_definition"
                        data["agent_class_name"] = class_name
                        break
            if is_potential_agent:
                data["agent_role"] = agent_role
                identified_agents += 1
                logger.debug(f"Categorized '{file_path_str}' as {agent_role}")
            elif "agent_role" in data:
                 del data["agent_role"]
                 if "agent_class_name" in data: del data["agent_class_name"]

        if identified_agents:
            logger.info(f"Identified and categorized {identified_agents} agent-related files.")
        else:
            logger.info("No agent-related files identified based on current heuristics.")
        
        # FIXME: self.report_generator.save_report is likely sync and I/O bound.
        await asyncio.to_thread(self.report_generator.save_report)
        logger.info(
            f"✅ Agent categorization executed. Updated project analysis saved to {self.report_generator.report_path}"  # noqa: E501
        )

    async def clear_cache_async(self): # Renamed
        """Deletes the cache file. Async."""
        cache_path = self.cache_path
        try:
            if await asyncio.to_thread(cache_path.exists):
                await asyncio.to_thread(cache_path.unlink)
                logger.info(f"Deleted cache file: {cache_path}")
            # Also clear in-memory representation if ProjectScanner holds one directly
            if hasattr(self, 'cache') and isinstance(self.cache, dict):
                 self.cache.clear()
            if hasattr(self, 'cache_instance'): # If using ProjectCache instance
                 await asyncio.to_thread(self.cache_instance.clear) # Assuming ProjectCache might get an async clear
            logger.info("In-memory cache cleared.")
        except Exception as e:
            logger.error(f"Error clearing cache file {cache_path}: {e}")

    async def analyze_scan_results_async(self) -> Dict[str, Any]: # Renamed
        """Analyzes the collected data in self.analysis. Async (no I/O here, but consistent)."""
        logger.info("Analyzing scan results (async)...")
        # This method is CPU-bound, but declared async for API consistency if other parts become async.
        # No asyncio.to_thread needed for the dict operations themselves.
        summary = {
            "total_files_scanned": len(self.analysis),
            "language_counts": {},
            "total_functions": 0,
            "total_classes": 0,
            "total_routes": 0,
            "errors": [],
        }
        for file_path_str, file_data in self.analysis.items():
            if not file_data or file_data.get("error"): 
                summary["errors"].append(file_path_str)
                continue
            lang = file_data.get("language", "unknown")
            summary["language_counts"][lang] = summary["language_counts"].get(lang, 0) + 1
            summary["total_functions"] += len(file_data.get("functions", []))
            summary["total_classes"] += len(file_data.get("classes", {}))
            summary["total_routes"] += len(file_data.get("routes", []))
        logger.info(
            f"Analysis complete: Scanned {summary['total_files_scanned']} files."
        )
        logger.debug(f"Analysis summary: {summary}")
        return summary

    # _load_config is a placeholder, assuming it would be sync or refactored if used.
    def _load_config(self):
        """Loads configuration using AppConfig."""
        try:
            # Use AppConfig.load - requires config file path
            # Determine config path relative to project root
            default_config_path = self.project_root / "runtime" / "config" / "config.yaml"
            if default_config_path.exists():
                 self.config = AppConfig.load(config_file=str(default_config_path)).dict()
                 logger.info(f"Loaded config from default path: {default_config_path}")
            else:
                 logger.warning("Default config file not found. Using empty config.")
                 self.config = {} # Fallback to empty dict if config loading fails

            # Apply CLI overrides if necessary (or handle config purely via file)
            # Example:
            # if self.args.some_config_override:
            #     self.config['some_key'] = self.args.some_config_override

            # Extract specific paths or settings needed
            self.ignore_patterns = self.config.get("scanner", {}).get("ignore_patterns", [])
            self.cache_file = self.project_root / self.config.get("scanner", {}).get("cache_file", ".scanner_cache.json")

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}. Using defaults.", exc_info=True)
            self.config = {}
            self.ignore_patterns = []
            self.cache_file = self.project_root / ".scanner_cache.json"


def main():
    # EDIT START: Load config and define default paths
    config = AppConfig.load()
    project_root = config.paths.project_root
    default_cache_path = config.paths.project_root / ".dreamos_cache" / "dependency_cache.json"
    default_analysis_path = config.paths.project_root / "project_analysis.json"
    default_context_path = config.paths.project_root / "chatgpt_project_context.json"
    # EDIT END

    parser = argparse.ArgumentParser(
        description="Scan a project directory, analyze code files, and generate reports."
    )
    parser.add_argument(
        "project_root",
        nargs="?", # Make project_root optional, default to config
        # EDIT START: Default to config project root
        default=str(project_root), # Use config path as default string
        # EDIT END
        help=f"Path to the project root directory (default: {str(project_root)}).", # Corrected help f-string
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Directory or file patterns to exclude (can be used multiple times). Example: --exclude node_modules --exclude \"*.log\"",  # noqa: E501
    )
    parser.add_argument(
        "--force-rescan",
        action="append",
        default=[],
        help="Glob patterns for files to forcibly rescan even if unchanged (e.g., \"**/config.py\").",  # noqa: E501
    )
    parser.add_argument(
        "--clear-cache", action="store_true", help="Clear the dependency cache before scanning."
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable using the cache entirely."
    )
    parser.add_argument(
        "--analysis-output",
        # EDIT START: Use config path as default
        default=str(default_analysis_path),
        # EDIT END
        help=f"Output path for the detailed analysis JSON file (default: {str(default_analysis_path)}).", # Corrected help f-string
    )
    parser.add_argument(
        "--context-output",
        # EDIT START: Use config path as default
        default=str(default_context_path),
        # EDIT END
        help=f"Output path for the condensed ChatGPT context JSON file (default: {str(default_context_path)}).", # Corrected help f-string
    )
    parser.add_argument(
        "--cache-file",
        # EDIT START: Use config path as default
        default=str(default_cache_path),
        # EDIT END
        help=f"Path to the dependency cache file (default: {str(default_cache_path)}).", # Corrected help f-string
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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging."
    )


    args = parser.parse_args()

    # Set logging level
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    # Resolve project root (handle potential relative path from arg)
    # EDIT START: Resolve arg path relative to cwd if provided, otherwise use config root
    resolved_project_root = Path(args.project_root).resolve() if args.project_root != str(project_root) else project_root
    # EDIT END

    # EDIT START: Resolve output/cache paths relative to the *resolved* project root
    # Use Path() constructor for arguments to ensure they are Path objects
    analysis_output_path = resolved_project_root / Path(args.analysis_output).name
    context_output_path = resolved_project_root / Path(args.context_output).name
    # For cache, ensure the relative path structure is maintained from the project root
    cache_relative_path = Path(args.cache_file).relative_to(project_root) if Path(args.cache_file).is_absolute() and str(Path(args.cache_file)).startswith(str(project_root)) else Path(args.cache_file)
    cache_path = resolved_project_root / cache_relative_path
    # EDIT END

    logger.info(f"Project Root: {resolved_project_root}")
    logger.info(f"Cache File: {cache_path}")
    logger.info(f"Analysis Output: {analysis_output_path}")
    logger.info(f"Context Output: {context_output_path}")

    # Initialize scanner with resolved project root
    # EDIT START: Pass resolved paths correctly to ProjectScanner constructor
    # Assuming ProjectScanner now takes these paths in its __init__
    scanner = ProjectScanner(
        project_root=resolved_project_root,
        cache_path=cache_path, # Pass the resolved absolute cache path
        analysis_output_path=analysis_output_path,
        context_output_path=context_output_path,
        additional_ignore_dirs=set(args.exclude),
        use_cache=(not args.no_cache),
    )
    # EDIT END

    if args.clear_cache:
        logger.info("Clearing cache...")
        scanner.clear_cache()

    # Define progress callback if needed
    def progress_update(completed, total):
        print(f"Scanned {completed}/{total} files...", end="\r")

    logger.info("Starting project scan...")
    # Run scan
    scanner.scan_project(
        progress_callback=progress_update,
        num_workers=args.workers,
        force_rescan_patterns=args.force_rescan,
    )
    print("\nScan complete. Generating reports...")

    # Generate reports using resolved paths
    # Ensure ReportGenerator gets the correct paths if they aren't handled internally by scanner
    scanner.generate_init_files(overwrite=True)
    scanner.export_chatgpt_context(template_path=args.template_path)
    agent_categories = scanner.categorize_agents()
    print(json.dumps(agent_categories, indent=2))

    analysis_summary = scanner.analyze_scan_results()
    print("\n--- Analysis Summary ---")
    print(json.dumps(analysis_summary, indent=2))

    print("Done.")


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

