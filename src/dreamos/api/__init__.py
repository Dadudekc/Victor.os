"""
Dream.OS API Package

Provides API endpoints for the Dream.OS system.
"""

from fastapi import FastAPI
from .empathy_logs import router as empathy_logs_router
from .empathy_scoring import router as empathy_scoring_router
from .empathy_websocket import router as empathy_websocket_router

app = FastAPI(title="Dream.OS API", version="1.0.0")

app.include_router(empathy_logs_router)
app.include_router(empathy_scoring_router)
app.include_router(empathy_websocket_router)

__all__ = ["app"] 