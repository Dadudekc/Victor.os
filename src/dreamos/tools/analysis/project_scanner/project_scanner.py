import argparse
import ast
import hashlib
import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Ensure the 'src' directory is in the Python path when run from root
SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parents[
    3
]  # Navigate up three levels from src/dreamos/tools/analysis/scanner to src/
PROJECT_ROOT = SRC_DIR.parent  # The project root is one level above src/
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Local imports - use relative imports based on actual file structure
# Remove the unused import causing the ModuleNotFoundError
# from dreamos.utils.file_utils import safe_read_file, find_project_root
from .analyzer import LanguageAnalyzer  # noqa: E402

# Need concurrency import?
from .concurrency import MultibotManager  # Added based on file list  # noqa: E402

# Assuming ProjectCache is also in file_processor or defined elsewhere? Let's try file_processor  # noqa: E501
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

# ---------------------------------
# Project Config / Cache File Setup
# ---------------------------------
CACHE_FILE = "dependency_cache.json"  # Original cache name
# Define cache path relative to project root
CACHE_PATH = PROJECT_ROOT / ".dreamos_cache" / CACHE_FILE


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
            else:
                logger.info("Cache clear requested, but no cache file found.")


# ... (rest of the file, ensure ProjectCache is instantiated correctly if used)

# Example modification in ProjectScanner.__init__ if ProjectCache was used:
# class ProjectScanner:
#     def __init__(...):
#         # ...
#         self.cache_handler = ProjectCache(CACHE_PATH)
#         self.cache = self.cache_handler.cache # Access the loaded cache dict
#         # ... pass self.cache_handler.cache_lock where needed


# ---------------------------------
# Language Analyzer
# ---------------------------------
class LanguageAnalyzer:  # noqa: F811
    """Handles language-specific code analysis for different programming languages."""

    def __init__(self):
        """Initialize language analyzers and parsers."""
        self.rust_parser = self._init_tree_sitter_language("rust")
        self.js_parser = self._init_tree_sitter_language("javascript")

    def _init_tree_sitter_language(self, lang_name: str) -> Optional[Parser]:
        """
        Initializes and returns a Parser for the given language name (rust, javascript).
        Adjust grammar_paths to point at your compiled .so files if using tree-sitter.
        """
        if not Language or not Parser:
            logger.warning(
                "⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled."  # noqa: E501
            )
            return None

        grammar_paths = {
            "rust": "path/to/tree-sitter-rust.so",  # <-- Adjust as needed
            "javascript": "path/to/tree-sitter-javascript.so",  # <-- Adjust as needed
        }
        if lang_name not in grammar_paths:
            logger.warning(f"⚠️ No grammar path for {lang_name}. Skipping.")
            return None

        grammar_path = grammar_paths[lang_name]
        if not Path(grammar_path).exists():
            logger.warning(f"⚠️ {lang_name} grammar not found at {grammar_path}")
            return None

        try:
            lang_lib = Language(grammar_path, lang_name)
            parser = Parser()
            parser.set_language(lang_lib)
            return parser
        except Exception as e:
            logger.error(f"⚠️ Failed to initialize tree-sitter {lang_name} parser: {e}")
            return None

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
        if suffix == ".py":
            return self._analyze_python(source_code)
        elif suffix == ".rs" and self.rust_parser:
            return self._analyze_rust(source_code)
        elif suffix in [".js", ".ts"] and self.js_parser:
            return self._analyze_javascript(source_code)
        else:
            return {
                "language": suffix,
                "functions": [],
                "classes": {},
                "routes": [],
                "complexity": 0,
            }

    def _analyze_python(self, source_code: str) -> Dict:
        """
        Analyzes Python source code using the builtin `ast` module.
        Extracts a naive list of function defs, classes, routes, complexity, etc.
        """
        tree = ast.parse(source_code)
        functions = []
        classes = {}
        routes = []

        for node in ast.walk(tree):
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

        # Complexity = function count + sum of class methods
        complexity = len(functions) + sum(len(c["methods"]) for c in classes.values())
        return {
            "language": ".py",
            "functions": functions,
            "classes": classes,
            "routes": routes,
            "complexity": complexity,
        }

    def _analyze_rust(self, source_code: str) -> Dict:
        """Analyzes Rust source code using tree-sitter (if available)."""
        if not self.rust_parser:
            return {
                "language": ".rs",
                "functions": [],
                "classes": {},
                "routes": [],
                "complexity": 0,
            }

        tree = self.rust_parser.parse(bytes(source_code, "utf-8"))
        functions = []
        classes = {}

        def _traverse(node):
            if node.type == "function_item":
                fn_name_node = node.child_by_field_name("name")
                if fn_name_node:
                    functions.append(fn_name_node.text.decode("utf-8"))
            elif node.type == "struct_item":
                struct_name_node = node.child_by_field_name("name")
                if struct_name_node:
                    classes[struct_name_node.text.decode("utf-8")] = []
            elif node.type == "impl_item":
                impl_type_node = node.child_by_field_name("type")
                if impl_type_node:
                    impl_name = impl_type_node.text.decode("utf-8")
                    if impl_name not in classes:
                        classes[impl_name] = []
                    for child in node.children:
                        if child.type == "function_item":
                            method_node = child.child_by_field_name("name")
                            if method_node:
                                classes[impl_name].append(
                                    method_node.text.decode("utf-8")
                                )
            for child in node.children:
                _traverse(child)

        _traverse(tree.root_node)
        complexity = len(functions) + sum(len(m) for m in classes.values())
        return {
            "language": ".rs",
            "functions": functions,
            "classes": classes,
            "routes": [],
            "complexity": complexity,
        }

    def _analyze_javascript(self, source_code: str) -> Dict:
        """Analyzes JS/TS using tree-sitter (if available)."""
        if not self.js_parser:
            return {
                "language": ".js",
                "functions": [],
                "classes": {},
                "routes": [],
                "complexity": 0,
            }

        tree = self.js_parser.parse(bytes(source_code, "utf-8"))
        root = tree.root_node
        functions = []
        classes = {}
        routes = []

        def get_node_text(node):
            return node.text.decode("utf-8")

        def _traverse(node):
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    functions.append(get_node_text(name_node))
            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    cls_name = get_node_text(name_node)
                    classes[cls_name] = []
            elif node.type == "lexical_declaration":
                # arrow functions, etc.
                for child in node.children:
                    if child.type == "variable_declarator":
                        name_node = child.child_by_field_name("name")
                        value_node = child.child_by_field_name("value")
                        if (
                            name_node
                            and value_node
                            and value_node.type == "arrow_function"
                        ):
                            functions.append(get_node_text(name_node))
            elif node.type == "call_expression":
                if node.child_count >= 2:
                    callee_node = node.child_by_field_name("function")
                    args_node = node.child_by_field_name("arguments")
                    if callee_node:
                        callee_text = get_node_text(callee_node)
                        parts = callee_text.split(".")
                        if len(parts) == 2:
                            obj, method = parts
                            if method.lower() in {
                                "get",
                                "post",
                                "put",
                                "delete",
                                "patch",
                            }:
                                path_str = "/unknown"
                                if args_node and args_node.child_count > 0:
                                    first_arg = args_node.child(0)
                                    if first_arg.type == "string":
                                        path_str = get_node_text(first_arg).strip("\"'")
                                routes.append(
                                    {
                                        "object": obj,
                                        "method": method.upper(),
                                        "path": path_str,
                                    }
                                )
            for child in node.children:
                _traverse(child)

        _traverse(root)
        complexity = len(functions) + sum(len(v) for v in classes.values())
        return {
            "language": ".js",
            "functions": functions,
            "classes": classes,
            "routes": routes,
            "complexity": complexity,
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
        except Exception as e:
            logger.error(f"❌ Error analyzing {file_path}: {e}")
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

        self.cache = self._load_cache()  # Load hash cache {relative_path: {hash: ...}}
        self.cache_lock = threading.Lock()
        self.additional_ignore_dirs = additional_ignore_dirs or set()

        # Initialize components
        self.language_analyzer = LanguageAnalyzer()
        self.file_processor = FileProcessor(
            self.project_root, self.cache, self.cache_lock, self.additional_ignore_dirs
        )
        # Initialize ReportGenerator with default paths
        self.report_generator = ReportGenerator(
            self.project_root,
            self.analysis,
            default_analysis_path,
            default_context_path,
        )

    def _load_cache(self) -> Dict[str, Dict]:
        """Loads the hash/analysis cache JSON from disk."""
        cache_path = self.cache_path  # Use the instance attribute
        if cache_path.exists():
            try:
                with cache_path.open("r", encoding="utf-8") as f:
                    content = f.read()
                    if not content:
                        return {}
                    loaded_cache = json.loads(content)
                    if isinstance(loaded_cache, dict):
                        return loaded_cache
                    else:
                        logger.warning(
                            f"Cache file {cache_path} is not a valid dictionary. Starting fresh."  # noqa: E501
                        )
                        return {}
            except json.JSONDecodeError as e:
                logger.error(
                    f"Invalid JSON in cache file {cache_path}: {e}. Starting fresh."
                )
                return {}
            except Exception as e:
                logger.error(
                    f"Error loading cache file {cache_path}: {e}. Starting fresh."
                )
                return {}
        return {}

    def _save_cache(self):
        """Writes the current file hash cache to disk."""
        cache_path = self.cache_path  # Use the instance attribute
        try:
            with self.cache_lock:  # Ensure thread safety writing cache
                valid_cache_entries = {
                    path: data
                    for path, data in self.cache.items()
                    if isinstance(data, dict) and "hash" in data
                }
            # Ensure parent directory exists
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump(valid_cache_entries, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Error saving cache to {cache_path}: {e}", exc_info=True)

    def _discover_files(self) -> List[Path]:
        """Finds project files eligible for analysis, respecting exclusions."""
        logger.info(f"Discovering files in {self.project_root}...")
        file_extensions = {".py", ".rs", ".js", ".ts"}
        valid_files = []

        # Use scandir for potentially better performance on some systems
        try:
            for entry in os.scandir(self.project_root):
                entry_path = Path(entry.path)
                # Check exclusions for the entry itself first
                if self.file_processor.should_exclude(entry_path):
                    continue

                if entry.is_dir(follow_symlinks=False):
                    # If it's a directory (and not excluded), walk it
                    self._walk_directory(entry_path, file_extensions, valid_files)
                elif entry.is_file():
                    # If it's a file (and not excluded), check extension and add if valid  # noqa: E501
                    if entry_path.suffix.lower() in file_extensions:
                        valid_files.append(entry_path)
        except PermissionError:
            logger.error(
                f"Permission denied accessing root directory: {self.project_root}"
            )
        except OSError as e:
            logger.error(f"OS error scanning root directory {self.project_root}: {e}")

        logger.info(f"📝 Found {len(valid_files)} potential files for analysis.")
        return valid_files

    def _walk_directory(
        self, current_path: Path, extensions: Set[str], valid_files: List[Path]
    ):
        """Recursive helper for discovering files, checking exclusions at each level."""
        if self.file_processor.should_exclude(current_path):
            # logger.debug(f"Skipping excluded directory: {current_path}")
            return

        try:
            # Iterate through directory entries
            for entry in os.scandir(current_path):
                entry_path = Path(entry.path)
                if entry.is_dir(
                    follow_symlinks=False
                ):  # Avoid infinite loops with symlinks
                    self._walk_directory(entry_path, extensions, valid_files)
                elif entry.is_file():
                    # Check extension and exclusion rules for the file itself
                    if (
                        entry_path.suffix.lower() in extensions
                        and not self.file_processor.should_exclude(entry_path)
                    ):
                        valid_files.append(entry_path)
        except PermissionError:
            logger.warning(
                f"Permission denied accessing directory: {current_path}. Skipping."
            )
        except OSError as e:
            logger.error(f"OS error scanning directory {current_path}: {e}. Skipping.")

    def _detect_moved_files(self, current_files_rel: Set[str]):
        """Compares hashes in cache to detect moved files."""
        logger.debug("Detecting moved files...")
        previous_files_rel = set(self.cache.keys())
        potential_new_files = current_files_rel - previous_files_rel
        potential_missing_files = previous_files_rel - current_files_rel

        moved_files_map: Dict[str, str] = {}  # {old_relative_path: new_relative_path}
        files_to_remove_from_cache: Set[str] = set()

        # Only check potentially missing files against potentially new files
        candidates_to_check = potential_missing_files

        with self.cache_lock:
            # Pre-calculate hashes for potential new files
            new_file_hashes: Dict[str, str] = {}
            for new_rel_path in potential_new_files:
                new_abs_path = self.project_root / new_rel_path
                # Use FileProcessor's hash method
                file_hash = self.file_processor.hash_file(new_abs_path)
                if file_hash:
                    new_file_hashes[new_rel_path] = file_hash

            # Check each potentially missing file's hash against new file hashes
            for old_rel_path in candidates_to_check:
                old_data = self.cache.get(old_rel_path)
                if not isinstance(old_data, dict) or "hash" not in old_data:
                    files_to_remove_from_cache.add(old_rel_path)
                    continue  # Cannot check hash if missing or invalid

                old_hash = old_data["hash"]
                found_match = False
                # Iterate through new files that haven't been matched yet
                for new_rel_path, new_hash in new_file_hashes.items():
                    if new_hash == old_hash:
                        logger.info(
                            f"Detected move: '{old_rel_path}' -> '{new_rel_path}'"
                        )
                        moved_files_map[old_rel_path] = new_rel_path
                        # Update cache: remove old, copy data to new key
                        self.cache[new_rel_path] = self.cache.pop(old_rel_path)
                        # Remove matched new file from further consideration
                        del new_file_hashes[new_rel_path]
                        found_match = True
                        break  # Move to the next old file

                if not found_match:
                    # This file is truly missing (or hash changed drastically)
                    files_to_remove_from_cache.add(old_rel_path)

            # Remove truly missing files from cache
            for path_to_remove in files_to_remove_from_cache:
                if path_to_remove in self.cache:
                    logger.debug(
                        f"Removing missing file '{path_to_remove}' from cache."
                    )
                    del self.cache[path_to_remove]

        logger.debug(f"Move detection complete. {len(moved_files_map)} moves detected.")
        # No explicit return needed, cache is updated directly

    def scan_project(
        self,
        progress_callback: Optional[callable] = None,
        num_workers: int = 4,
        force_rescan_patterns: Optional[List[str]] = None,
    ):
        """
        Orchestrates the project scan using the modular components.
        Accepts optional num_workers and force_rescan_patterns.
        """
        logger.info(f"🔍 Scanning project: {self.project_root} ...")

        all_eligible_files = self._discover_files()
        current_files_rel = {
            str(f.relative_to(self.project_root)).replace("\\", "/")
            for f in all_eligible_files
        }
        self._detect_moved_files(current_files_rel)

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

        manager = MultibotManager(
            scanner=self, num_workers=num_workers, status_callback=_status_update
        )

        # EDIT: Add logging before start_workers call
        logger.info(
            f"Attempting to start workers. Manager type: {type(manager)}, Methods: {dir(manager)}"  # noqa: E501
        )
        manager.start_workers()

        files_to_process = []
        patterns_to_force = []
        if force_rescan_patterns:
            from fnmatch import fnmatch

            patterns_to_force = force_rescan_patterns

        with self.cache_lock:
            for file_path in all_eligible_files:
                relative_path = str(file_path.relative_to(self.project_root)).replace(
                    "\\", "/"
                )
                force_this_file = False
                if patterns_to_force:
                    if any(
                        fnmatch(relative_path, pattern) for pattern in patterns_to_force
                    ):
                        force_this_file = True
                        logger.debug(f"Forcing rescan for {relative_path}")
                cached_item = self.cache.get(relative_path)
                needs_processing = True
                if (
                    not force_this_file
                    and isinstance(cached_item, dict)
                    and "hash" in cached_item
                ):
                    current_hash = self.file_processor.hash_file(file_path)
                    if current_hash and current_hash == cached_item["hash"]:
                        if "analysis" in cached_item:
                            needs_processing = False
                if needs_processing:
                    files_to_process.append(file_path)
                else:
                    _status_update(file_path, None)
                    if isinstance(cached_item, dict) and "analysis" in cached_item:
                        if relative_path not in self.analysis:
                            self.analysis[relative_path] = cached_item["analysis"]

        logger.info(
            f"Submitting {len(files_to_process)} files for analysis/cache update."
        )

        for file_path in files_to_process:
            manager.add_task(file_path)

        manager.wait_for_completion()
        manager.stop_workers()

        scan_results = manager.get_results()

        logger.info(f"Gathered {len(scan_results)} analysis results from workers.")

        self.analysis.clear()

        for result in scan_results:
            if result is not None and isinstance(result, tuple) and len(result) == 2:
                rel_path, analysis_data = result
                if isinstance(rel_path, str) and isinstance(analysis_data, dict):
                    self.analysis[rel_path] = analysis_data
                else:
                    logger.warning(f"Malformed result received from worker: {result}")

        with self.cache_lock:
            for rel_path, data in self.cache.items():
                if (
                    rel_path not in self.analysis
                    and isinstance(data, dict)
                    and "analysis" in data
                ):
                    self.analysis[rel_path] = data["analysis"]

        logger.info(f"Total analysis entries collected: {len(self.analysis)}")

        self.report_generator.save_report()
        self._save_cache()

        logger.info(
            f"✅ Scan complete. Results merged into {self.report_generator.report_path}"
        )

        # Categorize agents using the scanner's method (which delegates to ReportGenerator)  # noqa: E501
        # This updates the analysis_results dictionary in place.
        logger.info("Running agent categorization...")
        self.categorize_agents()
        logger.info("✅ Agent categorization complete.")

    def _process_file(self, file_path: Path) -> Optional[tuple]:
        """
        Internal method called by workers.
        Delegates to FileProcessor.process_file.
        Returns tuple (relative_path, analysis_result) or None.
        """
        return self.file_processor.process_file(file_path, self.language_analyzer)

    # --- Public methods to trigger optional steps ---

    def generate_init_files(self, overwrite: bool = True):
        """Generate __init__.py for python packages based on the latest analysis."""
        # No need to init reporter, already done in __init__
        logger.info("Generating __init__.py files...")
        self.report_generator.generate_init_files(overwrite)

    def export_chatgpt_context(self, template_path: Optional[str] = None):
        """Exports analysis context, merging with existing file or using a template."""
        # No need to init reporter
        logger.info("Exporting ChatGPT context...")
        # The reporter now knows its output path, no need to pass filename
        self.report_generator.export_chatgpt_context(template_path)

    def categorize_agents(self):
        """
        Identifies potential agent scripts based on heuristics (e.g., imports, naming).
        Adds an 'agent_role' key to the analysis dict for identified files.
        Saves the updated analysis back to the report file.
        """
        logger.info("Analyzing files for agent categorization...")
        agent_keywords = ["agent", "worker", "coordinator", "dispatcher"]
        agent_files = {}
        for file_path_str, data in self.analysis.items():
            file_path = Path(file_path_str)
            if any(keyword in file_path.name.lower() for keyword in agent_keywords):
                data["agent_role"] = "potential_agent"
                agent_files[file_path_str] = data
        if agent_files:
            logger.info(f"Identified {len(agent_files)} potential agent files.")
        else:
            logger.info(
                "No potential agent files identified based on current heuristics."
            )

        # No need to init reporter
        logger.warning(
            "Agent categorization logic is not yet fully implemented in ProjectScanner.categorize_agents."  # noqa: E501
        )

        # Save the potentially updated analysis data
        # Ensure reporter has latest analysis (already shares the dict reference)
        self.report_generator.save_report()  # Use the reporter's save method
        # Use the correct path for logging
        logger.info(
            f"✅ Agent categorization placeholder executed. Updated project analysis saved to {self.report_generator.report_path}"  # noqa: E501
        )

    def clear_cache(self):
        """Deletes the cache file specified by self.cache_path."""
        cache_path = self.cache_path  # Use the instance attribute
        try:
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Deleted cache file: {cache_path}")
            self.cache = {}  # Clear in-memory cache too
        except Exception as e:
            logger.error(f"Error clearing cache file {cache_path}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze project structure and dependencies."
    )
    parser.add_argument(
        "--target",
        type=str,
        default=".",  # Default to current directory
        help="Target directory or file to analyze (relative to project root). Defaults to the project root.",  # noqa: E501
    )
    parser.add_argument(
        "--ignore",
        nargs="*",
        default=None,
        help="List of directory/file patterns to ignore (e.g., venv, .git, build).",
    )
    parser.add_argument(
        "--categorize-agents",
        action="store_true",
        help="Attempt to categorize identified Python files as agents based on heuristics.",  # noqa: E501
    )
    parser.add_argument(
        "--no-chatgpt-context",
        action="store_true",
        help="Skip exporting the merged ChatGPT context file.",
    )
    parser.add_argument(
        "--generate-init",
        action="store_true",
        help="Generate missing __init__.py files in discovered Python packages.",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=os.cpu_count() or 4,  # Default to CPU count or 4 if unavailable
        help="Number of worker threads for parallel file processing.",
    )
    parser.add_argument(
        "--force-rescan",
        nargs="*",
        default=None,
        help="List of glob patterns for files/directories to force re-scanning, ignoring cache.",  # noqa: E501
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the existing dependency cache before scanning.",
    )
    # ADD NEW ARGUMENTS HERE
    parser.add_argument(
        "--output-analysis-file",
        type=str,
        default="project_analysis.json",
        help="Path (relative to project root) to save the main analysis JSON file.",
    )
    parser.add_argument(
        "--output-context-file",
        type=str,
        default="chatgpt_project_context.json",
        help="Path (relative to project root) to save the exported ChatGPT context JSON file.",  # noqa: E501
    )
    parser.add_argument(
        "--output-cache-file",
        type=str,
        default=".dreamos_cache/dependency_cache.json",
        help="Path (relative to project root) to save the dependency cache JSON file.",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    # Suppress noisy loggers if needed
    # logging.getLogger("some_noisy_library").setLevel(logging.WARNING)

    # Instantiate the scanner with the project root and ignore patterns
    # Project root calculation should be robust
    project_root = find_project_root()  # Use utility if available

    ignore_set = set(args.ignore) if args.ignore else set()
    scanner = ProjectScanner(
        project_root=project_root, additional_ignore_dirs=ignore_set
    )

    # Set output paths from args
    scanner.cache_path = project_root / args.output_cache_file
    scanner.report_generator.report_path = project_root / args.output_analysis_file
    scanner.report_generator.context_path = project_root / args.output_context_file

    if args.clear_cache:
        scanner.clear_cache()

    # Perform the scan
    logger.info(f"🔍 Scanning project: {project_root} ...")
    scanner.scan_project(
        num_workers=args.num_workers, force_rescan_patterns=args.force_rescan
    )
    logger.info(
        f"✅ Scan complete. Results merged into {scanner.report_generator.report_path}"
    )

    # Optional post-processing steps
    if args.categorize_agents:
        scanner.categorize_agents()  # Note: This now also saves the report internally

    if args.generate_init:
        scanner.generate_init_files()

    if not args.no_chatgpt_context:
        scanner.export_chatgpt_context()

    print("Project scan and optional post-processing steps complete.")


# --- Helper --- Add find_project_root if not imported
# Minimal version:
def find_project_root(marker: str = ".git") -> Path:
    """Find the project root by looking for a marker file/dir."""
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / marker).exists():
            return current
        current = current.parent
    # Fallback or raise error if marker not found
    raise FileNotFoundError(f"Project root marker '{marker}' not found.")


if __name__ == "__main__":
    main()
