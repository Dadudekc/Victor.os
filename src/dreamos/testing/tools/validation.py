"""
Validation utilities for Dream.OS testing.

This module provides verification and validation tools for testing
Dream.OS components and ensuring they meet operational requirements.
"""

import os
import sys
import time
from dreamos.testing.tools.reliability import ToolReliabilityTester

def run_basic_validation(base_path=None):
    """
    Run a basic validation check on the Dream.OS environment.
    
    This function performs a series of basic validation checks to ensure
    the Dream.OS environment is functioning correctly.
    
    Args:
        base_path (str, optional): Base path to use for testing. 
                                  Defaults to current directory.
    
    Returns:
        dict: Validation results
    """
    results = {
        "timestamp": time.time(),
        "success": True,
        "components": {}
    }
    
    base_path = base_path or os.getcwd()
    
    # Tool reliability validation
    reliability_tester = ToolReliabilityTester()
    try:
        reliability_results = reliability_tester.run_comprehensive_test(base_path=base_path)
        
        # Calculate overall success rate
        read_success = 0
        read_total = 0
        list_success = 0
        list_total = 0
        
        for path, result in reliability_results["read_file"]["standard"].items():
            read_success += result["success_count"]
            read_total += result["success_count"] + result["failure_count"]
        
        for path, result in reliability_results["list_dir"]["standard"].items():
            list_success += result["success_count"]
            list_total += result["success_count"] + result["failure_count"]
        
        # Set validation status
        if read_total > 0 and list_total > 0:
            read_rate = read_success / read_total
            list_rate = list_success / list_total
            
            results["components"]["tool_reliability"] = {
                "success": read_rate >= 0.95 and list_rate >= 0.95,
                "read_success_rate": read_rate * 100,
                "list_success_rate": list_rate * 100,
                "details": "Tool reliability validation completed"
            }
            
            if read_rate < 0.95 or list_rate < 0.95:
                results["success"] = False
        else:
            results["components"]["tool_reliability"] = {
                "success": False,
                "details": "No files or directories available for testing"
            }
            results["success"] = False
    except Exception as e:
        results["components"]["tool_reliability"] = {
            "success": False,
            "details": f"Error running tool reliability tests: {str(e)}"
        }
        results["success"] = False
    
    # Additional validations would be added here
    
    return results

def generate_validation_report(results):
    """
    Generate a human-readable validation report.
    
    Args:
        results (dict): Validation results from run_basic_validation
    
    Returns:
        str: Human-readable validation report
    """
    report = []
    report.append("# Dream.OS Validation Report")
    report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(results['timestamp']))}")
    report.append(f"Overall Status: {'PASS' if results['success'] else 'FAIL'}\n")
    
    for component, data in results["components"].items():
        report.append(f"## {component.replace('_', ' ').title()}")
        report.append(f"Status: {'PASS' if data['success'] else 'FAIL'}")
        
        if component == "tool_reliability" and "read_success_rate" in data:
            report.append(f"- Read operation success rate: {data['read_success_rate']:.2f}%")
            report.append(f"- List operation success rate: {data['list_success_rate']:.2f}%")
        
        if "details" in data:
            report.append(f"Details: {data['details']}")
        
        report.append("")
    
    return "\n".join(report)

def main():
    """Run validation as a standalone script."""
    base_path = sys.argv[1] if len(sys.argv) > 1 else None
    results = run_basic_validation(base_path)
    report = generate_validation_report(results)
    print(report)
    return 0 if results["success"] else 1

if __name__ == "__main__":
    sys.exit(main()) 