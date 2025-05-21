#!/usr/bin/env python3
"""
Module Validation and Dashboard Script

This script runs the Module Validation Framework to validate the Dream.OS bridge modules
and generates a web dashboard with the results.
"""

import os
import sys
import time
import subprocess
from dreamos.testing.module_validation.cli import run_all
from dreamos.testing.module_validation.web_dashboard import generate_and_save_dashboard

def main():
    """Main entry point."""
    # Define the modules to validate
    modules = ["bridge.module1_injector", "bridge.module2_processor", "bridge.module3_logging_error_handling"]
    
    # Define output directories
    base_output_dir = "logs/module_validation"
    dashboard_path = os.path.join(base_output_dir, "dashboard.html")
    
    # Ensure output directory exists
    os.makedirs(base_output_dir, exist_ok=True)
    
    # Run the validation framework
    print("Running module validation...")
    success = run_all(
        modules=modules,
        specs_dir="docs/specs/modules",
        tests_dir="tests/integration",
        output_dir=base_output_dir
    )
    
    # Print success/failure message
    if success:
        print("\nModule validation successful! 🎉")
    else:
        print("\nModule validation failed. ❌")
    
    # Generate web dashboard
    print("\nGenerating web dashboard...")
    dashboard_success = generate_and_save_dashboard(base_output_dir, dashboard_path)
    
    if dashboard_success:
        print(f"Dashboard generated successfully: {dashboard_path}")
        
        # Try to open the dashboard in the default browser
        try:
            import webbrowser
            dashboard_url = f"file://{os.path.abspath(dashboard_path)}"
            print(f"Opening dashboard in browser: {dashboard_url}")
            webbrowser.open(dashboard_url)
        except Exception as e:
            print(f"Failed to open dashboard in browser: {str(e)}")
            print(f"You can manually open the dashboard at: {os.path.abspath(dashboard_path)}")
    else:
        print("Failed to generate dashboard")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 