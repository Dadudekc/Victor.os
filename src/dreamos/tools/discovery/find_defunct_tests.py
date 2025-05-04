import argparse
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define constants for default paths relative to the project root (assumed to be parent of src)  # noqa: E501
DEFAULT_SRC_DIR = "src/dreamos"
DEFAULT_TESTS_DIR = "tests"
DEFAULT_OUTPUT_FILE = "runtime/logs/defunct_tests.jsonl"


def find_python_files(start_path: Path, exclude_init: bool = True) -> set[Path]:
    """Finds all .py files recursively in a directory."""
    files = set()
    for path in start_path.rglob("*.py"):
        if exclude_init and path.name == "__init__.py":
            continue
        files.add(path)
    return files


def map_test_to_source(
    test_file: Path, tests_root: Path, src_root: Path
) -> Path | None:
    """
    Attempts to map a test file path to a potential source file path.
    Basic heuristic: mirrors the directory structure and removes 'test_' prefix.
    e.g., tests/core/test_agent.py -> src/dreamos/core/agent.py
    e.g., tests/utils/test_helpers.py -> src/dreamos/utils/helpers.py
    Adjust this logic based on project conventions.
    """
    try:
        relative_test_path = test_file.relative_to(tests_root)
        # Handle cases where test filename directly maps to source module
        if relative_test_path.name.startswith("test_"):
            source_filename = relative_test_path.name[5:]  # Remove 'test_'
        else:
            # If no test_ prefix, maybe it tests an __init__ or a whole package?
            # Or maybe the convention is different. For now, assume it doesn't map.
            return None

        # Construct potential source path parts
        source_parts = list(relative_test_path.parts[:-1]) + [source_filename]
        potential_source_path = src_root.joinpath(*source_parts)
        return potential_source_path
    except ValueError:
        # test_file might not be under tests_root (shouldn't happen with proper input)
        logger.warning(f"Could not determine relative path for test file: {test_file}")
        return None


def find_defunct_tests(
    src_dir: str, tests_dir: str, output_file: str, args: argparse.Namespace
):
    """
    Identifies test files that may not correspond to existing source files
    and writes them to the specified output file.

    Args:
        src_dir: Relative path to source code directory.
        tests_dir: Relative path to tests directory.
        output_file: Relative path to output JSONL file.
        args: Parsed command-line arguments (for --exclude-dirs).
    """
    project_root = (
        Path(__file__).resolve().parents[4]
    )  # Adjust based on actual file location
    src_path = project_root / src_dir
    tests_path = project_root / tests_dir
    output_path = project_root / output_file

    logger.info(f"Project root detected as: {project_root}")
    logger.info(f"Scanning source directory: {src_path}")
    logger.info(f"Scanning tests directory: {tests_path}")

    if not src_path.is_dir():
        logger.error(f"Source directory not found: {src_path}")
        return
    if not tests_path.is_dir():
        logger.error(f"Tests directory not found: {tests_path}")
        return

    source_files = find_python_files(src_path, exclude_init=True)
    test_files = find_python_files(tests_path, exclude_init=True)

    # Exclude common test files that don't map 1:1
    test_files = {f for f in test_files if f.name != "conftest.py"}

    # {{ EDIT START: Use exclude_dirs argument }}
    # Define default exclusions
    default_excluded_dirs = ["fixtures", "integration", "snapshots", "__pycache__"]
    # Get exclusions from args, split if provided as comma-separated string
    excluded_dirs = getattr(args, "exclude_dirs", None)
    if excluded_dirs:
        # If provided via CLI, they override defaults unless explicitly added back
        # Simple override for now:
        resolved_excluded_dirs = [
            d.strip() for d in excluded_dirs.split(",") if d.strip()
        ]
        logger.info(f"Using provided exclude_dirs: {resolved_excluded_dirs}")
    else:
        resolved_excluded_dirs = default_excluded_dirs
        logger.info(f"Using default exclude_dirs: {resolved_excluded_dirs}")

    original_count = len(test_files)
    test_files = {
        f
        for f in test_files
        if not any(excluded_part in f.parts for excluded_part in resolved_excluded_dirs)
    }
    excluded_count = original_count - len(test_files)
    if excluded_count > 0:
        logger.info(
            f"Excluded {excluded_count} test files based on directory patterns: {resolved_excluded_dirs}"  # noqa: E501
        )
    # {{ EDIT END }}

    logger.info(
        f"Found {len(source_files)} source Python files (excluding __init__.py)."
    )
    logger.info(
        f"Found {len(test_files)} test Python files (excluding __init__.py, conftest.py, excluded dirs)."  # noqa: E501
    )  # Updated log

    defunct_tests = []
    mapped_sources = set()

    for test_file in test_files:
        potential_source = map_test_to_source(test_file, tests_path, src_path)
        if potential_source:
            mapped_sources.add(
                potential_source
            )  # Keep track of sources we expect tests for
            if not potential_source.exists():
                logger.warning(
                    f"Potential defunct test: {test_file} -> {potential_source} (Source missing)"  # noqa: E501
                )
                defunct_tests.append(test_file)
            # else:
            # logger.debug(f"Test mapping: {test_file} -> {potential_source} (Source exists)")  # noqa: E501
        else:
            # Test didn't map using the heuristic, could be integration, utils test, etc.  # noqa: E501
            # Or it could be defunct if it tested a module that's now gone.
            # For now, we only flag tests whose *mapped* source is missing.
            # A more advanced check could see if the *directory* still exists.
            logger.debug(
                f"Test file {test_file} did not map to a source file using the current heuristic."  # noqa: E501
            )

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write results to JSONL file
    try:
        with open(output_path, "w") as f:
            for test_file in defunct_tests:
                # Store relative path for portability
                relative_path_str = str(test_file.relative_to(project_root))
                json.dump({"defunct_test_file": relative_path_str}, f)
                f.write("\n")
        logger.info(f"Defunct test analysis complete. Results saved to: {output_path}")
        logger.info(f"Found {len(defunct_tests)} potentially defunct test files.")

    except IOError as e:
        logger.error(f"Failed to write output file {output_path}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Find defunct test files (tests whose corresponding source module might be missing)."  # noqa: E501
    )
    parser.add_argument(
        "--src-dir",
        default=DEFAULT_SRC_DIR,
        help=f"Relative path to the source directory (default: {DEFAULT_SRC_DIR})",
    )
    parser.add_argument(
        "--tests-dir",
        default=DEFAULT_TESTS_DIR,
        help=f"Relative path to the tests directory (default: {DEFAULT_TESTS_DIR})",
    )
    parser.add_argument(
        "--output-file",
        default=DEFAULT_OUTPUT_FILE,
        help=f"Relative path to the output JSONL file (default: {DEFAULT_OUTPUT_FILE})",
    )
    parser.add_argument(
        "--exclude-dirs",
        type=str,
        help=f"Comma-separated list of directory names to exclude within tests dir (e.g., fixtures,integration). Defaults: {','.join(DEFAULT_EXCLUDE_DIRS) if 'DEFAULT_EXCLUDE_DIRS' in locals() else 'fixtures,integration,snapshots,__pycache__'}",  # noqa: E501, F821
    )

    args = parser.parse_args()

    find_defunct_tests(args.src_dir, args.tests_dir, args.output_file, args)
