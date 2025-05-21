#!/usr/bin/env python3
"""
Module Validation Framework Demo Flow

This script demonstrates the complete flow of the Module Validation Framework,
from creating specifications to validating modules and generating reports.
"""

import os
import sys
import importlib
import time
from pprint import pprint

# Import the validation framework modules
from dreamos.testing.module_validation.interface_spec import ModuleInterfaceSpec
from dreamos.testing.module_validation.validator import ModuleValidator
from dreamos.testing.module_validation.integration import ModuleIntegrationTester
from dreamos.testing.module_validation.dashboard import ModuleValidationDashboard
from dreamos.testing.module_validation.web_dashboard import generate_and_save_dashboard

# Define output directories
SPECS_DIR = "docs/specs/modules"
TESTS_DIR = "tests/integration"
LOGS_DIR = "logs/module_validation"


def ensure_dirs():
    """Ensure necessary directories exist."""
    for d in [SPECS_DIR, TESTS_DIR, LOGS_DIR]:
        os.makedirs(d, exist_ok=True)


def step_header(title):
    """Print a step header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def pause(seconds=1):
    """Pause for a bit."""
    time.sleep(seconds)


def create_specs():
    """Create module specifications."""
    step_header("STEP 1: Creating Module Specifications")
    
    # Create Module 1 (Injector) specification
    print("Creating Module 1 (Injector) specification...")
    injector_spec = ModuleInterfaceSpec("module1_injector")
    injector_spec.add_method(
        "process_command",
        parameters=[
            {
                "name": "command_data",
                "type": "dict",
                "required": True,
                "description": "Dictionary containing command information"
            }
        ],
        return_type="dict",
        required=True
    )
    injector_spec.add_method(
        "health_check",
        parameters=[],
        return_type="dict",
        required=True
    )
    injector_spec.save_to_file(os.path.join(SPECS_DIR, "module1_injector.json"))
    print("✅ Created Module 1 specification")
    
    # Create Module 2 (Processor) specification
    print("Creating Module 2 (Processor) specification...")
    processor_spec = ModuleInterfaceSpec("module2_processor")
    processor_spec.add_method(
        "transform_payload",
        parameters=[
            {
                "name": "payload_data",
                "type": "dict",
                "required": True,
                "description": "Dictionary containing the payload to transform"
            },
            {
                "name": "transformation_type",
                "type": "str",
                "required": False,
                "description": "The type of transformation to apply (standard, minimal, verbose)"
            }
        ],
        return_type="dict",
        required=True
    )
    processor_spec.add_method(
        "process_data",
        parameters=[
            {
                "name": "input_data",
                "type": "dict",
                "required": True,
                "description": "Dictionary containing input data with data and optional metadata"
            },
            {
                "name": "processor_config",
                "type": "dict",
                "required": False,
                "description": "Optional configuration for the processor"
            }
        ],
        return_type="dict",
        required=True
    )
    processor_spec.add_method(
        "health_check",
        parameters=[],
        return_type="dict",
        required=True
    )
    processor_spec.save_to_file(os.path.join(SPECS_DIR, "module2_processor.json"))
    print("✅ Created Module 2 specification")
    
    # Create Module 3 (Logging & Error Handling) specification
    print("Creating Module 3 (Logging & Error Handling) specification...")
    logging_spec = ModuleInterfaceSpec("module3_logging_error_handling")
    logging_spec.add_method(
        "log",
        parameters=[
            {
                "name": "event_data",
                "type": "dict",
                "required": True,
                "description": "Dictionary containing event information"
            },
            {
                "name": "log_level",
                "type": "str",
                "required": False,
                "description": "Severity level (INFO, WARNING, ERROR, FATAL)"
            }
        ],
        return_type="str",
        required=True
    )
    logging_spec.add_method(
        "handle_error",
        parameters=[
            {
                "name": "error",
                "type": "Exception",
                "required": True,
                "description": "The exception that was caught"
            },
            {
                "name": "context",
                "type": "dict",
                "required": False,
                "description": "Additional context about where the error occurred"
            },
            {
                "name": "error_code",
                "type": "str",
                "required": False,
                "description": "Optional specific error code"
            }
        ],
        return_type="dict",
        required=True
    )
    logging_spec.save_to_file(os.path.join(SPECS_DIR, "module3_logging_error_handling.json"))
    print("✅ Created Module 3 specification")


def create_integration_tests():
    """Create integration tests."""
    step_header("STEP 2: Creating Integration Tests")
    
    # Create integration test
    print("Creating integration test...")
    tester = ModuleIntegrationTester(tests_dir=TESTS_DIR)
    test = tester.create_test("bridge_modules_integration", ["bridge.module1_injector", "bridge.module2_processor", "bridge.module3_logging_error_handling"])
    
    # Add test steps
    tester.add_call_step(
        "bridge_modules_integration",
        module="bridge.module3_logging_error_handling",
        method="log",
        args=[{"event": "test_event", "message": "Test message", "source": "test_integration"}],
        kwargs={"log_level": "INFO"}
    )
    
    # Add a step for module2_processor
    tester.add_call_step(
        "bridge_modules_integration",
        module="bridge.module2_processor",
        method="process_data",
        args=[{
            "data": {"test": "data"},
            "metadata": {"source": "test_integration"}
        }],
        expected={"processed": True}
    )
    
    tester.add_call_step(
        "bridge_modules_integration",
        module="bridge.module1_injector",
        method="process_command",
        args=[{
            "command_type": "test_command",
            "payload": {"test": "data"},
            "source": "test_integration",
            "metadata": {"test": "metadata"}
        }],
        expected={"status": "success"}
    )
    
    tester.add_call_step(
        "bridge_modules_integration",
        module="bridge.module1_injector",
        method="health_check",
        args=[],
        expected={"status": "healthy"}
    )
    
    tester.save_test("bridge_modules_integration")
    print("✅ Created integration test")


def validate_modules():
    """Validate modules against specifications."""
    step_header("STEP 3: Validating Modules")
    
    try:
        # Import modules
        print("Importing modules...")
        module1 = importlib.import_module("dreamos.bridge.module1_injector")
        module2 = importlib.import_module("dreamos.bridge.module2_processor")
        module3 = importlib.import_module("dreamos.bridge.module3_logging_error_handling")
        print("✅ Modules imported successfully")
        
        # Validate modules
        print("\nValidating Module 1 (Injector)...")
        validator = ModuleValidator(specs_dir=SPECS_DIR)
        validator.load_specifications()
        
        module1_results = validator.validate_module(module1, "module1_injector")
        print(f"Module 1 validation result: {module1_results['valid']}")
        if not module1_results['valid']:
            print("Issues found:")
            if module1_results['missing_methods']:
                print(f"  Missing methods: {', '.join(module1_results['missing_methods'])}")
            if module1_results['invalid_methods']:
                print(f"  Invalid methods: {', '.join(module1_results['invalid_methods'])}")
        else:
            print("✅ Module 1 is valid")
        
        print("\nValidating Module 2 (Processor)...")
        module2_results = validator.validate_module(module2, "module2_processor")
        print(f"Module 2 validation result: {module2_results['valid']}")
        if not module2_results['valid']:
            print("Issues found:")
            if module2_results['missing_methods']:
                print(f"  Missing methods: {', '.join(module2_results['missing_methods'])}")
            if module2_results['invalid_methods']:
                print(f"  Invalid methods: {', '.join(module2_results['invalid_methods'])}")
        else:
            print("✅ Module 2 is valid")
        
        print("\nValidating Module 3 (Logging & Error Handling)...")
        module3_results = validator.validate_module(module3, "module3_logging_error_handling")
        print(f"Module 3 validation result: {module3_results['valid']}")
        if not module3_results['valid']:
            print("Issues found:")
            if module3_results['missing_methods']:
                print(f"  Missing methods: {', '.join(module3_results['missing_methods'])}")
            if module3_results['invalid_methods']:
                print(f"  Invalid methods: {', '.join(module3_results['invalid_methods'])}")
        else:
            print("✅ Module 3 is valid")
            
        # Generate validation report
        report = validator.generate_report()
        report_path = os.path.join(LOGS_DIR, "validation_report.md")
        with open(report_path, "w") as f:
            f.write(report)
        print(f"\nValidation report saved to {report_path}")
        
        return validator
        
    except ImportError as e:
        print(f"❌ Error importing modules: {e}")
        print("Make sure you have implemented the bridge modules in src/dreamos/bridge/")
        return None


def run_integration_tests():
    """Run integration tests."""
    step_header("STEP 4: Running Integration Tests")
    
    try:
        # Run integration tests
        print("Running integration tests...")
        tester = ModuleIntegrationTester(tests_dir=TESTS_DIR)
        tester.load_tests()
        
        results = tester.run_test("bridge_modules_integration")
        
        # Check results
        if results['success']:
            print("✅ Integration tests passed!")
        else:
            print("❌ Integration tests failed!")
            for step in results['steps']:
                if not step['success']:
                    print(f"  Error in step: {step['type']}")
                    print(f"  Error message: {step['error']}")
        
        # Generate report
        report = tester.generate_report()
        report_path = os.path.join(LOGS_DIR, "integration_report.md")
        with open(report_path, "w") as f:
            f.write(report)
        print(f"\nIntegration test report saved to {report_path}")
        
        return tester
        
    except Exception as e:
        print(f"❌ Error running integration tests: {e}")
        return None


def generate_dashboard(validator, tester):
    """Generate module validation dashboard."""
    step_header("STEP 5: Generating Dashboard")
    
    if validator is None or tester is None:
        print("❌ Cannot generate dashboard: validator or tester is None")
        return
    
    try:
        # Create dashboard
        print("Generating dashboard...")
        dashboard = ModuleValidationDashboard(output_dir=LOGS_DIR)
        
        # Add modules
        dashboard.add_module("bridge.module1_injector")
        dashboard.add_module("bridge.module3_logging_error_handling")
        
        # Set validation status
        dashboard.set_validation_status(
            "bridge.module1_injector", 
            "Pass" if validator.results.get("module1_injector", {}).get("valid", False) else "Fail",
            validator.results.get("module1_injector", {})
        )
        dashboard.set_validation_status(
            "bridge.module3_logging_error_handling", 
            "Pass" if validator.results.get("module3_logging_error_handling", {}).get("valid", False) else "Fail",
            validator.results.get("module3_logging_error_handling", {})
        )
        
        # Set error handling status
        dashboard.set_error_handling_status("bridge.module1_injector", "Unknown")
        dashboard.set_error_handling_status("bridge.module3_logging_error_handling", "Unknown")
        
        # Set integration status
        test_results = tester.results.get("bridge_modules_integration", {})
        if "bridge.module1_injector" in test_results.get("modules", []):
            dashboard.set_integration_status(
                "bridge.module1_injector", 
                "Pass" if test_results.get("success", False) else "Fail",
                test_results
            )
        if "bridge.module3_logging_error_handling" in test_results.get("modules", []):
            dashboard.set_integration_status(
                "bridge.module3_logging_error_handling", 
                "Pass" if test_results.get("success", False) else "Fail",
                test_results
            )
        
        # Generate dashboard
        report = dashboard.generate_dashboard()
        dashboard_path = dashboard.save_dashboard()
        print(f"✅ Dashboard saved to {dashboard_path}")
        
        # Generate web dashboard
        web_dashboard_path = os.path.join(LOGS_DIR, "dashboard.html")
        if generate_and_save_dashboard(LOGS_DIR, web_dashboard_path):
            print(f"✅ Web dashboard generated at {web_dashboard_path}")
            
            # Try to open the dashboard in the default browser
            try:
                import webbrowser
                dashboard_url = f"file://{os.path.abspath(web_dashboard_path)}"
                print(f"Opening dashboard in browser: {dashboard_url}")
                webbrowser.open(dashboard_url)
            except Exception as e:
                print(f"❌ Failed to open dashboard in browser: {str(e)}")
                print(f"You can manually open the dashboard at: {os.path.abspath(web_dashboard_path)}")
        
    except Exception as e:
        print(f"❌ Error generating dashboard: {e}")


def main():
    """Main entry point."""
    print("Dream.OS Module Validation Framework Demo Flow")
    print("=============================================")
    
    # Ensure directories exist
    ensure_dirs()
    
    # Create specifications
    create_specs()
    pause(1)
    
    # Create integration tests
    create_integration_tests()
    pause(1)
    
    # Validate modules
    validator = validate_modules()
    pause(1)
    
    # Run integration tests
    tester = run_integration_tests()
    pause(1)
    
    # Generate dashboard
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