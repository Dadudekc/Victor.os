import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, call, ANY

import pytest

from dreamos.core.config import AppConfig, SummarizationConfig
from dreamos.memory.memory_manager import MemoryManager, UnifiedMemoryManager
from dreamos.memory.summarization_utils import (
    extract_keywords_bert,
)
from dreamos.memory.summarizer import (
    Summarizer, 
    SummarizationStrategy, 
    SlidingWindowSummarization,
    _generate_placeholder_summary,
    summarize_memory_file,
)

NOW = datetime.now(timezone.utc)


@pytest.fixture
def sample_memory_file(tmp_path):
    """Creates a temporary JSON file with sample memory data."""

    def _create(data):
        # Use a subdirectory within tmp_path to avoid potential conflicts
        mem_dir = tmp_path / "memory_tests"
        mem_dir.mkdir(exist_ok=True)
        # Use a fixed name or generate one
        p = mem_dir / "test_memory.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return str(p)  # Return path as string

    return _create


# --- Test _generate_placeholder_summary ---


def test_generate_summary_basic():
    """Test basic summary generation."""
    chunk = [
        {"timestamp": (NOW - timedelta(days=10)).isoformat(), "content": "entry 1"},
        {"timestamp": (NOW - timedelta(days=9)).isoformat(), "content": "entry 2"},
    ]
    summary = _generate_placeholder_summary(chunk)
    assert summary["type"] == "summary_chunk"
    assert summary["entry_count"] == 2
    assert summary["start_time"] == chunk[0]["timestamp"]
    assert summary["end_time"] == chunk[-1]["timestamp"]
    assert "Summary of 2 entries" in summary["content"]
    assert "summarized_at" in summary


def test_generate_summary_empty_chunk():
    """Test summary generation with an empty chunk."""
    summary = _generate_placeholder_summary([])
    assert summary is None


def test_generate_summary_missing_timestamps():
    """Test summary generation when timestamps are missing."""
    chunk = [{"content": "entry 1"}, {"content": "entry 2"}]
    summary = _generate_placeholder_summary(chunk)
    assert summary["start_time"] == "Unknown"
    assert summary["end_time"] == "Unknown"
    assert summary["entry_count"] == 2


# --- Test summarize_memory_file ---


def test_summarize_file_no_summarization_needed_too_few(sample_memory_file):
    """Test no summarization occurs if entries <= keep_recent_n."""
    data = [
        {"id": i, "timestamp": (NOW - timedelta(minutes=i)).isoformat()}
        for i in range(5)
    ]
    file_path = sample_memory_file(data)
    result = summarize_memory_file(file_path, keep_recent_n=10, max_age_days=7)
    assert not result  # Should return False as no summarization happened
    # Verify file content remains unchanged
    with open(file_path, "r") as f:
        final_data = json.load(f)
    assert final_data == data


def test_summarize_file_no_summarization_needed_all_recent(sample_memory_file):
    """Test no summarization occurs if all entries are newer than max_age_days."""
    data = [
        {"id": i, "timestamp": (NOW - timedelta(days=i)).isoformat()} for i in range(10)
    ]  # All within 7 days
    file_path = sample_memory_file(data)
    result = summarize_memory_file(file_path, keep_recent_n=5, max_age_days=7)
    assert not result
    with open(file_path, "r") as f:
        final_data = json.load(f)
    assert final_data == data


def test_summarize_file_simple_case(sample_memory_file):
    """Test basic summarization: some old, some recent."""
    keep_n = 3
    max_age = 5
    data = []
    # Old entries (should be summarized)
    for i in range(4):
        data.append(
            {
                "id": f"old_{i}",
                "timestamp": (NOW - timedelta(days=max_age + i + 1)).isoformat(),
            }
        )
    # Recent entries (should be kept raw)
    for i in range(keep_n):
        data.append(
            {"id": f"recent_{i}", "timestamp": (NOW - timedelta(minutes=i)).isoformat()}
        )

    file_path = sample_memory_file(data)
    result = summarize_memory_file(
        file_path, keep_recent_n=keep_n, max_age_days=max_age
    )

    assert result  # Should return True

    with open(file_path, "r") as f:
        final_data = json.load(f)

    assert len(final_data) == keep_n + 1  # 1 summary chunk + keep_n raw entries
    assert final_data[0]["type"] == "summary_chunk"
    assert final_data[0]["entry_count"] == 4  # Summarized the 4 old entries
    assert final_data[1]["id"] == "recent_0"
    assert final_data[-1]["id"] == f"recent_{keep_n - 1}"


def test_summarize_handles_missing_timestamps(sample_memory_file):
    """Test entries with missing timestamps are treated as summarizable (old)."""
    keep_n = 2
    max_age = 3
    data = [
        {"id": "old_1", "timestamp": (NOW - timedelta(days=max_age + 1)).isoformat()},
        {"id": "missing_ts"},  # Should be summarized
        {"id": "recent_1", "timestamp": NOW.isoformat()},
        {"id": "recent_2", "timestamp": (NOW - timedelta(minutes=1)).isoformat()},
    ]
    file_path = sample_memory_file(data)
    result = summarize_memory_file(
        file_path, keep_recent_n=keep_n, max_age_days=max_age
    )
    assert result
    with open(file_path, "r") as f:
        final_data = json.load(f)
    assert len(final_data) == keep_n + 1
    assert final_data[0]["type"] == "summary_chunk"
    assert final_data[0]["entry_count"] == 2  # old_1 and missing_ts
    assert final_data[1]["id"] == "recent_1"


def test_summarize_file_does_not_summarize_summaries(sample_memory_file):
    """Test that existing summary chunks are not re-summarized."""
    keep_n = 1
    max_age = 3
    data = [
        {
            "type": "summary_chunk",
            "timestamp": (NOW - timedelta(days=10)).isoformat(),
            "entry_count": 5,
        },  # Existing summary
        {"id": "old_1", "timestamp": (NOW - timedelta(days=max_age + 1)).isoformat()},
        {"id": "recent_1", "timestamp": NOW.isoformat()},
    ]
    file_path = sample_memory_file(data)
    result = summarize_memory_file(
        file_path, keep_recent_n=keep_n, max_age_days=max_age
    )
    assert result
    with open(file_path, "r") as f:
        final_data = json.load(f)
    # Should be: new summary (for old_1) + old summary + recent_1
    assert len(final_data) == 3
    assert final_data[0]["type"] == "summary_chunk"  # New summary
    assert final_data[0]["entry_count"] == 1
    assert final_data[1]["type"] == "summary_chunk"  # Old summary preserved
    assert final_data[1]["entry_count"] == 5
    assert final_data[2]["id"] == "recent_1"


@patch("src.dreamos.memory.summarizer.os.replace")
@patch("src.dreamos.memory.summarizer.shutil.copy2")
@patch("src.dreamos.memory.summarizer.tempfile.NamedTemporaryFile")
def test_summarize_safe_write_and_backup(
    mock_tempfile, mock_copy, mock_replace, sample_memory_file, tmp_path
):
    """Test that safe write (temp file, replace) and backup are called."""
    # Mock NamedTemporaryFile to simulate successful write
    mock_tf_object = MagicMock()
    mock_tf_object.__enter__.return_value.name = str(
        tmp_path / "memory_tests" / "tempfile.tmp"
    )
    mock_tempfile.return_value = mock_tf_object

    keep_n = 1
    max_age = 1
    data = [
        {"id": "old_1", "timestamp": (NOW - timedelta(days=max_age + 1)).isoformat()},
        {"id": "recent_1", "timestamp": NOW.isoformat()},
    ]
    file_path = sample_memory_file(data)

    # Test with backup enabled (default)
    result_with_backup = summarize_memory_file(
        file_path, keep_recent_n=keep_n, max_age_days=max_age, create_backup=True
    )
    assert result_with_backup
    mock_copy.assert_called_once_with(file_path, file_path + ".bak")
    mock_tempfile.assert_called_once()
    mock_replace.assert_called_once_with(
        mock_tf_object.__enter__.return_value.name, file_path
    )

    # Reset mocks and test with backup disabled
    mock_copy.reset_mock()
    mock_tempfile.reset_mock()
    mock_replace.reset_mock()
    result_without_backup = summarize_memory_file(
        file_path, keep_recent_n=keep_n, max_age_days=max_age, create_backup=False
    )
    assert result_without_backup
    mock_copy.assert_not_called()
    mock_tempfile.assert_called_once()
    mock_replace.assert_called_once()


# Add tests for file not found, invalid JSON format etc. if needed


def test_summarize_file_not_found(tmp_path):
    """Test handling when the memory file does not exist."""
    non_existent_path = str(tmp_path / "memory_tests" / "non_existent.json")
    # Should log a warning and return False (or raise specific exception if designed that way)  # noqa: E501
    # For now, assume it returns False indicating no summarization needed/possible
    assert not summarize_memory_file(non_existent_path, keep_recent_n=5, max_age_days=7)


def test_summarize_file_invalid_json(sample_memory_file):
    """Test handling when the memory file contains invalid JSON."""
    file_path = sample_memory_file("not valid json")  # Write invalid content
    # Expecting a JSONDecodeError or similar wrapped in a custom exception, or returning False  # noqa: E501
    # Assuming it returns False after logging an error
    assert not summarize_memory_file(file_path, keep_recent_n=5, max_age_days=7)
    # Could also check for logged error messages if logger is mocked


def test_summarize_file_empty_json(sample_memory_file):
    """Test handling when the memory file is empty."""
    file_path = sample_memory_file("")  # Write empty content
    # Similar to invalid JSON, expect it to handle gracefully, likely returning False
    assert not summarize_memory_file(file_path, keep_recent_n=5, max_age_days=7)


def test_summarize_file_json_not_list(sample_memory_file):
    """Test handling when the JSON root is not a list."""
    file_path = sample_memory_file({"key": "value"})  # Write a dict instead of list
    # Expecting it to handle gracefully, likely returning False
    assert not summarize_memory_file(file_path, keep_recent_n=5, max_age_days=7)
