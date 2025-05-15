import ast
import asyncio
import json
import logging
import os
import queue
import threading
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Set, Tuple # Added Set and Tuple

# Optional: If tree-sitter grammars are present for Rust/JS/TS
try:
    from tree_sitter import Language, Parser
except ImportError:
    Language = None
    Parser = None
    # logger.warning( # Logger not yet defined at this global scope, will log within classes
    #     "⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled."
    # )

logger = logging.getLogger(__name__)

# ---------------------------------
# Project Config / Cache File Setup - Constants
# ---------------------------------
# These might be configurable in the ProjectScanner class or passed during instantiation
# For now, defining them here if they are used by ReportGenerator directly.
# CACHE_FILE = "dependency_cache.json" # Handled by ProjectScanner instance
# PROJECT_ANALYSIS_FILE = "project_analysis.json" # Handled by ProjectScanner instance
# CHATGPT_PROJECT_CONTEXT_FILE = "chatgpt_project_context.json" # Handled by ProjectScanner instance


# ---------------------------------
# Language Analyzer
# ---------------------------------
class LanguageAnalyzer:
    """Handles language-specific code analysis for different programming languages."""

    def __init__(self):
        """Initialize language analyzers and parsers."""
        # Initialize parsers - paths to grammars might need to be configurable
        self.rust_parser = self._init_tree_sitter_language("rust", "path/to/tree-sitter-rust.so")
        self.js_parser = self._init_tree_sitter_language("javascript", "path/to/tree-sitter-javascript.so")
        if Language is None or Parser is None:
            logger.warning(
                "⚠️ tree-sitter not installed or not found. Rust/JS/TS AST parsing will be partially disabled."
            )

    def _init_tree_sitter_language(self, lang_name: str, grammar_path: str) -> Optional[Parser]:
        """
        Initializes and returns a Parser for the given language name.
        """
        if not Language or not Parser:
            return None

        if not Path(grammar_path).exists():
            logger.warning(f"⚠️ {lang_name} grammar not found at {grammar_path}. Ensure paths are correct.")
            return None

        try:
            lang_lib = Language(grammar_path, lang_name)
            parser = Parser()
            parser.set_language(lang_lib)
            logger.info(f"Initialized tree-sitter {lang_name} parser from {grammar_path}")
            return parser
        except Exception as e:
            logger.error(f"⚠️ Failed to initialize tree-sitter {lang_name} parser from {grammar_path}: {e}")
            return None

    def analyze_file(self, file_path: Path, source_code: str) -> Dict:
        """
        Analyzes source code based on file extension.
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
                "imports": [], # Added for consistency
                "complexity": 0,
            }

    def _analyze_python(self, source_code: str) -> Dict:
        """
        Analyzes Python source code using the builtin `ast` module.
        Extracts a naive list of function defs, classes, routes, complexity, etc.
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            logger.error(f"Syntax error parsing Python code: {e}")
            return {"language": ".py", "functions": [], "classes": {}, "routes": [], "imports": [], "complexity": 0, "error": str(e)}

        functions = []
        classes = {}
        routes = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({"type": "import", "name": alias.name, "asname": alias.asname})
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module if node.module else ""
                for alias in node.names:
                    imports.append({"type": "from_import", "module": module_name, "name": alias.name, "asname": alias.asname, "level": node.level})
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and hasattr(decorator.func, "attr"):
                        func_attr = decorator.func.attr.lower()
                        if func_attr in {"route", "get", "post", "put", "delete", "patch"}:
                            path_arg = "/unknown"
                            methods = [func_attr.upper()]
                            if decorator.args:
                                arg0 = decorator.args[0]
                                if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str): # ast.Str is deprecated
                                    path_arg = arg0.value
                            for kw in decorator.keywords:
                                if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)): # Allow tuple as well
                                    extracted_methods = []
                                    for elt in kw.value.elts:
                                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                            extracted_methods.append(elt.value.upper())
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
                    # else: # Handle other complex base types if necessary
                    #     base_classes.append(None) # Or ast.unparse(base) in Py 3.9+
                classes[node.name] = {
                    "methods": method_names,
                    "docstring": docstring,
                    "base_classes": base_classes,
                }
        complexity = len(functions) + sum(len(c.get("methods", [])) for c in classes.values())
        return {"language": ".py", "functions": functions, "classes": classes, "routes": routes, "imports": imports, "complexity": complexity}

    def _analyze_rust(self, source_code: str) -> Dict:
        """Analyzes Rust source code using tree-sitter (if available)."""
        if not self.rust_parser:
            return {"language": ".rs", "functions": [], "classes": {}, "routes": [], "imports": [], "complexity": 0}
        tree = self.rust_parser.parse(bytes(source_code, "utf-8"))
        functions: List[str] = []
        structs_and_impls: Dict[str, List[str]] = defaultdict(list) # Using dict to store methods per struct/impl
        # Basic import/use statement tracking
        imports: List[Dict[str, str]] = []


        def _traverse_rust(node):
            if node.type == "function_item":
                name_node = node.child_by_field_name("name")
                if name_node:
                    functions.append(name_node.text.decode("utf-8"))
            elif node.type == "struct_item":
                name_node = node.child_by_field_name("name")
                if name_node:
                    structs_and_impls[name_node.text.decode("utf-8")] = [] # Initialize if not exists
            elif node.type == "impl_item":
                # For impl blocks, associate methods with the struct/type being implemented
                type_node = node.child_by_field_name("type")
                if type_node:
                    type_name = type_node.text.decode("utf-8")
                    if type_name not in structs_and_impls:
                         structs_and_impls[type_name] = []
                    
                    body_node = node.child_by_field_name("body")
                    if body_node:
                        for child_node in body_node.children:
                            if child_node.type == "function_item":
                                method_name_node = child_node.child_by_field_name("name")
                                if method_name_node:
                                     structs_and_impls[type_name].append(method_name_node.text.decode("utf-8"))
            elif node.type == "use_declaration":
                # Simple import tracking: gets the full 'use' path
                path_node = node.child_by_field_name("argument") # tree-sitter-rust might use 'path' or 'argument'
                if not path_node and len(node.children) > 1: # Fallback for some structures
                    path_node = node.children[1] # often the path part
                if path_node:
                    imports.append({"type": "use", "path": path_node.text.decode("utf-8")})

            for child in node.children:
                _traverse_rust(child)
        
        _traverse_rust(tree.root_node)
        # For Rust, 'classes' can be represented by structs and their impl blocks
        # We'll consider each struct with methods as a "class" for complexity
        complexity = len(functions) + sum(len(methods) for methods in structs_and_impls.values())
        return {"language": ".rs", "functions": functions, "classes": structs_and_impls, "routes": [], "imports": imports, "complexity": complexity}


    def _analyze_javascript(self, source_code: str) -> Dict:
        """Analyzes JS/TS using tree-sitter (if available)."""
        if not self.js_parser:
            return {"language": ".js/.ts", "functions": [], "classes": {}, "routes": [], "imports": [], "complexity": 0}
        tree = self.js_parser.parse(bytes(source_code, "utf-8"))
        functions: List[str] = []
        classes: Dict[str, List[str]] = defaultdict(list)
        imports: List[Dict[str, Any]] = [] # For import/require statements

        def get_node_text(node) -> str:
            return node.text.decode("utf-8")

        def _traverse_js(node):
            nonlocal functions, classes, imports
            node_type = node.type
            
            if node_type in ("function_declaration", "arrow_function", "method_definition"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    functions.append(get_node_text(name_node))
                elif node_type == "arrow_function": # Try to get var name for anonymous arrow funcs
                    parent = node.parent
                    if parent and parent.type == "variable_declarator":
                         name_node = parent.child_by_field_name("name")
                         if name_node:
                            functions.append(f"{get_node_text(name_node)} (arrow)")


            elif node_type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    class_name = get_node_text(name_node)
                    classes[class_name] = []
                    body_node = node.child_by_field_name("body")
                    if body_node and hasattr(body_node, 'children'):
                        for member_node in body_node.children:
                            if member_node.type == "method_definition":
                                method_name_node = member_node.child_by_field_name("name")
                                if method_name_node:
                                    classes[class_name].append(get_node_text(method_name_node))
            
            elif node_type == "import_statement":
                source_node = node.child_by_field_name("source")
                source = get_node_text(source_node) if source_node else None
                # Iterate over named imports or default import
                for child in node.children:
                    if child.type == "import_clause":
                        for named_import_node in child.children:
                            if named_import_node.type == "named_imports":
                                for specifier in named_import_node.children:
                                     if specifier.type == "import_specifier":
                                        name = get_node_text(specifier.child_by_field_name("name"))
                                        alias = get_node_text(specifier.child_by_field_name("alias")) if specifier.child_by_field_name("alias") else None
                                        imports.append({"type": "named", "source": source, "name": name, "alias": alias})
                            elif named_import_node.type == "identifier": # Default import
                                imports.append({"type": "default", "source": source, "name": get_node_text(named_import_node)})
                    elif child.type == "string": # for side-effect imports like 'import "style.css";'
                        imports.append({"type": "side-effect", "source": get_node_text(child)})


            elif node_type == "call_expression": # For require('module')
                func_node = node.child_by_field_name("function")
                if func_node and get_node_text(func_node) == "require":
                    args_node = node.child_by_field_name("arguments")
                    if args_node and args_node.children:
                        first_arg = args_node.children[0] # Assuming first arg is the module path string
                        if first_arg.type in ("string", "template_string"):
                             module_name = get_node_text(first_arg).strip('"\'`')
                             # Try to find variable assignment for this require
                             var_name = None
                             if node.parent and node.parent.type == "variable_declarator":
                                 name_node = node.parent.child_by_field_name("name")
                                 if name_node:
                                     var_name = get_node_text(name_node)
                             imports.append({"type": "require", "module": module_name, "variable": var_name})
            
            if hasattr(node, 'children'):
                for child in node.children:
                    _traverse_js(child)

        _traverse_js(tree.root_node)
        complexity = len(functions) + sum(len(m) for m in classes.values())
        return {"language": ".js/.ts", "functions": functions, "classes": classes, "routes": [], "imports": imports, "complexity": complexity}


# ---------------------------------
# Worker and Manager for Parallel Processing
# ---------------------------------
class BotWorker(threading.Thread):
    """Worker thread for processing files from a queue."""
    def __init__(self, task_queue: queue.Queue, results_list: list, scanner_instance, status_callback=None): # scanner_instance to call _process_file_internal
        super().__init__()
        self.task_queue = task_queue
        self.results_list = results_list
        self.scanner_instance = scanner_instance # Store ProjectScanner instance
        self.status_callback = status_callback
        self.daemon = True # Allow main program to exit even if workers are blocked

    def run(self):
        while True:
            try:
                file_path = self.task_queue.get(timeout=1) # Timeout to allow thread to exit
            except queue.Empty:
                # logger.debug(f"{self.name} queue empty, exiting.")
                break # Exit if queue is empty

            if file_path is None: # Sentinel value to stop worker
                # logger.debug(f"{self.name} received sentinel, exiting.")
                self.task_queue.task_done()
                break
            
            # logger.debug(f"{self.name} processing {file_path}")
            try:
                # Use the scanner_instance's internal processing method
                result = self.scanner_instance._process_file_internal(file_path)
                if result:
                    self.results_list.append(result)
                if self.status_callback:
                    self.status_callback(f"Processed: {file_path.name}")
            except Exception as e:
                logger.error(f"Error processing {file_path} in {self.name}: {e}", exc_info=True)
            finally:
                self.task_queue.task_done()


class MultibotManager:
    """Manages multiple BotWorker threads for parallel file processing."""
    def __init__(self, scanner_instance, num_workers=os.cpu_count() or 1, status_callback=None):
        self.task_queue = queue.Queue()
        self.results_list: List[Tuple[Path, Dict]] = [] # Expect tuples of (file_path, analysis_data)
        self.scanner_instance = scanner_instance
        self.num_workers = num_workers
        self.workers: List[BotWorker] = []
        self.status_callback = status_callback

    def add_task(self, file_path: Path):
        self.task_queue.put(file_path)

    def start_workers(self):
        self.workers = []
        for i in range(self.num_workers):
            worker = BotWorker(self.task_queue, self.results_list, self.scanner_instance, self.status_callback)
            worker.start()
            self.workers.append(worker)
        # logger.info(f"Started {self.num_workers} worker threads.")


    def wait_for_completion(self):
        self.task_queue.join() # Wait for all tasks to be processed
        # logger.debug("All tasks processed by queue.")
        # Signal workers to stop by putting None for each worker
        for _ in self.workers:
            self.task_queue.put(None)
        # logger.debug("Sent sentinel values to workers.")
        for worker in self.workers:
            worker.join(timeout=5) # Wait for workers to finish
            if worker.is_alive():
                 logger.warning(f"Worker {worker.name} did not terminate cleanly.")
        # logger.info("All workers have completed.")
        return self.results_list


# ---------------------------------
# File Processor
# ---------------------------------
class FileProcessor:
    """Handles individual file processing including hashing, exclusion checks, and analysis calling."""
    def __init__(
        self,
        project_root: Path,
        cache: Dict, # Dependency cache
        cache_lock: threading.Lock,
        language_analyzer: LanguageAnalyzer, # Pass analyzer instance
        additional_ignore_dirs: Optional[Set[str]] = None,
        additional_ignore_files: Optional[Set[str]] = None,
        additional_include_extensions: Optional[Set[str]] = None,

    ):
        self.project_root = project_root
        self.cache = cache
        self.cache_lock = cache_lock
        self.language_analyzer = language_analyzer # Use passed instance
        self.ignore_dirs = {
            ".git", "__pycache__", "node_modules", "venv", "target", "build", "dist",
            "docs", "tests", "examples", "samples", "scripts", # Common general ignores
            ".vscode", ".idea", ".devcontainer" # IDE specific
        }.union(additional_ignore_dirs or set())
        
        self.ignore_files = {
            "poetry.lock", "package-lock.json", "yarn.lock", # Lock files
            ".DS_Store"
        }.union(additional_ignore_files or set())

        # Default to a wide range of source code and config files
        self.include_extensions = {
            ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp",
            ".cs", ".go", ".rs", ".swift", ".kt", ".kts", ".scala", ".rb", ".php",
            ".html", ".css", ".scss", ".less", ".vue", ".svelte",
            ".json", ".yaml", ".yml", ".xml", ".toml", ".ini", ".md", ".sh", ".ps1",
            "Dockerfile", # Dockerfile often has no extension
            ".tf", ".hcl" # Terraform
        }.union(additional_include_extensions or set())


    def hash_file(self, file_path: Path) -> str:
        """Computes an MD5 hash of the file content."""
        import hashlib # Local import as it's only used here
        hasher = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                buf = f.read(65536) # Read in 64k chunks
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(65536)
            return hasher.hexdigest()
        except IOError as e:
            logger.error(f"Could not read file for hashing {file_path}: {e}")
            return ""


    def should_exclude(self, file_path: Path) -> bool:
        """Determines if a file should be excluded based on ignore lists and extension includes."""
        if file_path.name in self.ignore_files:
            return True
        # Workaround for potential pathlib issue with .parts
        try:
            path_parts = file_path.parts
        except AttributeError:
            # Fallback if .parts fails unexpectedly
            path_parts = str(file_path).split(os.sep)
            logger.warning(f"Pathlib .parts failed for {file_path}, using string split fallback.")

        if any(part in self.ignore_dirs for part in path_parts):
            return True
        # If include_extensions is defined, only include those files
        # Handle files with no extension (like Dockerfile) specifically if needed
        if file_path.name in self.include_extensions : # e.g. "Dockerfile"
             return False
        if file_path.suffix.lower() not in self.include_extensions:
            return True
        return False

    def process_file(self, file_path: Path) -> Optional[Tuple[Path, Dict[str, Any]]]:
        """
        Processes a single file: checks cache, analyzes if needed, updates cache.
        Returns a tuple (file_path, analysis_data) or None if skipped or error.
        """
        relative_path_str = str(file_path.relative_to(self.project_root))
        
        if self.should_exclude(file_path):
            # logger.debug(f"Excluding file: {relative_path_str}")
            return None

        current_hash = self.hash_file(file_path)
        if not current_hash: # Hashing failed
             return None

        cached_entry = self.cache.get(relative_path_str)
        if cached_entry and cached_entry.get("hash") == current_hash:
            # logger.debug(f"Cache hit for {relative_path_str}")
            # Ensure all expected keys are present from cache, even if empty lists/dicts
            analysis_data = cached_entry.get("analysis", {})
            analysis_data.setdefault("functions", [])
            analysis_data.setdefault("classes", {})
            analysis_data.setdefault("routes", [])
            analysis_data.setdefault("imports", [])
            analysis_data.setdefault("complexity", 0)
            return file_path, analysis_data


        # logger.debug(f"Processing {relative_path_str} (hash: {current_hash})")
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                source_code = f.read()
        except Exception as e:
            logger.error(f"Could not read file {file_path}: {e}")
            return None

        analysis_data = self.language_analyzer.analyze_file(file_path, source_code)
        analysis_data["file_path"] = relative_path_str # Add relative path for context
        analysis_data["hash"] = current_hash

        # Update cache, ensuring thread safety
        with self.cache_lock:
            self.cache[relative_path_str] = {
                "hash": current_hash,
                "analysis": analysis_data,
            }
        return file_path, analysis_data


# ---------------------------------
# Report Generator
# ---------------------------------
class ReportGenerator:
    """Generates project analysis and ChatGPT context reports."""
    def __init__(self, project_root: Path, analysis_results: List[Tuple[Path, Dict[str, Any]]]):
        self.project_root = project_root
        # Convert list of tuples to dict for easier lookup by relative path
        self.analysis_data: Dict[str, Dict[str, Any]] = {
            str(path.relative_to(project_root)): data for path, data in analysis_results if data
        }
        self.project_analysis_file = project_root / "project_analysis.json"
        self.chatgpt_context_file = project_root / "chatgpt_project_context.json"


    def load_existing_report(self, report_path: Path) -> Dict[str, Any]:
        """Loads an existing JSON report file if it exists."""
        if report_path.exists():
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load existing report {report_path}: {e}")
        return {}

    def save_project_analysis_report(self):
        """Generates and saves the project_analysis.json report."""
        # existing_report = self.load_existing_report(self.project_analysis_file) # Merge logic can be complex
        
        # For now, overwrite with new full analysis data
        report_content = {
            "project_root": str(self.project_root),
            "files_analyzed": len(self.analysis_data),
            "analysis_details": self.analysis_data, # Contains all per-file analysis
            # TODO: Add summaries like total functions, classes, complexity, language breakdown etc.
            # "summary": self._generate_summary()
        }
        
        try:
            with open(self.project_analysis_file, "w", encoding="utf-8") as f:
                json.dump(report_content, f, indent=4, sort_keys=True)
            logger.info(f"Project analysis report saved to {self.project_analysis_file}")
        except IOError as e:
            logger.error(f"Could not save project analysis report to {self.project_analysis_file}: {e}")

    # Placeholder for a more detailed summary
    # def _generate_summary(self) -> Dict:
    #     summary = {"total_functions": 0, "total_classes": 0, "language_counts": defaultdict(int)}
    #     for data in self.analysis_data.values():
    #         summary["total_functions"] += len(data.get("functions", []))
    #         summary["total_classes"] += len(data.get("classes", {}))
    #         lang = data.get("language", "unknown")
    #         summary["language_counts"][lang] +=1
    #     return summary


    def export_chatgpt_context(self, template_path: Optional[Union[str, Path]] = None, output_path: Optional[Union[str, Path]] = None):
        """
        Exports a simplified project context for ChatGPT, optionally using a template.
        """
        context_data = []
        for file_path_str, data in self.analysis_data.items():
            context_data.append({
                "file_path": file_path_str,
                "language": data.get("language"),
                "functions": data.get("functions", []),
                "classes": list(data.get("classes", {}).keys()), # Just class names
                "imports": [imp.get("name") or imp.get("module") for imp in data.get("imports", []) if imp], # Simplified imports
            })

        # Sort by file path for consistent output
        context_data.sort(key=lambda x: x["file_path"])
        
        final_output_path = Path(output_path) if output_path else self.chatgpt_context_file

        # If a template is provided, try to use it (simple substitution for now)
        if template_path:
            template_p = Path(template_path)
            if template_p.exists():
                try:
                    with open(template_p, "r", encoding="utf-8") as f_template:
                        template_content = f_template.read()
                    # Very basic templating - replace a placeholder with JSON dump
                    # For more complex templating, consider libraries like Jinja2
                    output_content = template_content.replace("{{project_context_json}}", json.dumps(context_data, indent=2))
                except Exception as e:
                    logger.error(f"Error processing template {template_path}: {e}. Falling back to raw JSON.")
                    output_content = json.dumps({"project_context": context_data}, indent=4)
            else:
                logger.warning(f"Template file {template_path} not found. Exporting raw JSON.")
                output_content = json.dumps({"project_context": context_data}, indent=4)
        else:
            output_content = json.dumps({"project_context": context_data}, indent=4)
        
        try:
            with open(final_output_path, "w", encoding="utf-8") as f:
                f.write(output_content)
            logger.info(f"ChatGPT project context exported to {final_output_path}")
        except IOError as e:
            logger.error(f"Could not export ChatGPT project context to {final_output_path}: {e}")


# ---------------------------------
# Project Scanner
# ---------------------------------
class ProjectScanner:
    """
    Scans a software project, analyzes files, and generates reports.
    """
    DEFAULT_IGNORE_DIRS = {
        ".git", "__pycache__", "node_modules", "venv", "target", "build", "dist",
        "docs", "tests", "examples", "samples", # Often excluded from primary source analysis
        ".vscode", ".idea", ".devcontainer", "site", "htmlcov", ".pytest_cache", ".mypy_cache",
        "migrations", "static", "media", # Common web framework folders
    }
    DEFAULT_IGNORE_FILES = {
        "poetry.lock", "package-lock.json", "yarn.lock", ".DS_Store",
        "requirements.txt", "Pipfile", "Pipfile.lock", # Often not primary source
    }
    DEFAULT_INCLUDE_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp",
        ".cs", ".go", ".rs", ".swift", ".kt", ".kts", ".scala", ".rb", ".php",
        ".html", ".css", ".scss", ".less", ".vue", ".svelte",
        ".json", ".yaml", ".yml", ".xml", ".toml", ".ini", ".md", ".sh", ".ps1",
        "Dockerfile", ".tf", ".hcl",
    }


    def __init__(self, project_root: Union[str, Path] = ".",
                 cache_file_name: str = "dependency_cache.json",
                 analysis_file_name: str = "project_analysis.json",
                 chatgpt_context_file_name: str = "chatgpt_project_context.json",
                 ignore_dirs: Optional[Set[str]] = None,
                 ignore_files: Optional[Set[str]] = None,
                 include_extensions: Optional[Set[str]] = None,
                 num_workers: Optional[int] = None,
                 tree_sitter_grammar_paths: Optional[Dict[str,str]] = None): # e.g. {"rust": "/path/to/rust.so"}

        self.project_root = Path(project_root).resolve()
        self.cache_file = self.project_root / cache_file_name
        self.analysis_file = self.project_root / analysis_file_name # For ReportGenerator
        self.chatgpt_context_file = self.project_root / chatgpt_context_file_name # For ReportGenerator

        self.ignore_dirs = self.DEFAULT_IGNORE_DIRS.union(ignore_dirs or set())
        self.ignore_files = self.DEFAULT_IGNORE_FILES.union(ignore_files or set())
        self.include_extensions = self.DEFAULT_INCLUDE_EXTENSIONS.union(include_extensions or set())
        
        self.num_workers = num_workers if num_workers is not None else (os.cpu_count() or 1)

        self.cache_lock = threading.Lock()
        self.cache: Dict[str, Any] = self.load_cache()
        
        self.language_analyzer = LanguageAnalyzer()
        # Update grammar paths if provided
        if tree_sitter_grammar_paths:
            if 'rust' in tree_sitter_grammar_paths and self.language_analyzer.rust_parser:
                self.language_analyzer.rust_parser = self.language_analyzer._init_tree_sitter_language("rust", tree_sitter_grammar_paths['rust'])
            if 'javascript' in tree_sitter_grammar_paths and self.language_analyzer.js_parser:
                self.language_analyzer.js_parser = self.language_analyzer._init_tree_sitter_language("javascript", tree_sitter_grammar_paths['javascript'])


        self.file_processor = FileProcessor(
            project_root=self.project_root,
            cache=self.cache,
            cache_lock=self.cache_lock,
            language_analyzer=self.language_analyzer,
            additional_ignore_dirs=self.ignore_dirs, # Pass the combined set
            additional_ignore_files=self.ignore_files,
            additional_include_extensions=self.include_extensions
        )
        self.analysis_results: List[Tuple[Path, Dict[str, Any]]] = [] # Stores (file_path, analysis_data)

    def load_cache(self) -> Dict:
        if self.cache_file.exists():
            try:
                with self.cache_lock: # Ensure thread-safe read if ever needed, though typically init is single-threaded
                    with open(self.cache_file, "r", encoding="utf-8") as f:
                        loaded_cache = json.load(f)
                        logger.info(f"Loaded cache from {self.cache_file} with {len(loaded_cache)} entries.")
                        return loaded_cache
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load cache file {self.cache_file}: {e}. Starting with empty cache.")
        return {}

    def save_cache(self):
        try:
            with self.cache_lock:
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(self.cache, f, indent=2, sort_keys=True) # Using indent 2 for cache
                # logger.info(f"Saved cache to {self.cache_file} with {len(self.cache)} entries.")
        except IOError as e:
            logger.error(f"Could not save cache file {self.cache_file}: {e}")


    def scan_project(self, progress_callback: Optional[callable] = None) -> Dict[str, Any] :
        """
        Scans all files in the project root, using multiple workers.
        Returns the final analysis data.
        """
        logger.info(f"Starting project scan at {self.project_root} with {self.num_workers} workers.")
        
        manager = MultibotManager(scanner_instance=self, num_workers=self.num_workers, status_callback=progress_callback)
        manager.start_workers()

        file_count = 0
        processed_count = 0
        
        for file_path in self.project_root.rglob("*"):
            if file_path.is_file():
                file_count +=1
                # Delegate to FileProcessor's should_exclude, which is more comprehensive
                if not self.file_processor.should_exclude(file_path):
                    manager.add_task(file_path)
                    processed_count +=1
                elif progress_callback:
                    progress_callback(f"Skipped (excluded): {file_path.name}")


        logger.info(f"Found {file_count} total files. Queued {processed_count} files for analysis.")
        
        self.analysis_results = manager.wait_for_completion() # This now returns list of (path, data) tuples
        self.save_cache() # Save cache after all processing is done

        logger.info(f"Scan complete. Analyzed {len(self.analysis_results)} files.")

        # Generate reports
        report_generator = ReportGenerator(self.project_root, self.analysis_results)
        report_generator.project_analysis_file = self.analysis_file # Ensure it uses the configured name
        report_generator.chatgpt_context_file = self.chatgpt_context_file # Ensure it uses the configured name

        report_generator.save_project_analysis_report()
        
        # Return the content of project_analysis.json as the result of the scan
        if self.analysis_file.exists():
            try:
                with open(self.analysis_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load final analysis report for return: {e}")
                return {"error": "Failed to load final analysis report."}
        return {"error": "Analysis report not found after scan."}


    def _process_file_internal(self, file_path: Path) -> Optional[Tuple[Path, Dict[str, Any]]]:
        """
        Internal method for BotWorker to call, using the instance's FileProcessor.
        This ensures BotWorker doesn't need its own FileProcessor instance.
        """
        return self.file_processor.process_file(file_path)


    def export_chatgpt_context(self, template_path: Optional[Union[str, Path]] = None, output_path: Optional[Union[str, Path]] = None):
        """Exports a simplified project context for ChatGPT."""
        if not self.analysis_results:
             logger.warning("No analysis results available to export ChatGPT context. Run scan_project() first.")
             # Or, attempt to load from project_analysis.json if it exists
             if self.analysis_file.exists():
                 logger.info(f"Attempting to load analysis results from {self.analysis_file} for ChatGPT context export.")
                 try:
                    with open(self.analysis_file, "r", encoding="utf-8") as f:
                        loaded_analysis = json.load(f)
                    # Reconstruct analysis_results roughly if needed by ReportGenerator format
                    # This depends on the structure of project_analysis.json
                    # Assuming analysis_details has file_path as keys and data as values
                    if "analysis_details" in loaded_analysis:
                        temp_results = []
                        for path_str, data_dict in loaded_analysis["analysis_details"].items():
                            temp_results.append( (self.project_root / path_str , data_dict) )
                        report_generator = ReportGenerator(self.project_root, temp_results)
                        report_generator.chatgpt_context_file = Path(output_path) if output_path else self.chatgpt_context_file
                        report_generator.export_chatgpt_context(template_path=template_path) # output_path is handled by ReportGenerator now
                        return
                    else:
                        logger.error("Loaded analysis report does not contain 'analysis_details'. Cannot export context.")
                        return
                 except Exception as e:
                    logger.error(f"Failed to load or process {self.analysis_file} for context export: {e}")
                    return
             else:
                logger.error(f"{self.analysis_file} does not exist. Cannot export context.")
                return


        report_generator = ReportGenerator(self.project_root, self.analysis_results)
        report_generator.chatgpt_context_file = Path(output_path) if output_path else self.chatgpt_context_file
        report_generator.export_chatgpt_context(template_path=template_path)
        logger.info(f"ChatGPT context exported to {output_path or self.chatgpt_context_file}")

    def find_name_collisions(self, scan_path: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
        """
        Scans the project for directories and files that share the same base name,
        which could lead to confusion or import issues.

        Args:
            scan_path: Optional path to scan. Defaults to self.project_root.

        Returns:
            A list of dictionaries, each representing a collision.
            Example:
            [
                {
                    "name": "config",
                    "type": "dir_and_file_with_ext_collision", # or "dir_and_extensionless_file_collision"
                    "directory_paths": ["path/to/config/"],
                    "file_paths": ["path/to/config.py", "another/path/to/config.json"]
                },
                {
                    "name": "utils",
                    "type": "dir_and_extensionless_file_collision",
                    "directory_paths": ["path/to/utils/"],
                    "file_paths": ["path/to/utils"] # An extensionless file
                }
            ]
        """
        if scan_path is None:
            scan_path = self.project_root
        else:
            scan_path = Path(scan_path)

        item_map = defaultdict(lambda: {"dirs": set(), "files_no_ext": set(), "files_with_ext": defaultdict(set)})
        # files_with_ext will map base_name to a dict where keys are full_paths and values are original_extensions

        logger.info(f"Starting name collision scan for path: {scan_path}")

        # Ensure file_processor is initialized, it might not be if scan_project hasn't run.
        # This is a simplified assumption; in a real scenario, ensure all dependencies are ready.
        if not hasattr(self, 'file_processor') or self.file_processor is None:
            # Minimal init for file_processor if it's missing (e.g. if called standalone)
            # This is a basic setup and might need adjustment based on full FileProcessor needs
            logger.warning("FileProcessor not initialized by scan_project. Initializing with defaults for name collision scan.")
            self.file_processor = FileProcessor( # Assuming FileProcessor is defined in the same file
                project_root=self.project_root,
                cache={}, # Dummy cache
                cache_lock=threading.Lock(), # Dummy lock
                language_analyzer=self.language_analyzer, # Assuming this is initialized
                additional_ignore_dirs=self.ignore_dirs,
                additional_ignore_files=self.ignore_files,
                additional_include_extensions=self.include_extensions
            )


        for root, dirnames, filenames in os.walk(scan_path, topdown=True):
            current_path = Path(root)
            
            # Filter dirnames
            original_dirnames = list(dirnames) # Iterate over a copy for modification
            dirnames[:] = [] # Clear in-place
            for dname in original_dirnames:
                if not self.file_processor.should_exclude(current_path / dname):
                    dirnames.append(dname)
            
            # Filter filenames
            valid_filenames = []
            for fname in filenames:
                if not self.file_processor.should_exclude(current_path / fname):
                    valid_filenames.append(fname)

            for dname in dirnames:
                item_map[dname]["dirs"].add(str(current_path / dname))

            for fname in valid_filenames:
                full_path_str = str(current_path / fname)
                base, ext = os.path.splitext(fname)

                if not ext:  # File without extension
                    item_map[base]["files_no_ext"].add(full_path_str)
                else:  # File with extension
                    item_map[base]["files_with_ext"][full_path_str] = ext

        collisions = []
        for name, types in item_map.items():
            found_dirs = types["dirs"]
            # Files named exactly 'name' (e.g., file 'config' collides with dir 'config')
            found_files_matching_name_exactly = item_map[name]["files_no_ext"] if name in item_map else set()
            
            # Files like 'name.py', 'name.json' where 'name' is the base
            # These are already collected under item_map[name]["files_with_ext"]
            found_files_with_base_as_name = item_map[name]["files_with_ext"].keys() if name in item_map else set()

            if found_dirs:
                # Collision Type 1: Directory 'name' and extensionless file 'name'
                if found_files_matching_name_exactly:
                    collisions.append({
                        "name": name,
                        "type": "dir_and_extensionless_file",
                        "directory_paths": list(found_dirs),
                        "file_paths": list(found_files_matching_name_exactly)
                    })
                
                # Collision Type 2: Directory 'name' and file(s) 'name.ext'
                if found_files_with_base_as_name:
                     collisions.append({
                        "name": name,
                        "type": "dir_and_file_with_ext",
                        "directory_paths": list(found_dirs),
                        "file_paths": list(found_files_with_base_as_name)
                    })
        
        logger.info(f"Name collision scan completed. Found {len(collisions)} potential collision sets.")
        # Further refinement: a single entry in 'collisions' might have both types of file conflicts.
        # The current structure creates separate entries if dir 'foo' conflicts with file 'foo' AND file 'foo.py'.
        # This can be consolidated if needed.
        return collisions

# Example of how this module might be used (for testing or as a script if __main__ is added):
# # if __name__ == '__main__':
# #     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
# #     # Configure with actual paths to tree-sitter grammars if you have them
# #     # grammar_paths = {
# #     #     "rust": "/full/path/to/your/tree-sitter-rust.so",
# #     #     "javascript": "/full/path/to/your/tree-sitter-javascript.so"
# #     # }
# #     # scanner = ProjectScanner(project_root=".", tree_sitter_grammar_paths=grammar_paths)
      
# #     scanner = ProjectScanner(project_root=".") # Will use default (likely non-functional) grammar paths

# #     def my_progress_callback(message):
# #         print(f"SCAN_PROGRESS: {message}")

# #     analysis_output = scanner.scan_project(progress_callback=my_progress_callback)
# #     # print("\\nFinal Analysis Summary (first 5 files):")
# #     # if analysis_output and "analysis_details" in analysis_output:
# #     #     count = 0
# #     #     for file, details in analysis_output["analysis_details"].items():
# #     #         print(f"  File: {file}, Complexity: {details.get('complexity')}")
# #     #         count += 1
# #     #         if count >=5:
# #     #             break
# #     # else:
# #     #     print("No analysis details found or error during scan.")

# #     scanner.export_chatgpt_context()
# #     # To use a template:
# #     # scanner.export_chatgpt_context(template_path="path/to/your/template.txt") 