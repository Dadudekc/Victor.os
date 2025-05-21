"""
Command-Line Interface for Module Validation Framework.

This module provides the command-line interface for the Module Validation
Framework, allowing users to validate modules, run integration tests,
and generate reports.
"""

import os
import sys
import json
import time
import argparse
import importlib
from typing import Dict, Any, List, Optional

from dreamos.testing.module_validation.validator import ModuleValidator
from dreamos.testing.module_validation.integration import ModuleIntegrationTester
from dreamos.testing.module_validation.dashboard import ModuleValidationDashboard
from dreamos.testing.module_validation.web_dashboard import generate_and_save_dashboard

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Module Validation Framework")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate modules against specifications")
    validate_parser.add_argument("--modules", type=str, nargs="+", required=True,
                             help="Module names to validate")
    validate_parser.add_argument("--specs-dir", type=str, default=None,
                             help="Directory containing module specifications")
    validate_parser.add_argument("--output-dir", type=str, default="logs/module_validation",
                             help="Output directory for validation reports")
    validate_parser.add_argument("--web-dashboard", action="store_true",
                              help="Generate web dashboard")
    
    # Integration command
    integration_parser = subparsers.add_parser("integration", help="Run integration tests")
    integration_parser.add_argument("--tests", type=str, nargs="*",
                                 help="Test names to run (default: all)")
    integration_parser.add_argument("--tests-dir", type=str, default=None,
                                 help="Directory containing integration tests")
    integration_parser.add_argument("--output-dir", type=str, default="logs/integration",
                                 help="Output directory for integration test reports")
    integration_parser.add_argument("--web-dashboard", action="store_true",
                                  help="Generate web dashboard")
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Generate module validation dashboard")
    dashboard_parser.add_argument("--validation-results", type=str, default=None,
                               help="Path to validation results JSON file")
    dashboard_parser.add_argument("--integration-results", type=str, default=None,
                               help="Path to integration results JSON file")
    dashboard_parser.add_argument("--output-dir", type=str, default="logs/module_validation",
                               help="Output directory for dashboard reports")
    dashboard_parser.add_argument("--web", action="store_true",
                                help="Generate web dashboard")
    
    # All command (run all validations and generate dashboard)
    all_parser = subparsers.add_parser("all", help="Run all validations and generate dashboard")
    all_parser.add_argument("--modules", type=str, nargs="+", required=True,
                         help="Module names to validate")
    all_parser.add_argument("--specs-dir", type=str, default=None,
                         help="Directory containing module specifications")
    all_parser.add_argument("--tests-dir", type=str, default=None,
                         help="Directory containing integration tests")
    all_parser.add_argument("--output-dir", type=str, default="logs/module_validation",
                         help="Output directory for all reports")
    all_parser.add_argument("--web-dashboard", action="store_true",
                          help="Generate web dashboard")
    all_parser.add_argument("--open-browser", action="store_true",
                          help="Open web dashboard in browser")
    
    return parser.parse_args()

def validate_modules(modules: List[str], specs_dir: Optional[str] = None, output_dir: Optional[str] = None):
    """
    Validate modules against specifications.
    
    Args:
        modules: List of module names to validate
        specs_dir: Directory containing module specifications
        output_dir: Output directory for validation reports
        
    Returns:
        dict: Validation results
    """
    # Initialize validator
    validator = ModuleValidator(specs_dir=specs_dir)
    
    try:
        # Load specifications
        validator.load_specifications()
        print(f"Loaded {len(validator.specs)} module specifications")
    except FileNotFoundError as e:
        print(f"Error loading specifications: {str(e)}")
        return None
    
    # Validate modules
    print(f"Validating modules: {', '.join(modules)}")
    results = validator.validate_all_modules(modules)
    
    # Generate report
    try:
        report = validator.generate_report()
        print("\n" + report)
        
        # Save report
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            report_path = os.path.join(output_dir, "validation_report.md")
            with open(report_path, "w") as f:
                f.write(report)
            print(f"Saved validation report to {report_path}")
            
            # Save results as JSON
            results_path = os.path.join(output_dir, "validation_results.json")
            with open(results_path, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Saved validation results to {results_path}")
    except Exception as e:
        print(f"Error generating report: {str(e)}")
    
    return results

def run_integration_tests(tests: List[str] = None, tests_dir: Optional[str] = None, output_dir: Optional[str] = None):
    """
    Run integration tests.
    
    Args:
        tests: List of test names to run (default: all)
        tests_dir: Directory containing integration tests
        output_dir: Output directory for integration test reports
        
    Returns:
        dict: Integration test results
    """
    # Initialize tester
    tester = ModuleIntegrationTester(tests_dir=tests_dir)
    
    try:
        # Load tests
        tester.load_tests()
        print(f"Loaded {len(tester.tests)} integration tests")
    except FileNotFoundError as e:
        print(f"Error loading tests: {str(e)}")
        return None
    
    # Run tests
    if tests:
        print(f"Running integration tests: {', '.join(tests)}")
        results = {}
        for test_name in tests:
            try:
                results[test_name] = tester.run_test(test_name)
            except ValueError as e:
                print(f"Error running test {test_name}: {str(e)}")
    else:
        print("Running all integration tests")
        results = tester.run_all_tests()
    
    # Generate report
    report = tester.generate_report()
    print("\n" + report)
    
    # Save report
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, "integration_report.md")
        with open(report_path, "w") as f:
            f.write(report)
        print(f"Saved integration report to {report_path}")
        
        # Save results as JSON
        results_path = os.path.join(output_dir, "integration_results.json")
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Saved integration results to {results_path}")
    
    return results

def generate_dashboard(validation_results: Optional[str] = None, integration_results: Optional[str] = None, output_dir: Optional[str] = None, web: bool = False):
    """
    Generate module validation dashboard.
    
    Args:
        validation_results: Path to validation results JSON file
        integration_results: Path to integration results JSON file
        output_dir: Output directory for dashboard reports
        web: Whether to generate a web dashboard
        
    Returns:
        str: Path to the dashboard report
    """
    # Initialize dashboard
    dashboard = ModuleValidationDashboard(output_dir=output_dir)
    
    # Load validation results
    if validation_results and os.path.exists(validation_results):
        print(f"Loading validation results from {validation_results}")
        with open(validation_results, "r") as f:
            validation_data = json.load(f)
            
        for module_name, results in validation_data.items():
            # Interface compliance results
            if "error" in results:
                status = "Fail"
            elif results.get("valid", True):
                status = "Pass"
            else:
                status = "Fail"
                
            dashboard.set_validation_status(module_name, status, results)
    
    # Load integration results
    if integration_results and os.path.exists(integration_results):
        print(f"Loading integration results from {integration_results}")
        with open(integration_results, "r") as f:
            integration_data = json.load(f)
            
        for test_name, results in integration_data.items():
            for module_name in results.get("modules", []):
                if results.get("success", True):
                    status = "Pass"
                else:
                    status = "Fail"
                    
                dashboard.set_integration_status(module_name, status, results)
    
    # Generate dashboard
    dashboard_report = dashboard.generate_dashboard()
    print("\n" + dashboard_report)
    
    # Save dashboard
    if output_dir:
        dashboard_path = dashboard.save_dashboard()
        print(f"Saved dashboard report to {dashboard_path}")
        
        # Generate web dashboard
        if web:
            web_dashboard_path = os.path.join(output_dir, "dashboard.html")
            if generate_and_save_dashboard(output_dir, web_dashboard_path):
                print(f"Generated web dashboard at {web_dashboard_path}")
                return web_dashboard_path
        
        return dashboard_path
    
    return None

def run_all(modules: List[str], specs_dir: Optional[str] = None, tests_dir: Optional[str] = None, output_dir: Optional[str] = None, web_dashboard: bool = False, open_browser: bool = False):
    """
    Run all validations and generate dashboard.
    
    Args:
        modules: List of module names to validate
        specs_dir: Directory containing module specifications
        tests_dir: Directory containing integration tests
        output_dir: Output directory for all reports
        web_dashboard: Whether to generate a web dashboard
        open_browser: Whether to open the web dashboard in a browser
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Create output directories
    validation_dir = os.path.join(output_dir, "validation") if output_dir else None
    integration_dir = os.path.join(output_dir, "integration") if output_dir else None
    
    # Run validations
    validation_results = validate_modules(modules, specs_dir, validation_dir)
    if validation_results is None:
        return False
    
    # Run integration tests
    integration_results = run_integration_tests(tests_dir=tests_dir, output_dir=integration_dir)
    
    # Generate dashboard
    validation_results_path = os.path.join(validation_dir, "validation_results.json") if validation_dir else None
    integration_results_path = os.path.join(integration_dir, "integration_results.json") if integration_dir else None
    
    dashboard_path = generate_dashboard(
        validation_results=validation_results_path,
        integration_results=integration_results_path,
        output_dir=output_dir,
        web=web_dashboard
    )
    
    # Open web dashboard in browser
    if web_dashboard and open_browser and dashboard_path and dashboard_path.endswith(".html"):
        try:
            import webbrowser
            dashboard_url = f"file://{os.path.abspath(dashboard_path)}"
            print(f"Opening dashboard in browser: {dashboard_url}")
            webbrowser.open(dashboard_url)
        except Exception as e:
            print(f"Failed to open dashboard in browser: {str(e)}")
    
    return dashboard_path is not None

def main():
    """Main entry point."""
    args = parse_args()
    
    if args.command == "validate":
        success = validate_modules(args.modules, args.specs_dir, args.output_dir) is not None
        
        if success and args.web_dashboard:
            dashboard_dir = args.output_dir.rstrip("/").rstrip("\\")
            parent_dir = os.path.dirname(dashboard_dir) or "."
            web_dashboard_path = os.path.join(parent_dir, "dashboard.html")
            generate_and_save_dashboard(dashboard_dir, web_dashboard_path)
        
    elif args.command == "integration":
        success = run_integration_tests(args.tests, args.tests_dir, args.output_dir) is not None
        
        if success and args.web_dashboard:
            dashboard_dir = args.output_dir.rstrip("/").rstrip("\\")
            parent_dir = os.path.dirname(dashboard_dir) or "."
            web_dashboard_path = os.path.join(parent_dir, "dashboard.html")
            generate_and_save_dashboard(dashboard_dir, web_dashboard_path)
        
    elif args.command == "dashboard":
        success = generate_dashboard(args.validation_results, args.integration_results, args.output_dir, args.web) is not None
    elif args.command == "all":
        success = run_all(args.modules, args.specs_dir, args.tests_dir, args.output_dir, args.web_dashboard, args.open_browser)
    else:
        print("No command specified. Use --help for usage information.")
        success = False
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 