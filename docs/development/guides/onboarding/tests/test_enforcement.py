"""
Test script to verify agent compliance enforcement.
"""

import os
import json
import pytest
from pathlib import Path
from datetime import datetime
import tempfile

# Add project root to Python path
import sys
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.append(str(project_root))

from docs.development.guides.onboarding.utils.enforcement import check_agent_compliance, ComplianceError

# Test data
@pytest.fixture
def test_agent_dir(tmp_path):
    """Create a temporary agent directory with test files."""
    agent_dir = tmp_path / "agent-test-001"
    agent_dir.mkdir()
    
    # Create required files
    (agent_dir / "documentation.md").write_text("""
# Agent Documentation

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
""")
    
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
        json.dump(contract, f, indent=2)
    
    # Create protocol compliance file
    compliance = {
        "last_check": datetime.utcnow().isoformat(),
        "compliance_status": "compliant",
        "violations": []
    }
    with open(agent_dir / "protocol_compliance.json", 'w') as f:
        json.dump(compliance, f, indent=2)
    
    return agent_dir

def test_compliant_agent(test_agent_dir):
    """Test that a compliant agent passes checks."""
    result = check_agent_compliance(
        agent_id="test-001",
        base_path=str(test_agent_dir.parent),
        strict=True
    )
    assert result["compliant"] is True
    assert len(result["violations"]) == 0

def test_missing_directory():
    """Test that missing agent directory is caught."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = check_agent_compliance(
            agent_id="nonexistent-001",
            base_path=tmpdir,
            strict=False
        )
        assert result["compliant"] is False
        assert len(result["violations"]) == 1
        assert result["violations"][0]["type"] == "missing_directory"

def test_missing_required_file(test_agent_dir):
    """Test that missing required file is caught."""
    # Remove a required file
    os.remove(test_agent_dir / "documentation.md")
    
    result = check_agent_compliance(
        agent_id="test-001",
        base_path=str(test_agent_dir.parent),
        strict=False
    )
    assert result["compliant"] is False
    assert any(v["type"] == "missing_file" for v in result["violations"])

def test_strict_mode(test_agent_dir):
    """Test that strict mode raises exception."""
    # Remove a required file
    os.remove(test_agent_dir / "documentation.md")
    
    with pytest.raises(ComplianceError) as exc_info:
        check_agent_compliance(
            agent_id="test-001",
            base_path=str(test_agent_dir.parent),
            strict=True
        )
    assert len(exc_info.value.violations) > 0

def test_agent_1_compliance():
    """Test Agent-1's compliance using absolute path."""
    absolute_path = r"D:\Dream.os\runtime\agent_comms\agent_mailboxes\Agent-1"
    result = check_agent_compliance(
        agent_id="Agent-1",
        base_path=absolute_path,
        strict=False
    )
    print(f"\nAgent-1 Compliance Check Result:")
    print(f"Compliant: {result['compliant']}")
    if not result['compliant']:
        print("Violations:")
        for violation in result['violations']:
            print(f"- {violation['type']}: {violation['message']}")
    assert result["compliant"], f"Agent-1 failed onboarding compliance: {result['violations']}"

if __name__ == "__main__":
    # Run Agent-1 compliance check
    test_agent_1_compliance() 