#!/usr/bin/env python3
"""
Script to run the DreamOS Cursor Bridge HTTP Service using Uvicorn.

This script initializes and starts the FastAPI application defined in
`src.dreamos.bridge.http_bridge_service`.
It allows configuration of host, port, and reload options via command-line
arguments or environment variables.
"""

# scripts/run_bridge_service.py
import argparse
import logging
import os

# Configure logging early
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger(__name__)


def main():
    """
    Parses command-line arguments, imports the FastAPI application,
    and starts the Uvicorn server for the Cursor Bridge HTTP Service.
    """
    parser = argparse.ArgumentParser(
        description="Run the DreamOS Cursor Bridge HTTP Service."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("CURSOR_BRIDGE_HOST", "127.0.0.1"),
        help="Host to bind the service to (default: 127.0.0.1 or CURSOR_BRIDGE_HOST env var)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("CURSOR_BRIDGE_PORT", "8000")),
        help="Port to bind the service to (default: 8000 or CURSOR_BRIDGE_PORT env var)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable Uvicorn auto-reload (for development)",
    )
    args = parser.parse_args()

    logger.info("Attempting to start the Cursor Bridge HTTP Service...")

    try:
        # Import the FastAPI app and config *after* logging is set up and args parsed
        # This allows http_bridge_service internal logging to also be captured if it uses standard logging
        from src.dreamos.bridge.http_bridge_service import (
            BRIDGE_AVAILABLE,
            CONFIG_LOADED,
            app,
        )

        logger.info(
            f"FastAPI app imported. Bridge Available: {BRIDGE_AVAILABLE}, Config Loaded: {CONFIG_LOADED}"
        )

        if not BRIDGE_AVAILABLE:
            logger.critical(
                "Bridge components are not available (check http_bridge_service.py logs). Service cannot run effectively."
            )
            # Allow to run but it will likely return 503 for /interact

        if not CONFIG_LOADED:
            logger.warning(
                "Application configuration was not loaded (check http_bridge_service.py logs). Service may not function correctly."
            )
            # Allow to run but it will likely return 503 for /interact

    except ImportError as e:
        logger.critical(
            f"Failed to import FastAPI app from src.dreamos.bridge.http_bridge_service: {e}",
            exc_info=True,
        )
        logger.critical(
            "Ensure the http_bridge_service.py and its dependencies (FastAPI, etc.) are correctly installed and accessible."
        )
        return
    except Exception as e:
        logger.critical(
            f"An unexpected error occurred during app import: {e}", exc_info=True
        )
        return

    try:
        import uvicorn

        logger.info(
            f"Starting Uvicorn server on {args.host}:{args.port} (Reload: {args.reload})"
        )
        uvicorn.run(
            "src.dreamos.bridge.http_bridge_service:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info",  # Uvicorn's own log level
        )
    except ImportError:
        logger.critical(
            "Uvicorn is not installed. Cannot start the HTTP bridge service."
        )
        logger.critical("Please install it: pip install uvicorn[standard]")
    except Exception as e:
        logger.critical(f"Failed to start Uvicorn server: {e}", exc_info=True)


if __name__ == "__main__":
    main()
