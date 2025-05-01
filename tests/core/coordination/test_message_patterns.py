from datetime import datetime, timezone
from uuid import UUID

import pytest

from dreamos.core.coordination.message_patterns import (
    TaskMessage,
    TaskPriority,
    TaskStatus,
    create_task_message,
    update_task_status,
)

# --- Test TaskMessage Creation and Helpers ---


def test_create_task_message_defaults():
    """Test creating a task message with minimal info, checking defaults."""
    task = create_task_message(
        task_type="simple_test",
        agent_id="target_agent",
        input_data={"param": "value"},
        source_agent_id="source_agent",
    )

    assert isinstance(task, TaskMessage)
    assert task.task_type == "simple_test"
    assert task.agent_id == "target_agent"
    assert task.input_data == {"param": "value"}
    assert task.source_agent_id == "source_agent"

    # Check defaults
    assert task.status == TaskStatus.PENDING
    assert task.priority == TaskPriority.NORMAL
    assert task.result is None
    assert task.error is None
    assert isinstance(task.task_id, str) and task.task_id.startswith("task_")
    assert isinstance(task.correlation_id, str) and task.correlation_id.startswith(
        "corr_"
    )
    assert isinstance(task.created_at, datetime)
    assert isinstance(task.updated_at, datetime)
    assert task.created_at.tzinfo == timezone.utc
    assert task.updated_at.tzinfo == timezone.utc
    assert task.subtasks == []
    assert task.metadata == {}
    assert task.started_at is None
    assert task.completed_at is None
    assert task.score is None
    assert task.retry_count == 0


def test_create_task_message_explicit():
    """Test creating a task message with explicit values."""
    task = create_task_message(
        task_type="complex_test",
        agent_id="agent-xyz",
        input_data={"x": 1},
        source_agent_id="initiator",
        priority=TaskPriority.HIGH,
        parent_task_id="parent-123",
        correlation_id="my-corr-id",
        metadata={"context": "important"},
    )

    assert task.task_type == "complex_test"
    assert task.agent_id == "agent-xyz"
    assert task.priority == TaskPriority.HIGH
    assert task.parent_task_id == "parent-123"
    assert task.correlation_id == "my-corr-id"
    assert task.metadata == {"context": "important"}


def test_update_task_status():
    """Test the update_task_status helper function."""
    task = create_task_message("test", "agent", {})
    original_updated_at = task.updated_at

    # Update status
    updated_task = update_task_status(task, TaskStatus.RUNNING)
    assert updated_task is task  # Should modify in place
    assert task.status == TaskStatus.RUNNING
    assert task.updated_at > original_updated_at
    assert task.result is None
    assert task.error is None

    # Update with result
    result_data = {"output": "success"}
    updated_task = update_task_status(task, TaskStatus.COMPLETED, result=result_data)
    assert task.status == TaskStatus.COMPLETED
    assert task.result == result_data
    assert task.error is None  # Error should be cleared

    # Update with error
    error_msg = "Something went wrong"
    updated_task = update_task_status(task, TaskStatus.FAILED, error=error_msg)
    assert task.status == TaskStatus.FAILED
    assert task.error == error_msg
    assert task.result is None  # Result should be cleared

    # Update with subtasks
    subtask_ids = ["sub1", "sub2"]
    updated_task = update_task_status(task, TaskStatus.RUNNING, subtasks=subtask_ids)
    assert task.subtasks == subtask_ids

    # Test with invalid input type
    with pytest.raises(TypeError):
        update_task_status("not a task message", TaskStatus.FAILED)


# --- Test TaskMessage Serialization/Deserialization ---


def test_task_message_to_from_dict():
    """Test converting TaskMessage to dict and back."""
    now = datetime.now(timezone.utc)
    task = TaskMessage(
        task_id="t-1",
        agent_id="a-1",
        task_type="my_task",
        priority=TaskPriority.CRITICAL,
        status=TaskStatus.RUNNING,
        input_data={"input": 1},
        result={"output": 2},
        error=None,
        created_at=now,
        updated_at=now,
        correlation_id="c-1",
        source_agent_id="s-1",
        parent_task_id="p-1",
        subtasks=["sub-1"],
        metadata={"meta": "data"},
        started_at=now,
        completed_at=now,
        score={"accuracy": 0.9},
        retry_count=1,
    )

    task_dict = task.to_dict()

    # Verify dictionary structure and types
    assert task_dict["task_id"] == "t-1"
    assert task_dict["priority"] == "critical"  # Enum value
    assert task_dict["status"] == "running"  # Enum value
    assert task_dict["created_at"] == now.isoformat()
    assert task_dict["updated_at"] == now.isoformat()
    assert task_dict["started_at"] == now.isoformat()
    assert task_dict["completed_at"] == now.isoformat()
    assert task_dict["input_data"] == {"input": 1}
    assert task_dict["result"] == {"output": 2}
    assert task_dict["subtasks"] == ["sub-1"]
    assert task_dict["metadata"] == {"meta": "data"}
    assert task_dict["score"] == {"accuracy": 0.9}
    assert task_dict["retry_count"] == 1

    # Convert back
    reconstructed_task = TaskMessage.from_dict(task_dict)

    # Compare original and reconstructed
    assert reconstructed_task == task


def test_task_message_from_dict_minimal():
    """Test TaskMessage.from_dict with only required fields."""
    minimal_dict = {
        "task_id": "min-task",
        "agent_id": "min-agent",
        "task_type": "min-type",
        # All other fields omitted
    }

    task = TaskMessage.from_dict(minimal_dict)

    assert task.task_id == "min-task"
    assert task.agent_id == "min-agent"
    assert task.task_type == "min-type"
    # Check defaults for optional fields
    assert task.status == TaskStatus.PENDING
    assert task.priority == TaskPriority.NORMAL
    assert task.input_data == {}
    assert task.result is None
    assert task.error is None
    assert isinstance(task.created_at, datetime)
    assert isinstance(task.updated_at, datetime)
    assert task.subtasks == []
    assert task.metadata == {}


def test_task_message_from_dict_missing_required():
    """Test TaskMessage.from_dict raises ValueError if required fields are missing."""
    bad_dict = {
        "agent_id": "agent",
        "task_type": "type",
        # Missing task_id
    }
    with pytest.raises(ValueError, match="Missing required field"):
        TaskMessage.from_dict(bad_dict)


def test_task_message_from_dict_invalid_enum():
    """Test TaskMessage.from_dict raises ValueError for invalid enum strings."""
    bad_dict = {
        "task_id": "t-enum",
        "agent_id": "a-enum",
        "task_type": "type-enum",
        "status": "INVALID_STATUS_VALUE",
    }
    with pytest.raises(ValueError, match="Error reconstructing TaskMessage"):
        TaskMessage.from_dict(bad_dict)
