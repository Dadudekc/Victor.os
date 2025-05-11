"""Analysis modules for different aspects of the codebase."""

import ast
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .constants import (
    EXCLUDED_DIRS,
    EXCLUDED_FILES,
    SUPPORTED_EXTENSIONS,
)

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Container for file analysis results."""

    file_path: Path
    language: str
    imports: List[str]
    functions: List[Dict]
    classes: List[Dict]
    complexity: int
    size_bytes: int
    line_count: int
    error: Optional[str] = None


class FileAnalyzer:
    """Analyzes file statistics and content."""

    @staticmethod
    def get_file_stats(path: Path) -> Dict:
        """Get statistics for a file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                return {
                    "size": path.stat().st_size,
                    "lines": len(content.splitlines()),
                    "non_empty_lines": len(
                        [l for l in content.splitlines() if l.strip()]
                    ),
                    "content": content if path.suffix == ".py" else None,
                }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def should_analyze(path: Path) -> bool:
        """Check if a file should be analyzed."""
        if path.name in EXCLUDED_FILES:
            return False
        if any(part in EXCLUDED_DIRS for part in path.parts):
            return False
        return True


class ImportAnalyzer:
    """Analyzes Python import statements."""

    @staticmethod
    def extract_imports(content: str) -> List[str]:
        """Extract import statements from Python code."""
        try:
            tree = ast.parse(content)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            return imports
        except:
            return []

    @staticmethod
    def analyze_imports(files: List[Dict]) -> Dict[str, int]:
        """Analyze imports across multiple files."""
        import_counts = defaultdict(int)
        for file in files:
            if file.get("content"):
                for imp in ImportAnalyzer.extract_imports(file["content"]):
                    import_counts[imp] += 1
        return dict(import_counts)


class SizeAnalyzer:
    """Analyzes file and directory sizes."""

    @staticmethod
    def get_directory_size(path: Path) -> int:
        """Get total size of a directory in bytes."""
        total = 0
        for file_path in path.rglob("*"):
            if file_path.is_file() and FileAnalyzer.should_analyze(file_path):
                total += file_path.stat().st_size
        return total

    @staticmethod
    def find_large_files(files: List[Dict], threshold_kb: int) -> List[tuple]:
        """Find files larger than the threshold."""
        large_files = []
        for file in files:
            if file["size"] > threshold_kb * 1024:
                large_files.append((file["path"], file["size"]))
        return sorted(large_files, key=lambda x: x[1], reverse=True)

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format size in bytes to human readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


class LanguageAnalyzer:
    """Base class for language-specific analyzers."""

    def analyze_file(self, file_path: Path, source_code: str) -> Dict:
        """Analyze a file and return results."""
        try:
            ext = file_path.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                return {"error": f"Unsupported file type: {ext}"}

            # Get basic stats
            size_bytes = file_path.stat().st_size
            line_count = len(source_code.splitlines())

            # Language-specific analysis
            if ext == ".py":
                return self._analyze_python(
                    source_code, file_path, size_bytes, line_count
                )
            elif ext in {".js", ".jsx", ".ts", ".tsx"}:
                return self._analyze_javascript(
                    source_code, file_path, size_bytes, line_count
                )
            elif ext == ".rs":
                return self._analyze_rust(
                    source_code, file_path, size_bytes, line_count
                )
            elif ext in {".vue", ".svelte"}:
                return self._analyze_frontend(
                    source_code, file_path, size_bytes, line_count
                )
            else:
                return {"error": f"No analyzer for {ext}"}

        except Exception as e:
            return {"error": str(e)}

    def _analyze_python(
        self, source_code: str, file_path: Path, size_bytes: int, line_count: int
    ) -> Dict:
        """Analyze Python code."""
        try:
            tree = ast.parse(source_code)

            # Extract imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(
                            f"{node.module}.{name.name}" if name.asname else node.module
                        )

            # Extract functions and classes
            functions = []
            classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(
                        {
                            "name": node.name,
                            "args": [arg.arg for arg in node.args.args],
                            "returns": ast.unparse(node.returns)
                            if node.returns
                            else None,
                            "decorators": [
                                d.id
                                for d in node.decorator_list
                                if isinstance(d, ast.Name)
                            ],
                        }
                    )
                elif isinstance(node, ast.ClassDef):
                    classes.append(
                        {
                            "name": node.name,
                            "bases": [ast.unparse(b) for b in node.bases],
                            "methods": [
                                m.name
                                for m in node.body
                                if isinstance(m, ast.FunctionDef)
                            ],
                        }
                    )

            # Calculate complexity
            complexity = self._calculate_complexity(tree)

            return {
                "language": "python",
                "imports": imports,
                "functions": functions,
                "classes": classes,
                "complexity": complexity,
                "size_bytes": size_bytes,
                "line_count": line_count,
            }

        except Exception as e:
            return {"error": f"Python analysis error: {str(e)}"}

    def _analyze_javascript(
        self, source_code: str, file_path: Path, size_bytes: int, line_count: int
    ) -> Dict:
        """Analyze JavaScript/TypeScript code."""
        # Basic regex-based analysis for now
        imports = re.findall(
            r'import\s+(?:{[^}]+}|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]', source_code
        )
        functions = re.findall(
            r"(?:function|const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)",
            source_code,
        )
        classes = re.findall(r"class\s+(\w+)", source_code)

        return {
            "language": "javascript",
            "imports": imports,
            "functions": [{"name": f} for f in functions],
            "classes": [{"name": c} for c in classes],
            "complexity": 0,  # TODO: Implement JS complexity
            "size_bytes": size_bytes,
            "line_count": line_count,
        }

    def _analyze_rust(
        self, source_code: str, file_path: Path, size_bytes: int, line_count: int
    ) -> Dict:
        """Analyze Rust code."""
        # Basic regex-based analysis for now
        imports = re.findall(r"use\s+([^;]+);", source_code)
        functions = re.findall(r"fn\s+(\w+)\s*\([^)]*\)", source_code)
        structs = re.findall(r"struct\s+(\w+)", source_code)

        return {
            "language": "rust",
            "imports": imports,
            "functions": [{"name": f} for f in functions],
            "classes": [{"name": s} for s in structs],
            "complexity": 0,  # TODO: Implement Rust complexity
            "size_bytes": size_bytes,
            "line_count": line_count,
        }

    def _analyze_frontend(
        self, source_code: str, file_path: Path, size_bytes: int, line_count: int
    ) -> Dict:
        """Analyze Vue/Svelte code."""
        # Extract script section
        script_match = re.search(r"<script[^>]*>(.*?)</script>", source_code, re.DOTALL)
        if script_match:
            script_code = script_match.group(1)
            return self._analyze_javascript(
                script_code, file_path, size_bytes, line_count
            )
        return {"error": "No script section found"}

    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            if isinstance(
                node,
                (
                    ast.If,
                    ast.While,
                    ast.For,
                    ast.Try,
                    ast.ExceptHandler,
                    ast.With,
                    ast.Assert,
                ),
            ):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, ast.Return):
                complexity += 1

        return complexity
