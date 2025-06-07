#!/usr/bin/env python3
"""
Module Validation Framework Demo Flow

This script demonstrates the complete flow of the Module Validation Framework using helper functions from ``demo_flow_utils``.
"""

import os
import sys

from demo_flow_utils import (
    LOGS_DIR,
    SPECS_DIR,
    TESTS_DIR,
    create_integration_tests,
    create_specs,
    ensure_dirs,
    generate_dashboard,
    pause,
    run_integration_tests,
    step_header,
    validate_modules,
)


def main() -> int:
    """Run the demo workflow."""
    print("Dream.OS Module Validation Framework Demo Flow")
    print("=============================================")
    ensure_dirs()
    create_specs()
    pause(1)
    create_integration_tests()
    pause(1)
    validator = validate_modules()
    pause(1)
    tester = run_integration_tests()
    pause(1)
    generate_dashboard(validator, tester)
    step_header("DEMO COMPLETED")
    print("✅ The Module Validation Framework demo has been completed.")
    print("You can find the results in the following locations:")
    print(f"  - Module specifications: {SPECS_DIR}")
    print(f"  - Integration tests: {TESTS_DIR}")
    print(f"  - Validation reports: {LOGS_DIR}")
    print(f"  - Web dashboard: {os.path.join(LOGS_DIR, 'dashboard.html')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
