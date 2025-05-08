import ast
import json
import logging
import os
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[
    1
]  # Go up one level from auditing/ to scripts/, then one more to project root
SRC_DIR = PROJECT_ROOT / "src"  # Correct path: <project_root>/src
OUTPUT_FILE = PROJECT_ROOT / "import-graph.json"  # Output to project root
EXCLUDE_DIRS = {"__pycache__"}


def find_python_files(start_dir: Path) -> list[Path]:
    """Find all .py files recursively, excluding specified directories."""
    py_files = []
    for root, dirs, files in os.walk(start_dir):
        # Modify dirs in-place to exclude unwanted ones
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if file.endswith(".py"):
                py_files.append(Path(root) / file)
    return py_files


def get_imports_from_file(file_path: Path) -> set[str]:
    """Extract imported module names from a Python file using AST."""
    imports = set()
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split(".")[0])  # Get top-level module
                elif isinstance(node, ast.ImportFrom):
                    # Handle relative imports (level > 0) carefully?
                    # For now, just capture the module name, might be relative.
                    if node.module:
                        imports.add(node.module.split(".")[0])  # Get top-level module
                    # Also consider the names being imported if needed, but module is primary link  # noqa: E501
                    # for alias in node.names:
                    #     imports.add(alias.name)
    except SyntaxError as e:
        logging.warning(f"Syntax error parsing {file_path}: {e}")
    except Exception as e:
        logging.error(f"Error processing file {file_path}: {e}")
    return imports


def main():
    logging.info(f"Starting import analysis in {SRC_DIR.resolve()}...")
    py_files = find_python_files(SRC_DIR)
    logging.info(f"Found {len(py_files)} Python files.")

    import_graph = {}

    for py_file in py_files:
        relative_path_str = str(py_file.relative_to(SRC_DIR)).replace(
            "\\", "/"
        )  # Use SRC_DIR as base
        logging.debug(f"Processing: {relative_path_str}")
        imports = get_imports_from_file(py_file)
        # Convert imported paths to be relative to src or standard lib names
        # This part needs refinement - how to map imports back to project files?
        # For now, just list the raw imported top-level names.
        import_graph[relative_path_str] = sorted(list(imports))

    logging.info(f"Writing import graph to {OUTPUT_FILE.resolve()}...")
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(import_graph, f, indent=2)
        logging.info("Import graph generation complete.")
    except Exception as e:
        logging.error(f"Failed to write output file {OUTPUT_FILE}: {e}")


if __name__ == "__main__":
    main()
