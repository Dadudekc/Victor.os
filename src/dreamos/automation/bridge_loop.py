# src/dreamos/automation/bridge_loop.py

import asyncio
import logging
import time
from typing import Any, Dict, Optional

import tenacity

# Attempt to import necessary components
try:
    from dreamos.automation.cursor_orchestrator import (
        CursorOrchestrator,  # noqa F401
        CursorOrchestratorError,
        get_cursor_orchestrator,
    )
    from dreamos.core.config import AppConfig
    from dreamos.core.errors import DreamOSError  # noqa F401
except ImportError as e:
    print(f"Error importing DreamOS components: {e}")
    print("Bridge loop cannot run.")
    exit(1)

logger = logging.getLogger("BridgeLoop")


# Configure Tenacity for retrying the entire loop or specific parts
# Example: Retry the whole cycle up to 3 times with exponential backoff
@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
    retry=tenacity.retry_if_exception_type(CursorOrchestratorError),
    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
    reraise=True,  # Reraise the exception if all retries fail
)
async def run_bridge_cycle(
    orchestrator: CursorOrchestrator,
    agent_id: str,
    prompt: str,
    inject_timeout: Optional[float] = 30.0,  # Example timeouts
    retrieve_timeout: Optional[float] = 60.0,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Runs a single inject-retrieve cycle with the CursorOrchestrator."""
    logger.info(
        f"Starting bridge cycle for agent '{agent_id}'. Correlation ID: {correlation_id}"
    )
    start_time = time.monotonic()
    response_data = None
    error = None

    try:
        # --- Injection Phase ---
        logger.debug(f"Injecting prompt for {agent_id}...")
        inject_success = await orchestrator.inject_prompt(
            agent_id=agent_id,
            prompt=prompt,
            timeout=inject_timeout,
            correlation_id=correlation_id,
        )

        if not inject_success:
            logger.error(f"Injection failed for agent {agent_id}.")
            # No point trying to retrieve if injection failed
            raise CursorOrchestratorError(f"Injection failed for agent {agent_id}")

        logger.info(f"Injection successful for {agent_id}. Awaiting response...")
        # Optional: Add a small delay or check agent status if needed before retrieval
        await asyncio.sleep(1.0)

        # --- Retrieval Phase ---
        logger.debug(f"Retrieving response for {agent_id}...")
        response_data = await orchestrator.retrieve_response(
            agent_id=agent_id,
            timeout=retrieve_timeout,
            correlation_id=correlation_id,
        )

        if response_data is None:
            logger.error(
                f"Response retrieval failed for agent {agent_id} (returned None)."
            )
            raise CursorOrchestratorError(
                f"Response retrieval failed for agent {agent_id}"
            )

        logger.info(f"Response retrieved successfully for {agent_id}.")

    except CursorOrchestratorError as e:
        logger.error(f"CursorOrchestratorError during bridge cycle for {agent_id}: {e}")
        error = str(e)
        # The tenacity retry decorator will handle retries
        raise  # Reraise to trigger retry or final failure
    except Exception as e:
        logger.exception(f"Unexpected error during bridge cycle for {agent_id}: {e}")
        error = f"Unexpected error: {e}"
        raise CursorOrchestratorError(
            f"Unexpected bridge error for {agent_id}: {e}"
        ) from e
    finally:
        end_time = time.monotonic()
        duration = end_time - start_time
        logger.info(f"Bridge cycle for {agent_id} finished in {duration:.2f} seconds.")

    # Return results in a structured way
    return {
        "success": error is None,
        "response": response_data,
        "error": error,
        "agent_id": agent_id,
        "correlation_id": correlation_id,
        "duration_seconds": duration,
    }


# Example Usage (Conceptual - requires integration into an agent or service)
async def main_loop(config: AppConfig):
    orchestrator = await get_cursor_orchestrator(config=config)
    # Example: Process a queue of prompts
    prompt_queue = [
        {
            "agent_id": "agent_1",
            "prompt": "Write python code for fibonacci",
            "id": "p1",
        },
        {"agent_id": "agent_2", "prompt": "Explain quantum physics", "id": "p2"},
    ]

    for item in prompt_queue:
        try:
            result = await run_bridge_cycle(
                orchestrator=orchestrator,
                agent_id=item["agent_id"],
                prompt=item["prompt"],
                correlation_id=item["id"],
            )
            logger.info(
                f"Cycle Result for {item['id']}: Success={result['success']}, Error='{result['error']}'"
            )
            # Process the result['response'] here

        except CursorOrchestratorError:
            logger.error(
                f"Bridge cycle failed permanently for {item['id']} after retries."
            )
            # Handle permanent failure (e.g., mark task as failed)
        except Exception as e:
            logger.error(f"Unhandled exception in main loop for {item['id']}: {e}")

        await asyncio.sleep(2)  # Delay between cycles


# --- Add CLI or integration points as needed ---
# if __name__ == "__main__":
#     # Load config, setup logging, run main_loop
#     pass
