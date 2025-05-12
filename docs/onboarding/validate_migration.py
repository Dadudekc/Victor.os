#!/usr/bin/env python3
"""
Dream.OS Onboarding Migration Validator
Validates the migration spec against current repo state and performs pre-flight checks.
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_validation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Results from a single validation check."""
    passed: bool
    message: str
    details: Optional[Dict] = None

class MigrationValidator:
    """Validates the migration specification against the current repository state."""
    
    def __init__(self, spec_path: str = "docs/onboarding/migration_spec.yaml"):
        self.spec_path = Path(spec_path)
        self.repo_root = Path.cwd()
        self.spec = self._load_spec()
        self.results: List[ValidationResult] = []
        
    def _load_spec(self) -> Dict:
        """Load and parse the migration specification YAML."""
        try:
            with open(self.spec_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load migration spec: {e}")
            sys.exit(1)

    def validate_file_exists(self, path: str) -> bool:
        """Check if a file exists in the repository."""
        return (self.repo_root / path).exists()

    def validate_directory_structure(self) -> ValidationResult:
        """Validate that all required directories exist."""
        required_dirs = self.spec['structure'].keys()
        missing_dirs = []
        
        for dir_name in required_dirs:
            dir_path = self.repo_root / "docs/onboarding" / dir_name
            if not dir_path.exists():
                missing_dirs.append(str(dir_path))
        
        return ValidationResult(
            passed=len(missing_dirs) == 0,
            message="Directory structure validation",
            details={"missing_dirs": missing_dirs} if missing_dirs else None
        )

    def validate_source_files(self) -> ValidationResult:
        """Validate that all source files exist before migration."""
        missing_files = []
        
        for migration in self.spec['migrations']:
            if not self.validate_file_exists(migration['source']):
                missing_files.append(migration['source'])
        
        return ValidationResult(
            passed=len(missing_files) == 0,
            message="Source files validation",
            details={"missing_files": missing_files} if missing_files else None
        )

    def validate_dependencies(self) -> ValidationResult:
        """Validate that all dependencies are present and consistent."""
        issues = []
        
        for dep in self.spec['dependencies']:
            existing_locations = [
                loc for loc in dep['locations']
                if self.validate_file_exists(loc)
            ]
            
            if not existing_locations:
                issues.append(f"No instances found for {dep['name']}")
            elif len(existing_locations) > 1 and dep['status'] == 'consolidation_needed':
                issues.append(f"Multiple versions of {dep['name']} need consolidation")
        
        return ValidationResult(
            passed=len(issues) == 0,
            message="Dependencies validation",
            details={"issues": issues} if issues else None
        )

    def validate_import_paths(self) -> ValidationResult:
        """Validate that import paths can be updated correctly."""
        import_issues = []
        
        for migration in self.spec['migrations']:
            if migration['source'].endswith('.py'):
                try:
                    with open(self.repo_root / migration['source'], 'r') as f:
                        content = f.read()
                        if 'import' in content or 'from' in content:
                            # Basic check for import statements
                            if not any(pkg in content for pkg in ['docs.onboarding', 'dreamos']):
                                import_issues.append(f"Potential import path issues in {migration['source']}")
                except Exception as e:
                    import_issues.append(f"Failed to check imports in {migration['source']}: {e}")
        
        return ValidationResult(
            passed=len(import_issues) == 0,
            message="Import paths validation",
            details={"issues": import_issues} if import_issues else None
        )

    def run_all_checks(self) -> bool:
        """Run all validation checks and return overall status."""
        checks = [
            self.validate_directory_structure,
            self.validate_source_files,
            self.validate_dependencies,
            self.validate_import_paths
        ]
        
        all_passed = True
        for check in checks:
            result = check()
            self.results.append(result)
            if not result.passed:
                all_passed = False
                logger.warning(f"Check failed: {result.message}")
                if result.details:
                    logger.warning(f"Details: {result.details}")
            else:
                logger.info(f"Check passed: {result.message}")
        
        return all_passed

    def generate_report(self) -> str:
        """Generate a detailed validation report."""
        report = [
            f"Migration Validation Report - {datetime.now().isoformat()}",
            "=" * 50,
            f"Specification: {self.spec_path}",
            f"Repository: {self.repo_root}",
            "\nValidation Results:",
            "-" * 30
        ]
        
        for result in self.results:
            status = "✅ PASSED" if result.passed else "❌ FAILED"
            report.append(f"\n{status} - {result.message}")
            if result.details:
                report.append("Details:")
                for key, value in result.details.items():
                    report.append(f"  {key}:")
                    for item in value:
                        report.append(f"    - {item}")
        
        return "\n".join(report)

def main():
    """Main entry point for the validator."""
    validator = MigrationValidator()
    
    logger.info("Starting migration validation...")
    if validator.run_all_checks():
        logger.info("All validation checks passed!")
    else:
        logger.error("Validation failed! See details below.")
    
    # Generate and save report
    report = validator.generate_report()
    with open('migration_validation_report.txt', 'w') as f:
        f.write(report)
    
    logger.info("Validation report generated: migration_validation_report.txt")
    
    # Exit with appropriate status code
    sys.exit(0 if validator.run_all_checks() else 1)

if __name__ == "__main__":
    main() 