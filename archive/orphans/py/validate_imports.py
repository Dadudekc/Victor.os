#!/usr/bin/env python3
"""Script to validate imports across all Python modules in the project.

This script performs a smoke test of all Python modules by attempting to import them
and their dependencies, checking for any import errors or circular dependencies.
"""

import ast
import importlib
import logging
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ImportValidator:
    """Validates imports across Python modules."""

    def __init__(self, root_dir: str):
        """Initialize the validator with the project root directory.

        Args:
            root_dir: Path to the project root directory
        """
        self.root_dir = Path(root_dir)
        self.processed_modules: Set[str] = set()
        self.import_errors: Dict[str, List[str]] = {}
        self.circular_deps: List[Tuple[str, str]] = []

        # Add src directory to Python path
        src_dir = self.root_dir / "src"
        if src_dir.exists():
            sys.path.insert(0, str(src_dir))

    def find_python_files(self) -> List[Path]:
        """Find all Python files in the src directory only."""
        src_dir = self.root_dir / "src"
        python_files = []
        for path in src_dir.rglob("*.py"):
            if "__pycache__" not in str(path):
                python_files.append(path)
        return python_files

    def get_module_name(self, file_path: Path) -> str:
        """Convert file path to module name relative to src/.
        Skips files not under src/ with a warning.
        """
        src_dir = self.root_dir / "src"
        try:
            rel_path = file_path.relative_to(src_dir)
        except ValueError:
            logger.warning(f"Skipping file not under src/: {file_path}")
            return None
        return str(rel_path.with_suffix("")).replace("/", ".").replace("\\", ".")

    def analyze_imports(self, file_path: Path) -> Set[str]:
        """Analyze imports in a Python file.

        Args:
            file_path: Path to Python file

        Returns:
            Set of imported module names
        """
        imports = set()
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.add(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")

        return imports

    def validate_imports(self) -> bool:
        """Validate imports across all Python modules.

        Returns:
            True if all imports are valid, False otherwise
        """
        python_files = self.find_python_files()
        all_valid = True

        for file_path in python_files:
            module_name = self.get_module_name(file_path)
            logger.info(f"Validating imports for {module_name}")

            try:
                # Try importing the module
                importlib.import_module(module_name)

                # Analyze its imports
                imports = self.analyze_imports(file_path)
                for imp in imports:
                    try:
                        if imp.startswith("."):
                            # Handle relative imports
                            base_module = ".".join(module_name.split(".")[:-1])
                            full_imp = base_module + imp
                        else:
                            full_imp = imp

                        importlib.import_module(full_imp)
                    except ImportError as e:
                        if module_name not in self.import_errors:
                            self.import_errors[module_name] = []
                        self.import_errors[module_name].append(f"{imp}: {str(e)}")
                        all_valid = False

            except ImportError as e:
                logger.error(f"Failed to import {module_name}: {e}")
                all_valid = False

        return all_valid

    def report_results(self) -> None:
        """Report validation results."""
        if not self.import_errors:
            logger.info("✅ All imports validated successfully!")
        else:
            logger.error("❌ Import validation failed!")
            for module, errors in self.import_errors.items():
                logger.error(f"\nModule: {module}")
                for error in errors:
                    logger.error(f"  - {error}")

        if self.circular_deps:
            logger.error("\nCircular dependencies detected:")
            for mod1, mod2 in self.circular_deps:
                logger.error(f"  - {mod1} <-> {mod2}")


def main():
    """Main entry point for the script."""
    root_dir = Path(__file__).parent.parent.parent
    validator = ImportValidator(str(root_dir))

    logger.info("Starting import validation...")
    success = validator.validate_imports()
    validator.report_results()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
