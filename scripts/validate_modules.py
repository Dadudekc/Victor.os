#!/usr/bin/env python3
"""
Module Validation Script

This script runs the Module Validation Framework to validate the Dream.OS bridge modules.
"""

import os
import sys
import importlib
from dreamos.testing.module_validation.cli import run_all

def main():
    """Main entry point."""
    # Define the modules to validate
    modules = ["bridge.module1_injector", "bridge.module2_processor", "bridge.module3_logging_error_handling"]
    
    # Run the validation framework
    success = run_all(
        modules=modules,
        specs_dir="docs/specs/modules",
        tests_dir="tests/integration",
        output_dir="logs/module_validation"
    )
    
    # Print success/failure message
    if success:
        print("\nModule validation successful! 🎉")
        print("Check logs/module_validation for detailed results.")
    else:
        print("\nModule validation failed. ❌")
        print("Check logs/module_validation for error details.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 