"""
Tests for the DreamOS Promotion System.
"""

import json
import os
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from dreamos.automation.promotion import PromotionSystem
from dreamos.core.config import AppConfig
from dreamos.core.coordination.base_agent import BaseAgent


@pytest.fixture
def promotion_system(tmp_path):
    """Create a PromotionSystem instance with a temporary directory."""
    state_dir = str(tmp_path / "state")
    return PromotionSystem(state_dir=state_dir)

def test_initialization(promotion_system):
    """Test that the promotion system initializes correctly."""
    # Check that the state file was created
    assert os.path.exists(promotion_system.scores_file)
    
    # Load the state and verify its structure
    with open(promotion_system.scores_file, 'r') as f:
        state = json.load(f)
    
    assert "episode" in state
    assert "agents" in state
    assert "JARVIS" in state["agents"]
    assert "ORCHESTRATOR" in state["agents"]
    assert "VALIDATOR" in state["agents"]

def test_award_points(promotion_system):
    """Test awarding points to an agent."""
    # Award points to JARVIS
    success = promotion_system.award_points(
        agent="JARVIS",
        category="task_completion",
        points=50,
        reason="Completed core architecture task"
    )
    
    assert success
    
    # Verify the points were awarded
    jarvis_status = promotion_system.get_agent_status("JARVIS")
    assert jarvis_status["points"]["task_completion"] == 50
    assert jarvis_status["points"]["total"] == 50
    
    # Verify the history was updated
    assert len(jarvis_status["history"]) == 1
    history_entry = jarvis_status["history"][0]
    assert history_entry["category"] == "task_completion"
    assert history_entry["points"] == 50
    assert history_entry["reason"] == "Completed core architecture task"

def test_promotion_eligibility(promotion_system):
    """Test promotion eligibility checking."""
    # Award enough points for promotion
    promotion_system.award_points(
        agent="JARVIS",
        category="task_completion",
        points=1000,
        reason="Achieved promotion threshold"
    )
    
    # Check promotion eligibility
    jarvis_status = promotion_system.get_agent_status("JARVIS")
    assert jarvis_status["promotion_metrics"]["eligible_for_promotion"]

def test_update_streak(promotion_system):
    """Test updating an agent's streak."""
    # Update JARVIS's streak
    promotion_system.update_streak("JARVIS", 24)
    
    # Verify the streak was updated
    jarvis_status = promotion_system.get_agent_status("JARVIS")
    assert jarvis_status["promotion_metrics"]["current_streak"] == 24
    assert jarvis_status["promotion_metrics"]["highest_streak"] == 24
    
    # Update to a lower streak
    promotion_system.update_streak("JARVIS", 12)
    jarvis_status = promotion_system.get_agent_status("JARVIS")
    assert jarvis_status["promotion_metrics"]["current_streak"] == 12
    assert jarvis_status["promotion_metrics"]["highest_streak"] == 24

def test_invalid_agent(promotion_system):
    """Test handling of invalid agent names."""
    # Try to award points to a non-existent agent
    success = promotion_system.award_points(
        agent="NONEXISTENT",
        category="task_completion",
        points=50,
        reason="Test"
    )
    assert not success
    
    # Try to get status of a non-existent agent
    status = promotion_system.get_agent_status("NONEXISTENT")
    assert status is None 