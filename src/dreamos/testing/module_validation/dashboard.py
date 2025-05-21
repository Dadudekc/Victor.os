"""
Dashboard for Module Validation Framework.

This module provides a dashboard for visualizing the validation status of
Dream.OS bridge modules, including interface compliance, error handling,
and integration test results.
"""

import os
import time
import json
from typing import Dict, Any, List, Optional

class ModuleValidationDashboard:
    """
    Dashboard for Module Validation Framework.
    
    This class provides a dashboard for visualizing the validation status of
    Dream.OS bridge modules, including interface compliance, error handling,
    and integration test results.
    """
    
    def __init__(self, output_dir: str = "logs/module_validation"):
        """
        Initialize the dashboard.
        
        Args:
            output_dir: Directory to save dashboard reports
        """
        self.output_dir = output_dir
        self.modules = {}
        self.timestamp = time.time()
        self.errors = []
        
    def add_module(self, module_name: str):
        """
        Add a module to the dashboard.
        
        Args:
            module_name: Name of the module
        """
        if module_name not in self.modules:
            self.modules[module_name] = {
                "interface_compliance": "Unknown",
                "error_handling": "Unknown",
                "integration_tests": "Unknown",
                "overall": "Unknown",
                "details": {
                    "interface_compliance": {},
                    "error_handling": {},
                    "integration_tests": {}
                }
            }
    
    def set_validation_status(self, module_name: str, status: str, details: Dict[str, Any] = None):
        """
        Set the validation status for a module.
        
        Args:
            module_name: Name of the module
            status: Validation status (Pass, Fail, Partial, Unknown)
            details: Detailed validation results
        """
        self.add_module(module_name)
        self.modules[module_name]["interface_compliance"] = status
        if details:
            self.modules[module_name]["details"]["interface_compliance"] = details
        self._update_overall_status(module_name)
    
    def set_error_handling_status(self, module_name: str, status: str, details: Dict[str, Any] = None):
        """
        Set the error handling status for a module.
        
        Args:
            module_name: Name of the module
            status: Error handling status (Pass, Fail, Partial, Unknown)
            details: Detailed error handling results
        """
        self.add_module(module_name)
        self.modules[module_name]["error_handling"] = status
        if details:
            self.modules[module_name]["details"]["error_handling"] = details
        self._update_overall_status(module_name)
    
    def set_integration_status(self, module_name: str, status: str, details: Dict[str, Any] = None):
        """
        Set the integration test status for a module.
        
        Args:
            module_name: Name of the module
            status: Integration test status (Pass, Fail, Partial, Unknown)
            details: Detailed integration test results
        """
        self.add_module(module_name)
        self.modules[module_name]["integration_tests"] = status
        if details:
            self.modules[module_name]["details"]["integration_tests"] = details
        self._update_overall_status(module_name)
    
    def _update_overall_status(self, module_name: str):
        """
        Update the overall status for a module.
        
        Args:
            module_name: Name of the module
        """
        module = self.modules[module_name]
        statuses = [
            module["interface_compliance"],
            module["error_handling"],
            module["integration_tests"]
        ]
        
        if "Fail" in statuses:
            module["overall"] = "Fail"
        elif "Unknown" in statuses:
            module["overall"] = "Partial"
        else:
            module["overall"] = "Pass"
    
    def add_error(self, error: str):
        """
        Add an error message to the dashboard.
        
        Args:
            error: Error message
        """
        self.errors.append(error)
    
    def generate_dashboard(self) -> str:
        """
        Generate a dashboard report.
        
        Returns:
            str: Dashboard report in markdown format
        """
        report = []
        report.append("# Module Validation Dashboard")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.timestamp))}")
        report.append("")
        
        # Overall status
        overall_status = "Pass"
        for module in self.modules.values():
            if module["overall"] == "Fail":
                overall_status = "Fail"
                break
            elif module["overall"] == "Partial" and overall_status != "Fail":
                overall_status = "Partial"
        
        report.append(f"## Overall Status: {overall_status}")
        report.append("")
        
        # Module status
        report.append("## Module Status")
        report.append("")
        report.append("| Module | Interface Compliance | Error Handling | Integration Tests | Overall |")
        report.append("|--------|---------------------|---------------|-------------------|---------|")
        
        for module_name, module in sorted(self.modules.items()):
            report.append(f"| {module_name} | {module['interface_compliance']} | {module['error_handling']} | {module['integration_tests']} | {module['overall']} |")
        
        report.append("")
        
        # Error summary
        if self.errors:
            report.append("## Errors")
            report.append("")
            for error in self.errors:
                report.append(f"- {error}")
            report.append("")
        
        return "\n".join(report)
    
    def save_dashboard(self) -> str:
        """
        Save the dashboard report and data.
        
        Returns:
            str: Path to the saved dashboard report
        """
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Save dashboard report
        report = self.generate_dashboard()
        report_path = os.path.join(self.output_dir, "dashboard.md")
        with open(report_path, "w") as f:
            f.write(report)
        
        # Save dashboard data
        data = {
            "timestamp": self.timestamp,
            "modules": self.modules,
            "errors": self.errors
        }
        
        data_path = os.path.join(self.output_dir, f"dashboard_data_{int(self.timestamp)}.json")
        with open(data_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        # Also save as latest.json
        latest_path = os.path.join(self.output_dir, "latest.json")
        with open(latest_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        return report_path 