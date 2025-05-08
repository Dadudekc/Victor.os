import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure src directory is on path for imports if run from root
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Attempt to import the orchestrator
try:
    from dreamos.automation.cursor_orchestrator import (
        UI_AUTOMATION_AVAILABLE,
        CursorOrchestrator,
        get_cursor_orchestrator,
    )

    ORCHESTRATOR_AVAILABLE = True
except ImportError as e:
    print(f"Error: Failed to import CursorOrchestrator: {e}")
    print("Ensure src directory is in PYTHONPATH or run script from project root.")
    ORCHESTRATOR_AVAILABLE = False
    UI_AUTOMATION_AVAILABLE = False  # Assume false if import fails

    # Define dummy classes/functions if import fails to prevent further NameErrors
    class CursorOrchestrator:
        pass

    async def get_cursor_orchestrator() -> CursorOrchestrator:
        raise ImportError("CursorOrchestrator not available")


# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("TestCursorOrchestrator")


async def test_inject(orchestrator: CursorOrchestrator, agent_id: str, prompt: str):
    logger.info(f"--- Testing inject_prompt for {agent_id} ---")
    success = await orchestrator.inject_prompt(agent_id, prompt)
    if success:
        logger.info(f"[SUCCESS] inject_prompt for {agent_id} completed.")
    else:
        logger.error(f"[FAILURE] inject_prompt for {agent_id} failed.")
    await asyncio.sleep(1)  # Pause between actions


async def test_retrieve(orchestrator: CursorOrchestrator, agent_id: str):
    logger.info(f"--- Testing retrieve_response for {agent_id} ---")
    response = await orchestrator.retrieve_response(agent_id)
    if response is not None:
        logger.info(
            f"[SUCCESS] retrieve_response for {agent_id} returned (length {len(response)}): {response[:100]}..."  # noqa: E501
        )
    else:
        logger.error(
            f"[FAILURE] retrieve_response for {agent_id} failed or returned None."
        )
    await asyncio.sleep(1)


async def test_get_status(orchestrator: CursorOrchestrator, agent_id: str):
    logger.info(f"--- Testing get_agent_status for {agent_id} ---")
    status = await orchestrator.get_agent_status(agent_id)
    logger.info(f"[STATUS] get_agent_status for {agent_id}: {status}")
    await asyncio.sleep(0.5)


async def test_health_check(orchestrator: CursorOrchestrator, agent_id: str):
    logger.info(f"--- Testing check_window_health for {agent_id} ---")
    healthy = await orchestrator.check_window_health(agent_id)
    if healthy:
        logger.info(f"[SUCCESS] check_window_health for {agent_id} passed.")
    else:
        logger.error(f"[FAILURE] check_window_health for {agent_id} failed.")
    await asyncio.sleep(0.5)


async def main(args):
    if not ORCHESTRATOR_AVAILABLE:
        logger.critical("CursorOrchestrator module could not be imported. Exiting.")
        return

    if not UI_AUTOMATION_AVAILABLE:
        logger.critical(
            "UI Automation dependencies (pyautogui, pyperclip) not available. Exiting."
        )
        return

    logger.info("Getting CursorOrchestrator instance...")
    # Initialize orchestrator (assumes AgentBus is also available/initializable)
    try:
        orchestrator = await get_cursor_orchestrator()
        logger.info("CursorOrchestrator instance obtained.")
    except Exception as e:
        logger.exception(f"Failed to get or initialize CursorOrchestrator: {e}")
        return

    target_agent = args.agent_id
    logger.info(f"Targeting agent: {target_agent}")

    # Run requested actions
    if args.action == "all" or args.action == "status":
        await test_get_status(orchestrator, target_agent)

    if args.action == "all" or args.action == "health":
        await test_health_check(orchestrator, target_agent)

    if args.action == "all" or args.action == "inject":
        prompt = args.prompt or f"Test prompt for {target_agent} at {time.time()}"  # noqa: F821
        await test_inject(orchestrator, target_agent, prompt)

    if args.action == "all" or args.action == "retrieve":
        # Add a delay before retrieving if injecting first
        if args.action == "all" or args.action == "inject":
            wait_time = 5
            logger.info(f"Pausing {wait_time}s before retrieving response...")
            await asyncio.sleep(wait_time)
        await test_retrieve(orchestrator, target_agent)

    logger.info("--- Test Script Finished ---")
    # Orchestrator shutdown might be needed if it holds resources
    # await orchestrator.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test CursorOrchestrator functionality."
    )
    parser.add_argument("agent_id", help="The target agent ID (e.g., agent_01)")
    parser.add_argument(
        "action",
        choices=["inject", "retrieve", "status", "health", "all"],
        help="The action to perform.",
    )
    parser.add_argument(
        "-p",
        "--prompt",
        help="The prompt text to inject (required for 'inject' action if not using 'all'). Default is a test message.",  # noqa: E501
    )

    # Add check for prompt if action is inject
    temp_args, _ = parser.parse_known_args()
    if temp_args.action == "inject" and not temp_args.prompt:
        # Generate default prompt if not provided for inject action
        pass  # Default prompt is now handled in main()
        # parser.error("The --prompt argument is required when action is 'inject' (and not 'all')")  # noqa: E501

    args = parser.parse_args()

    asyncio.run(main(args))
