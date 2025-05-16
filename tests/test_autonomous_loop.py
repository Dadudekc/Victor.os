"""
Tests for the Dream.OS autonomous loop implementation.
"""

import asyncio
import json
import pytest
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import re
import logging
import os

from dreamos.agents.autonomous_loop import AutonomousLoop
from dreamos.core.coordination.abstract_base_agent import BaseAgent
from dreamos.core.config import AppConfig
from dreamos.core.project_board import ProjectBoardManager
from dreamos.automation.validation_utils import ImprovementValidator, ValidationStatus, ValidationResult

@pytest.fixture
def mock_agent():
    agent = MagicMock(spec=BaseAgent)
    agent.agent_id = "test-agent"
    agent.process_message = AsyncMock()
    return agent

@pytest.fixture
def mock_config():
    config = MagicMock(spec=AppConfig)
    return config

@pytest.fixture
def mock_pbm():
    pbm = MagicMock(spec=ProjectBoardManager)
    pbm.list_working_tasks = MagicMock(return_value=[])
    pbm.claim_task = MagicMock(return_value=True)
    return pbm

@pytest.fixture
def mock_agent_bus():
    bus = MagicMock()
    return bus

@pytest.fixture
def mock_validator():
    validator = MagicMock(spec=ImprovementValidator)
    validation_result_mock = MagicMock(spec=ValidationResult)
    validation_result_mock.status = ValidationStatus.PASSED
    validation_result_mock.message = "Mock validation passed"
    validation_result_mock.details = {}
    validation_result_mock.timestamp = datetime.utcnow().isoformat()
    validator.validate_current_state = AsyncMock(return_value=validation_result_mock)
    return validator

@pytest.fixture
def temp_mailbox(tmp_path):
    mailbox_path = tmp_path / "runtime/agent_comms/agent_mailboxes/test-agent"
    mailbox_path.mkdir(parents=True)
    return mailbox_path

@pytest.fixture
def temp_working_tasks(tmp_path):
    tasks_path = tmp_path / "runtime/agent_comms/agent_mailboxes/working_tasks.json"
    tasks_path.parent.mkdir(parents=True)
    return tasks_path

@pytest.fixture
def temp_episode(tmp_path):
    episode_path = tmp_path / "episodes/episode-launch-final-lock.yaml"
    episode_path.parent.mkdir(parents=True)
    return episode_path

@pytest.fixture
def temp_claim_lock(tmp_path):
    lock_path = tmp_path / "runtime/agent_comms/agent_mailboxes/claim_lock.json"
    lock_path.parent.mkdir(parents=True)
    with open(lock_path, 'w') as f:
        json.dump({"locked_tasks": {}}, f)
    return lock_path

@pytest.fixture
def mock_autonomy_engine(tmp_path):
    """Create a mock autonomy engine with devlog path."""
    engine = MagicMock()
    engine.devlog_path = tmp_path / "runtime" / "devlog" / "agents" / "Agent-1.md"
    engine.devlog_path.parent.mkdir(parents=True, exist_ok=True)
    return engine

@pytest.fixture
def mock_metrics_file(tmp_path):
    """Create a mock metrics file for testing."""
    metrics_path = tmp_path / "episode-metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, 'w') as f:
        json.dump({"tasks": [], "version": "1.0"}, f)
    return metrics_path

@pytest.mark.asyncio
async def test_process_mailbox(mock_agent, mock_config, mock_pbm, temp_mailbox):
    # Setup test mailbox with messages
    inbox_path = temp_mailbox / "inbox.json"
    test_messages = [
        {"type": "test", "content": "message1"},
        {"type": "test", "content": "message2"}
    ]
    with open(inbox_path, 'w') as f:
        json.dump(test_messages, f)
        
    # Create loop instance
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.mailbox_path = temp_mailbox
    
    # Test mailbox processing
    result = await loop._process_mailbox()
    
    # Verify results
    assert result is True
    assert mock_agent.process_message.call_count == 2
    
    # Verify messages were cleared
    with open(inbox_path) as f:
        assert json.load(f) == []

@pytest.mark.asyncio
async def test_check_working_tasks(mock_agent, mock_config, mock_pbm):
    # Setup mock working task
    test_task = {
        "id": "task1",
        "claimed_by": "test-agent",
        "status": "in_progress"
    }
    mock_pbm.list_working_tasks.return_value = [test_task]
    
    # Create loop instance
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    
    # Test working tasks check
    result = await loop._check_working_tasks()
    
    # Verify results
    assert result is not None
    assert result["id"] == "task1"
    assert result["claimed_by"] == "test-agent"
    
    # Verify ProjectBoardManager was called correctly
    mock_pbm.list_working_tasks.assert_called_once_with(agent_id="test-agent")

@pytest.mark.asyncio
async def test_claim_new_task(mock_agent, mock_config, mock_pbm, temp_episode):
    # Setup test episode file
    test_tasks = [
        {
            "id": "task1",
            "priority": 1,
            "description": "Test task 1"
        },
        {
            "id": "task2",
            "priority": 2,
            "description": "Test task 2"
        }
    ]
    with open(temp_episode, 'w') as f:
        yaml.dump({"tasks": test_tasks}, f)
        
    # Create loop instance
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.episode_path = temp_episode
    
    # Test task claiming
    result = await loop._claim_new_task()
    
    # Verify results
    assert result is not None
    assert result["id"] == "task2"  # Higher priority task
    
    # Verify ProjectBoardManager was called correctly
    mock_pbm.claim_task.assert_called_once_with("task2", "test-agent")

@pytest.mark.asyncio
async def test_claim_task_failure(mock_agent, mock_config, mock_pbm, temp_episode):
    # Setup test episode file
    test_tasks = [
        {
            "id": "task1",
            "priority": 1,
            "description": "Test task 1"
        }
    ]
    with open(temp_episode, 'w') as f:
        yaml.dump({"tasks": test_tasks}, f)
        
    # Setup mock to fail task claim
    mock_pbm.claim_task.return_value = False
    
    # Create loop instance
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.episode_path = temp_episode
    
    # Test task claiming
    result = await loop._claim_new_task()
    
    # Verify results
    assert result is None
    
    # Verify ProjectBoardManager was called
    mock_pbm.claim_task.assert_called_once_with("task1", "test-agent")

@pytest.mark.asyncio
async def test_check_blockers(mock_agent, mock_config, mock_pbm, mock_validator):
    # Setup mock validator
    mock_validator.validate_current_state.return_value = MagicMock(
        status="FAIL",
        message="Test validation error"
    )
    
    # Create loop instance with mock validator
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.validator = mock_validator
    
    # Test blocker check
    blockers = await loop._check_blockers()
    
    # Verify results
    assert len(blockers) == 1
    assert blockers[0]["type"] == "validation_error"
    assert blockers[0]["description"] == "Test validation error"
    assert blockers[0]["severity"] == "high"

@pytest.mark.asyncio
async def test_run_loop(mock_agent, mock_config, mock_pbm, temp_mailbox, mock_validator, temp_episode):
    # Setup test mailbox with message
    inbox_path = temp_mailbox / "inbox.json"
    with open(inbox_path, 'w') as f:
        json.dump([{"type": "test", "content": "message"}], f)
        
    # Create loop instance, patching load_config to prevent overwrite of mock_config
    with patch.object(AutonomousLoop, 'load_config', lambda self: None):
        loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    
    loop.mailbox_path = temp_mailbox
    loop.validator = mock_validator
    loop.episode_path = temp_episode

    # Ensure temp_episode is an empty, valid YAML file with an explicit empty tasks list
    with open(temp_episode, 'w') as f:
        yaml.dump({"tasks": []}, f) 
    
    processed_event = asyncio.Event()

    original_process_message = mock_agent.process_message
    async def side_effect_process_message(*args, **kwargs):
        # Call the original mock's behavior (if any, or just record call)
        # For an AsyncMock, just calling it would be `await original_process_message(*args, **kwargs)`
        # but since it's already an AsyncMock, we can just let it be called.
        # The primary goal here is to set the event.
        processed_event.set()
        # If original_process_message is an AsyncMock, it doesn't return a coroutine object
        # unless it's configured with a side_effect that is a coroutine.
        # Default AsyncMock behavior when called is to return another AsyncMock (or None if awaited).
        # To be safe, if we need to ensure it's awaited if it were a real coroutine:
        # return await original_process_message(*args, **kwargs) # This line might be complex if original is just AsyncMock()
        # For now, just set event. The assertion will check call_count.
        if asyncio.iscoroutinefunction(original_process_message):
             await original_process_message(*args, **kwargs)
        elif isinstance(original_process_message, (MagicMock, AsyncMock)):
             original_process_message(*args, **kwargs)


    # Temporarily wrap process_message to set an event
    mock_agent.process_message.side_effect = side_effect_process_message
    
    main_loop_task = None
    stop_task = None

    async def run_and_stop():
        nonlocal main_loop_task, stop_task
        
        async def stop_after_event_and_delay():
            try:
                await asyncio.wait_for(processed_event.wait(), timeout=1.0) # Wait for message to be processed
                await asyncio.sleep(0.05) # Allow loop to cycle once more if needed
            except asyncio.TimeoutError:
                print("Timeout waiting for message to be processed in stop_after_event_and_delay")
            finally:
                loop.stop()

        main_loop_task = asyncio.create_task(loop.run())
        stop_task = asyncio.create_task(stop_after_event_and_delay())
        
        try:
            await asyncio.wait_for(main_loop_task, timeout=2.0) # Overall timeout for the loop run
        except asyncio.TimeoutError:
            print("test_run_loop's loop.run() timed out.")
            if main_loop_task and not main_loop_task.done():
                main_loop_task.cancel()
            # loop.stop() is called in stop_task's finally, or here if that timed out
            if not loop._running: # Check if stop was already called
                 loop.stop()
        except asyncio.CancelledError:
            print("test_run_loop's loop.run() was cancelled.")
        finally:
            if stop_task and not stop_task.done():
                stop_task.cancel()
            # Await tasks to ensure cleanup and propagate exceptions if necessary
            # (though cancellation is expected for main_loop_task if timeout occurs)
            try:
                if main_loop_task: await main_loop_task
            except asyncio.CancelledError:
                pass
            try:
                if stop_task: await stop_task
            except asyncio.CancelledError:
                pass

    await run_and_stop()
    
    # Restore original mock behavior if other tests use the same mock_agent instance
    mock_agent.process_message.side_effect = None 
    
    assert processed_event.is_set(), "The message processing event was not set."
    assert mock_agent.process_message.call_count >= 1 # Ensure it was called
    # To be more precise, if the goal is exactly once:
    assert mock_agent.process_message.call_count == 1

@pytest.mark.asyncio
async def test_resume_on_drift_triggered(mock_agent, mock_config, mock_pbm, temp_mailbox):
    """Test that the loop properly handles drift detection and recovery."""
    # Setup mock agent with drift detection
    mock_agent.detect_drift = AsyncMock(return_value=True)
    mock_agent.resume_from_drift = AsyncMock()
    
    # Create loop instance
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.mailbox_path = temp_mailbox
    
    # Run loop for a short time
    async def stop_after_drift():
        await asyncio.sleep(0.1)  # Allow drift detection to trigger
        loop.stop()
    
    await asyncio.gather(
        loop.run(),
        stop_after_drift()
    )
    
    # Verify drift detection and recovery
    assert mock_agent.detect_drift.called
    assert mock_agent.resume_from_drift.called
    
    # Verify drift recovery parameters
    drift_call = mock_agent.resume_from_drift.call_args
    assert drift_call is not None
    assert isinstance(drift_call[0][0], dict)  # First argument should be drift context
    assert 'timestamp' in drift_call[0][0]
    assert 'detected_at' in drift_call[0][0]

@pytest.mark.asyncio
async def test_devlog_entry_on_task_execution(mock_agent, mock_config, mock_pbm, mock_autonomy_engine):
    """Test that task execution is properly logged in devlog."""
    # Setup mock task
    task_id = "TASK-123"
    mock_pbm.list_working_tasks.return_value = [{
        "id": task_id,
        "status": "IN_PROGRESS",
        "claimed_by": "test-agent"
    }]
    
    # Create loop instance with autonomy engine
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    
    # Simulate task completion
    await loop.process_message({
        "type": "TASK_COMPLETE",
        "task_id": task_id,
        "status": "COMPLETED",
        "summary": "Agent completed refactor loop."
    })
    
    # Verify devlog entry
    assert mock_autonomy_engine.devlog_path.exists()
    contents = mock_autonomy_engine.devlog_path.read_text()
    
    # Check required fields
    assert task_id in contents
    assert "COMPLETED" in contents
    assert "Agent completed refactor loop." in contents
    
    # Verify timestamp format
    timestamp_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    assert re.search(timestamp_pattern, contents) is not None
    
    # Verify entry structure
    assert "## Task Execution" in contents
    assert "### Status" in contents
    assert "### Summary" in contents
    
    # Verify context block if present
    if "### Context" in contents:
        assert "```" in contents  # Code block markers

@pytest.mark.asyncio
async def test_devlog_entry_on_drift_recovery(mock_agent, mock_config, mock_pbm, mock_autonomy_engine):
    """Test that drift recovery is properly logged in devlog."""
    # Setup drift detection
    mock_agent.detect_drift = AsyncMock(return_value=True)
    mock_agent.resume_from_drift = AsyncMock()
    
    # Create loop instance with autonomy engine
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    
    # Run loop briefly to trigger drift
    async def stop_after_drift():
        await asyncio.sleep(0.1)
        loop.stop()
    
    await asyncio.gather(
        loop.run(),
        stop_after_drift()
    )
    
    # Verify devlog entry
    assert mock_autonomy_engine.devlog_path.exists()
    contents = mock_autonomy_engine.devlog_path.read_text()
    
    # Check drift-specific fields
    assert "DRIFT DETECTED" in contents
    assert "RESUMED FROM DRIFT" in contents
    
    # Verify timestamp and structure
    timestamp_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    assert re.search(timestamp_pattern, contents) is not None
    assert "## Drift Recovery" in contents
    assert "### Detection Time" in contents
    assert "### Recovery Details" in contents

@pytest.mark.asyncio
async def test_devlog_entry_invalid_status(mock_agent, mock_config, mock_pbm, mock_autonomy_engine, caplog):
    """Test that invalid status values are properly handled in devlog entries."""
    # Setup logging capture
    caplog.set_level(logging.WARNING)
    
    # Create loop instance with autonomy engine
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    
    # Attempt to log with invalid status
    invalid_status = "WTF"
    await loop.process_message({
        "type": "TASK_COMPLETE",
        "task_id": "TASK-123",
        "status": invalid_status,
        "summary": "This should not be logged with invalid status."
    })
    
    # Verify warning was logged
    assert any(
        "Invalid status" in record.message and invalid_status in record.message
        for record in caplog.records
    )
    
    # Verify devlog was not written or contains error marker
    if mock_autonomy_engine.devlog_path.exists():
        contents = mock_autonomy_engine.devlog_path.read_text()
        assert "INVALID_STATUS" in contents
        assert "WARNING" in contents
        assert invalid_status not in contents  # Raw invalid status should not appear
    else:
        # If file doesn't exist, that's also valid - some implementations might skip invalid entries
        pass
    
    # Verify metrics were not updated for invalid status
    assert not any(
        "metrics" in record.message and "updated" in record.message
        for record in caplog.records
    )

@pytest.mark.asyncio
async def test_devlog_rotation(mock_agent, mock_config, mock_pbm, mock_autonomy_engine):
    """Test that devlog rotation works correctly when size limit is reached."""
    # Setup rotation parameters
    max_size = 1024  # 1KB for testing
    max_backups = 3
    
    # Create loop instance with autonomy engine
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    loop.autonomy_engine.max_log_size = max_size
    loop.autonomy_engine.max_log_backups = max_backups
    
    # Generate large log content
    large_content = "x" * (max_size + 100)  # Exceed max size
    
    # Write initial log
    mock_autonomy_engine.devlog_path.write_text(large_content)
    initial_size = mock_autonomy_engine.devlog_path.stat().st_size
    
    # Trigger rotation by writing new content
    await loop.process_message({
        "type": "TASK_COMPLETE",
        "task_id": "TASK-123",
        "status": "COMPLETED",
        "summary": "This should trigger rotation."
    })
    
    # Verify rotation occurred
    assert mock_autonomy_engine.devlog_path.exists()
    new_size = mock_autonomy_engine.devlog_path.stat().st_size
    assert new_size < initial_size  # New log should be smaller
    
    # Check backup files
    backup_files = list(mock_autonomy_engine.devlog_path.parent.glob("Agent-1.*.md"))
    assert len(backup_files) > 0
    
    # Verify backup naming and content
    latest_backup = max(backup_files, key=lambda p: p.stat().st_mtime)
    assert latest_backup.read_text() == large_content
    
    # Verify new log content
    new_content = mock_autonomy_engine.devlog_path.read_text()
    assert "TASK-123" in new_content
    assert "COMPLETED" in new_content
    assert "This should trigger rotation" in new_content
    
    # Test multiple rotations
    for i in range(max_backups + 1):
        mock_autonomy_engine.devlog_path.write_text(large_content)
        await loop.process_message({
            "type": "TASK_COMPLETE",
            "task_id": f"TASK-{i}",
            "status": "COMPLETED",
            "summary": f"Rotation test {i}"
        })
    
    # Verify backup count is maintained
    backup_files = list(mock_autonomy_engine.devlog_path.parent.glob("Agent-1.*.md"))
    assert len(backup_files) <= max_backups
    
    # Verify oldest backup was removed
    backup_times = [p.stat().st_mtime for p in backup_files]
    assert len(backup_times) == max_backups

@pytest.mark.asyncio
async def test_metrics_sync_on_task_completion(
    mock_agent, 
    mock_config, 
    mock_pbm, 
    mock_autonomy_engine,
    mock_metrics_file
):
    """Test that task completion properly syncs metrics with devlog."""
    # Setup task data
    task_id = "TASK-123"
    start_time = datetime.utcnow()
    
    # Create loop instance with metrics path
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    loop.autonomy_engine.metrics_path = mock_metrics_file
    
    # Simulate task execution
    await loop.process_message({
        "type": "TASK_START",
        "task_id": task_id,
        "timestamp": start_time.isoformat()
    })
    
    # Simulate task completion
    end_time = datetime.utcnow()
    await loop.process_message({
        "type": "TASK_COMPLETE",
        "task_id": task_id,
        "status": "COMPLETED",
        "summary": "Task completed successfully",
        "timestamp": end_time.isoformat()
    })
    
    # Verify devlog entry
    assert mock_autonomy_engine.devlog_path.exists()
    devlog_content = mock_autonomy_engine.devlog_path.read_text()
    assert task_id in devlog_content
    assert "COMPLETED" in devlog_content
    
    # Verify metrics update
    with open(mock_metrics_file) as f:
        metrics = json.load(f)
    
    # Find task in metrics
    task_metrics = next(
        (t for t in metrics["tasks"] if t["task_id"] == task_id),
        None
    )
    assert task_metrics is not None
    
    # Verify metric fields
    assert task_metrics["agent_id"] == mock_agent.agent_id
    assert task_metrics["status"] == "COMPLETED"
    assert "start_time" in task_metrics
    assert "end_time" in task_metrics
    assert "duration" in task_metrics
    
    # Verify timestamps match
    devlog_timestamp = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", devlog_content)
    assert devlog_timestamp is not None
    assert devlog_timestamp.group(0) in task_metrics["end_time"]
    
    # Verify version tracking
    assert "version" in metrics
    assert "sync_id" in task_metrics  # Links metric to devlog entry
    
    # Verify no duplicate entries
    task_count = sum(1 for t in metrics["tasks"] if t["task_id"] == task_id)
    assert task_count == 1

@pytest.mark.asyncio
async def test_task_retry_metrics(
    mock_agent, 
    mock_config, 
    mock_pbm, 
    mock_autonomy_engine,
    mock_metrics_file
):
    """Test that task retries are properly tracked in metrics and devlog."""
    # Setup task data
    task_id = "TASK-123"
    start_time = datetime.utcnow()
    
    # Create loop instance with metrics path
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    loop.autonomy_engine.metrics_path = mock_metrics_file
    
    # Simulate initial task attempt
    await loop.process_message({
        "type": "TASK_START",
        "task_id": task_id,
        "timestamp": start_time.isoformat()
    })
    
    # Simulate first failure
    fail_time = datetime.utcnow()
    await loop.process_message({
        "type": "TASK_FAIL",
        "task_id": task_id,
        "status": "FAILED",
        "error": "Temporary error",
        "timestamp": fail_time.isoformat()
    })
    
    # Simulate retry
    retry_time = datetime.utcnow()
    await loop.process_message({
        "type": "TASK_RETRY",
        "task_id": task_id,
        "retry_count": 1,
        "timestamp": retry_time.isoformat()
    })
    
    # Simulate successful completion after retry
    end_time = datetime.utcnow()
    await loop.process_message({
        "type": "TASK_COMPLETE",
        "task_id": task_id,
        "status": "COMPLETED",
        "summary": "Task completed after retry",
        "timestamp": end_time.isoformat()
    })
    
    # Verify devlog entries
    assert mock_autonomy_engine.devlog_path.exists()
    devlog_content = mock_autonomy_engine.devlog_path.read_text()
    
    # Check for failure and retry entries
    assert "FAILED" in devlog_content
    assert "Temporary error" in devlog_content
    assert "RETRY" in devlog_content
    assert "retry_count: 1" in devlog_content
    
    # Verify metrics update
    with open(mock_metrics_file) as f:
        metrics = json.load(f)
    
    # Find task in metrics
    task_metrics = next(
        (t for t in metrics["tasks"] if t["task_id"] == task_id),
        None
    )
    assert task_metrics is not None
    
    # Verify retry-specific fields
    assert "retry_count" in task_metrics
    assert task_metrics["retry_count"] == 1
    assert "retry_history" in task_metrics
    assert len(task_metrics["retry_history"]) == 1
    
    # Verify retry history entry
    retry_entry = task_metrics["retry_history"][0]
    assert "timestamp" in retry_entry
    assert "error" in retry_entry
    assert retry_entry["error"] == "Temporary error"
    
    # Verify timing information
    assert "total_duration" in task_metrics
    assert "retry_duration" in task_metrics
    assert task_metrics["total_duration"] > task_metrics["retry_duration"]
    
    # Verify final status
    assert task_metrics["status"] == "COMPLETED"
    assert "final_attempt" in task_metrics
    assert task_metrics["final_attempt"] is True

@pytest.mark.asyncio
async def test_metrics_pruning(
    mock_agent, 
    mock_config, 
    mock_pbm, 
    mock_autonomy_engine,
    mock_metrics_file
):
    """Test that metrics are properly pruned based on retention policy."""
    # Setup pruning parameters
    max_entries = 5
    retention_days = 2
    
    # Create loop instance with metrics path and pruning config
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    loop.autonomy_engine.metrics_path = mock_metrics_file
    loop.autonomy_engine.max_metrics_entries = max_entries
    loop.autonomy_engine.metrics_retention_days = retention_days
    
    # Generate test metrics with varying timestamps
    test_metrics = {
        "tasks": [],
        "version": "1.0"
    }
    
    # Add recent tasks (within retention period)
    now = datetime.utcnow()
    for i in range(3):
        test_metrics["tasks"].append({
            "task_id": f"RECENT-{i}",
            "agent_id": mock_agent.agent_id,
            "status": "COMPLETED",
            "start_time": (now - timedelta(hours=i)).isoformat(),
            "end_time": (now - timedelta(hours=i-1)).isoformat(),
            "duration": 3600,
            "sync_id": f"sync-{i}"
        })
    
    # Add old tasks (outside retention period)
    for i in range(3):
        test_metrics["tasks"].append({
            "task_id": f"OLD-{i}",
            "agent_id": mock_agent.agent_id,
            "status": "COMPLETED",
            "start_time": (now - timedelta(days=retention_days + i)).isoformat(),
            "end_time": (now - timedelta(days=retention_days + i - 1)).isoformat(),
            "duration": 3600,
            "sync_id": f"sync-old-{i}"
        })
    
    # Write initial metrics
    with open(mock_metrics_file, 'w') as f:
        json.dump(test_metrics, f)
    
    # Trigger pruning
    await loop.process_message({
        "type": "METRICS_PRUNE",
        "timestamp": now.isoformat()
    })
    
    # Verify metrics after pruning
    with open(mock_metrics_file) as f:
        pruned_metrics = json.load(f)
    
    # Verify entry count
    assert len(pruned_metrics["tasks"]) <= max_entries
    
    # Verify only recent tasks remain
    remaining_tasks = pruned_metrics["tasks"]
    for task in remaining_tasks:
        task_time = datetime.fromisoformat(task["start_time"])
        assert (now - task_time).days < retention_days
        assert task["task_id"].startswith("RECENT")
    
    # Verify no old tasks remain
    old_tasks = [t for t in remaining_tasks if t["task_id"].startswith("OLD")]
    assert len(old_tasks) == 0
    
    # Verify metrics integrity
    assert "version" in pruned_metrics
    assert pruned_metrics["version"] == test_metrics["version"]
    
    # Verify task data integrity
    for task in remaining_tasks:
        assert all(key in task for key in [
            "task_id", "agent_id", "status", "start_time",
            "end_time", "duration", "sync_id"
        ])
    
    # Verify pruning log entry
    assert mock_autonomy_engine.devlog_path.exists()
    devlog_content = mock_autonomy_engine.devlog_path.read_text()
    assert "METRICS PRUNED" in devlog_content
    assert str(len(old_tasks)) in devlog_content  # Number of pruned entries

@pytest.mark.asyncio
async def test_schema_evolution(
    mock_agent, 
    mock_config, 
    mock_pbm, 
    mock_autonomy_engine,
    mock_metrics_file
):
    """Test that the system handles telemetry schema evolution gracefully."""
    # Setup schema versions
    current_version = "2.0"
    legacy_version = "1.0"
    
    # Create loop instance with metrics path
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    loop.autonomy_engine.metrics_path = mock_metrics_file
    loop.autonomy_engine.current_schema_version = current_version
    
    # Generate legacy metrics format
    legacy_metrics = {
        "tasks": [
            {
                "task_id": "LEGACY-1",
                "agent_id": mock_agent.agent_id,
                "status": "COMPLETED",
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "duration": 3600
                # Missing sync_id and other v2 fields
            }
        ],
        "version": legacy_version
    }
    
    # Write legacy metrics
    with open(mock_metrics_file, 'w') as f:
        json.dump(legacy_metrics, f)
    
    # Setup schema migration mock
    mock_autonomy_engine.migrate_metrics_schema = AsyncMock()
    mock_autonomy_engine.migrate_metrics_schema.return_value = {
        "tasks": [
            {
                "task_id": "LEGACY-1",
                "agent_id": mock_agent.agent_id,
                "status": "COMPLETED",
                "start_time": legacy_metrics["tasks"][0]["start_time"],
                "end_time": legacy_metrics["tasks"][0]["end_time"],
                "duration": 3600,
                "sync_id": "migrated-sync-1",  # Added in v2
                "schema_version": current_version  # Added in v2
            }
        ],
        "version": current_version
    }
    
    # Trigger schema check
    await loop.process_message({
        "type": "SCHEMA_CHECK",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify migration was attempted
    mock_autonomy_engine.migrate_metrics_schema.assert_called_once()
    
    # Verify metrics after migration
    with open(mock_metrics_file) as f:
        migrated_metrics = json.load(f)
    
    # Verify version update
    assert migrated_metrics["version"] == current_version
    
    # Verify task data migration
    migrated_task = migrated_metrics["tasks"][0]
    assert "sync_id" in migrated_task
    assert "schema_version" in migrated_task
    assert migrated_task["schema_version"] == current_version
    
    # Verify original data preserved
    assert migrated_task["task_id"] == legacy_metrics["tasks"][0]["task_id"]
    assert migrated_task["status"] == legacy_metrics["tasks"][0]["status"]
    assert migrated_task["duration"] == legacy_metrics["tasks"][0]["duration"]
    
    # Verify devlog entry
    assert mock_autonomy_engine.devlog_path.exists()
    devlog_content = mock_autonomy_engine.devlog_path.read_text()
    assert "SCHEMA MIGRATION" in devlog_content
    assert legacy_version in devlog_content
    assert current_version in devlog_content
    
    # Test graceful failure handling
    mock_autonomy_engine.migrate_metrics_schema.side_effect = Exception("Migration failed")
    
    # Trigger schema check with failure
    with pytest.raises(Exception) as exc_info:
        await loop.process_message({
            "type": "SCHEMA_CHECK",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Verify error was logged
    assert "Migration failed" in str(exc_info.value)
    
    # Verify metrics file wasn't corrupted
    with open(mock_metrics_file) as f:
        final_metrics = json.load(f)
    assert final_metrics["version"] == current_version  # Should retain last good state

@pytest.mark.asyncio
async def test_corrupt_metrics_recovery(
    mock_agent, 
    mock_config, 
    mock_pbm, 
    mock_autonomy_engine,
    mock_metrics_file
):
    """Test that the system can recover from corrupt metrics files."""
    # Setup backup path
    backup_path = mock_metrics_file.parent / f"{mock_metrics_file.stem}.backup.json"
    
    # Create loop instance with metrics path
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    loop.autonomy_engine.metrics_path = mock_metrics_file
    loop.autonomy_engine.metrics_backup_path = backup_path
    
    # Generate valid metrics
    valid_metrics = {
        "tasks": [
            {
                "task_id": "VALID-1",
                "agent_id": mock_agent.agent_id,
                "status": "COMPLETED",
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "duration": 3600,
                "sync_id": "sync-1",
                "schema_version": "2.0"
            }
        ],
        "version": "2.0"
    }
    
    # Write valid metrics and create backup
    with open(mock_metrics_file, 'w') as f:
        json.dump(valid_metrics, f)
    with open(backup_path, 'w') as f:
        json.dump(valid_metrics, f)
    
    # Corrupt the metrics file
    with open(mock_metrics_file, 'w') as f:
        f.write('{"tasks": [{"task_id": "CORRUPT-1", "status": "IN_PROGRESS"')  # Truncated JSON
    
    # Setup recovery mock
    mock_autonomy_engine.recover_metrics = AsyncMock()
    mock_autonomy_engine.recover_metrics.return_value = valid_metrics
    
    # Trigger metrics read (should detect corruption)
    with pytest.raises(json.JSONDecodeError):
        await loop.process_message({
            "type": "METRICS_READ",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Verify recovery was attempted
    mock_autonomy_engine.recover_metrics.assert_called_once()
    
    # Verify metrics after recovery
    with open(mock_metrics_file) as f:
        recovered_metrics = json.load(f)
    
    # Verify data integrity
    assert recovered_metrics["version"] == valid_metrics["version"]
    assert len(recovered_metrics["tasks"]) == len(valid_metrics["tasks"])
    assert recovered_metrics["tasks"][0]["task_id"] == valid_metrics["tasks"][0]["task_id"]
    
    # Verify backup was preserved
    assert backup_path.exists()
    with open(backup_path) as f:
        backup_metrics = json.load(f)
    assert backup_metrics == valid_metrics
    
    # Test recovery from missing file
    mock_metrics_file.unlink()
    mock_autonomy_engine.recover_metrics.reset_mock()
    
    # Trigger metrics read with missing file
    await loop.process_message({
        "type": "METRICS_READ",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify recovery from backup
    mock_autonomy_engine.recover_metrics.assert_called_once()
    assert mock_metrics_file.exists()
    
    # Verify devlog entries
    assert mock_autonomy_engine.devlog_path.exists()
    devlog_content = mock_autonomy_engine.devlog_path.read_text()
    assert "METRICS RECOVERY" in devlog_content
    assert "CORRUPT" in devlog_content
    assert "RESTORED" in devlog_content

@pytest.mark.asyncio
async def test_agent_scoring(
    mock_agent, 
    mock_config, 
    mock_pbm, 
    mock_autonomy_engine,
    mock_metrics_file
):
    """Test that agent scoring and competition metrics are properly tracked."""
    # Setup scoring paths
    leaderboard_path = mock_metrics_file.parent / "leaderboard.json"
    score_history_path = mock_metrics_file.parent / "score_history.json"
    
    # Create loop instance with scoring paths
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    loop.autonomy_engine.metrics_path = mock_metrics_file
    loop.autonomy_engine.leaderboard_path = leaderboard_path
    loop.autonomy_engine.score_history_path = score_history_path
    
    # Initialize leaderboard
    initial_leaderboard = {
        "agents": {
            mock_agent.agent_id: {
                "score": 0,
                "rank": 1,
                "tasks_completed": 0,
                "help_points": 0,
                "recovery_points": 0,
                "last_updated": datetime.utcnow().isoformat()
            }
        },
        "version": "1.0"
    }
    
    with open(leaderboard_path, 'w') as f:
        json.dump(initial_leaderboard, f)
    
    # Test task completion scoring
    await loop.process_message({
        "type": "TASK_COMPLETE",
        "task_id": "TASK-1",
        "status": "COMPLETED",
        "score": 5,  # Base points for completion
        "bonus": 2,  # Extra points for quality
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify leaderboard update
    with open(leaderboard_path) as f:
        updated_leaderboard = json.load(f)
    
    agent_stats = updated_leaderboard["agents"][mock_agent.agent_id]
    assert agent_stats["score"] == 7  # Base + bonus
    assert agent_stats["tasks_completed"] == 1
    
    # Test help points
    await loop.process_message({
        "type": "AGENT_HELP",
        "helper_id": mock_agent.agent_id,
        "helped_id": "other-agent",
        "help_type": "code_review",
        "points": 3,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify help points added
    with open(leaderboard_path) as f:
        updated_leaderboard = json.load(f)
    
    agent_stats = updated_leaderboard["agents"][mock_agent.agent_id]
    assert agent_stats["help_points"] == 3
    assert agent_stats["score"] == 10  # Previous + help points
    
    # Test recovery points
    await loop.process_message({
        "type": "RECOVERY_SUCCESS",
        "agent_id": mock_agent.agent_id,
        "recovery_type": "drift",
        "points": 4,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify recovery points
    with open(leaderboard_path) as f:
        updated_leaderboard = json.load(f)
    
    agent_stats = updated_leaderboard["agents"][mock_agent.agent_id]
    assert agent_stats["recovery_points"] == 4
    assert agent_stats["score"] == 14  # Previous + recovery points
    
    # Verify score history
    assert score_history_path.exists()
    with open(score_history_path) as f:
        history = json.load(f)
    
    assert len(history["entries"]) == 3  # One entry per scoring event
    assert all("timestamp" in entry for entry in history["entries"])
    assert all("points" in entry for entry in history["entries"])
    assert all("reason" in entry for entry in history["entries"])
    
    # Verify devlog entries
    assert mock_autonomy_engine.devlog_path.exists()
    devlog_content = mock_autonomy_engine.devlog_path.read_text()
    assert "SCORE UPDATE" in devlog_content
    assert str(agent_stats["score"]) in devlog_content

@pytest.mark.asyncio
async def test_leaderboard_ranking(
    mock_agent, 
    mock_config, 
    mock_pbm, 
    mock_autonomy_engine,
    mock_metrics_file
):
    """Test that agent rankings are properly calculated and updated."""
    # Setup leaderboard with multiple agents
    leaderboard_path = mock_metrics_file.parent / "leaderboard.json"
    
    # Create loop instance
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    loop.autonomy_engine.leaderboard_path = leaderboard_path
    
    # Initialize multi-agent leaderboard
    initial_leaderboard = {
        "agents": {
            "agent-1": {"score": 10, "rank": 1},
            "agent-2": {"score": 20, "rank": 2},
            "agent-3": {"score": 15, "rank": 3}
        },
        "version": "1.0"
    }
    
    with open(leaderboard_path, 'w') as f:
        json.dump(initial_leaderboard, f)
    
    # Trigger score update that should change rankings
    await loop.process_message({
        "type": "SCORE_UPDATE",
        "agent_id": "agent-1",
        "points": 15,  # Should move to rank 1
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify rankings updated
    with open(leaderboard_path) as f:
        updated_leaderboard = json.load(f)
    
    # Check new rankings
    assert updated_leaderboard["agents"]["agent-1"]["rank"] == 1
    assert updated_leaderboard["agents"]["agent-2"]["rank"] == 2
    assert updated_leaderboard["agents"]["agent-3"]["rank"] == 3
    
    # Verify rank change logged
    assert mock_autonomy_engine.devlog_path.exists()
    devlog_content = mock_autonomy_engine.devlog_path.read_text()
    assert "RANK CHANGE" in devlog_content
    assert "agent-1" in devlog_content
    assert "1" in devlog_content  # New rank 

@pytest.mark.asyncio
async def test_discord_leaderboard_poster(
    mock_agent, 
    mock_config, 
    mock_pbm, 
    mock_autonomy_engine,
    mock_metrics_file
):
    """Test that leaderboard updates are properly posted to Discord."""
    # Setup Discord webhook mock
    mock_webhook = AsyncMock()
    mock_autonomy_engine.discord_webhook = mock_webhook
    
    # Create loop instance
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    
    # Setup leaderboard with rich data
    leaderboard_data = {
        "agents": {
            "agent-7": {
                "score": 412,
                "rank": 1,
                "tasks_completed": 6,
                "drift_events": 0,
                "last_updated": datetime.utcnow().isoformat()
            },
            "agent-3": {
                "score": 394,
                "rank": 2,
                "tasks_completed": 5,
                "drift_events": 1,
                "last_updated": datetime.utcnow().isoformat()
            },
            "agent-5": {
                "score": 362,
                "rank": 3,
                "tasks_completed": 4,
                "drift_events": 2,
                "last_updated": datetime.utcnow().isoformat()
            }
        },
        "version": "1.0",
        "last_posted": (datetime.utcnow() - timedelta(hours=1)).isoformat()
    }
    
    # Setup score history for delta calculation
    score_history = {
        "entries": [
            {
                "agent_id": "agent-4",
                "points": 110,
                "timestamp": datetime.utcnow().isoformat(),
                "reason": "task_completion"
            }
        ]
    }
    
    # Write test data
    leaderboard_path = mock_metrics_file.parent / "leaderboard.json"
    history_path = mock_metrics_file.parent / "score_history.json"
    
    with open(leaderboard_path, 'w') as f:
        json.dump(leaderboard_data, f)
    with open(history_path, 'w') as f:
        json.dump(score_history, f)
    
    # Trigger leaderboard update
    await loop.process_message({
        "type": "LEADERBOARD_UPDATE",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify Discord webhook was called
    mock_webhook.send.assert_called_once()
    
    # Get the posted message
    posted_message = mock_webhook.send.call_args[1]["content"]
    
    # Verify message structure
    assert "🏁 Dream.OS Agent Leaderboard" in posted_message
    assert "Updated every hour" in posted_message
    
    # Verify rankings
    assert "🥇 Agent-7 — 412 pts" in posted_message
    assert "🥈 Agent-3 — 394 pts" in posted_message
    assert "🥉 Agent-5 — 362 pts" in posted_message
    
    # Verify stats
    assert "Top performer: Agent-7 (6 task wins, 0 drift events)" in posted_message
    assert "Most improved: Agent-4 (+110 pts since last hour)" in posted_message
    
    # Test pin/unpin logic
    mock_webhook.pin_message = AsyncMock()
    mock_webhook.unpin_message = AsyncMock()
    
    # Trigger pin update
    await loop.process_message({
        "type": "LEADERBOARD_PIN",
        "message_id": "123456",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify pin/unpin
    mock_webhook.pin_message.assert_called_once()
    mock_webhook.unpin_message.assert_called_once()
    
    # Test error handling
    mock_webhook.send.side_effect = Exception("Discord API error")
    
    # Verify error is caught and logged
    with pytest.raises(Exception) as exc_info:
        await loop.process_message({
            "type": "LEADERBOARD_UPDATE",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    assert "Discord API error" in str(exc_info.value)
    
    # Verify error was logged
    assert mock_autonomy_engine.devlog_path.exists()
    devlog_content = mock_autonomy_engine.devlog_path.read_text()
    assert "LEADERBOARD POST FAILED" in devlog_content
    assert "Discord API error" in devlog_content 

@pytest.mark.asyncio
async def test_point_decay(
    mock_agent, 
    mock_config, 
    mock_pbm, 
    mock_autonomy_engine,
    mock_metrics_file
):
    """Test that agent points decay properly based on inactivity."""
    # Setup decay parameters
    decay_rate = 5  # points per day
    decay_threshold = 2  # days before decay starts
    
    # Create loop instance with decay config
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    loop.autonomy_engine.point_decay_rate = decay_rate
    loop.autonomy_engine.decay_threshold_days = decay_threshold
    
    # Setup leaderboard with mixed activity
    now = datetime.utcnow()
    leaderboard_data = {
        "agents": {
            "agent-4": {
                "score": 300,
                "rank": 4,
                "last_activity": (now - timedelta(days=3)).isoformat(),
                "streak_days": 0,
                "last_updated": now.isoformat()
            },
            "agent-6": {
                "score": 290,
                "rank": 5,
                "last_activity": now.isoformat(),
                "streak_days": 5,
                "last_updated": now.isoformat()
            }
        },
        "version": "1.0"
    }
    
    # Write test data
    leaderboard_path = mock_metrics_file.parent / "leaderboard.json"
    with open(leaderboard_path, 'w') as f:
        json.dump(leaderboard_data, f)
    
    # Trigger decay check
    await loop.process_message({
        "type": "DECAY_CHECK",
        "timestamp": now.isoformat()
    })
    
    # Verify leaderboard update
    with open(leaderboard_path) as f:
        updated_leaderboard = json.load(f)
    
    # Check decay applied
    agent_4 = updated_leaderboard["agents"]["agent-4"]
    assert agent_4["score"] == 285  # 300 - (5 * 3 days)
    assert agent_4["rank"] == 5  # Should drop rank
    
    # Check active agent unaffected
    agent_6 = updated_leaderboard["agents"]["agent-6"]
    assert agent_6["score"] == 290  # No decay
    assert agent_6["rank"] == 4  # Should move up
    
    # Verify decay log entry
    assert mock_autonomy_engine.devlog_path.exists()
    devlog_content = mock_autonomy_engine.devlog_path.read_text()
    assert "POINT DECAY" in devlog_content
    assert "agent-4" in devlog_content
    assert "-15" in devlog_content  # Decay amount
    
    # Test streak bonus
    await loop.process_message({
        "type": "TASK_COMPLETE",
        "agent_id": "agent-6",
        "score": 10,
        "timestamp": now.isoformat()
    })
    
    # Verify streak bonus applied
    with open(leaderboard_path) as f:
        final_leaderboard = json.load(f)
    
    agent_6 = final_leaderboard["agents"]["agent-6"]
    assert agent_6["streak_days"] == 6
    assert agent_6["score"] == 305  # 290 + 10 + 5 streak bonus
    
    # Test decay reset on activity
    await loop.process_message({
        "type": "TASK_COMPLETE",
        "agent_id": "agent-4",
        "score": 5,
        "timestamp": now.isoformat()
    })
    
    # Verify decay reset
    with open(leaderboard_path) as f:
        final_leaderboard = json.load(f)
    
    agent_4 = final_leaderboard["agents"]["agent-4"]
    assert agent_4["last_activity"] == now.isoformat()
    assert agent_4["streak_days"] == 1
    
    # Verify Discord update
    mock_webhook = mock_autonomy_engine.discord_webhook
    assert mock_webhook.send.called
    
    # Check decay message in Discord update
    posted_message = mock_webhook.send.call_args[1]["content"]
    assert "❄️ Agent-4: -15 pts (inactive 3 days)" in posted_message
    assert "🔼 Agent-6 overtook due to consistent execution" in posted_message
    assert "🔥 Agent-6: +15 pts (6 day streak)" in posted_message 

@pytest.mark.asyncio
async def test_rank_based_task_difficulty(
    mock_agent, 
    mock_config, 
    mock_pbm, 
    mock_autonomy_engine,
    mock_metrics_file
):
    """Test that tasks are assigned based on agent rank with appropriate rewards."""
    # Setup rank-based task rules
    task_rules = {
        "elite": {
            "min_rank": 1,
            "max_rank": 3,
            "difficulty": "HIGH_PRIORITY",
            "reward_multiplier": 2.0
        },
        "core": {
            "min_rank": 4,
            "max_rank": 6,
            "difficulty": "NORMAL",
            "reward_multiplier": 1.0
        },
        "support": {
            "min_rank": 7,
            "max_rank": 8,
            "difficulty": "REPAIR",
            "reward_multiplier": 0.8
        }
    }
    
    # Create loop instance with task rules
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    loop.autonomy_engine.task_rules = task_rules
    
    # Setup leaderboard with ranked agents
    leaderboard_data = {
        "agents": {
            "agent-1": {
                "score": 500,
                "rank": 1,
                "last_activity": datetime.utcnow().isoformat(),
                "streak_days": 10
            },
            "agent-4": {
                "score": 300,
                "rank": 4,
                "last_activity": datetime.utcnow().isoformat(),
                "streak_days": 5
            },
            "agent-7": {
                "score": 200,
                "rank": 7,
                "last_activity": datetime.utcnow().isoformat(),
                "streak_days": 2
            }
        },
        "version": "1.0"
    }
    
    # Write leaderboard
    leaderboard_path = mock_metrics_file.parent / "leaderboard.json"
    with open(leaderboard_path, 'w') as f:
        json.dump(leaderboard_data, f)
    
    # Setup task board with difficulty levels
    task_board = {
        "tasks": [
            {
                "id": "HIGH-1",
                "difficulty": "HIGH_PRIORITY",
                "base_reward": 50,
                "description": "Critical system optimization"
            },
            {
                "id": "NORM-1",
                "difficulty": "NORMAL",
                "base_reward": 30,
                "description": "Feature implementation"
            },
            {
                "id": "REPAIR-1",
                "difficulty": "REPAIR",
                "base_reward": 20,
                "description": "System cleanup"
            }
        ]
    }
    
    # Mock ProjectBoardManager task assignment
    mock_pbm.get_next_task = AsyncMock()
    mock_pbm.get_next_task.side_effect = lambda agent_id: {
        "agent-1": task_board["tasks"][0],
        "agent-4": task_board["tasks"][1],
        "agent-7": task_board["tasks"][2]
    }[agent_id]
    
    # Test elite agent task assignment
    elite_task = await loop.process_message({
        "type": "TASK_REQUEST",
        "agent_id": "agent-1",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    assert elite_task["difficulty"] == "HIGH_PRIORITY"
    assert elite_task["id"] == "HIGH-1"
    
    # Test core agent task assignment
    core_task = await loop.process_message({
        "type": "TASK_REQUEST",
        "agent_id": "agent-4",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    assert core_task["difficulty"] == "NORMAL"
    assert core_task["id"] == "NORM-1"
    
    # Test support agent task assignment
    support_task = await loop.process_message({
        "type": "TASK_REQUEST",
        "agent_id": "agent-7",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    assert support_task["difficulty"] == "REPAIR"
    assert support_task["id"] == "REPAIR-1"
    
    # Test reward scaling
    await loop.process_message({
        "type": "TASK_COMPLETE",
        "agent_id": "agent-1",
        "task_id": "HIGH-1",
        "status": "COMPLETED",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify scaled reward
    with open(leaderboard_path) as f:
        updated_leaderboard = json.load(f)
    
    elite_agent = updated_leaderboard["agents"]["agent-1"]
    assert elite_agent["score"] == 600  # 500 + (50 * 2.0)
    
    # Verify Discord update
    mock_webhook = mock_autonomy_engine.discord_webhook
    assert mock_webhook.send.called
    
    # Check reward message
    posted_message = mock_webhook.send.call_args[1]["content"]
    assert "🏆 Elite Task Completed" in posted_message
    assert "2.0x reward multiplier" in posted_message
    assert "+100 pts" in posted_message
    
    # Test rank promotion
    await loop.process_message({
        "type": "TASK_COMPLETE",
        "agent_id": "agent-4",
        "task_id": "NORM-1",
        "status": "COMPLETED",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify rank change
    with open(leaderboard_path) as f:
        final_leaderboard = json.load(f)
    
    promoted_agent = final_leaderboard["agents"]["agent-4"]
    assert promoted_agent["rank"] == 3  # Moved to elite tier
    
    # Verify promotion message
    posted_message = mock_webhook.send.call_args[1]["content"]
    assert "🌟 Rank Up" in posted_message
    assert "agent-4" in posted_message
    assert "Elite Tier" in posted_message 

@pytest.mark.asyncio
async def test_weekly_rank_reset(
    mock_agent, 
    mock_config, 
    mock_pbm, 
    mock_autonomy_engine,
    mock_metrics_file
):
    """Test that weekly rank resets preserve titles and handle transitions gracefully."""
    # Setup title tiers and retention rules
    title_rules = {
        "elite": {
            "min_rank": 1,
            "max_rank": 3,
            "title": "Elite Agent",
            "retention_threshold": 0.7  # Keep title if score > 70% of previous
        },
        "core": {
            "min_rank": 4,
            "max_rank": 6,
            "title": "Core Agent",
            "retention_threshold": 0.6
        },
        "support": {
            "min_rank": 7,
            "max_rank": 8,
            "title": "Support Agent",
            "retention_threshold": 0.5
        }
    }
    
    # Create loop instance with title rules
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    loop.autonomy_engine.title_rules = title_rules
    
    # Setup leaderboard with current week's data
    now = datetime.utcnow()
    last_week = now - timedelta(days=7)
    
    leaderboard_data = {
        "agents": {
            "agent-1": {
                "score": 1000,
                "rank": 1,
                "title": "Elite Agent",
                "last_week_score": 800,
                "titles_held": 3,
                "last_updated": now.isoformat()
            },
            "agent-4": {
                "score": 600,
                "rank": 4,
                "title": "Core Agent",
                "last_week_score": 500,
                "titles_held": 2,
                "last_updated": now.isoformat()
            },
            "agent-7": {
                "score": 300,
                "rank": 7,
                "title": "Support Agent",
                "last_week_score": 400,
                "titles_held": 1,
                "last_updated": now.isoformat()
            }
        },
        "version": "1.0",
        "last_reset": last_week.isoformat()
    }
    
    # Write leaderboard
    leaderboard_path = mock_metrics_file.parent / "leaderboard.json"
    with open(leaderboard_path, 'w') as f:
        json.dump(leaderboard_data, f)
    
    # Trigger weekly reset
    await loop.process_message({
        "type": "WEEKLY_RESET",
        "timestamp": now.isoformat()
    })
    
    # Verify leaderboard after reset
    with open(leaderboard_path) as f:
        reset_leaderboard = json.load(f)
    
    # Check elite agent (should retain title)
    elite_agent = reset_leaderboard["agents"]["agent-1"]
    assert elite_agent["title"] == "Elite Agent"
    assert elite_agent["titles_held"] == 4
    assert elite_agent["last_week_score"] == 1000
    assert elite_agent["score"] == 0  # Score reset
    
    # Check core agent (should retain title)
    core_agent = reset_leaderboard["agents"]["agent-4"]
    assert core_agent["title"] == "Core Agent"
    assert core_agent["titles_held"] == 3
    assert core_agent["last_week_score"] == 600
    assert core_agent["score"] == 0
    
    # Check support agent (should retain title)
    support_agent = reset_leaderboard["agents"]["agent-7"]
    assert support_agent["title"] == "Support Agent"
    assert support_agent["titles_held"] == 2
    assert support_agent["last_week_score"] == 300
    assert support_agent["score"] == 0
    
    # Test title loss scenario
    leaderboard_data["agents"]["agent-1"]["score"] = 400  # Below retention threshold
    with open(leaderboard_path, 'w') as f:
        json.dump(leaderboard_data, f)
    
    # Trigger another reset
    await loop.process_message({
        "type": "WEEKLY_RESET",
        "timestamp": (now + timedelta(days=7)).isoformat()
    })
    
    # Verify title loss
    with open(leaderboard_path) as f:
        final_leaderboard = json.load(f)
    
    fallen_agent = final_leaderboard["agents"]["agent-1"]
    assert fallen_agent["title"] == "Core Agent"  # Demoted
    assert fallen_agent["titles_held"] == 0  # Reset
    assert fallen_agent["last_week_score"] == 400
    
    # Verify Discord updates
    mock_webhook = mock_autonomy_engine.discord_webhook
    assert mock_webhook.send.called
    
    # Check reset message
    posted_message = mock_webhook.send.call_args[1]["content"]
    assert "🔄 Weekly Reset" in posted_message
    assert "Elite Agent" in posted_message
    assert "4 weeks" in posted_message  # Title held duration
    
    # Check title loss message
    assert "📉 Title Lost" in posted_message
    assert "agent-1" in posted_message
    assert "Core Agent" in posted_message 

@pytest.mark.asyncio
async def test_elite_challenge_tasks(
    mock_agent, 
    mock_config, 
    mock_pbm, 
    mock_autonomy_engine,
    mock_metrics_file
):
    """Test that elite agents can take on special challenge tasks with high rewards and risks."""
    # Setup challenge task rules
    challenge_rules = {
        "difficulty": "elite",
        "reward_multiplier": 3.0,
        "penalty_multiplier": 2.0,
        "immunity_days": 7,
        "min_title_held": 2  # Weeks
    }
    
    # Create loop instance with challenge rules
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    loop.autonomy_engine.challenge_rules = challenge_rules
    
    # Setup leaderboard with elite agents
    leaderboard_data = {
        "agents": {
            "agent-1": {
                "score": 1000,
                "rank": 1,
                "title": "Elite Agent",
                "titles_held": 3,
                "immunity_until": None,
                "last_updated": datetime.utcnow().isoformat()
            },
            "agent-2": {
                "score": 900,
                "rank": 2,
                "title": "Elite Agent",
                "titles_held": 2,
                "immunity_until": None,
                "last_updated": datetime.utcnow().isoformat()
            }
        },
        "version": "1.0"
    }
    
    # Write leaderboard
    leaderboard_path = mock_metrics_file.parent / "leaderboard.json"
    with open(leaderboard_path, 'w') as f:
        json.dump(leaderboard_data, f)
    
    # Setup challenge task
    challenge_task = {
        "id": "ELITE-1",
        "type": "challenge",
        "difficulty": "elite",
        "base_reward": 100,
        "description": "System-wide optimization challenge",
        "requirements": {
            "min_title_held": 2,
            "min_score": 800
        }
    }
    
    # Mock ProjectBoardManager for challenge task
    mock_pbm.get_challenge_task = AsyncMock(return_value=challenge_task)
    
    # Test challenge task assignment
    task = await loop.process_message({
        "type": "CHALLENGE_REQUEST",
        "agent_id": "agent-1",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    assert task["type"] == "challenge"
    assert task["difficulty"] == "elite"
    
    # Test successful challenge completion
    await loop.process_message({
        "type": "CHALLENGE_COMPLETE",
        "agent_id": "agent-1",
        "task_id": "ELITE-1",
        "status": "COMPLETED",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify reward and immunity
    with open(leaderboard_path) as f:
        updated_leaderboard = json.load(f)
    
    elite_agent = updated_leaderboard["agents"]["agent-1"]
    assert elite_agent["score"] == 1300  # 1000 + (100 * 3.0)
    assert elite_agent["immunity_until"] is not None
    
    # Test challenge failure
    await loop.process_message({
        "type": "CHALLENGE_FAIL",
        "agent_id": "agent-2",
        "task_id": "ELITE-2",
        "error": "Drift detected",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify penalty
    with open(leaderboard_path) as f:
        final_leaderboard = json.load(f)
    
    failed_agent = final_leaderboard["agents"]["agent-2"]
    assert failed_agent["title"] == "Core Agent"  # Demoted
    assert failed_agent["titles_held"] == 0  # Reset
    
    # Test agent trial (head-to-head)
    trial_task = {
        "id": "TRIAL-1",
        "type": "trial",
        "agents": ["agent-1", "agent-2"],
        "base_reward": 150,
        "description": "Performance optimization race"
    }
    
    mock_pbm.get_trial_task = AsyncMock(return_value=trial_task)
    
    # Start trial
    trial = await loop.process_message({
        "type": "TRIAL_START",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    assert trial["type"] == "trial"
    assert len(trial["agents"]) == 2
    
    # Verify Discord updates
    mock_webhook = mock_autonomy_engine.discord_webhook
    assert mock_webhook.send.called
    
    # Check challenge messages
    posted_message = mock_webhook.send.call_args[1]["content"]
    assert "🏆 Elite Challenge" in posted_message
    assert "3.0x reward multiplier" in posted_message
    assert "🛡️ Immunity granted" in posted_message
    
    # Check failure message
    assert "📉 Challenge Failed" in posted_message
    assert "Demoted to Core Agent" in posted_message
    
    # Check trial message
    assert "⚔️ Agent Trial" in posted_message
    assert "agent-1 vs agent-2" in posted_message 

@pytest.mark.asyncio
async def test_trial_matchmaking(
    mock_agent, 
    mock_config, 
    mock_pbm, 
    mock_autonomy_engine,
    mock_metrics_file
):
    """Test that elite agents can be matched for head-to-head trials."""
    # Setup trial rules
    trial_rules = {
        "rotation": "weekly",
        "min_elite_agents": 2,
        "max_trials_per_week": 3,
        "deadline_hours": 24,
        "winner_bonus": {
            "rank_boost": 3,
            "next_spotlight": True
        },
        "loser_penalty": {
            "drift_risk": 2.0,
            "decay_multiplier": 1.5
        }
    }
    
    # Create loop instance with trial rules
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    loop.autonomy_engine.trial_rules = trial_rules
    
    # Setup leaderboard with multiple elite agents
    leaderboard_data = {
        "agents": {
            "agent-1": {
                "score": 1000,
                "rank": 1,
                "title": "Elite Agent",
                "titles_held": 3,
                "last_trial": None,
                "trial_wins": 2,
                "last_updated": datetime.utcnow().isoformat()
            },
            "agent-2": {
                "score": 900,
                "rank": 2,
                "title": "Elite Agent",
                "titles_held": 2,
                "last_trial": None,
                "trial_wins": 1,
                "last_updated": datetime.utcnow().isoformat()
            },
            "agent-3": {
                "score": 800,
                "rank": 3,
                "title": "Elite Agent",
                "titles_held": 2,
                "last_trial": None,
                "trial_wins": 0,
                "last_updated": datetime.utcnow().isoformat()
            }
        },
        "version": "1.0",
        "last_trial_rotation": (datetime.utcnow() - timedelta(days=7)).isoformat()
    }
    
    # Write leaderboard
    leaderboard_path = mock_metrics_file.parent / "leaderboard.json"
    with open(leaderboard_path, 'w') as f:
        json.dump(leaderboard_data, f)
    
    # Setup trial task
    trial_task = {
        "id": "TRIAL-1",
        "type": "trial",
        "difficulty": "elite",
        "description": "Optimize file classification engine",
        "deadline": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "metrics": ["accuracy", "speed", "memory_usage"]
    }
    
    # Mock ProjectBoardManager for trial matching
    mock_pbm.get_trial_task = AsyncMock(return_value=trial_task)
    mock_pbm.match_agents = AsyncMock(return_value=["agent-1", "agent-2"])
    
    # Test trial rotation
    await loop.process_message({
        "type": "TRIAL_ROTATION",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify trial creation
    with open(leaderboard_path) as f:
        updated_leaderboard = json.load(f)
    
    # Check trial assignments
    assert updated_leaderboard["agents"]["agent-1"]["last_trial"] is not None
    assert updated_leaderboard["agents"]["agent-2"]["last_trial"] is not None
    
    # Test trial completion (winner)
    await loop.process_message({
        "type": "TRIAL_COMPLETE",
        "agent_id": "agent-1",
        "task_id": "TRIAL-1",
        "status": "COMPLETED",
        "metrics": {
            "accuracy": 0.95,
            "speed": 100,
            "memory_usage": 50
        },
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Test trial completion (loser)
    await loop.process_message({
        "type": "TRIAL_COMPLETE",
        "agent_id": "agent-2",
        "task_id": "TRIAL-1",
        "status": "COMPLETED",
        "metrics": {
            "accuracy": 0.90,
            "speed": 80,
            "memory_usage": 60
        },
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify winner rewards
    with open(leaderboard_path) as f:
        final_leaderboard = json.load(f)
    
    winner = final_leaderboard["agents"]["agent-1"]
    assert winner["trial_wins"] == 3
    assert winner["next_spotlight"] is True
    
    # Verify loser penalties
    loser = final_leaderboard["agents"]["agent-2"]
    assert loser["drift_risk"] == 2.0
    assert loser["decay_multiplier"] == 1.5
    
    # Verify Discord updates
    mock_webhook = mock_autonomy_engine.discord_webhook
    assert mock_webhook.send.called
    
    # Check trial messages
    posted_message = mock_webhook.send.call_args[1]["content"]
    assert "🏁 Elite Trial" in posted_message
    assert "agent-1 vs agent-2" in posted_message
    assert "24h" in posted_message
    assert "🎖️ Winner" in posted_message
    assert "📉 Loser" in posted_message
    
    # Test trial metrics comparison
    assert "accuracy: 0.95 vs 0.90" in posted_message
    assert "speed: 100 vs 80" in posted_message
    assert "memory: 50 vs 60" in posted_message 

@pytest.mark.asyncio
async def test_tournament_brackets(
    mock_agent, 
    mock_config, 
    mock_pbm, 
    mock_autonomy_engine,
    mock_metrics_file
):
    """Test that elite trials are tracked in tournament brackets with champion crowning."""
    # Setup tournament rules
    tournament_rules = {
        "term_weeks": 4,
        "bracket_size": 8,
        "champion_bonus": {
            "title": "Champion Agent",
            "immunity_weeks": 2,
            "reward_multiplier": 2.0,
            "exclusive_tasks": True
        },
        "bracket_progression": {
            "quarterfinals": 2,
            "semifinals": 1,
            "finals": 1
        }
    }
    
    # Create loop instance with tournament rules
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    loop.autonomy_engine.tournament_rules = tournament_rules
    
    # Setup tournament state
    tournament_data = {
        "current_term": 1,
        "start_date": datetime.utcnow().isoformat(),
        "end_date": (datetime.utcnow() + timedelta(weeks=4)).isoformat(),
        "brackets": {
            "quarterfinals": [
                {
                    "match_id": "QF-1",
                    "agents": ["agent-1", "agent-2"],
                    "winner": None,
                    "completed": False
                },
                {
                    "match_id": "QF-2",
                    "agents": ["agent-3", "agent-4"],
                    "winner": None,
                    "completed": False
                }
            ],
            "semifinals": [],
            "finals": []
        },
        "champions": [],
        "version": "1.0"
    }
    
    # Write tournament state
    tournament_path = mock_metrics_file.parent / "tournament.json"
    with open(tournament_path, 'w') as f:
        json.dump(tournament_data, f)
    
    # Setup leaderboard with tournament participants
    leaderboard_data = {
        "agents": {
            "agent-1": {
                "score": 1000,
                "rank": 1,
                "title": "Elite Agent",
                "tournament_wins": 0,
                "last_updated": datetime.utcnow().isoformat()
            },
            "agent-2": {
                "score": 900,
                "rank": 2,
                "title": "Elite Agent",
                "tournament_wins": 0,
                "last_updated": datetime.utcnow().isoformat()
            }
        },
        "version": "1.0"
    }
    
    # Write leaderboard
    leaderboard_path = mock_metrics_file.parent / "leaderboard.json"
    with open(leaderboard_path, 'w') as f:
        json.dump(leaderboard_data, f)
    
    # Test quarterfinal match
    await loop.process_message({
        "type": "TOURNAMENT_MATCH",
        "match_id": "QF-1",
        "agents": ["agent-1", "agent-2"],
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Simulate match completion
    await loop.process_message({
        "type": "TOURNAMENT_COMPLETE",
        "match_id": "QF-1",
        "winner": "agent-1",
        "metrics": {
            "completion_time": 3600,
            "quality_score": 0.95,
            "stability": 0.98
        },
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify bracket progression
    with open(tournament_path) as f:
        updated_tournament = json.load(f)
    
    # Check quarterfinal completion
    qf_match = next(m for m in updated_tournament["brackets"]["quarterfinals"] 
                   if m["match_id"] == "QF-1")
    assert qf_match["completed"] is True
    assert qf_match["winner"] == "agent-1"
    
    # Verify semifinal creation
    assert len(updated_tournament["brackets"]["semifinals"]) > 0
    
    # Test tournament completion
    # Simulate remaining matches
    for match in updated_tournament["brackets"]["semifinals"] + updated_tournament["brackets"]["finals"]:
        await loop.process_message({
            "type": "TOURNAMENT_COMPLETE",
            "match_id": match["match_id"],
            "winner": "agent-1",  # Same agent wins all
            "metrics": {
                "completion_time": 3600,
                "quality_score": 0.95,
                "stability": 0.98
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Verify champion crowning
    with open(tournament_path) as f:
        final_tournament = json.load(f)
    
    assert len(final_tournament["champions"]) == 1
    champion = final_tournament["champions"][0]
    assert champion["agent_id"] == "agent-1"
    assert champion["term"] == 1
    
    # Verify champion rewards
    with open(leaderboard_path) as f:
        final_leaderboard = json.load(f)
    
    champion_agent = final_leaderboard["agents"]["agent-1"]
    assert champion_agent["title"] == "Champion Agent"
    assert champion_agent["immunity_until"] is not None
    assert champion_agent["reward_multiplier"] == 2.0
    assert champion_agent["exclusive_tasks"] is True
    
    # Verify Discord updates
    mock_webhook = mock_autonomy_engine.discord_webhook
    assert mock_webhook.send.called
    
    # Check tournament messages
    posted_message = mock_webhook.send.call_args[1]["content"]
    assert "🏆 Tournament Match" in posted_message
    assert "agent-1 vs agent-2" in posted_message
    assert "Quarterfinals" in posted_message
    
    # Check champion announcement
    assert "👑 Champion Crowned" in posted_message
    assert "agent-1" in posted_message
    assert "Term 1" in posted_message
    
    # Verify metrics display
    assert "completion_time: 3600s" in posted_message
    assert "quality: 0.95" in posted_message
    assert "stability: 0.98" in posted_message 

@pytest.mark.asyncio
async def test_trial_streak_bonuses(
    mock_agent, 
    mock_config, 
    mock_pbm, 
    mock_autonomy_engine,
    mock_metrics_file
):
    """Test that trial streaks are tracked and rewarded with escalating bonuses."""
    # Setup streak rules
    streak_rules = {
        "levels": {
            "3": {
                "title": "Rising Star",
                "reward_multiplier": 1.2,
                "custom_flair": "⭐"
            },
            "5": {
                "title": "Elite Veteran",
                "reward_multiplier": 1.5,
                "custom_flair": "🌟",
                "immunity_days": 3
            },
            "10": {
                "title": "Legend",
                "reward_multiplier": 2.0,
                "custom_flair": "👑",
                "immunity_days": 7,
                "exclusive_tasks": True
            }
        },
        "decay": {
            "inactive_days": 7,
            "streak_loss": True
        }
    }
    
    # Create loop instance with streak rules
    loop = AutonomousLoop(mock_agent, mock_config, mock_pbm)
    loop.autonomy_engine = mock_autonomy_engine
    loop.autonomy_engine.streak_rules = streak_rules
    
    # Setup leaderboard with streak tracking
    leaderboard_data = {
        "agents": {
            "agent-1": {
                "score": 1000,
                "rank": 1,
                "title": "Elite Agent",
                "current_streak": 2,
                "best_streak": 2,
                "streak_level": None,
                "last_trial": datetime.utcnow().isoformat(),
                "last_updated": datetime.utcnow().isoformat()
            },
            "agent-2": {
                "score": 900,
                "rank": 2,
                "title": "Elite Agent",
                "current_streak": 4,
                "best_streak": 4,
                "streak_level": "Rising Star",
                "last_trial": datetime.utcnow().isoformat(),
                "last_updated": datetime.utcnow().isoformat()
            }
        },
        "version": "1.0"
    }
    
    # Write leaderboard
    leaderboard_path = mock_metrics_file.parent / "leaderboard.json"
    with open(leaderboard_path, 'w') as f:
        json.dump(leaderboard_data, f)
    
    # Test streak progression
    await loop.process_message({
        "type": "TRIAL_COMPLETE",
        "agent_id": "agent-1",
        "task_id": "TRIAL-1",
        "status": "COMPLETED",
        "metrics": {
            "completion_time": 3600,
            "quality_score": 0.95,
            "stability": 0.98
        },
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify streak update
    with open(leaderboard_path) as f:
        updated_leaderboard = json.load(f)
    
    agent_1 = updated_leaderboard["agents"]["agent-1"]
    assert agent_1["current_streak"] == 3
    assert agent_1["streak_level"] == "Rising Star"
    assert agent_1["reward_multiplier"] == 1.2
    assert agent_1["custom_flair"] == "⭐"
    
    # Test streak level up
    await loop.process_message({
        "type": "TRIAL_COMPLETE",
        "agent_id": "agent-2",
        "task_id": "TRIAL-2",
        "status": "COMPLETED",
        "metrics": {
            "completion_time": 3600,
            "quality_score": 0.95,
            "stability": 0.98
        },
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify level up
    with open(leaderboard_path) as f:
        final_leaderboard = json.load(f)
    
    agent_2 = final_leaderboard["agents"]["agent-2"]
    assert agent_2["current_streak"] == 5
    assert agent_2["streak_level"] == "Elite Veteran"
    assert agent_2["reward_multiplier"] == 1.5
    assert agent_2["custom_flair"] == "🌟"
    assert agent_2["immunity_until"] is not None
    
    # Test streak decay
    old_date = datetime.utcnow() - timedelta(days=8)
    agent_1["last_trial"] = old_date.isoformat()
    with open(leaderboard_path, 'w') as f:
        json.dump(final_leaderboard, f)
    
    # Trigger decay check
    await loop.process_message({
        "type": "STREAK_CHECK",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Verify streak reset
    with open(leaderboard_path) as f:
        decayed_leaderboard = json.load(f)
    
    agent_1 = decayed_leaderboard["agents"]["agent-1"]
    assert agent_1["current_streak"] == 0
    assert agent_1["streak_level"] is None
    assert agent_1["reward_multiplier"] == 1.0
    
    # Verify Discord updates
    mock_webhook = mock_autonomy_engine.discord_webhook
    assert mock_webhook.send.called
    
    # Check streak messages
    posted_message = mock_webhook.send.call_args[1]["content"]
    assert "🔥 Streak Level Up" in posted_message
    assert "agent-2" in posted_message
    assert "Elite Veteran" in posted_message
    assert "🌟" in posted_message
    
    # Check decay message
    assert "❄️ Streak Lost" in posted_message
    assert "agent-1" in posted_message
    assert "inactive" in posted_message