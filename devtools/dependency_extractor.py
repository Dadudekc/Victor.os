#!/usr/bin/env python3
"""
Utility to extract import dependencies from Python source files using AST.
"""

import ast
from pathlib import Path
from typing import List, Tuple, Set

def extract_imports_from_file(file_path: Path) -> Tuple[Set[str], Set[str]]:
    """
    Parses a Python file and extracts its import statements.

    Args:
        file_path: Path to the Python file.

    Returns:
        A tuple containing two sets:
        - direct_imports: Set of directly imported modules (e.g., 'os', 'sys').
        - from_imports: Set of modules from which specific names are imported 
                        (e.g., 'pathlib' from 'from pathlib import Path').
                        This captures the top-level package/module being imported from.
    """
    direct_imports: Set[str] = set()
    from_imports: Set[str] = set()

    if not file_path.is_file():
        # print(f"Warning: File not found {file_path}", file=sys.stderr)
        return direct_imports, from_imports

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        tree = ast.parse(source_code, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Capture the first part of a dotted import, e.g., A from 'import A.B.C'
                    direct_imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Capture the first part of a dotted import, e.g., A from 'from A.B.C import D'
                    from_imports.add(node.module.split('.')[0])
    except Exception as e:
        # print(f"Error parsing {file_path}: {e}", file=sys.stderr)
        pass # Continue if a file can't be parsed
    
    return direct_imports, from_imports

if __name__ == '__main__':
    # Example Usage (for testing this script directly)
    test_file = Path('src/dreamos/core/config.py') # Relative to project root
    if test_file.exists():
        direct, from_ = extract_imports_from_file(test_file)
        print(f"File: {test_file}")
        print(f"  Direct Imports: {direct}")
        print(f"  From Imports: {from_}")
    else:
        print(f"Test file {test_file} not found.")
    # print("Dependency Extractor Utility. Not meant to be run directly without modification for testing.") 