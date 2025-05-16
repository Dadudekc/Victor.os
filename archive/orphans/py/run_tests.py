# scripts/run_tests.py
# Reconstructed test runner script.
# This script is intended to run pytest for the project.

import os
import sys

import pytest

if __name__ == "__main__":
    print("Starting test execution via reconstructed run_tests.py...")
    # Assuming tests are primarily located in 'src/tests'
    # and the script is run from the project root.
    test_dir = "src/tests"

    # Add project root to Python path to allow imports from src
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, project_root)

    print(f"Project root added to sys.path: {project_root}")
    print(f"Looking for tests in: {test_dir}")

    # Ensure the current working directory is the project root for consistent test discovery
    os.chdir(project_root)
    print(f"Changed current working directory to: {os.getcwd()}")

    # pytest arguments:
    # -v for verbose output
    # --cov for coverage (pointing to src)
    # --cov-report for html and term coverage reports
    # test_dir to specify where to find tests
    # You might need to install pytest and pytest-cov: pip install pytest pytest-cov
    args = [
        "-v",
        # "--cov=src",  # Enable coverage for the 'src' directory
        # "--cov-report=html",
        # "--cov-report=term",
        test_dir,
    ]

    print(f"Running pytest with arguments: {args}")

    exit_code = pytest.main(args)

    print(f"Pytest execution finished with exit code: {exit_code}")
    sys.exit(exit_code)
