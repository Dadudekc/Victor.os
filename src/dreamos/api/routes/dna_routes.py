from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List

from ..dependencies import get_memory
from ...core.services.dna_websocket import DNAWebSocketService
from ...memory import AgentMemory

router = APIRouter(prefix="/api/dna", tags=["dna"])

# Store active WebSocket services
dna_services: Dict[str, DNAWebSocketService] = {}

@router.websocket("/ws/{agent_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    agent_id: str,
    memory: AgentMemory = Depends(get_memory)
):
    """WebSocket endpoint for real-time DNA updates."""
    # Get or create DNA service
    if agent_id not in dna_services:
        dna_services[agent_id] = DNAWebSocketService(memory)
        # Start background analysis task
        asyncio.create_task(dna_services[agent_id].start())
    
    service = dna_services[agent_id]
    
    try:
        await websocket.accept()
        await service.handle_connection(websocket)
    except WebSocketDisconnect:
        # Service will handle cleanup
        pass
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {str(e)}")
        await websocket.close()

@router.get("/agents/{agent_id}/profile")
async def get_agent_dna_profile(
    agent_id: str,
    memory: AgentMemory = Depends(get_memory)
):
    """Get the current DNA profile for an agent."""
    try:
        dna_analyzer = DNAAnalyzer(memory)
        profile = await dna_analyzer.analyze_agent_dna(agent_id)
        return profile
    except Exception as e:
        logger.error(f"Error getting DNA profile: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get agent DNA profile"
        )

@router.get("/agents/{agent_id}/history")
async def get_agent_dna_history(
    agent_id: str,
    days: int = 30,
    memory: AgentMemory = Depends(get_memory)
):
    """Get historical DNA profiles for an agent."""
    try:
        history = await memory.get_agent_dna_history(agent_id, days)
        return history
    except Exception as e:
        logger.error(f"Error getting DNA history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get agent DNA history"
        )

@router.get("/agents/{agent_id}/drift")
async def get_agent_drift_analysis(
    agent_id: str,
    memory: AgentMemory = Depends(get_memory)
):
    """Get drift analysis for an agent."""
    try:
        dna_analyzer = DNAAnalyzer(memory)
        drift = await dna_analyzer.calculate_drift_score(agent_id)
        return drift
    except Exception as e:
        logger.error(f"Error getting drift analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get agent drift analysis"
        )

@router.get("/agents/{agent_id}/patterns")
async def get_agent_behavioral_patterns(
    agent_id: str,
    memory: AgentMemory = Depends(get_memory)
):
    """Get behavioral patterns for an agent."""
    try:
        dna_analyzer = DNAAnalyzer(memory)
        patterns = await dna_analyzer.detect_behavioral_patterns(agent_id)
        return patterns
    except Exception as e:
        logger.error(f"Error getting behavioral patterns: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get agent behavioral patterns"
        ) 