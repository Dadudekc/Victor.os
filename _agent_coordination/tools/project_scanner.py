import os
import ast
import json
import hashlib
import threading
import queue
import logging
from pathlib import Path
from typing import Dict, Union, Optional, List, Any
import argparse
import re
import sys # Keep sys for exit

logger = logging.getLogger(__name__)

# Optional: If tree-sitter grammars are present for Rust/JS/TS
try:
    from tree_sitter import Language, Parser
except ImportError:
    Language = None
    Parser = None
    # logger.warning("⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled.") # Reduce noise

# ---------------------------------
# Project Config / Cache File Setup
# ---------------------------------
DEFAULT_CACHE_FILE = "project_scanner_cache.json" # Renamed for clarity

# ---------------------------------
# Language Analyzer
# ---------------------------------
class LanguageAnalyzer:
    """Handles language-specific code analysis for different programming languages."""
    def __init__(self):
        """Initialize language analyzers and parsers."""
        # NOTE: Tree-sitter paths need configuration if used. Disabled by default.
        self.rust_parser = None # self._init_tree_sitter_language("rust")
        self.js_parser = None # self._init_tree_sitter_language("javascript")

    def _init_tree_sitter_language(self, lang_name: str) -> Optional[Parser]:
        """
        Initializes and returns a Parser for the given language name (rust, javascript).
        Adjust grammar_paths to point at your compiled .so files if using tree-sitter.
        """
        if not Language or not Parser:
            # logger.warning("⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled.") # Reduce noise
            return None

        # FIXME: Grammar paths need proper configuration/discovery
        grammar_paths = {
            "rust": "path/to/tree-sitter-rust.so",          
            "javascript": "path/to/tree-sitter-javascript.so"  
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
            # Placeholder - Requires tree-sitter setup and implementation
            return self._analyze_rust(source_code) 
        elif suffix in [".js", ".ts"] and self.js_parser:
             # Placeholder - Requires tree-sitter setup and implementation
            return self._analyze_javascript(source_code)
        else:
            # Basic info for unsupported types (like markdown, json, etc.)
            # Check if it looks like text before counting lines
            is_likely_text = True
            try:
                 # Check first few KB for null bytes which often indicate binary
                 if '\0' in source_code[:4096]: 
                      is_likely_text = False
            except:
                 is_likely_text = False # Error reading likely means not text

            return {
                "language": suffix,
                "functions": [],
                "classes": {},
                "routes": [],
                "complexity": len(source_code.splitlines()) if is_likely_text else 0, 
                "is_text": is_likely_text,
                "size_bytes": len(source_code.encode('utf-8', errors='ignore'))
            }

    def _analyze_python(self, source_code: str) -> Dict:
        """
        Analyzes Python source code using the builtin `ast` module.
        Extracts functions, classes, routes, complexity, etc.
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
             logger.warning(f"Syntax error parsing Python file: {e}. Skipping AST analysis.")
             return {
                "language": ".py",
                "functions": [],
                "classes": {},
                "routes": [],
                "complexity": len(source_code.splitlines()),
                "error": f"SyntaxError: {e}",
                "size_bytes": len(source_code.encode('utf-8', errors='ignore'))
             }
             
        functions = []
        classes = {}
        routes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Basic function info
                func_info = {
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "lineno": node.lineno,
                    "end_lineno": getattr(node, 'end_lineno', node.lineno) # Requires Python 3.8+
                }
                functions.append(func_info)

                # Route detection (Flask/FastAPI style)
                for decorator in node.decorator_list:
                    # Check if decorator is a Call object (like @app.route(...))
                    if isinstance(decorator, ast.Call):
                         # Get the decorator function name (e.g., 'route', 'get', 'post')
                         decorator_name = None
                         if isinstance(decorator.func, ast.Attribute): # e.g. app.route
                              decorator_name = decorator.func.attr.lower()
                         elif isinstance(decorator.func, ast.Name): # e.g. route()
                              decorator_name = decorator.func.id.lower()
                              
                         if decorator_name in {"route", "get", "post", "put", "delete", "patch"}:
                            path_arg = "/unknown"
                            methods = [decorator_name.upper()] if decorator_name != "route" else []
                            
                            # Try to get path from first arg (string constant)
                            if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
                                path_arg = decorator.args[0].value
                                
                            # Check for methods kwarg
                            for kw in decorator.keywords:
                                if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                                    m = []
                                    for elt in kw.value.elts:
                                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                            m.append(elt.value.upper())
                                    if m: methods = m
                            
                            # If methods list is empty (e.g. from @app.route), default to GET
                            if not methods: methods = ['GET']
                                
                            for method in methods:
                                routes.append({
                                    "function": node.name, 
                                    "method": method, 
                                    "path": path_arg,
                                    "lineno": node.lineno
                                })

            elif isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node)
                method_nodes = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                methods = [{
                    "name": m.name, 
                    "args": [arg.arg for arg in m.args.args],
                    "lineno": m.lineno,
                    "end_lineno": getattr(m, 'end_lineno', m.lineno)
                 } for m in method_nodes]
                 
                base_classes = []
                for base in node.bases:
                    # Handle Name, Attribute recursively
                    parts = []
                    curr = base
                    while isinstance(curr, ast.Attribute):
                        parts.append(curr.attr)
                        curr = curr.value
                    if isinstance(curr, ast.Name):
                        parts.append(curr.id)
                        base_classes.append(".".join(reversed(parts)))
                    # else: pass # Could handle other base types if needed

                classes[node.name] = {
                    "methods": methods,
                    "docstring": docstring,
                    "base_classes": base_classes,
                    "lineno": node.lineno,
                    "end_lineno": getattr(node, 'end_lineno', node.lineno)
                }

        # Complexity = function count + sum of class methods
        complexity = len(functions) + sum(len(c.get("methods", [])) for c in classes.values())
        return {
            "language": ".py",
            "functions": functions,
            "classes": classes,
            "routes": routes,
            "complexity": complexity,
            "size_bytes": len(source_code.encode('utf-8', errors='ignore'))
        }

    def _analyze_rust(self, source_code: str) -> Dict:
        """Analyzes Rust source code using tree-sitter (if available). Placeholder."""
        # Placeholder implementation returns basic info
        return {
            "language": ".rs", 
            "functions": [], 
            "classes": {}, 
            "routes": [], 
            "complexity": len(source_code.splitlines()), 
            "error": "Tree-sitter Rust analysis not implemented",
            "size_bytes": len(source_code.encode('utf-8', errors='ignore'))
            }

    def _analyze_javascript(self, source_code: str) -> Dict:
        """Analyzes JS/TS using tree-sitter (if available). Placeholder."""
         # Placeholder implementation returns basic info
        return {
            "language": ".js/.ts", 
            "functions": [], 
            "classes": {}, 
            "routes": [], 
            "complexity": len(source_code.splitlines()), 
            "error": "Tree-sitter JS/TS analysis not implemented",
            "size_bytes": len(source_code.encode('utf-8', errors='ignore'))
            }


# ---------------------------------
# BotWorker & MultibotManager
# ---------------------------------
class BotWorker(threading.Thread):
    """
    A background worker that pulls file tasks from a queue,
    processes them using the FileProcessor, and appends results to results_list.
    """
    def __init__(self, task_queue: queue.Queue, results_list: list, file_processor: 'FileProcessor', language_analyzer: LanguageAnalyzer, status_callback=None):
        super().__init__()
        self.task_queue = task_queue
        self.results_list = results_list
        self.file_processor = file_processor
        self.language_analyzer = language_analyzer
        self.status_callback = status_callback
        self.daemon = True
        self.start()

    def run(self):
        while True:
            try:
                file_path = self.task_queue.get()
                if file_path is None: # Sentinel value to stop
                    # logger.debug("Worker received sentinel. Exiting.")
                    break
                # Use FileProcessor instance to handle caching and analysis call
                result = self.file_processor.process_file(file_path, self.language_analyzer)
                if result is not None:
                    self.results_list.append(result) # result is (relative_path, analysis_data) or None
                if self.status_callback:
                    self.status_callback(file_path, result is not None) # Indicate if processed or skipped
            except Exception as e:
                 logger.error(f"Error in worker thread processing {file_path}: {e}", exc_info=True)
            finally:
                 self.task_queue.task_done()

class MultibotManager:
    """Manages a pool of BotWorker threads for concurrent file processing."""
    def __init__(self, file_processor: 'FileProcessor', language_analyzer: LanguageAnalyzer, num_workers=4, status_callback=None):
        self.task_queue = queue.Queue()
        self.results_list = [] # Stores (relative_path, analysis_data) tuples
        self.file_processor = file_processor
        self.language_analyzer = language_analyzer
        self.status_callback = status_callback
        self.num_workers = num_workers
        self.workers = []

    def start_workers(self):
         self.workers = [
            BotWorker(self.task_queue, self.results_list, self.file_processor, self.language_analyzer, self.status_callback)
            for _ in range(self.num_workers)
        ]
         # logger.debug(f"Started {len(self.workers)} worker threads.")

    def add_task(self, file_path: Path):
        self.task_queue.put(file_path)

    def wait_for_completion(self):
        """Blocks until all tasks in the queue have been processed."""
        self.task_queue.join()

    def stop_workers(self):
        """Sends sentinel values to stop all worker threads."""
        # logger.debug("Sending stop sentinels to workers...")
        for _ in self.workers:
            try:
                 self.task_queue.put(None)
            except queue.Full:
                 logger.warning("Queue full while trying to send stop sentinel. Some workers might not stop cleanly.")
                 
        # logger.debug("Joining worker threads...")
        for worker in self.workers:
             try:
                 worker.join(timeout=5.0) # Add timeout to join
                 if worker.is_alive():
                      logger.warning(f"Worker thread {worker.name} did not exit cleanly after sentinel.")
             except Exception as e:
                  logger.error(f"Error joining worker thread {worker.name}: {e}")
        # logger.debug("Workers joined.")
        self.workers = [] # Clear worker list after stopping

# ---------------------------------
# FileProcessor
# ---------------------------------
class FileProcessor:
    """Handles file hashing, ignoring, caching checks, and delegates analysis."""
    # Define default excludes at class level
    DEFAULT_EXCLUDE_DIRS = {
        "venv", ".venv", "__pycache__", "node_modules", "migrations", "build", 
        "dist", "target", ".git", ".hg", ".svn", "coverage", "site-packages",
        "*.egg-info" 
    }
    # Exclude common binary/resource files
    DEFAULT_EXCLUDE_SUFFIXES = { 
        '.log', '.db', '.sqlite', '.sqlite3', '.bak', '.tmp', '.swp', '.swo',
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.ico', '.pdf', '.zip', 
        '.tar', '.gz', '.rar', '.7z', '.exe', '.dll', '.so', '.dylib', '.jar', 
        '.class', '.pyc', '.pyo', '.o', '.a', '.obj', '.lib', '.ncb', '.suo',
        '.lock', '.map', '.min.js', '.min.css', '.woff', '.woff2', '.ttf', '.eot'
        # Removed .css - might want to analyze CSS
    }

    def __init__(self, project_root: Path, cache: Dict, cache_lock: threading.Lock, additional_ignore_patterns: List[str]):
        self.project_root = project_root.resolve() # Ensure absolute path
        self.cache = cache
        self.cache_lock = cache_lock
        self.additional_ignore_patterns = additional_ignore_patterns
        try:
             self._script_path = Path(__file__).resolve() # Cache own path
        except NameError: # If run interactively where __file__ is not defined
             self._script_path = None

    def hash_file(self, file_path: Path) -> str:
        """Calculates the MD5 hash of a file's content."""
        try:
            # Read in chunks for potentially large files
            hasher = hashlib.md5()
            with file_path.open("rb") as f:
                while chunk := f.read(8192):
                     hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning(f"Could not hash file {file_path}: {e}")
            return ""

    def should_exclude(self, file_path: Path) -> bool:
        """Determines if a file or directory should be excluded based on patterns."""
        file_abs = file_path.resolve()

        # Exclude self
        if self._script_path and file_abs == self._script_path:
            return True
            
        # Check file suffix first (cheaper)
        if file_path.suffix.lower() in self.DEFAULT_EXCLUDE_SUFFIXES:
             return True

        # Check default directory names
        if any(part in self.DEFAULT_EXCLUDE_DIRS for part in file_path.parts):
            return True
            
        # Check additional ignore patterns (relative to project root)
        for pattern in self.additional_ignore_patterns:
             # Simple check: does the relative path start with the pattern?
             # TODO: Implement more robust glob/gitignore style matching if needed
             try:
                  relative_path_str = str(file_abs.relative_to(self.project_root))
                  if relative_path_str.startswith(pattern):
                       return True
             except ValueError:
                  # Path is not relative to project root (shouldn't happen often if called from walk)
                  pass
                  
        return False

    def process_file(self, file_path: Path, language_analyzer: LanguageAnalyzer) -> Optional[tuple]:
        """
        Processes a single file: checks cache, hashes, analyzes if needed.
        Returns a tuple (relative_path, analysis_result) if analyzed, otherwise None.
        Updates the shared cache with the new hash.
        """
        # Removed should_exclude check here, moved to perform_scan for efficiency
        # if self.should_exclude(file_path):
        #      return None

        try:
            file_hash_val = self.hash_file(file_path)
            if not file_hash_val: # Skip if hashing failed
                 return None

            relative_path_str = str(file_path.relative_to(self.project_root))

            # Check cache (read-only check outside lock first for performance)
            cached_entry = self.cache.get(relative_path_str)
            if cached_entry and cached_entry.get("hash") == file_hash_val:
                # logger.debug(f"Cache hit for {relative_path_str}")
                return None # File hasn't changed, skip analysis

            # logger.debug(f"Analyzing file: {relative_path_str}")
            # Read and analyze
            source_code = ""
            try:
                # Read as bytes first to detect encoding / handle binary better
                source_bytes = file_path.read_bytes()
                # Basic check for null bytes suggesting binary
                if b'\0' in source_bytes[:4096]:
                     # logger.debug(f"Detected likely binary file: {relative_path_str}")
                     analysis_result = {
                         "language": file_path.suffix.lower(),
                         "functions": [], "classes": {}, "routes": [],
                         "complexity": 0, "is_text": False,
                         "size_bytes": len(source_bytes)
                     }
                else:
                     # Try decoding as UTF-8, fallback to latin-1
                     try:
                          source_code = source_bytes.decode('utf-8')
                     except UnicodeDecodeError:
                          # logger.warning(f"UTF-8 decode failed for {relative_path_str}, trying latin-1.")
                          source_code = source_bytes.decode('latin-1')
                     analysis_result = language_analyzer.analyze_file(file_path, source_code)

            except Exception as e:
                 logger.warning(f"Could not read/decode file {file_path}: {e}")
                 # Still cache the hash even if read fails, but don't return analysis
                 with self.cache_lock:
                     self.cache[relative_path_str] = {"hash": file_hash_val}
                 return None 
                 
            # Update cache (requires lock)
            with self.cache_lock:
                self.cache[relative_path_str] = {"hash": file_hash_val}
                
            return (relative_path_str, analysis_result)

        except Exception as e:
            logger.error(f"❌ Unexpected error analyzing {file_path}: {e}", exc_info=True)
            return None

# ---------------------------------
# Core Scanning Function
# ---------------------------------

def perform_scan(project_root: Union[str, Path], 
                 additional_ignore_patterns: List[str] = [], 
                 cache_file_name: str = DEFAULT_CACHE_FILE,
                 num_workers: Optional[int] = None,
                 progress_callback: Optional[callable] = None
                 ) -> Dict[str, Dict]:
    """
    Performs the project scan and returns the analysis results.

    Args:
        project_root: The root directory of the project to scan.
        additional_ignore_patterns: List of additional path prefixes to ignore (relative to root).
        cache_file_name: Name of the cache file (relative to project root).
        num_workers: Number of worker threads (default: CPU count).
        progress_callback: Optional function called with (current_count, total_files).

    Returns:
        A dictionary where keys are relative file paths and values are analysis results.
            { 
              'src/main.py': {'language': '.py', 'functions': [...], ...},
              ... 
            }
    """
    project_root_path = Path(project_root).resolve()
    if not project_root_path.is_dir():
        raise ValueError(f"Project root is not a valid directory: {project_root_path}")

    logger.info(f"🔍 Scanning project: {project_root_path} ...")
    
    cache_path = project_root_path / cache_file_name
    
    # Load Cache
    cache: Dict[str, Dict] = {}
    if cache_path.exists():
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                cache = json.load(f)
            logger.info(f"Loaded cache from {cache_path} with {len(cache)} entries.")
        except json.JSONDecodeError:
            logger.warning(f"Cache file {cache_path} is corrupted. Starting with empty cache.")
        except Exception as e:
            logger.error(f"Error loading cache file {cache_path}: {e}. Starting with empty cache.")

    cache_lock = threading.Lock()
    
    language_analyzer = LanguageAnalyzer()
    file_processor = FileProcessor(
        project_root_path,
        cache, # Pass mutable cache dict
        cache_lock,
        additional_ignore_patterns
    )

    # --- File Discovery ---
    # Supported extensions for analysis (add more if needed)
    analysis_extensions = {'.py', '.rs', '.js', '.ts'} 
    # Include common text files for basic info (hashing, line count)
    other_text_extensions = {'.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.sh', '.bat', '.xml', '.html', '.css'}
    valid_extensions = analysis_extensions.union(other_text_extensions)

    all_files_to_consider: List[Path] = []
    logger.debug(f"Starting file walk from: {project_root_path}")
    for root, dirs, files in os.walk(project_root_path, topdown=True):
        root_path = Path(root)
        # logger.debug(f"Walking: {root_path}")
        
        # Filter directories in-place to avoid descending into excluded ones
        # Must compare resolved paths if ignore patterns might be absolute
        original_dirs = dirs[:]
        dirs[:] = [d for d in original_dirs if not file_processor.should_exclude(root_path / d)]
        # if len(original_dirs) != len(dirs):
        #      logger.debug(f"Excluded dirs in {root_path}: {set(original_dirs) - set(dirs)}")

        for file in files:
            file_path = root_path / file
            # Check excludes for files too
            if file_path.suffix.lower() in valid_extensions and not file_processor.should_exclude(file_path):
                all_files_to_consider.append(file_path)
            # else:
            #      logger.debug(f"Skipping file: {file_path} (suffix: {file_path.suffix.lower()} / exclude: {file_processor.should_exclude(file_path)})")

    total_files = len(all_files_to_consider)
    logger.info(f"📝 Found {total_files} relevant files for analysis/caching after filtering.")
    if total_files == 0:
         logger.warning("No relevant files found to process.")
         return {}

    # --- Detect Moved/Deleted Files (Cache Management) ---
    previous_files_in_cache = set(cache.keys())
    current_files_rel = {str(f.relative_to(project_root_path)) for f in all_files_to_consider}
    
    # Files in cache but not found in current scan (might be deleted or moved)
    missing_from_scan_rel = previous_files_in_cache - current_files_rel
    moved_files_map = {} # old_rel_path -> new_rel_path

    # Check if missing files were actually moved (by hash matching)
    # Map hashes of missing files to their old paths
    hashes_of_missing_files = {}
    potentially_deleted_rel = set()
    for old_rel_path in missing_from_scan_rel:
        old_hash = cache.get(old_rel_path, {}).get("hash")
        if old_hash:
             hashes_of_missing_files[old_hash] = old_rel_path
        else:
             # No hash, definitely deleted or excluded now (remove from cache)
             potentially_deleted_rel.add(old_rel_path)

    logger.info(f"Checking {len(hashes_of_missing_files)} missing files' hashes for potential moves...")
    # Only need to hash files that are new relative to the cache
    files_to_hash_check = [f for f in all_files_to_consider if str(f.relative_to(project_root_path)) not in previous_files_in_cache]
    
    for new_file in files_to_hash_check:
        new_hash = file_processor.hash_file(new_file)
        if new_hash in hashes_of_missing_files:
             old_rel_path = hashes_of_missing_files[new_hash]
             new_rel_path = str(new_file.relative_to(project_root_path))
             moved_files_map[old_rel_path] = new_rel_path
             logger.info(f"Detected move: '{old_rel_path}' -> '{new_rel_path}'")
             # Update cache entry immediately (under lock)
             with cache_lock:
                  if old_rel_path in cache: # Ensure it wasn't deleted concurrently
                       cache[new_rel_path] = cache.pop(old_rel_path)
             # No need to look for this hash anymore
             del hashes_of_missing_files[new_hash] 
             # It wasn't deleted
             potentially_deleted_rel.discard(old_rel_path)

    # Add remaining missing files (whose hashes didn't match any new file) to deleted set
    potentially_deleted_rel.update(hashes_of_missing_files.values())

    # Remove truly deleted files from cache
    if potentially_deleted_rel:
         logger.info(f"Removing {len(potentially_deleted_rel)} deleted/moved-out files from cache...")
         # logger.debug(f"Deleting from cache: {potentially_deleted_rel}")
         with cache_lock:
              for deleted_rel_path in potentially_deleted_rel:
                   cache.pop(deleted_rel_path, None)

    # --- Asynchronous Processing ---
    logger.info("⏱️ Processing files asynchronously...")
    if num_workers is None:
        num_workers = min(os.cpu_count() or 1, total_files) # Don't use more workers than files
    else:
         num_workers = min(num_workers, total_files) # Respect user limit
    logger.info(f"Using {num_workers} worker threads.")

    processed_count = 0
    processed_lock = threading.Lock()

    def status_update(file_path: Path, was_processed: bool):
        nonlocal processed_count
        with processed_lock:
            processed_count += 1
        # logger.debug(f"Status: Processed {file_path} ({'Analyzed' if was_processed else 'Skipped/Cached'})")
        if progress_callback:
            # Ensure callback gets numbers
            try:
                 current = int(processed_count)
                 total = int(total_files)
                 progress_callback(current, total)
            except Exception as cb_err:
                 logger.error(f"Error in progress callback: {cb_err}")
                 
        elif processed_count % 100 == 0 or processed_count == total_files: # Log progress periodically
             try: # Protect against division by zero if total_files is somehow 0
                  percent = (processed_count / total_files) * 100 if total_files > 0 else 100
                  logger.info(f"Progress: {processed_count}/{total_files} files checked ({percent:.1f}%)." )
             except:
                  logger.info(f"Progress: {processed_count}/{total_files} files checked.")

    manager = MultibotManager(
        file_processor=file_processor,
        language_analyzer=language_analyzer,
        num_workers=num_workers,
        status_callback=status_update
    )
    manager.start_workers()

    queued_count = 0
    for file_path in all_files_to_consider:
        manager.add_task(file_path)
        queued_count += 1
        
    logger.info(f"Queued {queued_count} files for processing.")
    manager.wait_for_completion()
    # logger.info("All tasks completed by workers.")
    manager.stop_workers()
    # logger.info("Workers stopped and joined.")

    # --- Collect Results ---
    # Results are stored directly in manager.results_list by workers
    final_analysis: Dict[str, Dict] = {}
    for rel_path, analysis_data in manager.results_list:
        final_analysis[rel_path] = analysis_data
        
    logger.info(f"Analysis generated for {len(final_analysis)} new/modified files.")

    # --- Save Updated Cache ---
    try:
        # Ensure cache directory exists
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("w", encoding="utf-8") as f:
            # Save potentially modified cache (hash updates, deletions, moves)
            # Sort keys for consistent output
            json.dump(cache, f, sort_keys=True) 
        logger.info(f"💾 Cache updated and saved to {cache_path}")
    except Exception as e:
        logger.error(f"❌ Error saving updated cache to {cache_path}: {e}")

    logger.info(f"✅ Scan complete. Returning analysis for {len(final_analysis)} processed files.")
    return final_analysis


# ---------------------------------
# CLI Usage
# ---------------------------------
def main():
    # Setup logging based on verbosity potentially before parsing
    log_level = logging.INFO
    if "-v" in sys.argv or "--verbose" in sys.argv:
         log_level = logging.DEBUG
         
    logging.basicConfig(level=log_level, 
                        format="[%(levelname)s][%(asctime)s][%(threadName)s] %(message)s",
                        datefmt="%H:%M:%S")

    parser = argparse.ArgumentParser(
        description="Scans a project directory, analyzes code files (Python, etc.), "
                    "and outputs the analysis as JSON. Uses caching to speed up subsequent runs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Show defaults
    )
    parser.add_argument(
        "project_root", 
        help="Root directory of the project to scan."
    )
    parser.add_argument(
        "--ignore", 
        nargs="*", default=[], 
        help="Additional path prefixes to ignore (relative to project root). E.g., 'docs/' 'data/'"
    )
    parser.add_argument(
        "--cache-file", 
        default=DEFAULT_CACHE_FILE, 
        help=f"Name of the cache file within the project root."
    )
    parser.add_argument(
        "--workers", 
        type=int, default=None, 
        help="Number of worker threads (default: CPU count)."
    )
    parser.add_argument(
        "--output-json", 
        action="store_true", 
        help="Output the final analysis dictionary as JSON to stdout."
    )
    parser.add_argument(
        "--save-analysis-file", 
        metavar="FILENAME",
        default="project_analysis.json", # Default filename to save analysis
        help="Save the full analysis dictionary to this JSON file in the project root. Set to empty string '' to disable saving."
    )
    parser.add_argument(
         "-v", "--verbose",
         action="store_true",
         help="Enable verbose logging (DEBUG level)."
    )

    args = parser.parse_args()

    if args.verbose:
         logging.getLogger().setLevel(logging.DEBUG) # Ensure level is set if -v passed
         logger.debug("Verbose logging enabled.")
         
    try:
        logger.info("Starting project scan via CLI...")
        analysis_result = perform_scan(
            project_root=args.project_root,
            additional_ignore_patterns=args.ignore,
            cache_file_name=args.cache_file,
            num_workers=args.workers
            # TODO: Add CLI progress bar using progress_callback if desired
        )

        if args.output_json:
             # logger.info("Outputting analysis as JSON to stdout.")
             # Print directly to stdout
             print(json.dumps(analysis_result, indent=2)) 
             
        if args.save_analysis_file:
             save_path = Path(args.project_root).resolve() / args.save_analysis_file
             try:
                  # Ensure directory exists
                  save_path.parent.mkdir(parents=True, exist_ok=True)
                  with save_path.open("w", encoding="utf-8") as f:
                       # Sort keys for consistent output
                       json.dump(analysis_result, f, indent=2, sort_keys=True) 
                  logger.info(f"💾 Full analysis saved to: {save_path}")
             except Exception as e:
                  logger.error(f"❌ Failed to save analysis file to {save_path}: {e}")

        logger.info("Project scan finished.")

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
         logger.error(f"File not found error during scan: {e}")
         sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during scanning: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 