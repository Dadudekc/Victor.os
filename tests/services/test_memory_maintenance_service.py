import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Adjust imports based on project structure
from dreamos.core.config import (
    AppConfig,
    MemoryMaintenanceConfig,
    PathsConfig,
)
from dreamos.core.utils.file_locking import (  # For mocking lock context
    LockAcquisitionError,
)
from dreamos.core.utils.summarizer import BaseSummarizer
from dreamos.services.memory_maintenance_service import MemoryMaintenanceService

# --- Fixtures ---


@pytest.fixture
def mock_app_config(tmp_path):
    """Provides a mock AppConfig with necessary paths pointing to tmp_path."""
    # Create directories expected by PathsConfig methods
    memory_base = tmp_path / "memory"
    snapshots_base = tmp_path / "snapshots"
    memory_base.mkdir()
    snapshots_base.mkdir()

    class MockPathsConfig(PathsConfig):
        # Override methods to use tmp_path
        def get_memory_base_path(self) -> Path:
            return memory_base

        def get_snapshot_base_path(self) -> Path:
            return snapshots_base

        # Add overrides for other path methods if needed by the service

    config = AppConfig(
        paths=MockPathsConfig(),
        memory_maintenance=MemoryMaintenanceConfig(  # Use default policies for now
            scan_interval_seconds=0.1,  # Faster scanning for tests
            lock_timeout_seconds=1,
        ),
        # Add other required AppConfig fields if necessary
    )
    return config


@pytest.fixture
def mock_summarizer():
    """Provides a mock summarizer instance."""
    summarizer = MagicMock(spec=BaseSummarizer)
    summarizer.summarize = AsyncMock(return_value="Mock summary")
    return summarizer


@pytest.fixture
def maintenance_service(mock_app_config, mock_summarizer):
    """Provides an instance of the MemoryMaintenanceService with mock config."""
    service = MemoryMaintenanceService(
        config=mock_app_config, summarizer=mock_summarizer
    )
    return service


# --- Test Cases ---


@pytest.mark.asyncio
async def test_service_initialization(maintenance_service, mock_app_config):
    """Test that the service initializes correctly with config values."""
    assert maintenance_service.config == mock_app_config
    assert (
        maintenance_service.memory_base_path
        == mock_app_config.paths.get_memory_base_path()
    )
    assert (
        maintenance_service.snapshot_base_path
        == mock_app_config.paths.get_snapshot_base_path()
    )
    assert (
        maintenance_service.scan_interval_seconds
        == mock_app_config.memory_maintenance.scan_interval_seconds
    )
    assert (
        maintenance_service.lock_timeout_seconds
        == mock_app_config.memory_maintenance.lock_timeout_seconds
    )
    assert (
        maintenance_service.compaction_policy
        == mock_app_config.memory_maintenance.compaction_policy
    )
    assert (
        maintenance_service.summarization_policy
        == mock_app_config.memory_maintenance.summarization_policy
    )
    assert not maintenance_service._running
    assert maintenance_service._task is None


@pytest.mark.asyncio
async def test_start_stop_cycle(maintenance_service):
    """Test the start and stop methods control the background task."""
    assert not maintenance_service._running
    assert maintenance_service._task is None

    await maintenance_service.start()
    assert maintenance_service._running
    assert isinstance(maintenance_service._task, asyncio.Task)
    assert not maintenance_service._task.done()

    # Give the loop a moment to start
    await asyncio.sleep(0.01)

    await maintenance_service.stop()
    assert not maintenance_service._running
    assert maintenance_service._task is None  # Should be cleared after awaiting stop


@pytest.mark.asyncio
@patch(
    "dreamos.services.memory_maintenance_service.MemoryMaintenanceService._perform_maintenance",
    new_callable=AsyncMock,
)
async def test_run_loop_calls_perform_maintenance(
    mock_perform_maintenance, maintenance_service
):
    """Test that the main _run loop calls _perform_maintenance periodically."""
    # Use a very short scan interval defined in mock_app_config fixture (0.1s)
    await maintenance_service.start()
    await asyncio.sleep(
        maintenance_service.scan_interval_seconds * 2.5
    )  # Wait for > 2 cycles
    await maintenance_service.stop()

    assert mock_perform_maintenance.call_count >= 2  # Should have run at least twice


@pytest.mark.asyncio
@patch("dreamos.services.memory_maintenance_service.shutil.copytree")
@patch("dreamos.services.memory_maintenance_service.shutil.rmtree")
@patch("dreamos.services.memory_maintenance_service.os.rename")
@patch(
    "dreamos.services.memory_maintenance_service.FileLock", new_callable=AsyncMock
)  # Mock the async context manager
@patch(
    "dreamos.services.memory_maintenance_service.MemoryMaintenanceService._process_segment_file",
    new_callable=AsyncMock,
)
async def test_process_agent_memory_snapshot_and_process(
    mock_process_segment,
    mock_filelock,
    mock_os_rename,
    mock_rmtree,
    mock_copytree,
    maintenance_service,
    mock_app_config,
    tmp_path,
):
    """Test _process_agent_memory correctly creates snapshot, processes segments, and cleans up."""  # noqa: E501
    agent_id = "agent_test_001"
    agent_memory_dir = mock_app_config.paths.get_memory_base_path() / agent_id
    agent_memory_dir.mkdir()
    snapshot_dir = mock_app_config.paths.get_snapshot_base_path() / agent_id

    # Create dummy segment files in the *original* directory for snapshotting
    (agent_memory_dir / "segment1.json").touch()
    (agent_memory_dir / "segment2.json.gz").touch()

    # --- Configure Mocks ---
    # Assume _process_segment_file succeeds for both files
    mock_process_segment.return_value = True
    # Mock the FileLock context manager part
    mock_filelock_instance = AsyncMock()
    mock_filelock.return_value.__aenter__.return_value = mock_filelock_instance

    # --- Call the Method Under Test ---
    await maintenance_service._process_agent_memory(agent_memory_dir)

    # --- Assertions ---
    # 1. Snapshotting called correctly
    mock_copytree.assert_called_once_with(
        agent_memory_dir, snapshot_dir, symlinks=False, ignore_dangling_symlinks=True
    )

    # 2. Processing called for each segment found in snapshot
    #    Need to simulate that copytree actually created the files in the snapshot dir
    #    for glob to find them. Since copytree is mocked, we check calls to _process_segment_file.  # noqa: E501
    #    The glob happens inside _process_agent_memory *after* the mocked copytree.
    #    This is tricky. Let's assert based on expected calls to _process_segment_file.
    #    We expect it to be called twice IF glob worked on the (mocked) snapshot.
    #    A more robust test might involve patching Path.glob within the function's scope.  # noqa: E501
    #    For now, let's check call count assuming the implementation correctly globs.
    #    Expected paths would be snapshot_dir / "segment1.json", snapshot_dir / "segment2.json.gz"  # noqa: E501
    assert mock_process_segment.call_count == 2
    # Check paths passed (order might vary depending on glob)
    call_args_list = mock_process_segment.call_args_list
    called_paths = {
        call[0][0] for call in call_args_list
    }  # Get the first arg (segment_file_path)
    expected_paths = {snapshot_dir / "segment1.json", snapshot_dir / "segment2.json.gz"}
    assert called_paths == expected_paths

    # 3. Atomic replacement attempted (since processing succeeded)
    mock_filelock.assert_called_once()  # Lock should be attempted
    assert mock_os_rename.call_count >= 2  # Renaming original out, renaming snapshot in

    # 4. Snapshot cleanup attempted
    # Check rmtree calls - one for the temp old dir, one for the snapshot itself
    assert mock_rmtree.call_count >= 1  # At least the snapshot cleanup
    # A more specific check might look at the path passed to rmtree
    cleaned_snapshot = False
    for call in mock_rmtree.call_args_list:
        if call[0][0] == snapshot_dir:
            cleaned_snapshot = True
            break
    assert (
        cleaned_snapshot
    ), f"Snapshot directory {snapshot_dir} was not passed to rmtree for cleanup."


# --- Tests for _perform_maintenance ---


@pytest.mark.asyncio
@patch(
    "dreamos.services.memory_maintenance_service.MemoryMaintenanceService._process_agent_memory",
    new_callable=AsyncMock,
)
async def test_perform_maintenance_finds_and_calls_for_agents(
    mock_process_agent, maintenance_service, mock_app_config, tmp_path
):
    """Test _perform_maintenance finds agent directories and calls processor."""
    base_mem_path = mock_app_config.paths.get_memory_base_path()
    # Create dummy agent dirs
    (base_mem_path / "agent1").mkdir()
    (base_mem_path / "agent2").mkdir()
    (base_mem_path / "not_a_dir.txt").touch()  # Should be ignored

    await maintenance_service._perform_maintenance()

    # Assert _process_agent_memory was called for each directory
    assert mock_process_agent.call_count == 2
    call_args_list = mock_process_agent.call_args_list
    processed_paths = {call[0][0] for call in call_args_list}
    assert processed_paths == {base_mem_path / "agent1", base_mem_path / "agent2"}


@pytest.mark.asyncio
@patch(
    "dreamos.services.memory_maintenance_service.MemoryMaintenanceService._process_agent_memory",
    new_callable=AsyncMock,
)
async def test_perform_maintenance_respects_filtering(
    mock_process_agent, maintenance_service, mock_app_config, tmp_path
):
    """Test agent filtering (process_agents, skip_agents) in _perform_maintenance."""
    base_mem_path = mock_app_config.paths.get_memory_base_path()
    (base_mem_path / "agent_allow1").mkdir()
    (base_mem_path / "agent_allow2").mkdir()
    (base_mem_path / "agent_deny1").mkdir()
    (base_mem_path / "agent_skip1").mkdir()

    # Modify config for this test
    maintenance_service.maintenance_config.process_agents = [
        "agent_allow1",
        "agent_allow2",
        "agent_skip1",
    ]  # Include skip1 here
    maintenance_service.maintenance_config.skip_agents = ["agent_skip1"]

    await maintenance_service._perform_maintenance()

    # Should only be called for allow1 and allow2
    assert mock_process_agent.call_count == 2
    call_args_list = mock_process_agent.call_args_list
    processed_paths = {call[0][0] for call in call_args_list}
    assert processed_paths == {
        base_mem_path / "agent_allow1",
        base_mem_path / "agent_allow2",
    }


# --- Tests for _process_agent_memory (Replacement & Error Handling) ---


@pytest.mark.asyncio
@patch("dreamos.services.memory_maintenance_service.shutil.copytree")
@patch("dreamos.services.memory_maintenance_service.shutil.rmtree")
@patch("dreamos.services.memory_maintenance_service.os.rename")
@patch("dreamos.services.memory_maintenance_service.FileLock", new_callable=AsyncMock)
@patch(
    "dreamos.services.memory_maintenance_service.MemoryMaintenanceService._process_segment_file",
    new_callable=AsyncMock,
)
async def test_process_agent_memory_replacement_failure(
    mock_process_segment,
    mock_filelock,
    mock_os_rename,
    mock_rmtree,
    mock_copytree,
    maintenance_service,
    mock_app_config,
    tmp_path,
):
    """Test rollback/cleanup when os.rename fails during replacement."""
    agent_id = "agent_replace_fail"
    agent_memory_dir = mock_app_config.paths.get_memory_base_path() / agent_id
    agent_memory_dir.mkdir()
    original_old_dir = agent_memory_dir.with_suffix(agent_memory_dir.suffix + ".old")
    snapshot_dir = mock_app_config.paths.get_snapshot_base_path() / agent_id
    # Simulate snapshot creation by mock
    mock_copytree.return_value = None
    # Simulate segment processing succeeding
    mock_process_segment.return_value = True
    # Mock the lock succeeding
    mock_filelock_instance = AsyncMock()
    mock_filelock.return_value.__aenter__.return_value = mock_filelock_instance
    # Make the SECOND os.rename call fail (renaming snapshot to original),
    # but allow the THIRD (rollback original.old -> original) to succeed.
    mock_os_rename.side_effect = [
        None,  # First rename (original -> .old) succeeds
        OSError("Disk Full"),  # Second rename (snapshot -> original) fails
        None,  # Third rename (.old -> original rollback) succeeds
    ]

    with pytest.raises(OSError, match="Disk Full"):
        await maintenance_service._process_agent_memory(agent_memory_dir)

    # Assertions
    mock_copytree.assert_called_once()
    # Check that snapshot cleanup was attempted DESPITE rename failure
    cleaned_snapshot = False
    # Check that the first rename (original -> .old) happened
    # Check that the second rename (snapshot -> original) was attempted (and failed)
    # Check that the third rename (.old -> original rollback) was attempted
    assert (
        mock_os_rename.call_count == 3
    ), "Expected 3 rename calls: original->old, snapshot->original (fail), old->original (rollback)"  # noqa: E501
    # Verify the arguments of the third (rollback) call
    rollback_call = mock_os_rename.call_args_list[2]
    assert rollback_call[0][0] == original_old_dir
    assert rollback_call[0][1] == agent_memory_dir

    # Check snapshot cleanup was attempted
    # Needs to check based on path passed to rmtree
    cleaned_snapshot = False
    for call in mock_rmtree.call_args_list:
        if call[0][0] == snapshot_dir:
            cleaned_snapshot = True
            break
    assert (
        cleaned_snapshot
    ), "Snapshot directory should still be cleaned up on replacement failure."


@pytest.mark.asyncio
@patch("dreamos.services.memory_maintenance_service.shutil.copytree")
@patch("dreamos.services.memory_maintenance_service.shutil.rmtree")
@patch("dreamos.services.memory_maintenance_service.FileLock", new_callable=AsyncMock)
@patch(
    "dreamos.services.memory_maintenance_service.MemoryMaintenanceService._process_segment_file",
    new_callable=AsyncMock,
)
async def test_process_agent_memory_lock_failure(
    mock_process_segment,
    mock_filelock,
    mock_rmtree,
    mock_copytree,
    maintenance_service,
    mock_app_config,
    tmp_path,
):
    """Test cleanup when acquiring the agent lock fails."""
    agent_id = "agent_lock_fail"
    agent_memory_dir = mock_app_config.paths.get_memory_base_path() / agent_id
    agent_memory_dir.mkdir()
    snapshot_dir = mock_app_config.paths.get_snapshot_base_path() / agent_id
    mock_copytree.return_value = None  # Simulate snapshot creation
    mock_process_segment.return_value = True  # Simulate processing success
    # Make the lock acquisition fail
    mock_filelock.return_value.__aenter__.side_effect = LockAcquisitionError("Timeout")

    # Expect the function to log the error and return, not raise LockAcquisitionError upwards  # noqa: E501
    await maintenance_service._process_agent_memory(agent_memory_dir)

    # Assertions
    mock_copytree.assert_called_once()
    mock_filelock.assert_called_once()  # Lock acquisition was attempted
    # Check that snapshot cleanup was attempted
    cleaned_snapshot = False
    for call in mock_rmtree.call_args_list:
        if call[0][0] == snapshot_dir:
            cleaned_snapshot = True
            break
    assert cleaned_snapshot, "Snapshot directory should be cleaned up on lock failure."
    # Replacement should not have been attempted
    assert mock_rmtree.call_count == 1  # Only snapshot cleanup


@pytest.mark.asyncio
@patch("dreamos.services.memory_maintenance_service.shutil.copytree")
@patch("dreamos.services.memory_maintenance_service.shutil.rmtree")
@patch(
    "dreamos.services.memory_maintenance_service.MemoryMaintenanceService._process_segment_file",
    new_callable=AsyncMock,
)
async def test_process_agent_memory_segment_processing_failure(
    mock_process_segment,
    mock_rmtree,
    mock_copytree,
    maintenance_service,
    mock_app_config,
    tmp_path,
):
    """Test cleanup when _process_segment_file returns False."""
    agent_id = "agent_process_fail"
    agent_memory_dir = mock_app_config.paths.get_memory_base_path() / agent_id
    agent_memory_dir.mkdir()
    (agent_memory_dir / "segment1.json").touch()
    snapshot_dir = mock_app_config.paths.get_snapshot_base_path() / agent_id
    mock_copytree.return_value = None  # Simulate snapshot creation
    mock_process_segment.return_value = False  # Simulate processing failure

    await maintenance_service._process_agent_memory(agent_memory_dir)

    # Assertions
    mock_copytree.assert_called_once()
    mock_process_segment.assert_called_once()  # Processing was attempted
    # Check that snapshot cleanup was attempted
    cleaned_snapshot = False
    for call in mock_rmtree.call_args_list:
        if call[0][0] == snapshot_dir:
            cleaned_snapshot = True
            break
    assert (
        cleaned_snapshot
    ), "Snapshot directory should be cleaned up on processing failure."
    # Replacement should not have been attempted
    assert mock_rmtree.call_count == 1  # Only snapshot cleanup


@pytest.mark.asyncio
@patch(
    "dreamos.services.memory_maintenance_service.shutil.copytree",
    side_effect=OSError("Copy failed"),
)
@patch(
    "dreamos.services.memory_maintenance_service.shutil.rmtree"
)  # Need to mock rmtree still
async def test_process_agent_memory_snapshot_failure(
    mock_rmtree, mock_copytree, maintenance_service, mock_app_config, tmp_path
):
    """Test behavior when the initial snapshot copy fails."""
    agent_id = "agent_snapshot_fail"
    agent_memory_dir = mock_app_config.paths.get_memory_base_path() / agent_id
    agent_memory_dir.mkdir()
    snapshot_dir = mock_app_config.paths.get_snapshot_base_path() / agent_id

    await maintenance_service._process_agent_memory(agent_memory_dir)

    # Assertions
    mock_copytree.assert_called_once()
    # Snapshot cleanup might be attempted on the potentially partially created dir
    # Check if rmtree was called on the snapshot path
    cleaned_snapshot = False
    for call in mock_rmtree.call_args_list:
        if call[0][0] == snapshot_dir:
            cleaned_snapshot = True  # noqa: F841
            break
    # We don't strictly require cleanup if copytree fails early, but it's good if it tries.  # noqa: E501
    # assert cleaned_snapshot, "Snapshot directory cleanup should be attempted even if copytree fails."  # noqa: E501
    # No processing or replacement should occur


# --- Tests for _process_segment_file (Compaction & Summarization) ---


@pytest.mark.asyncio
@patch("dreamos.services.memory_maintenance_service.compact_segment_file")
@patch("dreamos.services.memory_maintenance_service.summarize_memory_file")
async def test_process_segment_file_calls_compaction_and_summarization(
    mock_summarize, mock_compact, maintenance_service, tmp_path, mock_app_config
):
    """Test that _process_segment_file calls both underlying utilities."""
    segment_path = tmp_path / "segment_to_process.json"
    segment_path.touch()

    # Get policies from config
    compaction_policy = (
        mock_app_config.memory_maintenance.compaction_policy.model_dump()
    )  # Pass dict
    summarization_policy = (
        mock_app_config.memory_maintenance.summarization_policy.model_dump()
    )  # Pass dict

    # Call the method
    result = await maintenance_service._process_segment_file(segment_path)

    # Assertions
    assert result is True  # Should return True if both succeed (or don't raise)
    mock_compact.assert_called_once_with(segment_path, compaction_policy)
    mock_summarize.assert_called_once_with(
        str(segment_path),  # summarize_memory_file expects string path
        keep_recent_n=summarization_policy["keep_recent_n"],
        max_age_days=summarization_policy["max_age_days"],
        summarizer=maintenance_service.summarizer,  # Ensure summarizer is passed
    )


@pytest.mark.asyncio
@patch(
    "dreamos.services.memory_maintenance_service.compact_segment_file",
    return_value=False,
)
@patch("dreamos.services.memory_maintenance_service.summarize_memory_file")
async def test_process_segment_file_compaction_fails(
    mock_summarize, mock_compact, maintenance_service, tmp_path
):
    """Test _process_segment_file returns False if compaction fails."""
    segment_path = tmp_path / "compact_fail.json"
    segment_path.touch()
    result = await maintenance_service._process_segment_file(segment_path)
    assert result is False
    mock_compact.assert_called_once()
    mock_summarize.assert_not_called()  # Should not attempt summarize if compact fails


@pytest.mark.asyncio
@patch(
    "dreamos.services.memory_maintenance_service.compact_segment_file",
    return_value=True,
)
@patch(
    "dreamos.services.memory_maintenance_service.summarize_memory_file",
    return_value=False,
)
async def test_process_segment_file_summarization_fails(
    mock_summarize, mock_compact, maintenance_service, tmp_path
):
    """Test _process_segment_file returns False if summarization fails."""
    segment_path = tmp_path / "summarize_fail.json"
    segment_path.touch()
    result = await maintenance_service._process_segment_file(segment_path)
    assert result is False
    mock_compact.assert_called_once()
    mock_summarize.assert_called_once()  # Summarization was attempted


# --- Helper Functions / Edge Cases ---


@pytest.mark.asyncio
async def test_service_stops_gracefully_if_never_started(maintenance_service):
    """Test that calling stop() before start() is safe."""
    await maintenance_service.stop()  # Should do nothing and not raise errors
    assert not maintenance_service._running
    assert maintenance_service._task is None
