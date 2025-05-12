"""
Unit tests for Dream.os onboarding utilities.
Tests validation, compliance checking, and documentation verification.
"""

import os
import json
import yaml
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from ..utils.onboarding_utils import OnboardingValidator, generate_onboarding_report
from ..utils.protocol_compliance import ProtocolComplianceChecker
from ..utils.validation_utils import DocumentationValidator

# Test data
@pytest.fixture
def test_agent_data():
    return {
        "initialization": ["system_checks", "contract_verification"],
        "protocol_compliance": ["regular_checks", "updates_reviewed"],
        "documentation": ["activities_documented", "format_followed"],
        "security": ["authentication_completed", "access_controls_implemented"],
        "operational": ["monitoring_established", "error_handling_implemented"]
    }

@pytest.fixture
def test_agent_dir(tmp_path):
    """Create a temporary agent directory with test files."""
    agent_dir = tmp_path / "agent-test-001"
    agent_dir.mkdir()
    
    # Create onboarding contract
    contract = {
        "agent_id": "test-001",
        "protocol_version": "1.0.0",
        "compliance_checks": [
            "initialization_complete",
            "protocol_compliance_verified"
        ],
        "documentation_requirements": [
            "overview_section",
            "protocol_compliance_section"
        ]
    }
    with open(agent_dir / "onboarding_contract.yaml", 'w') as f:
        yaml.dump(contract, f)
    
    # Create protocol compliance file
    compliance = {
        "last_check": datetime.utcnow().isoformat(),
        "compliance_status": "pending",
        "violations": []
    }
    with open(agent_dir / "protocol_compliance.json", 'w') as f:
        json.dump(compliance, f)
    
    # Create documentation
    doc_content = """# Agent Documentation

## Overview
Test agent for validation.

## Protocol Compliance
- [x] Initialization complete
- [x] Protocol compliance verified

## Documentation
- [x] Overview section
- [x] Protocol compliance section

## Security
- [x] Authentication completed
- [x] Authorization levels verified

## Operational Status
- [x] Monitoring established
- [x] Error handling implemented

## Version
- v1.0.0

## Timestamp
- 2024-03-20T00:00:00Z
"""
    with open(agent_dir / "documentation.md", 'w') as f:
        f.write(doc_content)
    
    return agent_dir

class TestOnboardingValidator:
    """Test suite for OnboardingValidator."""
    
    def test_validate_agent(self, test_agent_data):
        validator = OnboardingValidator("docs/development/guides/onboarding/protocols")
        results = validator.validate_agent("test-001", test_agent_data)
        
        assert isinstance(results, dict)
        assert all(isinstance(v, bool) for v in results.values())
        assert all(results.values())  # All checks should pass
    
    def test_generate_report(self, test_agent_data):
        validator = OnboardingValidator("docs/development/guides/onboarding/protocols")
        results = validator.validate_agent("test-001", test_agent_data)
        report = generate_onboarding_report("test-001", results)
        
        assert isinstance(report, str)
        assert "test-001" in report
        assert all(category in report for category in results.keys())

class TestProtocolComplianceChecker:
    """Test suite for ProtocolComplianceChecker."""
    
    def test_check_agent(self, test_agent_dir):
        checker = ProtocolComplianceChecker("docs/development/guides/onboarding")
        results = checker.check_agent(test_agent_dir)
        
        assert isinstance(results, dict)
        assert "timestamp" in results
        assert "checks" in results
        assert all(isinstance(v, dict) for v in results["checks"].values())
    
    def test_check_required_files(self, test_agent_dir):
        checker = ProtocolComplianceChecker("docs/development/guides/onboarding")
        results = checker._check_required_files(test_agent_dir)
        
        assert isinstance(results, dict)
        assert all(isinstance(v, bool) for v in results.values())
        assert all(results.values())  # All files should exist
    
    def test_validate_contract(self, test_agent_dir):
        checker = ProtocolComplianceChecker("docs/development/guides/onboarding")
        with open(test_agent_dir / "onboarding_contract.yaml") as f:
            contract = yaml.safe_load(f)
        
        assert checker._validate_contract(contract)
    
    def test_validate_compliance(self, test_agent_dir):
        checker = ProtocolComplianceChecker("docs/development/guides/onboarding")
        with open(test_agent_dir / "protocol_compliance.json") as f:
            compliance = json.load(f)
        
        assert checker._validate_compliance(compliance)

class TestDocumentationValidator:
    """Test suite for DocumentationValidator."""
    
    def test_validate_documentation(self, test_agent_dir):
        validator = DocumentationValidator("docs/development/guides/onboarding")
        results = validator.validate_documentation(test_agent_dir / "documentation.md")
        
        assert isinstance(results, dict)
        assert "timestamp" in results
        assert "checks" in results
        assert all(isinstance(v, dict) for v in results["checks"].values())
    
    def test_check_required_sections(self, test_agent_dir):
        validator = DocumentationValidator("docs/development/guides/onboarding")
        with open(test_agent_dir / "documentation.md") as f:
            content = f.read()
        
        results = validator._check_required_sections(content)
        assert isinstance(results, dict)
        assert all(isinstance(v, bool) for v in results.values())
        assert all(results.values())  # All sections should be present
    
    def test_check_version_info(self, test_agent_dir):
        validator = DocumentationValidator("docs/development/guides/onboarding")
        with open(test_agent_dir / "documentation.md") as f:
            content = f.read()
        
        assert validator._check_version_info(content)
    
    def test_check_timestamp(self, test_agent_dir):
        validator = DocumentationValidator("docs/development/guides/onboarding")
        with open(test_agent_dir / "documentation.md") as f:
            content = f.read()
        
        assert validator._check_timestamp(content)

def test_noncompliant_agent(tmp_path):
    """Test handling of noncompliant agent data."""
    validator = OnboardingValidator("docs/development/guides/onboarding/protocols")
    noncompliant_data = {
        "initialization": [],  # Missing required checks
        "protocol_compliance": ["regular_checks"],
        "documentation": ["activities_documented"],
        "security": ["authentication_completed"],
        "operational": ["monitoring_established"]
    }
    
    results = validator.validate_agent("noncompliant-001", noncompliant_data)
    assert not all(results.values())  # Some checks should fail

def test_drift_behavior(tmp_path):
    """Test detection of protocol drift."""
    checker = ProtocolComplianceChecker("docs/development/guides/onboarding")
    
    # Create agent with outdated protocol version
    agent_dir = tmp_path / "agent-drift-001"
    agent_dir.mkdir()
    
    contract = {
        "agent_id": "drift-001",
        "protocol_version": "0.9.0",  # Outdated version
        "compliance_checks": ["initialization_complete"],
        "documentation_requirements": ["overview_section"]
    }
    
    with open(agent_dir / "onboarding_contract.yaml", 'w') as f:
        yaml.dump(contract, f)
    
    results = checker.check_agent(agent_dir)
    assert not all(v for v in results["checks"]["protocol_compliance"].values())

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 