import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from dreamos.automation.cursor_orchestrator import (  # noqa: E402
    UI_AUTOMATION_AVAILABLE,
    CursorOrchestratorError,
    get_cursor_orchestrator,
)
from dreamos.core.agent_bus import AgentBus  # noqa: E402
from dreamos.core.config import AppConfig  # noqa: E402

# Basic Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
        # TODO: Add FileHandler based on AppConfig?
    ],
)
logger = logging.getLogger("CursorOrchestratorRunner")


async def main():
    """Initializes and runs the CursorOrchestrator service."""
    logger.info("Starting Cursor Orchestrator Service...")

    if not UI_AUTOMATION_AVAILABLE:
        logger.critical(
            "UI Automation dependencies (pyautogui, pyperclip) not found. Exiting."
        )
        sys.exit(1)

    # 1. Load Config
    try:
        config = AppConfig.load()
        logger.info("AppConfig loaded successfully.")
    except Exception as e:
        logger.critical(f"Failed to load AppConfig: {e}. Exiting.", exc_info=True)
        sys.exit(1)

    # 2. Initialize AgentBus (use singleton)
    # AgentBus should be initialized elsewhere ideally, but we get the instance here
    try:
        agent_bus = AgentBus()
        logger.info("AgentBus instance obtained.")
    except Exception as e:
        logger.critical(
            f"Failed to get AgentBus instance: {e}. Exiting.", exc_info=True
        )
        sys.exit(1)

    # 3. Get/Initialize CursorOrchestrator
    try:
        # Pass the loaded config and bus instance
        orchestrator = await get_cursor_orchestrator(config=config, agent_bus=agent_bus)
        logger.info("CursorOrchestrator instance obtained and initialized.")
    except CursorOrchestratorError as e:
        logger.critical(
            f"Failed to initialize CursorOrchestrator: {e}. Exiting.", exc_info=True
        )
        sys.exit(1)
    except Exception as e:
        logger.critical(
            f"Unexpected error getting CursorOrchestrator: {e}. Exiting.", exc_info=True
        )
        sys.exit(1)

    # 4. Start Orchestrator Listener (assuming it handles AgentBus subscriptions)
    try:
        await orchestrator.start_listening()  # Assumes this method exists and is async
        logger.info("CursorOrchestrator listener started.")
    except AttributeError:
        logger.critical(
            "CursorOrchestrator does not have a 'start_listening' method. Cannot process commands. Exiting."  # noqa: E501
        )
        # Perform cleanup/shutdown if needed
        await orchestrator.shutdown()  # Assuming shutdown exists
        sys.exit(1)
    except Exception as e:
        logger.critical(
            f"Failed to start CursorOrchestrator listener: {e}. Exiting.", exc_info=True
        )
        await orchestrator.shutdown()
        sys.exit(1)

    # 5. Keep running until interrupted
    logger.info("Cursor Orchestrator Service running. Press Ctrl+C to exit.")
    stop_event = asyncio.Event()

    # Handle signals for graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig, lambda: asyncio.create_task(shutdown_handler(stop_event, orchestrator))
        )

    await stop_event.wait()


async def shutdown_handler(stop_event: asyncio.Event, orchestrator):
    """Handles graceful shutdown procedures."""
    logger.info("Shutdown signal received. Stopping Cursor Orchestrator...")
    try:
        await orchestrator.shutdown()  # Assuming an async shutdown method exists
        logger.info("Cursor Orchestrator shut down successfully.")
    except Exception as e:
        logger.error(f"Error during orchestrator shutdown: {e}", exc_info=True)
    finally:
        stop_event.set()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Exiting.")
    except Exception as e:
        logger.critical(f"Unhandled exception in main loop: {e}", exc_info=True)
        sys.exit(1)
