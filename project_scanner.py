import os
import ast
import json
import hashlib
import threading
import queue
import logging
import datetime
from pathlib import Path
from typing import Dict, Union, Optional, List, Any
import argparse

logger = logging.getLogger(__name__)

# Optional: If tree-sitter grammars are present for Rust/JS/TS
try:
    from tree_sitter import Language, Parser
except ImportError:
    Language = None
    Parser = None
    logger.warning("⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled.")

# ---------------------------------
# Project Config / Cache File Setup
# ---------------------------------
CACHE_FILE = "dependency_cache.json"
# Faster to delete and have it rewrite the whole thing(dependency_cache.json)...ngl
# We'll store our final "project_analysis.json" and "chatgpt_project_context.json"
# in the project root, merging new data with old each time.


# ---------------------------------
# Language Analyzer
# ---------------------------------
class LanguageAnalyzer:
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
            logger.warning("⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled.")
            return None

        grammar_paths = {
            "rust": "path/to/tree-sitter-rust.so",          # <-- Adjust as needed
            "javascript": "path/to/tree-sitter-javascript.so"  # <-- Adjust as needed
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
                "complexity": 0
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
                    if isinstance(decorator, ast.Call) and hasattr(decorator.func, 'attr'):
                        func_attr = decorator.func.attr.lower()
                        if func_attr in {"route", "get", "post", "put", "delete", "patch"}:
                            path_arg = "/unknown"
                            methods = [func_attr.upper()]
                            if decorator.args:
                                arg0 = decorator.args[0]
                                if isinstance(arg0, ast.Str):
                                    path_arg = arg0.s
                            # Check for "methods" kwarg
                            for kw in decorator.keywords:
                                if kw.arg == "methods" and isinstance(kw.value, ast.List):
                                    extracted_methods = []
                                    for elt in kw.value.elts:
                                        if isinstance(elt, ast.Str):
                                            extracted_methods.append(elt.s.upper())
                                    if extracted_methods:
                                        methods = extracted_methods
                            for m in methods:
                                routes.append({"function": node.name, "method": m, "path": path_arg})

            elif isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node)
                method_names = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
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
                    "base_classes": base_classes
                }

        # Complexity = function count + sum of class methods
        complexity = len(functions) + sum(len(c["methods"]) for c in classes.values())
        return {
            "language": ".py",
            "functions": functions,
            "classes": classes,
            "routes": routes,
            "complexity": complexity
        }

    def _analyze_rust(self, source_code: str) -> Dict:
        """Analyzes Rust source code using tree-sitter (if available)."""
        if not self.rust_parser:
            return {"language": ".rs", "functions": [], "classes": {}, "routes": [], "complexity": 0}

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
                                classes[impl_name].append(method_node.text.decode("utf-8"))
            for child in node.children:
                _traverse(child)

        _traverse(tree.root_node)
        complexity = len(functions) + sum(len(m) for m in classes.values())
        return {
            "language": ".rs",
            "functions": functions,
            "classes": classes,
            "routes": [],
            "complexity": complexity
        }

    def _analyze_javascript(self, source_code: str) -> Dict:
        """Analyzes JS/TS using tree-sitter (if available)."""
        if not self.js_parser:
            return {"language": ".js", "functions": [], "classes": {}, "routes": [], "complexity": 0}

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
                        if name_node and value_node and value_node.type == "arrow_function":
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
                            if method.lower() in {"get", "post", "put", "delete", "patch"}:
                                path_str = "/unknown"
                                if args_node and args_node.child_count > 0:
                                    first_arg = args_node.child(0)
                                    if first_arg.type == "string":
                                        path_str = get_node_text(first_arg).strip('"\'')
                                routes.append({
                                    "object": obj,
                                    "method": method.upper(),
                                    "path": path_str
                                })
            for child in node.children:
                _traverse(child)

        _traverse(root)
        complexity = len(functions) + sum(len(v) for v in classes.values())
        return {
            "language": ".js",
            "functions": functions,
            "classes": classes,
            "routes": routes,
            "complexity": complexity
        }


# ---------------------------------
# BotWorker & MultibotManager
# ---------------------------------
class BotWorker(threading.Thread):
    """
    A background worker that pulls file tasks from a queue,
    processes them, and appends results to results_list.
    """
    def __init__(self, task_queue: queue.Queue, results_list: list, scanner, status_callback=None):
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
    def __init__(self, scanner, num_workers=4, status_callback=None):
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


# ---------------------------------
# FileProcessor
# ---------------------------------
class FileProcessor:
    """Handles file hashing, ignoring, caching checks, etc."""
    
    # Maximum file size to analyze (10MB default)
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
    
    # Common file extensions to analyze
    SUPPORTED_EXTENSIONS = {
        ".py", ".rs", ".js", ".ts", ".tsx", ".jsx", ".md", ".json", 
        ".yaml", ".yml", ".toml", ".sh", ".rst"
    }
    
    # Comprehensive list of directories to ignore
    DEFAULT_IGNORE_DIRS = {
        # Version control
        ".git", ".svn", ".hg", ".bzr",
        
        # Python related
        "__pycache__", "*.egg-info", "*.egg", "*.pyc", 
        "venv", ".venv", "env", "virtualenv", ".virtualenv", "virtual_env", ".virtual_env",
        "venv*", "*venv", "*-venv", "venv-*",  # Catch common venv naming patterns
        ".pytest_cache", ".mypy_cache", ".coverage", "htmlcov",
        "build", "dist", ".tox",
        
        # JavaScript/Node.js related
        "node_modules", "bower_components", ".npm", 
        ".yarn", ".pnp", ".next", ".nuxt", ".cache",
        
        # Rust related
        "target", "cargo-target",
        
        # Go related
        ".go-cache",
        
        # Java related
        ".gradle", "gradle-build", ".m2", "maven-target",
        
        # IDE and editor related
        ".idea", ".vscode", ".vs", ".eclipse", ".settings", 
        ".sublime-*", ".atom", ".devcontainer",
        
        # macOS specific
        ".DS_Store", ".AppleDouble", ".LSOverride",
        
        # Windows specific
        "Thumbs.db", "ehthumbs.db", "Desktop.ini", "$RECYCLE.BIN",
        
        # Dream.OS specific
        ".dreamos_cache", "runtime/reports", "runtime/cache", "runtime/logs",
        
        # Large data directories
        "data", "datasets", "logs", "output", "results", "temp", "tmp",
        "static", "media", "uploads", "downloads", "videos", "images",
        
        # Large documentation
        "docs", "site-docs", "documentation", "site",
        
        # Archives
        "archive", "archives", "backup", "backups", "old",
        
        # Compiled files
        "*.min.js", "*.min.css", "*.bundle.js", "*.bundle.css",
        
        # Generated files
        ".generated", "generated", "auto-generated",
        
        # Tests
        "tests", "test", "testing", "e2e-tests", "integration-tests",
        
        # Chrome profiles
        "chrome_profile", "chrome-profile",
        
        # Migrations
        "migrations"
    }
    
    # Files to ignore regardless of directory
    DEFAULT_IGNORE_FILES = {
        # Git related
        ".gitignore", ".gitkeep", ".gitattributes", ".gitmodules", ".gitconfig", 
        ".github", ".gitlab-ci.yml", ".travis.yml",
        
        # Docker related
        ".dockerignore", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
        
        # Documentation
        "LICENSE", "LICENSE.md", "README.md", "README.rst", "CHANGELOG.md", 
        "CONTRIBUTING.md", "AUTHORS", "NOTICES", "PATENTS", "CODE_OF_CONDUCT.md",
        
        # Package related
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml", 
        "Pipfile.lock", "poetry.lock", "requirements.txt", "setup.py",
        
        # Configuration
        ".env", ".env.local", ".env.development", ".env.production", ".env.test",
        ".editorconfig", ".eslintrc", ".prettierrc", ".stylelintrc", ".pylintrc",
        "tox.ini", "pytest.ini", "mypy.ini", "setup.cfg", ".babelrc",
        "tsconfig.json", "jsconfig.json", ".flowconfig", ".browserslistrc",
        
        # Large generated files
        "*.map", "*.min.*", "*.bundle.*", "*.gz", "*.zip", "*.tar", "*.rar", "*.7z",
        "*.pdf", "*.docx", "*.xlsx", "*.pptx",
        
        # Binary/media files
        "*.jpg", "*.jpeg", "*.png", "*.gif", "*.ico", "*.svg", "*.webp",
        "*.mp3", "*.mp4", "*.wav", "*.ogg", "*.avi", "*.mov", "*.webm",
        "*.ttf", "*.woff", "*.woff2", "*.eot", "*.otf",
        "*.exe", "*.dll", "*.so", "*.dylib", "*.bin", "*.dat",
        
        # Build output
        "*.o", "*.obj", "*.a", "*.lib", "*.pyc", "*.pyo", "*.pyd",
        "*.class", "*.jar", "*.war", "*.ear"
    }
    
    # Regex patterns for common venv path formats (case-insensitive)
    VENV_PATH_PATTERNS = [
        r'.*[/\\]venv[/\\].*',
        r'.*[/\\].venv[/\\].*',
        r'.*[/\\]env[/\\].*', 
        r'.*[/\\]virtualenv[/\\].*',
        r'.*[/\\].virtualenv[/\\].*',
        r'.*[/\\]python\d+[/\\].*',
        r'.*[/\\](?:venv|virtualenv|env)(?:-\w+|\.\w+|\w+)[/\\].*'  # venv-name, venv.name, venvname
    ]
    
    def __init__(self, project_root: Path, cache: Dict, cache_lock: threading.Lock, additional_ignore_dirs: set):
        self.project_root = project_root
        self.cache = cache
        self.cache_lock = cache_lock
        
        # Process ignore patterns
        self.ignore_dirs = set(self.DEFAULT_IGNORE_DIRS)
        if additional_ignore_dirs:
            self.ignore_dirs.update(additional_ignore_dirs)
            
        # Compile venv patterns
        import re
        self.venv_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.VENV_PATH_PATTERNS]
        
        # Log the ignored directories to help with debugging
        logger.info(f"Ignoring directories: {sorted(list(self.ignore_dirs))}")
        logger.info(f"Max file size: {self.MAX_FILE_SIZE_BYTES / (1024 * 1024):.2f} MB")

    def hash_file(self, file_path: Path) -> str:
        try:
            with file_path.open("rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def should_exclude(self, file_path: Path) -> bool:
        """
        Determine if a file should be excluded from analysis.
        
        Args:
            file_path: The path to check
            
        Returns:
            True if the file should be excluded, False otherwise
        """
        # Check if this is the scanner itself
        try:
            if file_path.resolve() == Path(__file__).resolve():
                return True
        except NameError:
            pass
        
        # Normalize path for consistent comparisons
        try:
            file_abs = file_path.resolve()
            rel_path = file_path.relative_to(self.project_root)
            str_path = str(rel_path).replace("\\", "/")
            path_parts = rel_path.parts
        except ValueError:
            # Path is not relative to project_root
            return True
        
        # Check file size first for efficiency
        if file_path.is_file() and file_path.stat().st_size > self.MAX_FILE_SIZE_BYTES:
            logger.debug(f"Excluding large file: {file_path} (> {self.MAX_FILE_SIZE_BYTES / (1024 * 1024):.2f} MB)")
            return True
        
        # Check for venv patterns in the path
        for pattern in self.venv_patterns:
            if pattern.match(str_path):
                logger.debug(f"Excluding file in virtual environment: {file_path}")
                return True
                
        # Look for virtual environment indicators
        try:
            # Look for pyvenv.cfg or similar files that indicate a venv
            if any(p.name == "pyvenv.cfg" for p in file_abs.parents):
                logger.debug(f"Excluding file in virtual environment (pyvenv.cfg found): {file_path}")
                return True
            
            # Look for bin/activate or Scripts/activate.bat
            for parent in file_abs.parents:
                if (parent / "bin" / "activate").exists() or \
                   (parent / "Scripts" / "activate.bat").exists():
                    logger.debug(f"Excluding file in virtual environment (activate script found): {file_path}")
                    return True
        except (OSError, PermissionError):
            # Handle permission errors gracefully
            pass
        
        # Ignore hidden files and directories (starting with .)
        if any(part.startswith(".") for part in path_parts) and not rel_path.suffix == ".py":
            logger.debug(f"Excluding hidden file: {file_path}")
            return True
        
        # Check if any parent directory or current directory is in ignore_dirs
        for i in range(len(path_parts)):
            dir_name = path_parts[i]
            if any(self._glob_match(dir_name, ignore_pattern) for ignore_pattern in self.ignore_dirs):
                logger.debug(f"Excluding file in ignored directory '{dir_name}': {file_path}")
                return True
            
            # Also check the full directory path
            partial_path = Path(*path_parts[:i+1]).as_posix()
            for ignore_dir in self.ignore_dirs:
                # Handle glob patterns
                if self._glob_match(partial_path, ignore_dir) or partial_path.startswith(f"{ignore_dir}/"):
                    logger.debug(f"Excluding file in composite ignored path '{partial_path}': {file_path}")
                    return True
        
        # Check file extension
        if file_path.is_file():
            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                logger.debug(f"Excluding unsupported file extension: {file_path}")
                return True
                
            # Check filename against ignored files
            if any(self._glob_match(file_path.name, ignore_file) for ignore_file in self.DEFAULT_IGNORE_FILES):
                logger.debug(f"Excluding ignored file name: {file_path}")
                return True
                
            # Check for binary files
            try:
                # Quick binary check for the first few bytes
                with open(file_path, 'rb') as f:
                    content_sample = f.read(8192)  # Read first few KB
                    if b'\x00' in content_sample:  # Simple binary check
                        logger.debug(f"Excluding likely binary file: {file_path}")
                        return True
            except (IOError, PermissionError):
                logger.warning(f"Cannot read file to check if binary: {file_path}")
                return True  # Exclude files we can't read
            
        return False
    
    def _glob_match(self, string: str, pattern: str) -> bool:
        """Simple glob pattern matching for exclusion patterns."""
        if pattern == string:
            return True
            
        if '*' not in pattern:
            return False
            
        # Convert glob pattern to regex pattern
        import re
        regex_pattern = pattern.replace('.', '\\.').replace('*', '.*')
        return bool(re.match(f'^{regex_pattern}$', string))

    def process_file(self, file_path: Path, language_analyzer: LanguageAnalyzer) -> Optional[tuple]:
        """Analyzes a file if not in cache or changed, else returns None."""
        # Convert to string for logging and relative path handling
        try:
            file_path_str = str(file_path.relative_to(self.project_root))
        except ValueError:
            # If path is not relative to project_root
            return None
            
        # Check if in exclusion list
        if self.should_exclude(file_path):
            logger.debug(f"Skipping excluded file: {file_path_str}")
            return None
            
        # Check cache for unchanged files
        file_hash_val = self.hash_file(file_path)
        with self.cache_lock:
            if file_path_str in self.cache and self.cache[file_path_str].get("hash") == file_hash_val:
                logger.debug(f"Using cached result for {file_path_str}")
                return None
                
        try:
            # Try to read the file as text
            try:
                with file_path.open("r", encoding="utf-8", errors="replace") as f:
                    source_code = f.read()
            except UnicodeDecodeError:
                logger.warning(f"Unicode decode error for {file_path_str}, likely a binary file")
                return None
                
            # Analyze the file
            analysis_result = language_analyzer.analyze_file(file_path, source_code)
            
            # Update cache
            with self.cache_lock:
                self.cache[file_path_str] = {"hash": file_hash_val, "data": analysis_result}
                
            return (file_path_str, analysis_result)
        except Exception as e:
            logger.error(f"❌ Error analyzing {file_path}: {e}")
            return None


# ---------------------------------
# ReportGenerator (Merges Old + New)
# ---------------------------------
class ReportGenerator:
    """Handles merging new analysis into existing project_analysis.json and chatgpt context."""

    def __init__(self, project_root: Path, analysis: Dict[str, Dict]):
        self.project_root = project_root
        self.analysis = analysis  # e.g. { 'subdir/file.py': {language:..., classes:...}, ... }

    def load_existing_report(self, report_path: Path) -> Dict[str, Any]:
        """Loads any existing project_analysis.json to preserve old entries."""
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
        """
        report_path = self.project_root / "project_analysis.json"
        existing = self.load_existing_report(report_path)

        # Merge logic: new data overrides old entries with the same filename,
        # but preserves any old entries for files not in the current scan.
        merged = {**existing, **self.analysis}

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
                "# DO NOT EDIT MANUALLY - changes may be overwritten\n"
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

    def load_existing_chatgpt_context(self, context_path: Path) -> Dict[str, Any]:
        """Load any existing chatgpt_project_context.json."""
        if context_path.exists():
            try:
                with context_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading existing ChatGPT context: {e}")
        return {}

    def export_chatgpt_context(self, template_path: Optional[str] = None, output_path: Optional[str] = None, 
                               split_by: str = "directory", max_files_per_chunk: int = 100):
        """
        Exports the analysis data in a format suitable for ChatGPT to provide project context.
        Can split the output into multiple files to avoid size limitations.
        
        Args:
            template_path: Optional path to a template file to use for export
            output_path: Optional path to write the output files
            split_by: How to split the output - "directory", "language", or "none"
            max_files_per_chunk: Maximum number of files per chunk when using "none" split
        """
        if not output_path:
            reports_dir = self.project_root / "runtime" / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            context_base_path = reports_dir / "project_context"
        else:
            context_base_path = Path(output_path)
            
        context_base_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"💾 Writing ChatGPT context to: {context_base_path.parent}")

        # Create all_files dictionary with analysis data
        all_files = {}
        for file_path, analysis in self.analysis.items():
            # Skip files with errors
            if "error" in analysis:
                continue
                
            # Create file entry
            suffix = Path(file_path).suffix.lower()
            language = self._determine_language(suffix)
            
            file_entry = {
                "type": "file",
                "language": language,
                "size_bytes": analysis.get("size_bytes", 0),
                "lines": analysis.get("lines", 0),
            }
            
            # Add functions if present
            if "functions" in analysis:
                functions = analysis["functions"]
                if isinstance(functions, list):
                    file_entry["functions"] = functions
                    
            # Add classes if present
            if "classes" in analysis:
                classes = analysis["classes"]
                if isinstance(classes, dict):
                    file_entry["classes"] = list(classes.keys())
                    
            # Add complexity if present
            if "complexity" in analysis:
                file_entry["complexity"] = analysis["complexity"]
                
            # Add to all_files
            all_files[file_path.replace("/", "\\")] = file_entry
            
        # If using template, handle that case separately
        if template_path:
            try:
                from jinja2 import Template
                with open(template_path, "r", encoding="utf-8") as tf:
                    template_content = tf.read()
                t = Template(template_content)

                context_dict = {
                    "project_root": str(self.project_root),
                    "analysis": all_files,
                    "num_files_analyzed": len(all_files),
                    "split_by": split_by,
                    "max_files_per_chunk": max_files_per_chunk
                }
                rendered = t.render(context=context_dict)
                output_file = f"{context_base_path}.md" if not output_path else context_base_path
                with open(output_file, "w", encoding="utf-8") as outf:
                    outf.write(rendered)
                logger.info(f"✅ Rendered ChatGPT context to: {output_file}")
                return
            except ImportError:
                logger.error("⚠️ Jinja2 not installed. Run `pip install jinja2` and re-try.")
                logger.info("Falling back to JSON output...")
            except Exception as e:
                logger.error(f"❌ Error rendering Jinja template: {e}")
                logger.info("Falling back to JSON output...")
        
        # Generate index file that points to all the chunks
        context_index = {
            "type": "index",
            "total_files": len(all_files),
            "project_root": str(self.project_root),
            "generated_at": str(datetime.datetime.now()),
            "chunks": []
        }
        
        # Split and save the context data
        if split_by == "directory":
            self._export_by_directory(all_files, context_base_path.parent, context_index)
        elif split_by == "language":
            self._export_by_language(all_files, context_base_path.parent, context_index)
        else:
            self._export_by_chunks(all_files, context_base_path.parent, context_index, max_files_per_chunk)
        
        # Save the index file
        index_path = context_base_path.parent / "project_context_index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(context_index, f, indent=4)
        
        # Also save a metadata file with basic project info
        metadata_path = context_base_path.parent / "project_metadata.json"
        metadata = {
            "type": "metadata",
            "total_files": len(all_files),
            "project_root": str(self.project_root),
            "generated_at": str(datetime.datetime.now()),
            "languages": list(set(file["language"] for file in all_files.values())),
            "file_extensions": list(set(Path(file_path).suffix for file_path in all_files.keys())),
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)
            
        logger.info(f"✅ Exported ChatGPT context to multiple files in {context_base_path.parent}")
        
    def _export_by_directory(self, all_files: Dict, output_dir: Path, context_index: Dict):
        """Split the context data by directory structure."""
        # Group files by their top-level directory
        dir_groups = {}
        for file_path, file_data in all_files.items():
            # Get the top-level directory
            parts = Path(file_path).parts
            if len(parts) > 1:
                top_dir = parts[0]
            else:
                top_dir = "_root_"  # For files in the root directory
            
            dir_groups.setdefault(top_dir, {})
            dir_groups[top_dir][file_path] = file_data
        
        # Save each directory group to a separate file
        for dir_name, files in dir_groups.items():
            safe_dir_name = dir_name.replace("\\", "_").replace("/", "_").replace(":", "_")
            output_path = output_dir / f"project_context_{safe_dir_name}.json"
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(files, f, indent=4)
            
            # Add to index
            context_index["chunks"].append({
                "name": dir_name,
                "file_count": len(files),
                "path": output_path.name
            })
    
    def _export_by_language(self, all_files: Dict, output_dir: Path, context_index: Dict):
        """Split the context data by programming language."""
        # Group files by their language
        lang_groups = {}
        for file_path, file_data in all_files.items():
            lang = file_data.get("language", "unknown")
            lang_groups.setdefault(lang, {})
            lang_groups[lang][file_path] = file_data
        
        # Save each language group to a separate file
        for lang, files in lang_groups.items():
            output_path = output_dir / f"project_context_{lang}.json"
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(files, f, indent=4)
            
            # Add to index
            context_index["chunks"].append({
                "language": lang,
                "file_count": len(files),
                "path": output_path.name
            })
    
    def _export_by_chunks(self, all_files: Dict, output_dir: Path, context_index: Dict, max_files_per_chunk: int):
        """Split the context data into equal-sized chunks."""
        file_items = list(all_files.items())
        chunks = [file_items[i:i + max_files_per_chunk] for i in range(0, len(file_items), max_files_per_chunk)]
        
        # Save each chunk to a separate file
        for i, chunk in enumerate(chunks):
            chunk_dict = dict(chunk)
            output_path = output_dir / f"project_context_chunk{i+1}.json"
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(chunk_dict, f, indent=4)
            
            # Add to index
            context_index["chunks"].append({
                "chunk": i+1,
                "file_count": len(chunk_dict),
                "path": output_path.name
            })
            
    def _determine_language(self, extension: str) -> str:
        """Determine the language from a file extension."""
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".html": "html",
            ".css": "css",
            ".md": "markdown",
            ".json": "json",
            ".xml": "xml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".sh": "bash",
            ".bat": "batch",
            ".ps1": "powershell",
            ".sql": "sql",
        }
        return extension_map.get(extension.lower(), "text")


# ---------------------------------
# ProjectScanner
# ---------------------------------
class ProjectScanner:
    """
    A universal project scanner that:
      - Identifies Python, Rust, JS, TS files.
      - Extracts functions, classes, routes, complexity.
      - Caches file hashes to skip unchanged files.
      - Detects moved files by matching file hashes.
      - Merges new analysis into existing project_analysis.json (preserving old entries).
      - Exports a merged ChatGPT context if requested (preserving old context data).
      - Processes files asynchronously with BotWorker threads.
      - Auto-generates __init__.py files for Python packages.
      - Can split output into multiple files based on directories, languages, or fixed chunks.
    """
    def __init__(self, project_root: Union[str, Path] = "."):
        self.project_root = Path(project_root).resolve()
        self.analysis: Dict[str, Dict] = {}
        self.cache = self.load_cache()
        self.cache_lock = threading.Lock()
        self.additional_ignore_dirs = set()
        self.use_cache = True
        self.language_analyzer = LanguageAnalyzer()
        self.file_processor = FileProcessor(
            self.project_root,
            self.cache,
            self.cache_lock,
            self.additional_ignore_dirs
        )
        self.report_generator = ReportGenerator(self.project_root, self.analysis)

    def load_cache(self) -> Dict:
        """Loads JSON cache from disk if present. Otherwise returns empty."""
        cache_path = Path(CACHE_FILE)
        if cache_path.exists():
            try:
                with cache_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def save_cache(self):
        """Writes the updated cache to disk."""
        cache_path = Path(CACHE_FILE)
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=4)

    def scan_project(self, progress_callback: Optional[callable] = None, split_output_by: str = "directory", max_files_per_chunk: int = 100):
        """
        Orchestrates the project scan:
        - Finds Python, Rust, JS, TS files with os.walk()
        - Excludes certain directories
        - Detects moved files by comparing cached hashes
        - Spawns multibot workers for concurrency
        - Merges new analysis with old project_analysis.json (preserving old data)
        - Writes/updates 'project_analysis.json' without overwriting unscanned files
        - Reports progress via progress_callback(percent)
        - Splits output files based on specified strategy
        
        Args:
            progress_callback: Optional callback for progress updates
            split_output_by: How to split the context output - "directory", "language", or "none"
            max_files_per_chunk: Maximum number of files per chunk when using "none" split
        """
        logger.info(f"🔍 Scanning project: {self.project_root} ...")

        # Update FileProcessor with current additional_ignore_dirs
        self.file_processor = FileProcessor(
            self.project_root,
            self.cache,
            self.cache_lock,
            self.additional_ignore_dirs
        )

        file_extensions = self.file_processor.SUPPORTED_EXTENSIONS
        valid_files = []
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)
            if self.file_processor.should_exclude(root_path):
                continue
            for file in files:
                file_path = root_path / file
                if file_path.suffix.lower() in file_extensions and not self.file_processor.should_exclude(file_path):
                    valid_files.append(file_path)

        total_files = len(valid_files)
        logger.info(f"📝 Found {total_files} valid files for analysis.")

        # Progress reporting: update every file processed
        processed_count = 0

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

        # Asynchronous processing
        logger.info("⏱️  Processing files asynchronously...")
        num_workers = os.cpu_count() or 4
        manager = MultibotManager(
            scanner=self,
            num_workers=num_workers,
            status_callback=lambda fp, res: logger.info(f"Processed: {fp}")
        )
        for file_path in valid_files:
            manager.add_task(file_path)
        manager.wait_for_completion()
        manager.stop_workers()

        # Update progress for each processed file
        for result in manager.results_list:
            processed_count += 1
            if progress_callback:
                percent = int((processed_count / total_files) * 100)
                progress_callback(percent)
            if result is not None:
                file_path, analysis_result = result
                self.analysis[file_path] = analysis_result

        # Update the report_generator with the new analysis
        self.report_generator = ReportGenerator(self.project_root, self.analysis)

        # Merge & write final report + save updated cache
        self.report_generator.save_report() 
        
        # Export ChatGPT context with the specified splitting strategy
        self.report_generator.export_chatgpt_context(split_by=split_output_by, max_files_per_chunk=max_files_per_chunk)
        
        self.save_cache()
        logger.info(f"✅ Scan complete. Results saved in {self.project_root / 'runtime' / 'reports'} directory")


    def _process_file(self, file_path: Path):
        """Processes a file via FileProcessor, returning (relative_path, analysis_result)."""
        return self.file_processor.process_file(file_path, self.language_analyzer)

    def generate_init_files(self, overwrite: bool = True):
        """Generate __init__.py for python packages."""
        self.report_generator.generate_init_files(overwrite)

    def export_chatgpt_context(self, template_path: Optional[str] = None, output_path: Optional[str] = None, 
                                split_by: str = "directory", max_files_per_chunk: int = 100):
        """
        Exports the analysis data in a format suitable for ChatGPT to provide project context.
        Can split the output into multiple files based on the specified strategy.
        
        Args:
            template_path: Optional path to a template file to use for export
            output_path: Optional path to write the output files
            split_by: How to split the output - "directory", "language", or "none"
            max_files_per_chunk: Maximum number of files per chunk when using "none" split
        """
        self.report_generator.export_chatgpt_context(
            template_path=template_path, 
            output_path=output_path,
            split_by=split_by,
            max_files_per_chunk=max_files_per_chunk
        )

    # ----- Agent Categorization -----
    def categorize_agents(self):
        """
        Loops over analyzed Python classes, assigning maturity & agent_type.
        """
        for file_path, result in self.analysis.items():
            if file_path.endswith(".py"):
                for class_name, class_data in result.get("classes", {}).items():
                    class_data["maturity"] = self._maturity_level(class_name, class_data)
                    class_data["agent_type"] = self._agent_type(class_name, class_data)

    def _maturity_level(self, class_name: str, class_data: Dict[str, Any]) -> str:
        score = 0
        if class_data.get("docstring"):
            score += 1
        if len(class_data.get("methods", [])) > 3:
            score += 1
        if any(base for base in class_data.get("base_classes", []) if base not in ("object", None)):
            score += 1
        if class_name and class_name[0].isupper():
            score += 1
        levels = ["Kiddie Script", "Prototype", "Core Asset", "Core Asset"]
        return levels[min(score, 3)]

    def _agent_type(self, class_name: str, class_data: Dict[str, Any]) -> str:
        doc = (class_data.get("docstring") or "").lower()
        methods = class_data.get("methods", [])
        if "run" in methods:
            return "ActionAgent"
        if "transform" in doc or "parse" in doc:
            return "DataAgent"
        if any(m in methods for m in ["predict", "analyze"]):
            return "SignalAgent"
        return "Utility"

# ---------------------------------
# CLI Usage
# ---------------------------------
def main():
    """
    Main entry point for the project scanner.
    Uses the modular implementation for better maintainability.
    """
    import sys
    import argparse
    import asyncio

    # Use the modular implementation
    try:
        from dreamos.tools.scanner.cli import main as scanner_main
        # Run the modular scanner CLI
        asyncio.run(scanner_main())
        return
    except ImportError:
        print("Could not import modular scanner. Falling back to legacy implementation.")
        # Continue with legacy implementation below
    
    parser = argparse.ArgumentParser(description="Dream.OS Project Scanner")
    parser.add_argument("-p", "--project-root", default=".", help="Root directory of the project to scan")
    parser.add_argument("--exclude", action="append", default=[], help='Directory patterns to exclude (can be used multiple times)')
    parser.add_argument("--no-cache", action="store_true", help="Disable using the file hash cache")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker threads for analysis")
    
    # Add output splitting options
    parser.add_argument(
        "--split-output",
        type=str,
        choices=["directory", "language", "none"],
        default="directory",
        help="How to split the context output for ChatGPT (directory, language, or none)"
    )
    parser.add_argument(
        "--max-files-per-chunk",
        type=int,
        default=100,
        help="Maximum number of files per chunk when using 'none' split mode"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # When running from command line, print progress to console
    def progress_update(percent_complete, current_file=None):
        msg = f"Scan progress: {percent_complete:.1f}%"
        if current_file:
            msg += f" (Processing: {current_file})"
        print(msg, end='\r')  # Overwrite the line
        if percent_complete >= 100:
            print()  # Add newline at the end
    
    # Create and run the scanner
    scanner = ProjectScanner(project_root=args.project_root)
    scanner.additional_ignore_dirs = set(args.exclude)
    scanner.use_cache = not args.no_cache
    
    try:
        # Run scanner with output splitting options
        scanner.scan_project(
            progress_callback=progress_update,
            split_output_by=args.split_output,
            max_files_per_chunk=args.max_files_per_chunk
        )
        
        print("\nGenerating project reports...")
        scanner.generate_init_files()
        
        # No need to call export_chatgpt_context separately as it's already done in scan_project
        print(f"Scan complete! Reports saved to {Path(args.project_root) / 'runtime' / 'reports'}")
    except KeyboardInterrupt:
        print("\nScan canceled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

