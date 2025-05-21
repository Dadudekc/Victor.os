"""
Integration Test Runner for Dream.OS
Executes all integration tests and generates a comprehensive report.
"""

import os
import sys
import json
import unittest
import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from dreamos.tests.integration.system_integration_test import TestSystemIntegration

def run_integration_tests() -> Dict:
    """Run all integration tests and return results."""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSystemIntegration)
    
    # Create test runner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Run tests
    results = runner.run(suite)
    
    # Generate report
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "total_tests": results.testsRun,
        "failures": len(results.failures),
        "errors": len(results.errors),
        "skipped": len(results.skipped),
        "success_rate": (results.testsRun - len(results.failures) - len(results.errors)) / results.testsRun * 100,
        "test_details": []
    }
    
    # Add test details
    for test, error in results.failures:
        report["test_details"].append({
            "name": str(test),
            "status": "FAILURE",
            "error": str(error)
        })
    
    for test, error in results.errors:
        report["test_details"].append({
            "name": str(test),
            "status": "ERROR",
            "error": str(error)
        })
    
    for test, reason in results.skipped:
        report["test_details"].append({
            "name": str(test),
            "status": "SKIPPED",
            "reason": str(reason)
        })
    
    return report

def save_report(report: Dict) -> str:
    """Save test report to file."""
    # Create reports directory
    reports_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'runtime', 'test_results')
    os.makedirs(reports_dir, exist_ok=True)
    
    # Generate report filename
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = os.path.join(reports_dir, f'integration_test_report_{timestamp}.json')
    
    # Save report
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report_file

def main():
    """Main entry point for integration test runner."""
    print("Starting Dream.OS Integration Tests...")
    
    try:
        # Run tests
        report = run_integration_tests()
        
        # Save report
        report_file = save_report(report)
        
        # Print summary
        print("\nIntegration Test Summary:")
        print(f"Total Tests: {report['total_tests']}")
        print(f"Failures: {report['failures']}")
        print(f"Errors: {report['errors']}")
        print(f"Skipped: {report['skipped']}")
        print(f"Success Rate: {report['success_rate']:.2f}%")
        print(f"\nDetailed report saved to: {report_file}")
        
        # Exit with appropriate code
        if report['failures'] > 0 or report['errors'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"Error running integration tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 