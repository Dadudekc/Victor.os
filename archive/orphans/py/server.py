"""
Dream.OS Server

Main server entry point for Dream.OS API and WebSocket services.
"""

import logging
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Import API routers
from .api.empathy_logs import router as empathy_logs_router
from .api.empathy_scoring import router as empathy_scoring_router
from .api.empathy_websocket import router as empathy_websocket_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Dream.OS API",
    description="API for Dream.OS empathy intelligence system",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(empathy_logs_router)
app.include_router(empathy_scoring_router)
app.include_router(empathy_websocket_router)

# Serve static files
try:
    static_dir = Path(__file__).parent.parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
except Exception as e:
    logger.error(f"Failed to mount static files: {e}")


# Health check endpoint
@app.get("/health")
async def health_check() -> Dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "Dream.OS API"}


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"},
    )


# Startup event
@app.on_event("startup")
async def startup_event() -> None:
    """Execute startup tasks."""
    # Create necessary directories
    log_dir = Path("runtime/logs/empathy")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Dream.OS API server started")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Execute shutdown tasks."""
    logger.info("Dream.OS API server shutting down")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "dreamos.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
