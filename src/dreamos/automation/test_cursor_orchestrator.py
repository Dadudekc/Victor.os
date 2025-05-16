import asyncio
import logging
from pathlib import Path

from src.dreamos.core.config import AppConfig
from src.dreamos.core.coordination.agent_bus import AgentBus, EventType
from src.dreamos.automation.cursor_orchestrator import get_cursor_orchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_cursor_orchestrator():
    """Test the CursorOrchestrator functionality."""
    try:
        # Create test config
        config = AppConfig()
        config.gui_automation.input_coords_file_path = str(Path(__file__).parent / "input_coordinates.json")
        config.gui_automation.copy_coords_file_path = str(Path(__file__).parent / "copy_coordinates.json")

        # Initialize orchestrator
        orchestrator = await get_cursor_orchestrator(config)
        await orchestrator.initialize()

        # Test window health check
        for agent_id in ["Agent-1", "Agent-2", "Agent-3"]:
            is_healthy = await orchestrator.check_window_health(agent_id)
            logger.info(f"Window health check for {agent_id}: {'Healthy' if is_healthy else 'Unhealthy'}")

        # Test prompt injection
        test_prompt = "Hello, this is a test prompt!"
        for agent_id in ["Agent-1", "Agent-2", "Agent-3"]:
            success = await orchestrator.inject_prompt(agent_id, test_prompt)
            logger.info(f"Prompt injection for {agent_id}: {'Success' if success else 'Failed'}")

        # Test response retrieval
        for agent_id in ["Agent-1", "Agent-2", "Agent-3"]:
            response = await orchestrator.retrieve_response(agent_id)
            logger.info(f"Response from {agent_id}: {response}")

        # Test event handling
        agent_bus = AgentBus()
        await agent_bus.emit(
            EventType.CURSOR_ACTION,
            {
                "action": "inject",
                "agent_id": "Agent-1",
                "prompt": "Test event prompt"
            }
        )

        # Wait for event processing
        await asyncio.sleep(2)

        # Cleanup
        await orchestrator.shutdown()

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_cursor_orchestrator()) 