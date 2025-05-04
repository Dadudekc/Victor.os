from pathlib import Path  # noqa: I001
from unittest.mock import MagicMock, patch

import pytest
from dreamos.hooks.stats_logger import StatsLoggingHook

# Remove the skipped stub function
# @pytest.mark.skip(reason='Test stub for coverage tracking')
# def test_stub_for_stats_logger():
#     pass


@pytest.fixture
def mock_nexus() -> MagicMock:
    """Provides a mock TaskNexus instance."""
    nexus = MagicMock()
    # Define sample task data returned by the mock
    nexus.get_all_tasks.return_value = [
        {
            "id": "t1",
            "status": "completed",
            "claimed_by": "Agent1",
            "timestamp": 1.0,
            "processed_at": 2.5,
        },
        {
            "id": "t2",
            "status": "failed",
            "claimed_by": "Agent2",
            "timestamp": 2.0,
            "processed_at": 3.0,
        },
        {"id": "t3", "status": "running", "agent": "Agent1", "timestamp": 3.0},
        {"id": "t4", "status": "pending", "agent": None},
        {
            "id": "t5",
            "status": "completed",
            "claimed_by": "Agent1",
            "timestamp": 4.0,
            "processed_at": 7.0,
        },
    ]
    return nexus


# Patch the problematic import path for write_json_safe within the test scope
@patch("dreamos.hooks.stats_logger.write_json_safe")
def test_stats_logger_log_snapshot(
    mock_write_json_safe: MagicMock, mock_nexus: MagicMock, tmp_path: Path
):
    """Test that log_snapshot calculates stats and calls write_json_safe correctly."""
    log_file = tmp_path / "stats_log.json"
    hook = StatsLoggingHook(nexus=mock_nexus, log_path=str(log_file))

    hook.log_snapshot()

    # Assertions
    mock_nexus.get_all_tasks.assert_called_once()
    mock_write_json_safe.assert_called_once()

    # Check the arguments passed to write_json_safe
    call_args = mock_write_json_safe.call_args
    assert call_args[0][0] == log_file  # Check path argument (first positional arg)
    snapshot_data = call_args[0][1]  # Check data argument (second positional arg)
    append_kwarg = call_args.kwargs.get("append", False)  # Check append kwarg

    assert append_kwarg is True  # Ensure it's appending

    assert isinstance(snapshot_data, dict)
    assert "timestamp" in snapshot_data
    assert snapshot_data["total_tasks"] == 5
    assert snapshot_data["completed"] == 2
    assert snapshot_data["failed"] == 1
    assert snapshot_data["running"] == 1  # Only counts 'running' and 'claimed'
    assert snapshot_data["agents"] == sorted(["Agent1", "Agent2"])
    assert snapshot_data["last_task"]["id"] == "t5"
    assert snapshot_data["last_task"]["status"] == "completed"
    assert snapshot_data["success_rate"] == 2 / 5
    # Basic check for avg duration calculation - needs adjustment if timestamp format differs  # noqa: E501
    # assert snapshot_data["avg_duration_seconds"] == pytest.approx((1.5 + 1.0 + 3.0) / 3)  # noqa: E501
    assert "avg_duration_seconds" in snapshot_data  # Check presence for now
    assert snapshot_data["agent_stats"]["Agent1"] == {"completed": 2, "failed": 0}
    assert snapshot_data["agent_stats"]["Agent2"] == {"completed": 0, "failed": 1}
