#!/usr/bin/env python3
"""Script to regenerate __init__.py files with proper exports and documentation.

This script analyzes Python modules in the project and regenerates their __init__.py
files with proper exports, documentation, and type hints.
"""

import ast
import os
from pathlib import Path
from typing import Any, Dict, Set


class ModuleAnalyzer:
    """Analyzes Python modules to determine their exports and dependencies."""

    def __init__(self, root_dir: str):
        """Initialize the analyzer with the project root directory.

        Args:
            root_dir: Path to the project root directory
        """
        self.root_dir = Path(root_dir)
        self.processed_modules: Set[str] = set()

    def analyze_module(self, module_path: Path) -> Dict[str, Any]:
        """Analyze a Python module to determine its exports and structure.

        Args:
            module_path: Path to the Python module

        Returns:
            Dict containing module analysis results
        """
        if not module_path.exists() or module_path.name == "__init__.py":
            return {}

        try:
            with open(module_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            # Extract module-level definitions
            exports = []
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    exports.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    if not node.name.startswith("_"):
                        exports.append(node.name)
                elif isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            return {
                "exports": exports,
                "imports": imports,
                "docstring": ast.get_docstring(tree),
            }
        except Exception as e:
            print(f"Error analyzing {module_path}: {e}")
            return {}


class InitFileGenerator:
    """Generates __init__.py files with proper exports and documentation."""

    def __init__(self, root_dir: str):
        """Initialize the generator with the project root directory.

        Args:
            root_dir: Path to the project root directory
        """
        self.root_dir = Path(root_dir)
        self.analyzer = ModuleAnalyzer(root_dir)

    def generate_init_file(self, package_dir: Path) -> None:
        """Generate an __init__.py file for a package directory.

        Args:
            package_dir: Path to the package directory
        """
        init_path = package_dir / "__init__.py"

        # Analyze all Python files in the directory
        exports = set()
        imports = set()
        docstrings = []

        for py_file in package_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            analysis = self.analyzer.analyze_module(py_file)
            exports.update(analysis.get("exports", []))
            imports.update(analysis.get("imports", []))
            if analysis.get("docstring"):
                docstrings.append(analysis["docstring"])

        # Generate the __init__.py content
        content = []

        # Add package docstring
        if docstrings:
            content.append('"""' + docstrings[0] + '"""\n')
        else:
            content.append(f'"""Package {package_dir.name}."""\n')

        # Add imports
        for imp in sorted(imports):
            if not imp.startswith("_"):
                content.append(f"from . import {imp}")

        content.append("\n")

        # Add exports
        if exports:
            content.append("__all__ = [\n")
            for exp in sorted(exports):
                content.append(f"    '{exp}',")
            content.append("]\n")

        # Write the file
        with open(init_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))

    def regenerate_all(self) -> None:
        """Regenerate all __init__.py files in the project."""
        for root, dirs, files in os.walk(self.root_dir):
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")

            if any(f.endswith(".py") for f in files):
                self.generate_init_file(Path(root))


def main():
    """Main entry point for the script."""
    root_dir = Path(__file__).parent.parent.parent
    generator = InitFileGenerator(str(root_dir))
    generator.regenerate_all()


if __name__ == "__main__":
    main()
