"""
Test suite for Dream.OS ethos validation.

This module contains tests to ensure that agents and actions comply with
the Dream.OS ethos principles and operational guidelines.
"""

from datetime import datetime
from typing import Dict, List

import pytest

from dreamos.core.ethos_validator import EthosValidator


@pytest.fixture
def validator():
    """Create a fresh validator instance for each test."""
    return EthosValidator()

@pytest.fixture
def sample_action():
    """Create a sample action that complies with ethos."""
    return {
        "type": "decision",
        "context": {
            "user_state": "active",
            "environment": "development",
            "history": ["previous_action"]
        },
        "impact": "low",
        "confidence": 0.9,
        "human_approval": True
    }

@pytest.fixture
def sample_behavior_log():
    """Create a sample behavior log for testing."""
    return [
        {
            "type": "decision",
            "context": {
                "user_state": "active",
                "environment": "development",
                "history": []
            },
            "impact": "low",
            "confidence": 0.9,
            "human_approval": True
        },
        {
            "type": "data_access",
            "context": {
                "user_state": "active",
                "environment": "development",
                "history": ["previous_action"]
            },
            "impact": "medium",
            "confidence": 0.8,
            "privacy_check": True,
            "consent_verified": True
        }
    ]

def test_validator_initialization(validator):
    """Test that validator initializes correctly."""
    assert validator.ethos is not None
    assert "version" in validator.ethos
    assert "core_values" in validator.ethos

def test_validate_action_compliant(validator, sample_action):
    """Test validation of a compliant action."""
    assert validator.validate_action(sample_action)
    assert len(validator.violations) == 0

def test_validate_action_non_compliant(validator):
    """Test validation of a non-compliant action."""
    action = {
        "type": "decision",
        "context": {},
        "impact": "high",
        "confidence": 0.9
    }
    assert not validator.validate_action(action)
    assert len(validator.violations) > 0

def test_validate_agent_behavior(validator, sample_behavior_log):
    """Test validation of a sequence of behaviors."""
    results = validator.validate_agent_behavior(sample_behavior_log)
    assert results["total_actions"] == len(sample_behavior_log)
    assert results["compliant_actions"] > 0
    assert "compliance_rate" in results

def test_generate_compliance_report(validator, sample_behavior_log):
    """Test generation of compliance report."""
    report = validator.generate_compliance_report(sample_behavior_log)
    assert "Dream.OS Ethos Compliance Report" in report
    assert "Total Actions" in report
    assert "Compliance Rate" in report

def test_check_ethos_alignment(validator):
    """Test checking agent state alignment with ethos."""
    agent_state = {
        "compassion_metrics": {"empathy_score": 0.8},
        "clarity_metrics": {"communication_score": 0.9},
        "collaboration_metrics": {"teamwork_score": 0.85},
        "adaptability_metrics": {"flexibility_score": 0.75}
    }
    alignment = validator.check_ethos_alignment(agent_state)
    assert "metrics" in alignment
    assert "recommendations" in alignment
    assert "timestamp" in alignment

def test_human_centricity_check(validator):
    """Test human-centricity principle validation."""
    # High confidence without human approval
    action = {
        "type": "decision",
        "confidence": 0.9
    }
    assert not validator._check_human_centricity(action)
    
    # Low confidence action
    action["confidence"] = 0.7
    assert validator._check_human_centricity(action)
    
    # Action with human approval
    action["confidence"] = 0.9
    action["human_approval"] = True
    assert validator._check_human_centricity(action)

def test_context_awareness_check(validator):
    """Test context awareness validation."""
    # Missing required context
    action = {
        "type": "action",
        "context": {}
    }
    assert not validator._check_context_awareness(action)
    
    # Complete context
    action["context"] = {
        "user_state": "active",
        "environment": "development",
        "history": []
    }
    assert validator._check_context_awareness(action)

def test_uncertainty_handling_check(validator):
    """Test uncertainty handling validation."""
    # High confidence action
    action = {
        "type": "action",
        "confidence": 0.9
    }
    assert validator._check_uncertainty_handling(action)
    
    # Low confidence without fallback
    action["confidence"] = 0.6
    assert not validator._check_uncertainty_handling(action)
    
    # Low confidence with fallback
    action["fallback_plan"] = True
    action["human_escalation"] = True
    assert validator._check_uncertainty_handling(action)

def test_ethical_boundaries_check(validator):
    """Test ethical boundaries validation."""
    # Data access without privacy check
    action = {
        "type": "data_access",
        "consent_verified": True
    }
    assert not validator._check_ethical_boundaries(action)
    
    # Data access with privacy check
    action["privacy_check"] = True
    assert validator._check_ethical_boundaries(action)
    
    # Non-data access action
    action["type"] = "other"
    assert validator._check_ethical_boundaries(action)

def test_value_alignment_calculation(validator):
    """Test calculation of value alignment scores."""
    agent_state = {
        "compassion_metrics": {"empathy_score": 0.8},
        "clarity_metrics": {"communication_score": 0.9},
        "collaboration_metrics": {"teamwork_score": 0.85},
        "adaptability_metrics": {"flexibility_score": 0.75}
    }
    
    for value in ["compassion", "clarity", "collaboration", "adaptability"]:
        score = validator._calculate_value_alignment(agent_state, value)
        assert isinstance(score, float)
        assert 0 <= score <= 1

def test_ethos_structure_validation(validator):
    """Test validation of ethos structure."""
    # Valid structure
    valid_ethos = {
        "version": "1.0.0",
        "last_updated": datetime.now().isoformat(),
        "core_mission": {},
        "core_values": {},
        "operational_principles": {},
        "safeguards": {},
        "system_behavior": {},
        "legacy_commitment": {}
    }
    validator._validate_ethos_structure(valid_ethos)
    
    # Invalid structure
    invalid_ethos = {
        "version": "1.0.0",
        "last_updated": datetime.now().isoformat()
    }
    with pytest.raises(ValueError):
        validator._validate_ethos_structure(invalid_ethos) 