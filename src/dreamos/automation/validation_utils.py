"""
DreamOS Validation Utilities
Provides tools for validating agent improvements and enhancements.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class ValidationStatus(Enum):
    """Status of a validation check."""
    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"
    ERROR = "error"

@dataclass
class ValidationResult:
    """Result of a validation check."""
    status: ValidationStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = datetime.utcnow().isoformat()

class ImprovementValidator:
    """Validates agent improvements and enhancements."""
    
    def __init__(self, state_dir: str = "runtime/state"):
        self.state_dir = state_dir
        self.validation_file = os.path.join(state_dir, "improvement_validations.json")
        self._load_state()

    def _load_state(self) -> None:
        """Load the current validation state."""
        if os.path.exists(self.validation_file):
            with open(self.validation_file, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = self._initialize_state()
            self._save_state()

    def _save_state(self) -> None:
        """Save the current validation state."""
        os.makedirs(os.path.dirname(self.validation_file), exist_ok=True)
        with open(self.validation_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def _initialize_state(self) -> Dict:
        """Initialize a new validation state."""
        return {
            "last_updated": datetime.utcnow().isoformat(),
            "validations": {},
            "metrics": {
                "total_validations": 0,
                "passed_validations": 0,
                "failed_validations": 0,
                "pending_validations": 0
            }
        }

    def validate_improvement(self, 
                           improvement_id: str,
                           tests: List[Dict[str, Any]],
                           documentation: Dict[str, Any],
                           implementation: Dict[str, Any],
                           demonstration: Dict[str, Any]) -> ValidationResult:
        """Validate an improvement against the required criteria."""
        
        # Initialize validation result
        validation = {
            "improvement_id": improvement_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": ValidationStatus.PENDING.value,
            "results": {
                "tests": self._validate_tests(tests),
                "documentation": self._validate_documentation(documentation),
                "implementation": self._validate_implementation(implementation),
                "demonstration": self._validate_demonstration(demonstration)
            }
        }

        # Determine overall status
        all_passed = all(
            result["status"] == ValidationStatus.PASSED.value
            for result in validation["results"].values()
        )

        validation["status"] = (
            ValidationStatus.PASSED.value if all_passed
            else ValidationStatus.FAILED.value
        )

        # Update state
        self.state["validations"][improvement_id] = validation
        self._update_metrics(validation["status"])
        self._save_state()

        return ValidationResult(
            status=ValidationStatus(validation["status"]),
            message="Validation complete",
            details=validation
        )

    def _validate_tests(self, tests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate test coverage and results."""
        return {
            "status": ValidationStatus.PASSED.value if tests else ValidationStatus.FAILED.value,
            "message": "Tests validated" if tests else "No tests provided",
            "details": {
                "test_count": len(tests),
                "test_results": tests
            }
        }

    def _validate_documentation(self, documentation: Dict[str, Any]) -> Dict[str, Any]:
        """Validate documentation completeness."""
        required_fields = ["description", "usage_examples", "api_changes"]
        missing_fields = [field for field in required_fields if field not in documentation]
        
        return {
            "status": (
                ValidationStatus.PASSED.value if not missing_fields
                else ValidationStatus.FAILED.value
            ),
            "message": (
                "Documentation complete" if not missing_fields
                else f"Missing fields: {', '.join(missing_fields)}"
            ),
            "details": documentation
        }

    def _validate_implementation(self, implementation: Dict[str, Any]) -> Dict[str, Any]:
        """Validate implementation completeness."""
        required_fields = ["code", "dependencies", "error_handling"]
        missing_fields = [field for field in required_fields if field not in implementation]
        
        return {
            "status": (
                ValidationStatus.PASSED.value if not missing_fields
                else ValidationStatus.FAILED.value
            ),
            "message": (
                "Implementation complete" if not missing_fields
                else f"Missing fields: {', '.join(missing_fields)}"
            ),
            "details": implementation
        }

    def _validate_demonstration(self, demonstration: Dict[str, Any]) -> Dict[str, Any]:
        """Validate demonstration evidence."""
        required_fields = ["evidence", "performance_metrics", "error_handling"]
        missing_fields = [field for field in required_fields if field not in demonstration]
        
        return {
            "status": (
                ValidationStatus.PASSED.value if not missing_fields
                else ValidationStatus.FAILED.value
            ),
            "message": (
                "Demonstration complete" if not missing_fields
                else f"Missing fields: {', '.join(missing_fields)}"
            ),
            "details": demonstration
        }

    def _update_metrics(self, status: str) -> None:
        """Update validation metrics."""
        self.state["metrics"]["total_validations"] += 1
        if status == ValidationStatus.PASSED.value:
            self.state["metrics"]["passed_validations"] += 1
        elif status == ValidationStatus.FAILED.value:
            self.state["metrics"]["failed_validations"] += 1
        else:
            self.state["metrics"]["pending_validations"] += 1

    def get_validation_status(self, improvement_id: str) -> Optional[Dict[str, Any]]:
        """Get the validation status for an improvement."""
        return self.state["validations"].get(improvement_id)

    def get_metrics(self) -> Dict[str, Any]:
        """Get the current validation metrics."""
        return self.state["metrics"]

def validate_task_completion(task_data: Dict[str, Any]) -> ValidationResult:
    """Wrapper for task validation used in test cases and agent completion checks.
    Calls the internal improvement validator.

    Args:
        task_data: Task details with keys: 'tests', 'documentation', 'implementation', 'demonstration'

    Returns:
        ValidationResult: Validation results with status and details
    """
    validator = ImprovementValidator()
    return validator.validate_improvement(
        improvement_id=task_data.get("task_id", "unknown"),
        tests=task_data.get("tests", []),
        documentation=task_data.get("documentation", {}),
        implementation=task_data.get("implementation", {}),
        demonstration=task_data.get("demonstration", {})
    ) 