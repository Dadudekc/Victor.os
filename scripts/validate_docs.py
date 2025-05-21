#!/usr/bin/env python3
"""
Dream.OS Documentation Validation Script

Runs the documentation validator and reports results.
"""

import sys
import os
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.append(str(src_path))

from dreamos.tools.validation.doc_validator import DocValidator

def main():
    """Main entry point for documentation validation."""
    print("Running Dream.OS Documentation Validation...")
    
    # Initialize validator
    validator = DocValidator()
    
    # Run validation
    results = validator.validate_all()
    
    # Generate and print report
    report = validator.generate_report(results)
    print("\n" + report)
    
    # Write report to file
    report_path = Path("runtime/validation/docs_validation_report.txt")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    
    # Exit with appropriate status
    if results["missing_files"] or any(issues["errors"] for issues in results["file_issues"].values()):
        print("\nValidation failed. See report for details.")
        sys.exit(1)
    else:
        print("\nValidation passed successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main() 