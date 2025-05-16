"""
Tests for the DreamOS Validation Utilities.
"""

import json
import os
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from dreamos.automation.validation_utils import (
    ImprovementValidator,
    ValidationResult,
    ValidationStatus,
    validate_task_completion,
)


@pytest.fixture
def validator(tmp_path):
    """Create an ImprovementValidator instance with a temporary directory."""
    return ImprovementValidator(state_dir=str(tmp_path))

def test_initialization(validator):
    """Test that the validator initializes correctly."""
    # Check that the validation file was created
    assert os.path.exists(validator.validation_file)
    
    # Load the state and verify its structure
    with open(validator.validation_file, 'r') as f:
        state = json.load(f)
    
    assert "last_updated" in state
    assert "validations" in state
    assert "metrics" in state
    assert state["metrics"]["total_validations"] == 0

def test_validate_improvement(validator):
    """Test validating an improvement."""
    # Prepare test data
    improvement_id = "test_improvement_001"
    tests = [
        {
            "name": "test_feature",
            "status": "passed",
            "details": "Feature works as expected"
        }
    ]
    documentation = {
        "description": "Test feature description",
        "usage_examples": ["example1", "example2"],
        "api_changes": "No API changes"
    }
    implementation = {
        "code": "def test_feature(): pass",
        "dependencies": [],
        "error_handling": "try/except blocks implemented"
    }
    demonstration = {
        "evidence": "Screenshots and logs",
        "performance_metrics": {"latency": "100ms"},
        "error_handling": "Error cases handled"
    }

    # Validate the improvement
    result = validator.validate_improvement(
        improvement_id=improvement_id,
        tests=tests,
        documentation=documentation,
        implementation=implementation,
        demonstration=demonstration
    )

    # Verify the result
    assert result.status == ValidationStatus.PASSED
    assert result.message == "Validation complete"
    assert result.details["improvement_id"] == improvement_id
    assert result.details["status"] == ValidationStatus.PASSED.value

    # Verify metrics were updated
    metrics = validator.get_metrics()
    assert metrics["total_validations"] == 1
    assert metrics["passed_validations"] == 1
    assert metrics["failed_validations"] == 0

def test_validate_incomplete_improvement(validator):
    """Test validating an incomplete improvement."""
    # Prepare test data with missing fields
    improvement_id = "test_improvement_002"
    tests = []  # No tests
    documentation = {
        "description": "Test feature description"
        # Missing usage_examples and api_changes
    }
    implementation = {
        "code": "def test_feature(): pass"
        # Missing dependencies and error_handling
    }
    demonstration = {
        "evidence": "Screenshots and logs"
        # Missing performance_metrics and error_handling
    }

    # Validate the improvement
    result = validator.validate_improvement(
        improvement_id=improvement_id,
        tests=tests,
        documentation=documentation,
        implementation=implementation,
        demonstration=demonstration
    )

    # Verify the result
    assert result.status == ValidationStatus.FAILED
    assert result.message == "Validation complete"
    assert result.details["improvement_id"] == improvement_id
    assert result.details["status"] == ValidationStatus.FAILED.value

    # Verify metrics were updated
    metrics = validator.get_metrics()
    assert metrics["total_validations"] == 1
    assert metrics["passed_validations"] == 0
    assert metrics["failed_validations"] == 1

def test_get_validation_status(validator):
    """Test retrieving validation status."""
    # First validate an improvement
    improvement_id = "test_improvement_003"
    tests = [{"name": "test", "status": "passed"}]
    documentation = {
        "description": "Test",
        "usage_examples": ["example"],
        "api_changes": "None"
    }
    implementation = {
        "code": "pass",
        "dependencies": [],
        "error_handling": "None"
    }
    demonstration = {
        "evidence": "None",
        "performance_metrics": {},
        "error_handling": "None"
    }

    validator.validate_improvement(
        improvement_id=improvement_id,
        tests=tests,
        documentation=documentation,
        implementation=implementation,
        demonstration=demonstration
    )

    # Get the validation status
    status = validator.get_validation_status(improvement_id)
    assert status is not None
    assert status["improvement_id"] == improvement_id
    assert status["status"] == ValidationStatus.PASSED.value

    # Try to get status for non-existent improvement
    status = validator.get_validation_status("non_existent")
    assert status is None 