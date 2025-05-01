# src/dreamos/tools/validation/check_dependencies.py
import logging
import shutil
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_TOOLS = [
    "vulture",
    "flake8",
    "ruff",
    "pytest",
    "mypy",
    "black",
    # Add other essential tools here if needed
]


def check_cli_dependencies(
    tools_to_check: Optional[List[str]] = None,
) -> Dict[str, Optional[str]]:
    """
    Checks if specified CLI tools are installed and available in the system PATH.

    Args:
        tools_to_check: A list of command names to check. Defaults to a standard list
                       (vulture, flake8, ruff, pytest, mypy, black).

    Returns:
        A dictionary mapping tool names to their found executable path (str)
        or None if the tool was not found.
    """
    if tools_to_check is None:
        tools_to_check = DEFAULT_TOOLS

    results: Dict[str, Optional[str]] = {}
    logger.info(f"Checking for CLI dependencies: {', '.join(tools_to_check)}")

    all_found = True
    for tool in tools_to_check:
        found_path = shutil.which(tool)
        results[tool] = found_path
        if found_path:
            logger.info(f"  ✅ Found '{tool}' at: {found_path}")
        else:
            logger.warning(
                f"  ⚠️ Could not find '{tool}'. Some functionality might be unavailable."
            )
            all_found = False

    if all_found:
        logger.info("All checked dependencies were found.")
    else:
        logger.warning(
            "Some dependencies were not found. Please ensure they are installed and in the system PATH."
        )

    return results


def main():
    """CLI entry point function."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    print("Running Dream.OS CLI dependency check...")
    dependency_status = check_cli_dependencies()
    print("\nDependency Status Report:")
    found_all = True
    for tool, path in dependency_status.items():
        status = f"Found: {path}" if path else "NOT FOUND"
        print(f"- {tool:<10}: {status}")
        if not path:
            found_all = False

    if not found_all:
        print("\nWarning: Some dependencies were not found.")
        # Potentially exit with non-zero code if needed
        # import sys
        # sys.exit(1)
    else:
        print("\nAll checked dependencies found.")


# Main execution block
if __name__ == "__main__":
    main()
