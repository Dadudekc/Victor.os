"""
WebSocket handler for real-time empathy log updates.

Provides live updates of log entries to connected clients.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set
import logging

from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ..core.drift_detector import DriftDetector
from ..core.predictive_model import PredictiveModel
from .empathy_logs import parse_log_content

logger = logging.getLogger("empathy_websocket")
logger.setLevel(logging.INFO)

class LogFileHandler(FileSystemEventHandler):
    """Handles file system events for log files."""
    
    def __init__(self, websocket_manager: 'WebSocketManager'):
        self.manager = websocket_manager
        
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.md'):
            return
        self.manager.notify_new_log(event.src_path)
        
    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith('.md'):
            return
        self.manager.notify_log_update(event.src_path)

class WebSocketManager:
    """Manages WebSocket connections and log updates."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.log_dir = Path("runtime/logs/empathy")
        self.file_handler = LogFileHandler(self)
        self.observer = Observer()
        self.observer.schedule(self.file_handler, str(self.log_dir), recursive=False)
        self.observer.start()
        self.drift_detector = DriftDetector()
        self.predictive_model = PredictiveModel()
        
    async def connect(self, websocket: WebSocket):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections.add(websocket)
        
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        self.active_connections.remove(websocket)
        
    async def broadcast(self, message: Dict):
        """Broadcast a message to all connected clients."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.add(connection)
                
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
            
    def notify_new_log(self, log_path: str):
        """Notify clients of a new log file."""
        asyncio.create_task(self._process_log_update(log_path, "new"))
        
    def notify_log_update(self, log_path: str):
        """Notify clients of a log file update."""
        asyncio.create_task(self._process_log_update(log_path, "update"))
        
    async def _process_log_update(self, log_path: str, event_type: str) -> None:
        """
        Process a log file update and send updates to connected clients.
        
        Args:
            log_path: Path to the log file
            event_type: Type of event (new/modified/deleted)
        """
        try:
            # Read the log file
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the log content
            log_data = parse_log_content(content)
            
            # Send log_update message first
            for websocket in self.active_connections:
                try:
                    await websocket.send_json({
                        "type": "log_update",
                        "log_type": log_data["type"],
                        "severity": log_data["severity"],
                        "agent_id": log_data["agent_id"],
                        "content": content
                    })
                except Exception as e:
                    logger.error(f"Error sending log update: {str(e)}")
                    continue
            
            # Process the log data
            if log_data["type"] == "compliance":
                # Check for drift
                drift_warning = self.drift_detector.add_action(
                    log_data["agent_id"],
                    log_data["metrics"],
                    log_data["metrics"].get("compliance_score", 1.0)
                )
                
                if drift_warning:
                    await self.broadcast({
                        "type": "drift_warning",
                        "data": drift_warning
                    })
                
                # Get compliance prediction
                prediction = self.predictive_model.predict_drift(
                    log_data["agent_id"],
                    log_data["metrics"]
                )
                
                await self.broadcast({
                    "type": "compliance_prediction",
                    "data": prediction
                })
                
            elif log_data["type"] == "violation":
                # Check for violation patterns
                pattern_warning = self.drift_detector.add_violation(
                    log_data["agent_id"],
                    log_data["metrics"]
                )
                
                if pattern_warning:
                    await self.broadcast({
                        "type": "pattern_warning",
                        "data": pattern_warning
                    })
            
            # Get agent insights
            insights = self.predictive_model.get_agent_insights(log_data["agent_id"])
            await self.broadcast({
                "type": "agent_insights",
                "data": insights
            })
            
        except Exception as e:
            logger.error(f"Error processing log update: {str(e)}")
            # Broadcast error to all connected clients
            await self.broadcast({
                "type": "log_update",
                "error": str(e)
            })

    def stop(self):
        """Stop the file system observer."""
        self.observer.stop()
        self.observer.join()

    async def process_log_update(self, websocket: WebSocket, log_path: str) -> None:
        """
        Process a log file update and send updates to connected clients.
        
        Args:
            websocket: WebSocket connection
            log_path: Path to the log file
        """
        try:
            # Read the log file
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the log content
            log_data = parse_log_content(content)
            
            # Process the log data
            if log_data["type"] == "compliance":
                # Check for drift
                drift_warning = self.drift_detector.add_action(
                    log_data["agent_id"],
                    log_data["metrics"],
                    log_data["metrics"].get("compliance_score", 1.0)
                )
                
                if drift_warning:
                    await websocket.send_json({
                        "type": "drift_warning",
                        "data": drift_warning
                    })
                
                # Get compliance prediction
                prediction = self.predictive_model.predict_drift(
                    log_data["agent_id"],
                    log_data["metrics"]
                )
                
                await websocket.send_json({
                    "type": "compliance_prediction",
                    "data": prediction
                })
                
            elif log_data["type"] == "violation":
                # Check for violation patterns
                pattern_warning = self.drift_detector.add_violation(
                    log_data["agent_id"],
                    log_data["metrics"]
                )
                
                if pattern_warning:
                    await websocket.send_json({
                        "type": "pattern_warning",
                        "data": pattern_warning
                    })
            
            # Get agent insights
            insights = self.predictive_model.get_agent_insights(log_data["agent_id"])
            await websocket.send_json({
                "type": "agent_insights",
                "data": insights
            })
            
        except Exception as e:
            logger.error(f"Error processing log update: {str(e)}")
            await websocket.send_json({
                "type": "error",
                "data": {"message": f"Error processing log: {str(e)}"}
            })

    async def broadcast_to_agent(self, agent_id: str, message: dict):
        # For test/mock, just send to all active connections
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception:
                continue

# Global WebSocket manager instance
manager = WebSocketManager()

# Create router
router = APIRouter(prefix="/empathy/ws", tags=["empathy"])

@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for empathy log updates."""
    try:
        await manager.connect(websocket)
        while True:
            try:
                data = await websocket.receive_json()
                if "log_path" in data:
                    await manager.process_log_update(websocket, data["log_path"])
            except WebSocketDisconnect:
                manager.disconnect(websocket)
                break
            except Exception as e:
                logger.error(f"Error in websocket connection: {str(e)}")
                break
    finally:
        manager.disconnect(websocket)
        manager.stop() 