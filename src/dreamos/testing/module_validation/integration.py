"""
Integration Tester for Module Validation Framework.

This module provides integration testing capabilities for the Module Validation
Framework, allowing tests to be run on multiple modules together.
"""

import os
import sys
import json
import time
import importlib
from typing import Dict, Any, List, Optional

class ModuleIntegrationTester:
    """
    Integration tester for the Module Validation Framework.
    
    This class allows tests to be run on multiple modules together, verifying
    that they interact correctly.
    """
    
    def __init__(self, tests_dir: Optional[str] = None):
        """
        Initialize the integration tester.
        
        Args:
            tests_dir: Directory containing integration tests
        """
        self.tests_dir = tests_dir or "tests/integration"
        self.tests = {}
        self.results = {}
    
    def load_tests(self):
        """
        Load all integration tests from the tests directory.
        
        Raises:
            FileNotFoundError: If the tests directory does not exist
        """
        if not os.path.exists(self.tests_dir):
            os.makedirs(self.tests_dir, exist_ok=True)
            return
        
        # Load all JSON files in the tests directory
        for filename in os.listdir(self.tests_dir):
            if filename.endswith(".json"):
                try:
                    file_path = os.path.join(self.tests_dir, filename)
                    with open(file_path, "r") as f:
                        test = json.load(f)
                    
                    # Add the test to the tests dictionary
                    if "name" in test:
                        self.tests[test["name"]] = test
                except Exception as e:
                    print(f"Error loading test {filename}: {str(e)}")
    
    def create_test(self, name: str, modules: List[str]) -> Dict[str, Any]:
        """
        Create a new integration test.
        
        Args:
            name: Name of the test
            modules: List of module names to include in the test
            
        Returns:
            dict: New test definition
        """
        test = {
            "name": name,
            "description": f"Integration test for modules: {', '.join(modules)}",
            "modules": modules,
            "steps": []
        }
        
        self.tests[name] = test
        return test
    
    def add_call_step(self, test_name: str, module: str, method: str, args: List[Any] = None, kwargs: Dict[str, Any] = None, expected: Any = None):
        """
        Add a call step to a test.
        
        Args:
            test_name: Name of the test
            module: Module name
            method: Method name
            args: Arguments to pass to the method
            kwargs: Keyword arguments to pass to the method
            expected: Expected result (if None, any result is acceptable)
            
        Returns:
            dict: Updated test definition
        """
        if test_name not in self.tests:
            raise ValueError(f"No test found with name: {test_name}")
        
        args = args or []
        kwargs = kwargs or {}
        
        step = {
            "type": "call",
            "description": f"Call {module}.{method}",
            "module": module,
            "method": method,
            "args": args,
            "kwargs": kwargs
        }
        
        if expected is not None:
            step["expected_contains"] = expected
        
        self.tests[test_name]["steps"].append(step)
        return self.tests[test_name]
    
    def save_test(self, test_name: str) -> str:
        """
        Save a test to a file.
        
        Args:
            test_name: Name of the test
            
        Returns:
            str: Path to the saved test file
            
        Raises:
            ValueError: If no test is found with the given name
        """
        if test_name not in self.tests:
            raise ValueError(f"No test found with name: {test_name}")
        
        os.makedirs(self.tests_dir, exist_ok=True)
        file_path = os.path.join(self.tests_dir, f"{test_name}.json")
        
        with open(file_path, "w") as f:
            json.dump(self.tests[test_name], f, indent=4)
        
        return file_path
    
    def run_test(self, test_name: str) -> Dict[str, Any]:
        """
        Run a specific integration test.
        
        Args:
            test_name: Name of the test to run
            
        Returns:
            dict: Test results
            
        Raises:
            ValueError: If no test is found with the given name
        """
        if test_name not in self.tests:
            if len(self.tests) == 0:
                self.load_tests()
            if test_name not in self.tests:
                raise ValueError(f"No test found with name: {test_name}")
        
        test = self.tests[test_name]
        results = {
            "name": test["name"],
            "modules": test["modules"],
            "steps": [],
            "success": True
        }
        
        # Import modules
        modules = {}
        for module_name in test["modules"]:
            try:
                # Import the module
                module = importlib.import_module(f"dreamos.{module_name}")
                modules[module_name] = module
            except ImportError as e:
                results["steps"].append({
                    "type": "import",
                    "module": module_name,
                    "success": False,
                    "error": str(e)
                })
                results["success"] = False
        
        # Skip test if modules couldn't be imported
        if not results["success"]:
            self.results[test_name] = results
            return results
        
        # Run test steps
        for step in test["steps"]:
            step_result = self._run_test_step(step, modules)
            results["steps"].append(step_result)
            if not step_result["success"]:
                results["success"] = False
        
        self.results[test_name] = results
        return results
    
    def _run_test_step(self, step: Dict[str, Any], modules: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single test step.
        
        Args:
            step: Test step to run
            modules: Dictionary of imported modules
            
        Returns:
            dict: Step result
        """
        step_type = step["type"]
        step_result = {
            "type": step_type,
            "success": False,
            "error": None
        }
        
        try:
            if step_type == "call":
                module_name = step["module"]
                method_name = step["method"]
                args = step.get("args", [])
                kwargs = step.get("kwargs", {})
                
                if module_name not in modules:
                    step_result["error"] = f"Module not found: {module_name}"
                    return step_result
                
                module = modules[module_name]
                if not hasattr(module, method_name):
                    step_result["error"] = f"Method not found: {method_name}"
                    return step_result
                
                method = getattr(module, method_name)
                result = method(*args, **kwargs)
                
                # Check expected result if provided
                if "expected_contains" in step:
                    expected = step["expected_contains"]
                    if isinstance(expected, dict) and isinstance(result, dict):
                        # Check that expected key-value pairs are in result
                        for key, value in expected.items():
                            if key not in result or result[key] != value:
                                step_result["error"] = f"Expected {key}={value}, got {key}={result.get(key, 'not found')}"
                                return step_result
                    elif result != expected:
                        step_result["error"] = f"Expected {expected}, got {result}"
                        return step_result
                
                step_result["success"] = True
                step_result["result"] = result
            else:
                step_result["error"] = f"Unknown step type: {step_type}"
        except Exception as e:
            step_result["error"] = str(e)
        
        return step_result
    
    def run_all_tests(self) -> Dict[str, Dict[str, Any]]:
        """
        Run all integration tests.
        
        Returns:
            dict: Dictionary of test results
        """
        if len(self.tests) == 0:
            self.load_tests()
        
        results = {}
        for test_name in self.tests:
            results[test_name] = self.run_test(test_name)
        
        return results
    
    def generate_report(self) -> str:
        """
        Generate a report of integration test results.
        
        Returns:
            str: Report in markdown format
        """
        report = []
        report.append("# Integration Test Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if len(self.results) == 0 and len(self.tests) > 0:
            # Run all tests
            self.run_all_tests()
        
        if len(self.results) == 0:
            report.append("\nNo tests have been run.")
            return "\n".join(report)
        
        # Summarize results
        total_tests = len(self.results)
        passed_tests = sum(1 for results in self.results.values() if results["success"])
        failed_tests = total_tests - passed_tests
        
        report.append(f"\n## Summary")
        report.append(f"- Total tests: {total_tests}")
        report.append(f"- Passed tests: {passed_tests}")
        report.append(f"- Failed tests: {failed_tests}")
        report.append(f"- Success rate: {passed_tests / total_tests * 100:.2f}%")
        
        # Generate detailed results
        report.append("\n## Details")
        
        for test_name, results in self.results.items():
            status = "✅ Pass" if results["success"] else "❌ Fail"
            report.append(f"\n### {test_name} ({status})")
            report.append(f"Modules: {', '.join(results['modules'])}")
            
            for step in results["steps"]:
                step_type = step["type"]
                step_status = "✅ Pass" if step["success"] else "❌ Fail"
                
                if step_type == "import":
                    report.append(f"- Import {step.get('module', '')}: {step_status}")
                    if not step["success"]:
                        report.append(f"  - Error: {step['error']}")
                elif step_type == "call":
                    method_str = f"{step.get('module', '')}.{step.get('method', '')}"
                    report.append(f"- Call {method_str}: {step_status}")
                    if not step["success"]:
                        report.append(f"  - Error: {step['error']}")
                    elif "result" in step:
                        report.append(f"  - Result: {step['result']}")
        
        return "\n".join(report) 