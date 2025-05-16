import json
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from .api.empathy_logs import export_logs, get_logs
from .api.empathy_websocket import manager

app = FastAPI(title="DreamOS Empathy Intelligence API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/empathy")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message["type"] == "subscribe":
                    await manager.subscribe(websocket, message["agent_id"])
                elif message["type"] == "unsubscribe":
                    await manager.unsubscribe(websocket, message["agent_id"])
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "data": {"message": "Invalid JSON message"}}
                )
    except Exception:
        await manager.disconnect(websocket)


@app.get("/api/logs")
async def get_logs_endpoint(
    agent_id: Optional[str] = None,
    log_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict]:
    """
    Get logs with optional filtering.

    Args:
        agent_id: Filter by agent ID
        log_type: Filter by log type (compliance/violation)
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)

    Returns:
        List of log entries
    """
    try:
        logs = await get_logs(agent_id, log_type, start_date, end_date)
        return logs
    except Exception as e:
        import traceback

        print(f"Error in get_logs_endpoint: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs/export")
async def export_logs_endpoint(
    agent_id: Optional[str] = None,
    log_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "markdown",
) -> Dict:
    """
    Export logs in the specified format.

    Args:
        agent_id: Filter by agent ID
        log_type: Filter by log type (compliance/violation)
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)
        format: Export format (markdown/json)

    Returns:
        Dictionary containing export data
    """
    try:
        return await export_logs(agent_id, log_type, start_date, end_date, format)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check() -> Dict:
    """
    Health check endpoint.

    Returns:
        Dictionary containing health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }
