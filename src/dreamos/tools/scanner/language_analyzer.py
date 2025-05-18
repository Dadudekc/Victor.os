"""
Language analysis module for the project scanner.

This module provides functionality to analyze code in different programming languages,
extracting information such as classes, functions, dependencies, etc.
"""

import ast
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Optional: If tree-sitter grammars are present for Rust/JS/TS
try:
    from tree_sitter import Language, Parser
except ImportError:
    Language, Parser = None, None  # Indicate tree-sitter is unavailable
    logger.warning(
        "⚠️ tree-sitter not installed. Rust/JS/TS AST parsing will be partially disabled."
    )


class LanguageAnalyzer:
    """Handles language-specific code analysis for different programming languages."""

    def __init__(self, project_root_for_grammars: Path):
        """Initialize language analyzers and parsers."""
        # Define grammar locations and build library
        self.grammar_base_dir = (
            project_root_for_grammars / "runtime" / "tree-sitter-grammars"
        )
        self.build_lib_path = (
            self.grammar_base_dir / "languages.so"
        )  # Or .dll on Windows

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
                        # Grammar sources
                        available_grammar_paths
                    )
                except Exception as e:
                    logger.warning(f"Failed to build tree-sitter library: {e}")
                    # Will fallback to non-tree-sitter parsing for those languages
            else:
                logger.warning(
                    "No tree-sitter grammar source directories found in {self.grammar_base_dir}."
                )

    async def _load_parsers_from_library(self):
        """Load language parsers from the built library."""
        if not (Language and Parser):
            logger.warning("Tree-sitter not installed, skipping parser loading")
            return

        if not self.build_lib_path.exists():
            logger.warning(
                f"Tree-sitter library not found at {self.build_lib_path}, skipping parser loading"
            )
            return

        for lang_name in self.grammar_sources.keys():
            if not self.grammar_sources[lang_name].exists():
                continue  # Skip if grammar source doesn't exist

            try:
                if lang_name not in self.parsers:
                    language = Language(str(self.build_lib_path), lang_name)
                    parser = Parser()
                    parser.set_language(language)
                    self.parsers[lang_name] = parser
                    logger.info(f"Loaded {lang_name} parser")
            except Exception as e:
                logger.warning(f"Failed to load {lang_name} parser: {e}")

    def analyze_file(self, file_path: Path, source_code: str) -> Dict:
        """
        Analyze a file and extract information based on its extension.
        
        Args:
            file_path: Path to the file
            source_code: Content of the file
            
        Returns:
            Dict containing analysis results
        """
        extension = file_path.suffix.lower()
        file_analysis = {
            "path": str(file_path),
            "extension": extension,
            "size_bytes": len(source_code),
            "lines": source_code.count("\n") + 1,
        }

        try:
            if extension == ".py":
                py_analysis = self._analyze_python_ast(source_code)
                file_analysis.update(py_analysis)
            elif extension in {".js", ".jsx", ".ts", ".tsx"}:
                js_analysis = self._analyze_with_tree_sitter("javascript", source_code)
                file_analysis.update(js_analysis)
            elif extension == ".rs":
                rs_analysis = self._analyze_with_tree_sitter("rust", source_code)
                file_analysis.update(rs_analysis)
            # Can add more language support here

        except Exception as e:
            logger.warning(f"Error analyzing {file_path}: {e}")
            # Still include basic info even if detailed analysis fails
            file_analysis["analysis_error"] = str(e)

        return file_analysis

    def _analyze_python_ast(self, source_code: str) -> Dict:
        """
        Analyze Python code using the built-in ast module.
        
        Args:
            source_code: Python source code
            
        Returns:
            Dict with extracted imports, functions, classes, and dependencies
        """
        result = {
            "imports": [],
            "from_imports": [],
            "functions": [],
            "classes": {},
            "complexity": 0,
        }

        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            logger.warning(f"Syntax error in Python file: {e}")
            result["syntax_error"] = str(e)
            return result

        # Track imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    result["imports"].append(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:  # some from imports don't have a module (e.g., from . import x)
                    for name in node.names:
                        result["from_imports"].append(
                            {"module": node.module, "name": name.name, "level": node.level}
                        )

            # Track function definitions
            elif isinstance(node, ast.FunctionDef):
                complexity = 1  # Base complexity
                # Count branches in the function (if, while, for statements increase complexity)
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.comprehension)):
                        complexity += 1
                function_info = {
                    "name": node.name,
                    "args": len(node.args.args),
                    "decorators": [
                        self._get_decorator_name(d) for d in node.decorator_list
                    ],
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "complexity": complexity,
                }
                result["functions"].append(function_info)
                result["complexity"] += complexity

            # Track class definitions
            elif isinstance(node, ast.ClassDef):
                class_info = {
                    "bases": [self._get_node_name(base) for base in node.bases],
                    "methods": [],
                    "decorators": [
                        self._get_decorator_name(d) for d in node.decorator_list
                    ],
                }

                # Find methods in the class
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_complexity = 1
                        for child in ast.walk(item):
                            if isinstance(
                                child, (ast.If, ast.While, ast.For, ast.comprehension)
                            ):
                                method_complexity += 1
                        
                        method_info = {
                            "name": item.name,
                            "args": len(item.args.args) - 1 if item.args.args else 0,  # Skip self
                            "decorators": [
                                self._get_decorator_name(d) for d in item.decorator_list
                            ],
                            "is_async": isinstance(item, ast.AsyncFunctionDef),
                            "complexity": method_complexity,
                        }
                        class_info["methods"].append(method_info)
                        result["complexity"] += method_complexity

                result["classes"][node.name] = class_info

        return result

    def _get_decorator_name(self, node) -> str:
        """Extract decorator name from an AST node."""
        if isinstance(node, ast.Call):
            return self._get_node_name(node.func)
        return self._get_node_name(node)

    def _get_node_name(self, node) -> str:
        """Extract name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_node_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_node_name(node.func)
        elif isinstance(node, ast.Subscript):
            # Handle subscripts like Type[T]
            return f"{self._get_node_name(node.value)}[...]"
        return "unknown"

    def _analyze_with_tree_sitter(self, lang_name: str, source_code: str) -> Dict:
        """
        Analyze code using tree-sitter for languages other than Python.
        
        Args:
            lang_name: Language name (must match a tree-sitter parser)
            source_code: Source code to analyze
            
        Returns:
            Dict with extracted information
        """
        result = {
            "tree_sitter_analysis": False,
            "functions": [],
            "classes": {},
        }

        if not (Language and Parser):
            return result
        
        parser = self.parsers.get(lang_name)
        if not parser:
            return result

        try:
            tree = parser.parse(bytes(source_code, "utf8"))
            result["tree_sitter_analysis"] = True
            
            # Example of extracting function names - actual implementation would be more complex
            # and language-specific
            query_string = ''
            if lang_name == "javascript":
                query_string = "(function_declaration name: (identifier) @func_name)"
            elif lang_name == "rust":
                query_string = "(function_item name: (identifier) @func_name)"
            
            if query_string:
                language = parser.language
                query = language.query(query_string)
                captures = query.captures(tree.root_node)
                
                for capture in captures:
                    node, tag = capture
                    if tag == "func_name":
                        result["functions"].append({"name": node.text.decode('utf8')})
            
            # This is simplified - a real implementation would extract more information
            
        except Exception as e:
            logger.warning(f"Error in tree-sitter analysis for {lang_name}: {e}")
            
        return result 