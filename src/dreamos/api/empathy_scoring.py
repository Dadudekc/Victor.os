"""
Empathy Scoring API module for FastAPI integration.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
import logging

from ..core.empathy_scoring import EmpathyScorer, EmpathyScore

# Initialize router
router = APIRouter(prefix="/api/empathy", tags=["empathy"])

# Initialize scorer
scorer = EmpathyScorer()

# Global score cache
score_cache: Dict[str, Any] = {}

# Setup logging
logger = logging.getLogger(__name__)


@router.get("/scores")
async def get_agent_scores(force_update: bool = Query(False, alias="force_update")):
    """Get scores for all agents."""
    try:
        if force_update:
            update_score_cache(force=True)
        
        # Return cached scores
        scores = []
        for agent_id, score_data in score_cache.items():
            scores.append({
                "agent_id": agent_id,
                "score": score_data.get("score", 0.0),
                "status": score_data.get("status", "unknown"),
                "timestamp": score_data.get("timestamp", datetime.utcnow().isoformat())
            })
        
        return scores
    except Exception as e:
        logger.error(f"Error getting agent scores: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/scores/{agent_id}")
async def get_agent_score(agent_id: str, days: int = Query(30, ge=1, le=365)):
    """Get score for a specific agent."""
    try:
        # Check cache first
        if agent_id in score_cache:
            return score_cache[agent_id]
        
        # Calculate score if not in cache
        score_data = scorer.calculate_agent_score(agent_id, days)
        score_cache[agent_id] = score_data
        return score_data
    except Exception as e:
        logger.error(f"Error getting score for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/comparison")
async def get_agent_comparison():
    """Get agent comparison data."""
    try:
        update_score_cache()
        comparison_data = scorer.get_agent_comparisons()
        return comparison_data
    except Exception as e:
        logger.error(f"Error getting agent comparison: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/recalculate/{agent_id}")
async def recalculate_agent_score(agent_id: str):
    """Recalculate score for a specific agent."""
    try:
        # Remove from cache to force recalculation
        if agent_id in score_cache:
            del score_cache[agent_id]
        
        # Calculate new score
        score_data = scorer.calculate_agent_score(agent_id)
        score_cache[agent_id] = score_data
        
        return {
            "agent_id": agent_id,
            "message": "Score recalculated successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error recalculating score for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/threshold-status")
async def get_threshold_status():
    """Get system threshold status."""
    try:
        update_score_cache()
        
        # Calculate system status
        all_scores = list(score_cache.values())
        if not all_scores:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "No data",
                "average_score": 0.0,
                "agents_below_threshold": 0,
                "critical_agents": 0
            }
        
        average_score = sum(score.get("score", 0) for score in all_scores) / len(all_scores)
        agents_below_threshold = sum(1 for score in all_scores if score.get("score", 0) < 0.7)
        critical_agents = sum(1 for score in all_scores if score.get("score", 0) < 0.5)
        
        status = "Healthy" if average_score >= 0.8 else "Warning" if average_score >= 0.6 else "Critical"
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            "average_score": average_score,
            "agents_below_threshold": agents_below_threshold,
            "critical_agents": critical_agents
        }
    except Exception as e:
        logger.error(f"Error getting threshold status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def update_score_cache(force: bool = False):
    """Update the score cache."""
    try:
        if force or not score_cache:
            # Calculate scores for all agents
            all_scores = scorer.calculate_all_agent_scores()
            score_cache.clear()
            score_cache.update(all_scores)
            logger.info(f"Updated score cache with {len(all_scores)} agents")
    except Exception as e:
        logger.error(f"Error updating score cache: {e}")


# Add missing methods to EmpathyScorer for API compatibility
def calculate_agent_score(self, agent_id: str, days: int = 30) -> Dict[str, Any]:
    """Calculate score for a specific agent (API compatibility method)."""
    # This is a placeholder - the actual implementation would be more complex
    return {
        "agent_id": agent_id,
        "score": 0.85,  # Placeholder score
        "status": "proficient",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {"violations": 0, "compliances": 10},
        "value_scores": {"compassion": 0.9, "clarity": 0.85},
        "weighted_components": {"core_values": 0.87, "frequency": 0.84}
    }


def calculate_all_agent_scores(self) -> Dict[str, Any]:
    """Calculate scores for all agents (API compatibility method)."""
    # This is a placeholder - the actual implementation would be more complex
    return {
        "agent-1": {
            "agent_id": "agent-1",
            "score": 0.85,
            "status": "proficient",
            "timestamp": datetime.utcnow().isoformat()
        }
    }


def get_agent_comparisons(self) -> Dict[str, Any]:
    """Get agent comparison data (API compatibility method)."""
    # This is a placeholder - the actual implementation would be more complex
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "rankings": [["agent-1", 0.85]],
        "average_score": 0.85,
        "category_leaders": {
            "core_values": {"agent_id": "agent-1", "score": 0.87},
            "frequency": {"agent_id": "agent-1", "score": 0.84}
        },
        "empathy_status": "Healthy"
    }


# Add methods to EmpathyScorer class
EmpathyScorer.calculate_agent_score = calculate_agent_score
EmpathyScorer.calculate_all_agent_scores = calculate_all_agent_scores
EmpathyScorer.get_agent_comparisons = get_agent_comparisons 