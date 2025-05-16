# src/dreamos/bridge/http_bridge_service.py
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# --- Bridge Component Imports ---
BRIDGE_AVAILABLE = False
AppConfig = None
CursorBridgeError = Exception  # Base exception fallback
interact_with_cursor = None

try:
    from dreamos.core.config import AppConfig
    from dreamos.tools.cursor_bridge.cursor_bridge import (  # Import other specific exceptions if needed (e.g., CursorInjectError)
        CursorBridgeError,
        interact_with_cursor,
    )

    BRIDGE_AVAILABLE = True
    logging.info("Successfully imported bridge components.")
except ImportError as e:
    logging.critical(
        f"Failed to import critical bridge components: {e}. HTTP Bridge Service endpoints will be unavailable.",
        exc_info=True,
    )
    # Keep BRIDGE_AVAILABLE as False, AppConfig/functions as None/BaseException

logger = logging.getLogger(__name__)

# --- FastAPI App Setup ---

app = FastAPI(
    title="DreamOS Cursor Bridge Service",
    description="Provides an HTTP interface to interact with the Cursor IDE via PyAutoGUI.",
    version="0.1.0",
)

# --- Configuration Loading ---
config: Optional[AppConfig] = None
CONFIG_LOADED = False
if AppConfig:  # Only try to load if AppConfig class was successfully imported
    try:
        config = AppConfig()  # Assumes default loading works
        CONFIG_LOADED = True
        logger.info("AppConfig loaded successfully for HTTP Bridge Service.")
    except Exception as e:
        logger.error(
            f"Failed to load AppConfig on startup: {e}. Bridge interactions will fail.",
            exc_info=True,
        )
        # CONFIG_LOADED remains False
else:
    logger.error("AppConfig class not imported, configuration loading skipped.")

# --- Request/Response Models ---


class InteractRequest(BaseModel):
    prompt: str


class InteractResponse(BaseModel):
    response: str


class ErrorResponse(BaseModel):
    error: str


# --- API Endpoint --- #


@app.post(
    "/interact",
    response_model=InteractResponse,
    responses={
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
async def handle_interaction(request: InteractRequest):
    """Receives a prompt, uses the Cursor bridge to inject it,
    extract the response, and return it.
    """
    logger.debug(
        f"Received /interact request for prompt: {request.prompt[:50]}..."
    )  # Use debug for potentially verbose logging

    if not BRIDGE_AVAILABLE:
        logger.error(
            "Cannot process /interact: Bridge components not available due to import errors."
        )
        raise HTTPException(
            status_code=503, detail="Bridge service dependencies are unavailable."
        )  # 503 Service Unavailable

    if not CONFIG_LOADED or config is None:
        logger.error(
            "Cannot process /interact: Application configuration is not loaded."
        )
        raise HTTPException(
            status_code=503, detail="Bridge service configuration is unavailable."
        )  # 503 Service Unavailable

    try:
        # Call the core bridge interaction function
        result_text = interact_with_cursor(request.prompt, config)
        logger.info(
            f"Interaction successful. Returning response (length: {len(result_text)}). Preview: {result_text[:100]}..."
        )
        return InteractResponse(response=result_text)

    except CursorBridgeError as e:
        # Handle specific errors from the bridge
        logger.error(f"CursorBridgeError during interaction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Bridge Interaction Error: {e}")
    except ValueError as e:
        # Handle potential validation errors (e.g., invalid payload structure if handle_gpt_payload was used)
        logger.error(f"ValueError during interaction: {e}", exc_info=True)
        raise HTTPException(
            status_code=400, detail=f"Invalid Request Data: {e}"
        )  # 400 for bad input
    except Exception as e:
        # Catch any other unexpected errors
        logger.exception(f"Unexpected error during /interact endpoint processing: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected Internal Server Error: {type(e).__name__}",
        )  # Avoid leaking detailed error message


# --- Optional: Add health check endpoint ---
@app.get("/health")
async def health_check():
    # Reflect actual state based on imports and config load
    return {
        "status": "ok" if BRIDGE_AVAILABLE and CONFIG_LOADED else "error",
        "bridge_available": BRIDGE_AVAILABLE,
        "config_loaded": CONFIG_LOADED,
    }


# --- Running the server (for local testing) ---
# This part would typically be handled by a deployment tool like uvicorn
# Example: uvicorn src.dreamos.bridge.http_bridge_service:app --reload
if __name__ == "__main__":
    # Basic logging setup for local running
    # More sophisticated logging should be configured via AppConfig if possible
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format)

    try:
        import uvicorn

        logger.info("Starting HTTP Bridge Service locally with uvicorn...")
        # Use host="127.0.0.1" for local only access, "0.0.0.0" to allow external access
        # Port 8000 is an example, make configurable if needed
        uvicorn.run(app, host="127.0.0.1", port=8000)
    except ImportError:
        logger.critical("Uvicorn is not installed. Cannot start service locally.")
        logger.critical("Please install it: pip install uvicorn[standard]")
    except Exception as e:
        logger.critical(f"Failed to start Uvicorn server: {e}", exc_info=True)
