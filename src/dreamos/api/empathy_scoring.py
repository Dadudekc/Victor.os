"""
Empathy Scoring API

Provides endpoints for accessing and calculating agent empathy scores.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from ..core.empathy_scoring import EmpathyScorer

router = APIRouter()
scorer = EmpathyScorer()

# Cache for scores to reduce calculation overhead
score_cache: Dict[str, Dict] = {}
last_cache_update = datetime.min


class AgentScore(BaseModel):
    """Model for agent empathy scores."""
    agent_id: str
    score: float
    status: str
    summary: str
    timestamp: str


class ScoreDetails(BaseModel):
    """Model for detailed empathy score metrics."""
    agent_id: str
    score: float
    status: str
    summary: str
    timestamp: str
    metrics: Dict[str, Any]
    value_scores: Dict[str, float]
    frequency: Dict[str, Any]
    trend: Dict[str, float]
    recovery: Dict[str, Any]
    context: Dict[str, Any]
    weighted_components: Dict[str, float]


class AgentComparison(BaseModel):
    """Model for agent comparison results."""
    timestamp: str
    rankings: List[List[Any]]
    average_score: float
    category_leaders: Dict[str, Dict[str, Any]]
    empathy_status: str


def update_score_cache(force: bool = False):
    """Update the score cache if needed or forced."""
    global last_cache_update, score_cache
    
    # Check if cache needs update (every 30 minutes by default)
    if force or datetime.now() - last_cache_update > timedelta(minutes=30):
        try:
            # Get all agents with logs
            log_dir = Path("runtime/logs/empathy")
            if not log_dir.exists():
                return
                
            # Extract unique agent IDs from log files
            agent_ids = set()
            for log_file in log_dir.glob("*.md"):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        agent_match = content.split("Agent:", 1)[1].split("\n", 1)[0].strip() if "Agent:" in content else None
                        if agent_match:
                            agent_ids.add(agent_match)
                except Exception:
                    continue
                    
            # Calculate scores for all agents
            if agent_ids:
                score_cache = scorer.calculate_all_agent_scores(list(agent_ids))
                last_cache_update = datetime.now()
        except Exception as e:
            print(f"Error updating score cache: {e}")


@router.get("/api/empathy/scores")
async def get_agent_scores(
    background_tasks: BackgroundTasks,
    force_update: bool = Query(False, description="Force recalculation of scores")
) -> List[AgentScore]:
    """
    Get empathy scores for all agents.
    
    Args:
        force_update: Force recalculation of scores
        
    Returns:
        List of agent empathy scores
    """
    if force_update:
        update_score_cache(force=True)
    else:
        background_tasks.add_task(update_score_cache)
        
    return [
        AgentScore(
            agent_id=agent_id,
            score=data["score"],
            status=data["status"],
            summary=data["summary"],
            timestamp=data["timestamp"]
        )
        for agent_id, data in score_cache.items()
    ]


@router.get("/api/empathy/scores/{agent_id}")
async def get_agent_score(agent_id: str, days: int = Query(30, description="Days of history to include")) -> ScoreDetails:
    """
    Get detailed empathy score for a specific agent.
    
    Args:
        agent_id: ID of the agent
        days: Number of days of history to include in calculation
        
    Returns:
        Detailed empathy score metrics
    """
    try:
        # Check cache first if recent
        if agent_id in score_cache and datetime.now() - datetime.fromisoformat(score_cache[agent_id]["timestamp"].replace('Z', '+00:00')) < timedelta(minutes=30):
            score_data = score_cache[agent_id]
        else:
            # Calculate fresh score
            score_data = scorer.calculate_agent_score(agent_id, days)
            score_cache[agent_id] = score_data
            
        return ScoreDetails(**score_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating score: {str(e)}")


@router.get("/api/empathy/comparison")
async def get_agent_comparison() -> AgentComparison:
    """
    Get comparison of all agent empathy scores.
    
    Returns:
        Comparison metrics and rankings
    """
    try:
        # Ensure cache is updated
        update_score_cache()
        
        # Get agent IDs from cache
        agent_ids = list(score_cache.keys())
        
        # Get comparison data
        comparison = scorer.get_agent_comparisons(agent_ids)
        
        return AgentComparison(**comparison)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating comparison: {str(e)}")


@router.post("/api/empathy/recalculate/{agent_id}")
async def recalculate_agent_score(agent_id: str) -> ScoreDetails:
    """
    Force recalculation of empathy score for a specific agent.
    
    Args:
        agent_id: ID of the agent
        
    Returns:
        Updated empathy score metrics
    """
    try:
        # Calculate fresh score
        score_data = scorer.calculate_agent_score(agent_id)
        score_cache[agent_id] = score_data
        
        return ScoreDetails(**score_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recalculating score: {str(e)}")


@router.get("/api/empathy/threshold-status")
async def get_empathy_threshold_status() -> Dict[str, Any]:
    """
    Get system-wide empathy threshold status.
    
    Returns:
        System empathy status metrics
    """
    try:
        # Ensure cache is updated
        update_score_cache()
        
        # Get agent IDs from cache
        agent_ids = list(score_cache.keys())
        
        if not agent_ids:
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "Unknown",
                "average_score": 0.0,
                "agents_below_threshold": 0,
                "critical_agents": []
            }
        
        # Calculate average score
        avg_score = sum(data["score"] for data in score_cache.values()) / len(score_cache)
        
        # Find agents below threshold
        threshold = 65.0
        below_threshold = [
            agent_id for agent_id, data in score_cache.items()
            if data["score"] < threshold
        ]
        
        # Find critical agents
        critical_agents = [
            {"agent_id": agent_id, "score": data["score"]}
            for agent_id, data in score_cache.items()
            if data["status"] == "critical"
        ]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": scorer._determine_system_status(avg_score),
            "average_score": avg_score,
            "agents_below_threshold": len(below_threshold),
            "critical_agents": critical_agents
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting threshold status: {str(e)}") 