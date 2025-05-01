import asyncio
import json
import logging
import uuid  # Needed for correlation ID
from pathlib import Path  # noqa E402
from typing import Any, Dict

from dreamos.coordination.agent_bus import AgentBus, EventType

# Import the standardized event publisher
from dreamos.core.eventing.publishers import publish_cursor_inject_event

# Remove direct orchestrator import
# from dreamos.automation.cursor_orchestrator import get_cursor_orchestrator, CursorOrchestratorError


# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Agent2InfraSurgeon")

AGENT_ID = "Agent2"  # Define the agent ID used in coordinate files
# DEFAULT_RESPONSE_WAIT_TIME = 15.0 # No longer needed, response is async via bus


async def run_agent2_task(task_prompt: str):
    """
    Runs a single task by PUBLISHING an event requesting prompt injection
    via the AgentBus.
    Does NOT wait for or retrieve the response directly.
    """
    # Removed orchestrator instantiation and status check - relies on bus now
    try:
        logger.info(f"Attempting task via AgentBus event: '{task_prompt}'")
        correlation_id = str(uuid.uuid4())  # Generate ID to track request/response

        # --- Publish Injection Request Event ---
        logger.info(
            f"Publishing cursor inject request for {AGENT_ID} (CorrID: {correlation_id})..."
        )
        success = await publish_cursor_inject_event(
            target_agent_id=AGENT_ID,
            prompt=task_prompt,
            source_agent_id=AGENT_ID,  # Self-identifying as source
            correlation_id=correlation_id,
        )

        if not success:
            logger.error(
                f"Failed to publish cursor inject event for {AGENT_ID}. Aborting task."
            )
            # Retry logic is handled by RecoveryCoordinatorAgent (Agent4) based on TASK_FAILED events.
            return False  # Indicate publishing failure

        logger.info(
            f"Cursor inject request published successfully (CorrID: {correlation_id})."
        )
        logger.info(
            "Agent task complete (publish only). Response handling requires separate listener."
        )
        return True  # Indicate publishing success

        # --- Removed direct interaction logic ---
        # logger.info(f"Injecting prompt into {AGENT_ID}...")
        # success = await orchestrator.inject_prompt(AGENT_ID, task_prompt)
        # ... removed sleep and retrieve_response ...

    # Keep broad exception handling, but remove CursorOrchestratorError
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred during Agent 2 task execution (publishing): {e}"
        )
        return False  # Indicate failure
    # Removed finally block as orchestrator state is no longer managed here


async def main():
    """Main entry point for testing the agent task runner (publish only)."""
    # Example task - replace with actual task generation logic later
    test_prompt = (
        "List all python files in the src/dreamos/agents directory using AgentBus."
    )

    logger.info(
        "--- Starting Agent 2 Test Task --- AgentBus Event Cycle --- Publish Only --- CIL"
    )
    # Run the task publisher
    published_ok = await run_agent2_task(test_prompt)

    if published_ok:
        logger.info("--- Agent 2 Test Task Publishing Completed Successfully ---")
    else:
        logger.error("--- Agent 2 Test Task Publishing Failed ---")


if __name__ == "__main__":
    # No longer need PyAutoGUI delay, but keep imports clean
    # time.sleep(1)
    try:
        asyncio.run(main())
    # Remove CursorOrchestratorError catch
    except ImportError as e:
        logger.critical(f"Missing critical dependency for Agent 2: {e}")
    except KeyboardInterrupt:
        logger.info("Agent 2 execution interrupted by user.")

    # EDIT START: Increase sleep duration
    # await asyncio.sleep(5) # Check every 5 seconds
    # EDIT END: Increase sleep duration

    # Keep broad exception handling, but remove CursorOrchestratorError
    except Exception as e:
        logger.error(f"Error during mailbox check: {e}", exc_info=True)
