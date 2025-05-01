import json
import os
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

# Adjust import path based on actual location
from dreamos.memory.memory_manager import UnifiedMemoryManager

# Sample data for testing
NOW = datetime.now(timezone.utc)
SAMPLE_TIMESTAMP_RECENT = NOW.isoformat()
SAMPLE_TIMESTAMP_OLD = (NOW - timedelta(days=40)).isoformat()


@pytest.fixture
def memory_manager(tmp_path):
    """Provides a UnifiedMemoryManager instance with a temporary base directory."""
    manager = UnifiedMemoryManager(base_dir=str(tmp_path))
    # Override default config for predictable testing
    manager.compaction_config = {
        "enabled": True,
        "check_on_write": True,  # Test trigger
        "default_policy": "time_based",
        "default_max_age_days": 30,
        "default_keep_n": 3,  # Small number for testing keep_n
        "threshold_max_size_mb": 0.0001,  # ~100 bytes
        "threshold_max_entries": 5,
    }
    return manager


@pytest.fixture
def create_segment_file(memory_manager):
    """Helper to create a segment file with specific content."""

    def _create(segment_id, data):
        segment_path = memory_manager._segment_file(segment_id)
        os.makedirs(os.path.dirname(segment_path), exist_ok=True)
        with open(segment_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return segment_path

    return _create


# --- Threshold Tests ---


def test_compaction_triggered_by_size(memory_manager, create_segment_file):
    """Test compaction is triggered when size threshold is exceeded."""
    segment_id = "size_test"
    # Create data larger than threshold_max_size_mb (e.g., > 100 bytes)
    large_data = [
        {"id": i, "timestamp": SAMPLE_TIMESTAMP_RECENT, "padding": "x" * 50}
        for i in range(3)
    ]
    segment_path = create_segment_file(segment_id, large_data)

    with patch.object(memory_manager, "_compact_segment") as mock_compact:
        memory_manager._check_and_compact(segment_id)
        mock_compact.assert_called_once()
        logger_output = (
            memory_manager.logger.info.call_args_list
        )  # Check logs if logger mocked
        # assert any("triggered by size" in str(call) for call in logger_output)


def test_compaction_triggered_by_entries(memory_manager, create_segment_file):
    """Test compaction is triggered when entry count threshold is exceeded."""
    segment_id = "entry_test"
    # Create data with more entries than threshold_max_entries (e.g., > 5)
    many_entries_data = [
        {"id": i, "timestamp": SAMPLE_TIMESTAMP_RECENT} for i in range(6)
    ]
    segment_path = create_segment_file(segment_id, many_entries_data)

    with patch.object(memory_manager, "_compact_segment") as mock_compact:
        memory_manager._check_and_compact(segment_id)
        mock_compact.assert_called_once()
        # Check logs if needed


def test_compaction_not_triggered_below_thresholds(memory_manager, create_segment_file):
    """Test compaction is NOT triggered when below thresholds."""
    segment_id = "below_threshold"
    small_data = [{"id": 1, "timestamp": SAMPLE_TIMESTAMP_RECENT}]
    segment_path = create_segment_file(segment_id, small_data)

    with patch.object(memory_manager, "_compact_segment") as mock_compact:
        memory_manager._check_and_compact(segment_id)
        mock_compact.assert_not_called()


# --- Policy Tests ---


def test_time_based_compaction_list(memory_manager, create_segment_file):
    """Test time-based policy correctly removes old entries from a list."""
    segment_id = "time_list_test"
    data = [
        {"id": 1, "timestamp": SAMPLE_TIMESTAMP_OLD, "value": "old"},
        {"id": 2, "timestamp": SAMPLE_TIMESTAMP_RECENT, "value": "recent1"},
        {
            "id": 3,
            "timestamp": (NOW - timedelta(days=10)).isoformat(),
            "value": "recent2",
        },
        {"id": 4, "timestamp": SAMPLE_TIMESTAMP_OLD, "value": "old2"},
    ]
    segment_path = create_segment_file(segment_id, data)

    memory_manager._check_and_compact(segment_id)  # Trigger compaction

    with open(segment_path, "r", encoding="utf-8") as f:
        compacted_data = json.load(f)

    assert len(compacted_data) == 2
    assert compacted_data[0]["id"] == 2
    assert compacted_data[1]["id"] == 3
    assert all("old" not in entry["value"] for entry in compacted_data)


def test_time_based_compaction_dict(memory_manager, create_segment_file):
    """Test time-based policy correctly removes old entries from a dict."""
    segment_id = "time_dict_test"
    data = {
        "key_old1": {"timestamp": SAMPLE_TIMESTAMP_OLD, "value": "old"},
        "key_recent1": {"timestamp": SAMPLE_TIMESTAMP_RECENT, "value": "recent1"},
        "key_recent2": {
            "timestamp": (NOW - timedelta(days=10)).isoformat(),
            "value": "recent2",
        },
        "key_old2": {"timestamp": SAMPLE_TIMESTAMP_OLD, "value": "old2"},
    }
    segment_path = create_segment_file(segment_id, data)
    memory_manager._check_and_compact(segment_id)
    with open(segment_path, "r", encoding="utf-8") as f:
        compacted_data = json.load(f)
    assert len(compacted_data) == 2
    assert "key_recent1" in compacted_data
    assert "key_recent2" in compacted_data
    assert "key_old1" not in compacted_data
    assert "key_old2" not in compacted_data


def test_keep_n_compaction_list(memory_manager, create_segment_file):
    """Test keep-N policy correctly keeps the last N entries in a list."""
    segment_id = "keepn_list_test"
    memory_manager.compaction_config["default_policy"] = "keep_n"
    # Keep N = 3 based on fixture config
    data = [
        {"id": i, "timestamp": (NOW - timedelta(days=10 - i)).isoformat()}
        for i in range(6)
    ]  # 0 to 5
    segment_path = create_segment_file(segment_id, data)
    memory_manager._check_and_compact(segment_id)
    with open(segment_path, "r", encoding="utf-8") as f:
        compacted_data = json.load(f)
    assert len(compacted_data) == 3
    assert compacted_data[0]["id"] == 3
    assert compacted_data[1]["id"] == 4
    assert compacted_data[2]["id"] == 5


# --- Safety & Edge Cases ---


@patch("os.replace")
def test_safe_rewrite(mock_replace, memory_manager, create_segment_file):
    """Test that compaction uses atomic os.replace."""
    segment_id = "safe_rewrite_test"
    # Use data that will definitely trigger compaction (e.g., time-based)
    data = [{"id": 1, "timestamp": SAMPLE_TIMESTAMP_OLD}]
    segment_path = create_segment_file(segment_id, data)
    memory_manager._check_and_compact(segment_id)
    mock_replace.assert_called_once()
    # Check that original file exists until replace is called (harder to test precisely)


def test_compaction_handles_invalid_json(memory_manager, tmp_path):
    """Test compaction check handles JSONDecodeError gracefully."""
    segment_id = "invalid_json_test"
    segment_path = memory_manager._segment_file(segment_id)
    os.makedirs(os.path.dirname(segment_path), exist_ok=True)
    with open(segment_path, "w") as f:
        f.write("this is not json")

    # Ensure size threshold is met to trigger read attempt
    memory_manager.compaction_config["threshold_max_size_mb"] = 0.000001

    with patch.object(memory_manager, "_compact_segment") as mock_compact:
        try:
            memory_manager._check_and_compact(segment_id)
        except Exception as e:
            pytest.fail(f"_check_and_compact raised unexpected exception: {e}")
        mock_compact.assert_not_called()  # Compaction should not proceed
        # Check logs for JSONDecodeError warning if logger mocked


def test_compaction_handles_missing_timestamp(memory_manager, create_segment_file):
    """Test time-based policy handles entries without timestamps (keeps them)."""
    segment_id = "missing_ts_test"
    data = [
        {"id": 1, "timestamp": SAMPLE_TIMESTAMP_OLD},  # Will be removed
        {"id": 2},  # Missing timestamp, should be kept
        {"id": 3, "timestamp": SAMPLE_TIMESTAMP_RECENT},  # Will be kept
    ]
    segment_path = create_segment_file(segment_id, data)
    memory_manager._check_and_compact(segment_id)
    with open(segment_path, "r", encoding="utf-8") as f:
        compacted_data = json.load(f)
    assert len(compacted_data) == 2
    assert compacted_data[0]["id"] == 2
    assert compacted_data[1]["id"] == 3
    # Check logs for warning about missing timestamp
