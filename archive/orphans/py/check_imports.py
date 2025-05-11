"""
Import Validation Script

Checks for broken imports after directory restructuring.
Reports any unresolved modules or circular dependencies.
"""

import ast
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class ImportValidator:
    """Validates Python imports in the codebase."""

    def __init__(self, root_dir: str = "src/dreamos"):
        self.root_dir = Path(root_dir)
        self.imports: Dict[str, List[str]] = {}  # file -> list of imports
        self.unresolved: Dict[str, List[str]] = {}  # file -> list of unresolved imports
        self.circular: List[Tuple[str, str]] = []  # list of circular import pairs

    def _parse_file(self, file_path: Path) -> List[str]:
        """Parse a Python file and extract its imports."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return []

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return imports

    def _check_import_resolution(
        self, file_path: Path, imports: List[str]
    ) -> List[str]:
        """Check if imports can be resolved."""
        unresolved = []
        for imp in imports:
            # Skip standard library imports
            if imp in sys.stdlib_module_names:
                continue

            # Try to resolve the import
            try:
                __import__(imp)
            except ImportError:
                unresolved.append(imp)
        return unresolved

    def _detect_circular_imports(self):
        """Detect circular dependencies between modules."""
        visited = set()
        path = []

        def dfs(module: str):
            if module in path:
                # Found a cycle
                cycle_start = path.index(module)
                cycle = path[cycle_start:] + [module]
                self.circular.append(tuple(cycle))
                return

            if module in visited:
                return

            visited.add(module)
            path.append(module)

            # Check all imports of this module
            for imp in self.imports.get(module, []):
                if imp in self.imports:  # Only check modules we've parsed
                    dfs(imp)

            path.pop()

        # Start DFS from each module
        for module in self.imports:
            if module not in visited:
                dfs(module)

    def validate(self) -> bool:
        """Run the full import validation."""
        # Find all Python files
        python_files = list(self.root_dir.rglob("*.py"))
        if not python_files:
            logger.warning(f"No Python files found in {self.root_dir}")
            return False

        # Parse each file
        for file_path in python_files:
            relative_path = file_path.relative_to(self.root_dir)
            module_name = str(relative_path).replace("/", ".").replace("\\", ".")[:-3]

            imports = self._parse_file(file_path)
            self.imports[module_name] = imports

            # Check import resolution
            unresolved = self._check_import_resolution(file_path, imports)
            if unresolved:
                self.unresolved[module_name] = unresolved

        # Detect circular imports
        self._detect_circular_imports()

        # Report results
        has_issues = bool(self.unresolved or self.circular)

        if self.unresolved:
            print("\n❌ Unresolved imports found:")
            for module, imports in self.unresolved.items():
                print(f"\n  {module}:")
                for imp in imports:
                    print(f"    - {imp}")

        if self.circular:
            print("\n❌ Circular dependencies found:")
            for cycle in self.circular:
                print(f"\n  {' -> '.join(cycle)}")

        if not has_issues:
            print("\n✅ All imports resolved successfully!")

        return not has_issues


def main():
    """CLI entry point for import validation."""
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s"
    )

    validator = ImportValidator()
    if validator.validate():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
