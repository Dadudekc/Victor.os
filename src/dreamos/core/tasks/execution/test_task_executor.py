"""
Tests for the enhanced TaskExecutor implementation.
"""

import os
import json
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch

from dreamos.core.tasks.execution.task_executor import TaskExecutor, TaskExecutionError, ProductOutputError
from dreamos.core.tasks.task_nexus import TaskNexus
from dreamos.feedback import FeedbackEngineV2

@pytest.fixture
def task_nexus():
    """Create a mock task nexus."""
    nexus = Mock(spec=TaskNexus)
    nexus.get_task_by_id.return_value = {
        "task_id": "test_task",
        "name": "Test Task",
        "status": "pending"
    }
    return nexus

@pytest.fixture
def feedback_engine():
    """Create a mock feedback engine."""
    return Mock(spec=FeedbackEngineV2)

@pytest.fixture
def executor(task_nexus, feedback_engine):
    """Create a task executor instance."""
    return TaskExecutor(task_nexus, feedback_engine)

@pytest.fixture
def product_output_dir(tmp_path):
    """Create a temporary product output directory."""
    output_dir = tmp_path / "product_outputs"
    output_dir.mkdir()
    return output_dir

@pytest.mark.asyncio
async def test_execute_task_success(executor, task_nexus, feedback_engine):
    """Test successful task execution."""
    # Execute task
    success = await executor.execute_task("test_task", "test_agent")
    
    # Verify success
    assert success is True
    
    # Verify task status updates
    task_nexus.update_task_status.assert_any_call("test_task", "in_progress")
    task_nexus.update_task_status.assert_any_call(
        "test_task",
        "completed",
        result={
            "product_output": {
                "type": "code",
                "content": "# Example product output",
                "metadata": {
                    "language": "python",
                    "quality_score": 0.95
                }
            },
            "user_feedback": {
                "satisfaction": 0.9,
                "comments": "Good output quality"
            }
        }
    )
    
    # Verify feedback collection
    feedback_engine.ingest_feedback.assert_called()

@pytest.mark.asyncio
async def test_execute_task_not_found(executor, task_nexus):
    """Test task execution when task is not found."""
    # Configure mock
    task_nexus.get_task_by_id.return_value = None
    
    # Execute task
    success = await executor.execute_task("nonexistent_task", "test_agent")
    
    # Verify failure
    assert success is False
    
    # Verify task status update
    task_nexus.update_task_status.assert_called_with(
        "nonexistent_task",
        "failed",
        result={"error": "Task nonexistent_task not found for execution"}
    )

@pytest.mark.asyncio
async def test_execute_task_failure(executor, task_nexus):
    """Test task execution failure."""
    # Configure mock to raise exception
    task_nexus.update_task_status.side_effect = Exception("Test error")
    
    # Execute task
    success = await executor.execute_task("test_task", "test_agent")
    
    # Verify failure
    assert success is False
    
    # Verify error handling
    assert "test_task" in executor.quality_metrics
    assert executor.quality_metrics["test_task"]["execution_count"] == 1
    assert executor.quality_metrics["test_task"]["success_count"] == 0

def test_validate_product_output(executor):
    """Test product output validation."""
    # Valid output
    valid_output = {
        "type": "code",
        "content": "# Test code",
        "metadata": {
            "language": "python",
            "quality_score": 0.95
        }
    }
    executor._validate_product_output("test_task", valid_output)
    
    # Invalid output - missing fields
    invalid_output = {
        "type": "code",
        "content": "# Test code"
    }
    with pytest.raises(ProductOutputError):
        executor._validate_product_output("test_task", invalid_output)
    
    # Invalid output - invalid quality score
    invalid_score = {
        "type": "code",
        "content": "# Test code",
        "metadata": {
            "language": "python",
            "quality_score": 1.5  # Invalid score
        }
    }
    with pytest.raises(ProductOutputError):
        executor._validate_product_output("test_task", invalid_score)

def test_package_product_output(executor, product_output_dir):
    """Test product output packaging."""
    # Configure executor
    executor.product_output_dir = product_output_dir
    
    # Package output
    output = {
        "type": "code",
        "content": "# Test code",
        "metadata": {
            "language": "python",
            "quality_score": 0.95
        }
    }
    executor._package_product_output("test_task", output)
    
    # Verify output files
    task_dir = product_output_dir / "test_task"
    assert task_dir.exists()
    assert (task_dir / "output.code").exists()
    assert (task_dir / "metadata.json").exists()
    
    # Verify content
    with open(task_dir / "output.code") as f:
        assert f.read() == "# Test code"
    
    with open(task_dir / "metadata.json") as f:
        metadata = json.load(f)
        assert metadata["language"] == "python"
        assert metadata["quality_score"] == 0.95

def test_track_quality_metrics(executor, feedback_engine):
    """Test quality metrics tracking."""
    # Track metrics
    result = {
        "product_output": {
            "type": "code",
            "content": "# Test code",
            "metadata": {
                "language": "python",
                "quality_score": 0.95
            }
        },
        "user_feedback": {
            "satisfaction": 0.9,
            "comments": "Good output"
        }
    }
    executor._track_quality_metrics("test_task", result)
    
    # Verify metrics
    metrics = executor.quality_metrics["test_task"]
    assert metrics["execution_count"] == 1
    assert metrics["success_count"] == 1
    assert metrics["quality_scores"] == [0.95]
    assert metrics["user_satisfaction"] == [0.9]
    
    # Verify feedback collection
    feedback_engine.ingest_feedback.assert_called_with({
        "event_type": "quality_metrics",
        "task_id": "test_task",
        "metrics": metrics
    })

def test_collect_user_feedback(executor, feedback_engine):
    """Test user feedback collection."""
    # Collect feedback
    feedback = {
        "satisfaction": 0.9,
        "comments": "Good output"
    }
    executor._collect_user_feedback("test_task", feedback)
    
    # Verify feedback collection
    feedback_engine.ingest_feedback.assert_called_with({
        "event_type": "user_feedback",
        "task_id": "test_task",
        "feedback": feedback
    })

def test_handle_task_failure(executor, task_nexus, feedback_engine):
    """Test task failure handling."""
    # Handle failure
    executor._handle_task_failure("test_task", "test_agent", "Test error")
    
    # Verify task status update
    task_nexus.update_task_status.assert_called_with(
        "test_task",
        "failed",
        result={"error": "Test error"}
    )
    
    # Verify metrics
    metrics = executor.quality_metrics["test_task"]
    assert metrics["execution_count"] == 1
    assert metrics["success_count"] == 0
    
    # Verify feedback collection
    feedback_engine.ingest_feedback.assert_called_with({
        "event_type": "task_failure",
        "task_id": "test_task",
        "agent_id": "test_agent",
        "error": "Test error"
    })

def test_get_quality_metrics(executor):
    """Test quality metrics retrieval."""
    # Add some metrics
    executor.quality_metrics["task1"] = {
        "execution_count": 2,
        "success_count": 1,
        "quality_scores": [0.8, 0.9],
        "user_satisfaction": [0.7, 0.8]
    }
    executor.quality_metrics["task2"] = {
        "execution_count": 1,
        "success_count": 1,
        "quality_scores": [0.95],
        "user_satisfaction": [0.9]
    }
    
    # Get all metrics
    all_metrics = executor.get_quality_metrics()
    assert len(all_metrics) == 2
    assert "task1" in all_metrics
    assert "task2" in all_metrics
    
    # Get specific task metrics
    task1_metrics = executor.get_quality_metrics("task1")
    assert task1_metrics["execution_count"] == 2
    assert task1_metrics["success_count"] == 1
    assert task1_metrics["quality_scores"] == [0.8, 0.9]
    assert task1_metrics["user_satisfaction"] == [0.7, 0.8]
    
    # Get nonexistent task metrics
    nonexistent_metrics = executor.get_quality_metrics("nonexistent")
    assert nonexistent_metrics == {} 