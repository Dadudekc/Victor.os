# tests/dreamscape/agents/test_planner_agent.py
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: I001

import pytest
from dreamos.coordination.agent_bus import AgentBus
from dreamos.core.config import AppConfig  # Updated import
from dreamos.core.coordination.base_agent import TaskMessage, TaskPriority, TaskStatus

# Import the agent class
from src.dreamscape.agents.planner_agent import ContentPlannerAgent

# --- Fixtures ---


@pytest.fixture
def mock_agent_bus() -> MagicMock:
    bus = MagicMock(spec=AgentBus)
    # Add spec for methods used by BaseAgent or the tested agent
    bus.subscribe = AsyncMock()
    bus.unsubscribe = AsyncMock()
    bus.dispatch_event = AsyncMock()
    return bus


@pytest.fixture
def mock_app_config() -> MagicMock:
    # Mock config as needed. For now, a simple mock.
    config = MagicMock(spec=AppConfig)
    # Mock config access if get_config is used directly
    config.dreamscape.planner_agent.agent_id = "test_planner_agent_001"
    return config


@pytest.fixture
def planner_agent(mock_app_config, mock_agent_bus) -> ContentPlannerAgent:
    """Provides an instance of the ContentPlannerAgent for testing."""
    # Ensure BaseAgent internal queue is mocked if necessary for direct testing
    # or rely on testing via command handling
    agent = ContentPlannerAgent(config=mock_app_config, agent_bus=mock_agent_bus)
    return agent


# --- Test Cases ---


def test_planner_agent_init(planner_agent: ContentPlannerAgent, mock_agent_bus):
    """Test basic initialization and command handler registration."""
    assert planner_agent.agent_id == "test_planner_agent_001"
    assert planner_agent.agent_bus == mock_agent_bus
    assert planner_agent.PLAN_COMMAND_TYPE in planner_agent._command_handlers
    assert (
        planner_agent._command_handlers[planner_agent.PLAN_COMMAND_TYPE]
        == planner_agent.handle_plan_request
    )


@pytest.mark.asyncio
async def test_handle_plan_request_success(
    planner_agent: ContentPlannerAgent, mock_agent_bus
):
    """Test the handle_plan_request handler with valid task parameters."""
    topic = "Test Topic Alpha"
    task = TaskMessage(
        task_id="plan-task-1",
        task_type=planner_agent.PLAN_COMMAND_TYPE,
        params={"topic": topic},
        priority=TaskPriority.NORMAL,
        status=TaskStatus.ACCEPTED,  # Status before handler is called
    )

    # Mock internal publish methods used by the handler
    planner_agent.publish_task_progress = AsyncMock()

    # Call the handler directly
    result = await planner_agent.handle_plan_request(task)

    # Assert the result structure (based on placeholder logic)
    assert isinstance(result, dict)
    assert result["topic"] == topic
    assert isinstance(result["outline"], list)
    assert len(result["outline"]) == 5
    assert f"Introduction to {topic}" in result["outline"][0]
    assert "error" not in result

    # Assert progress was published
    assert planner_agent.publish_task_progress.call_count >= 1


@pytest.mark.asyncio
async def test_handle_plan_request_missing_topic(planner_agent: ContentPlannerAgent):
    """Test the handle_plan_request handler when the topic is missing."""
    task = TaskMessage(
        task_id="plan-task-2",
        task_type=planner_agent.PLAN_COMMAND_TYPE,
        params={},  # Missing topic
        priority=TaskPriority.NORMAL,
        status=TaskStatus.ACCEPTED,
    )

    planner_agent.publish_task_progress = AsyncMock()

    result = await planner_agent.handle_plan_request(task)

    # Assert error is returned
    assert isinstance(result, dict)
    assert "error" in result
    assert "Missing topic" in result["error"]

    # Progress shouldn't be published if it fails early
    planner_agent.publish_task_progress.assert_not_called()


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)  # Patch sleep inside the handler
async def test_handle_plan_request_planning_exception(
    mock_sleep, planner_agent: ContentPlannerAgent
):
    """Test the handle_plan_request handler when the internal logic raises an exception."""  # noqa: E501
    topic = "Test Topic Beta"
    task = TaskMessage(
        task_id="plan-task-3",
        task_type=planner_agent.PLAN_COMMAND_TYPE,
        params={"topic": topic},
        priority=TaskPriority.NORMAL,
        status=TaskStatus.ACCEPTED,
    )

    planner_agent.publish_task_progress = AsyncMock()

    # Simulate an error during the placeholder logic (e.g., make ContentPlan fail)
    # For simplicity, patch the ContentPlan import/call if it were complex,
    # or just raise an exception directly after the initial progress update.
    original_content_plan = (  # noqa: F841
        planner_agent.ContentPlan
    )  # If ContentPlan is a class attribute or import
    with patch(
        "src.dreamscape.agents.planner_agent.ContentPlan",
        side_effect=ValueError("Simulated planning error"),
    ):
        result = await planner_agent.handle_plan_request(task)

    # Assert error is returned
    assert isinstance(result, dict)
    assert "error" in result
    assert (
        "Exception during planning: ValueError: Simulated planning error"
        in result["error"]
    )
    assert "details" in result
    assert "Traceback (most recent call last):" in result["details"]

    # Assert progress was published at least once before the error
    planner_agent.publish_task_progress.assert_called_once()
