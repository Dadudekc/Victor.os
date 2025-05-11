# tests/dreamscape/agents/test_writer_agent.py
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: I001

import pytest
from dreamos.coordination.agent_bus import AgentBus
from dreamos.core.config import AppConfig
from dreamos.core.coordination.base_agent import TaskMessage, TaskPriority, TaskStatus

# Import the agent class and dependent models
from src.dreamscape.agents.writer_agent import (
    ContentWriterAgent,
)
from src.dreamscape.core.content_models import ContentPlan

# --- Fixtures ---


@pytest.fixture
def mock_agent_bus() -> MagicMock:
    bus = MagicMock(spec=AgentBus)
    bus.subscribe = AsyncMock()
    bus.unsubscribe = AsyncMock()
    bus.dispatch_event = AsyncMock()
    return bus


@pytest.fixture
def mock_app_config() -> MagicMock:
    config = MagicMock(spec=AppConfig)
    config.dreamscape.writer_agent.agent_id = "test_writer_agent_001"
    return config


@pytest.fixture
def writer_agent(mock_app_config, mock_agent_bus) -> ContentWriterAgent:
    """Provides an instance of the ContentWriterAgent for testing."""
    agent = ContentWriterAgent(config=mock_app_config, agent_bus=mock_agent_bus)
    return agent


@pytest.fixture
def sample_plan() -> ContentPlan:
    """Provides a sample ContentPlan object."""
    return ContentPlan(topic="Sample Topic", outline=["Intro", "Body", "Conclusion"])


# --- Test Cases ---


def test_writer_agent_init(writer_agent: ContentWriterAgent, mock_agent_bus):
    """Test basic initialization and command handler registration."""
    assert writer_agent.agent_id == "test_writer_agent_001"
    assert writer_agent.agent_bus == mock_agent_bus
    assert writer_agent.WRITE_COMMAND_TYPE in writer_agent._command_handlers
    assert (
        writer_agent._command_handlers[writer_agent.WRITE_COMMAND_TYPE]
        == writer_agent.handle_write_request
    )


@pytest.mark.asyncio
async def test_handle_write_request_success(
    writer_agent: ContentWriterAgent, sample_plan: ContentPlan
):
    """Test the handle_write_request handler with a valid plan."""
    task = TaskMessage(
        task_id="write-task-1",
        task_type=writer_agent.WRITE_COMMAND_TYPE,
        params={"plan": sample_plan.model_dump()},  # Pass plan as dict
        priority=TaskPriority.NORMAL,
        status=TaskStatus.ACCEPTED,
    )

    writer_agent.publish_task_progress = AsyncMock()

    result = await writer_agent.handle_write_request(task)

    # Assert the result structure (based on placeholder logic)
    assert isinstance(result, dict)
    assert result["title"] == f"Exploring {sample_plan.topic}"
    assert isinstance(result["body"], str)
    assert "[Placeholder content for Intro...]" in result["body"]
    assert result["plan"] == sample_plan.model_dump()  # Check if plan is included
    assert "error" not in result

    # Assert progress was published
    assert writer_agent.publish_task_progress.call_count >= 1


@pytest.mark.asyncio
async def test_handle_write_request_missing_plan(writer_agent: ContentWriterAgent):
    """Test handler when the plan is missing from params."""
    task = TaskMessage(
        task_id="write-task-2",
        task_type=writer_agent.WRITE_COMMAND_TYPE,
        params={},  # Missing plan
        priority=TaskPriority.NORMAL,
        status=TaskStatus.ACCEPTED,
    )

    writer_agent.publish_task_progress = AsyncMock()
    result = await writer_agent.handle_write_request(task)

    assert isinstance(result, dict)
    assert "error" in result
    assert "Invalid or missing 'plan'" in result["error"]
    writer_agent.publish_task_progress.assert_not_called()


@pytest.mark.asyncio
async def test_handle_write_request_invalid_plan_data(writer_agent: ContentWriterAgent):
    """Test handler when the plan data in params is invalid (cannot be parsed)."""
    task = TaskMessage(
        task_id="write-task-3",
        task_type=writer_agent.WRITE_COMMAND_TYPE,
        params={"plan": {"invalid_field": "value"}},  # Invalid plan data
        priority=TaskPriority.NORMAL,
        status=TaskStatus.ACCEPTED,
    )

    writer_agent.publish_task_progress = AsyncMock()
    result = await writer_agent.handle_write_request(task)

    assert isinstance(result, dict)
    assert "error" in result
    assert "Failed to parse ContentPlan data" in result["error"]
    assert "details" in result
    writer_agent.publish_task_progress.assert_not_called()


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)  # Patch sleep inside the handler
async def test_handle_write_request_writing_exception(
    mock_sleep, writer_agent: ContentWriterAgent, sample_plan: ContentPlan
):
    """Test handler when the internal writing logic raises an exception."""
    task = TaskMessage(
        task_id="write-task-4",
        task_type=writer_agent.WRITE_COMMAND_TYPE,
        params={"plan": sample_plan.model_dump()},
        priority=TaskPriority.NORMAL,
        status=TaskStatus.ACCEPTED,
    )

    writer_agent.publish_task_progress = AsyncMock()

    # Simulate an error during the placeholder logic
    with patch(
        "src.dreamscape.agents.writer_agent.ContentDraft",
        side_effect=RuntimeError("Simulated writing error"),
    ):
        result = await writer_agent.handle_write_request(task)

    assert isinstance(result, dict)
    assert "error" in result
    assert (
        "Exception during draft generation: RuntimeError: Simulated writing error"
        in result["error"]
    )
    assert "details" in result
    assert "Traceback (most recent call last):" in result["details"]
    assert result["topic"] == sample_plan.topic  # Check topic is included in error

    # Assert progress was published at least once before the error
    writer_agent.publish_task_progress.assert_called_once()
