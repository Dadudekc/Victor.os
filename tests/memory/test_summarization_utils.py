import json  # noqa: I001
import os
import zlib  # Needed for checking compressed data
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from dreamos.core.config import SummarizationConfig
from dreamos.utils.summarizer import BaseSummarizer  # For mocking

# Adjust the import path based on your project structure
from dreamos.memory.summarization_utils import (
    SummarizationError,  # Import custom error
    _build_llm_summary_prompt,
    _rewrite_memory_safely,
    summarize_conversations,
    summarize_segment_chunk,
    summarize_segment_file,
)


# Mock Summarizer Implementation
class MockSummarizer(BaseSummarizer):
    async def summarize_entries(self, entries: list[dict]) -> str:
        count = len(entries)
        first_text = entries[0].get("text", "")[:15] if entries else ""
        return f"Mock summary of {count} entries: {first_text}..."


@pytest.fixture
def mock_summarizer_instance():
    return MockSummarizer()


@pytest.fixture
def sample_policy():
    """Provides a default summarization policy for tests."""
    return SummarizationConfig(
        enabled=True,
        max_entries_before_summarize=5,  # Low threshold for testing
        summarization_chunk_size=3,
    )


@pytest.fixture
def create_segment_file(tmp_path):
    """Helper fixture to create a segment file with given data."""

    def _creator(filename: str, data: list):
        file_path = tmp_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # Use _rewrite_memory_safely to ensure consistent creation (e.g., handling compression)  # noqa: E501
        # For simplicity here, just write directly. Adapt if _rewrite is needed.
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return file_path

    return _creator


# --- Tests for summarize_segment_chunk ---


@pytest.fixture
def sample_chunk():
    return [
        {"id": 1, "timestamp": "2023-01-01T10:00:00Z", "text": "Entry 1 data"},
        {"id": 2, "timestamp": "2023-01-01T11:00:00Z", "text": "Entry 2 data"},
    ]


def test_summarize_segment_chunk_placeholder(sample_chunk, sample_policy):
    """Test placeholder generation when no summarizer is provided."""
    summary_entry = summarize_segment_chunk(sample_chunk, sample_policy.dict(), None)
    assert summary_entry["type"] == "memory_summary"
    assert summary_entry["original_entry_count"] == 2
    assert "[Placeholder summary" in summary_entry["summary_content"]
    assert summary_entry["time_range_start"] == sample_chunk[0]["timestamp"]
    assert summary_entry["time_range_end"] == sample_chunk[-1]["timestamp"]
    assert "policy_used" in summary_entry


def test_summarize_segment_chunk_with_summarizer(
    sample_chunk, sample_policy, mock_summarizer_instance
):
    """Test summary generation using a mock summarizer."""
    summary_entry = summarize_segment_chunk(
        sample_chunk, sample_policy.dict(), mock_summarizer_instance
    )
    assert summary_entry["type"] == "memory_summary"
    assert summary_entry["original_entry_count"] == 2
    assert "Mock summary of 2 entries" in summary_entry["summary_content"]
    assert "Entry 1 data..." in summary_entry["summary_content"]


@patch("dreamos.memory.summarization_utils.logger.error")  # Mock logger to check calls
def test_summarize_segment_chunk_summarizer_error(
    mock_log_error, sample_chunk, sample_policy, mock_summarizer_instance
):
    """Test fallback to placeholder when summarizer raises an error."""
    mock_summarizer_instance.summarize_entries = MagicMock(
        side_effect=Exception("Test Summarizer Fail")
    )

    summary_entry = summarize_segment_chunk(
        sample_chunk, sample_policy.dict(), mock_summarizer_instance
    )

    assert summary_entry["type"] == "memory_summary"
    assert summary_entry["original_entry_count"] == 2
    assert (
        "[Summarizer Error (Test Summarizer Fail)" in summary_entry["summary_content"]
    )
    mock_log_error.assert_called_once()


def test_summarize_segment_chunk_empty_chunk(sample_policy):
    """Test handling of an empty input chunk."""
    summary_entry = summarize_segment_chunk([], sample_policy.dict(), None)
    assert "summary_error" in summary_entry
    assert summary_entry["summary_error"] == "Empty chunk provided"


# --- Tests for summarize_segment_file ---


# Mark test as async
@pytest.mark.asyncio
async def test_summarize_segment_triggers_summarization(
    create_segment_file, mock_summarizer_instance, sample_policy, tmp_path
):
    """Test that summarization is triggered when criteria are met."""
    segment_filename = "summarize_me.json"
    # Create data exceeding the policy's max_entries threshold (5)
    data = [
        {"id": i, "timestamp": f"2023-01-0{i+1}T10:00:00Z", "text": f"Entry {i}"}
        for i in range(7)
    ]
    segment_path = create_segment_file(segment_filename, data)

    # Patch the rewrite function to avoid actual file modification during assertion phase  # noqa: E501
    # and check its call arguments
    with patch(
        "dreamos.memory.summarization_utils._rewrite_memory_safely"
    ) as mock_rewrite:
        # Patch the summarizer's summarize method to track calls
        with patch.object(
            mock_summarizer_instance,
            "summarize_entries",
            wraps=mock_summarizer_instance.summarize_entries,
        ) as mock_summarize_method:
            summarize_segment_file(
                file_path=segment_path,
                summarizer=mock_summarizer_instance,
                policy=sample_policy.dict(),
            )

            # Assertions
            mock_summarize_method.assert_called_once()
            mock_rewrite.assert_called_once()

            # Check the data passed to the rewrite function
            rewritten_data = mock_rewrite.call_args[0][1]
            assert isinstance(rewritten_data, list)
            # Should contain 1 summary chunk + remaining raw entries (7 total - 3 summarized chunk size = 4 raw)  # noqa: E501
            assert len(rewritten_data) == 1 + (
                len(data) - sample_policy.summarization_chunk_size
            )
            assert rewritten_data[0]["type"] == "memory_summary"
            assert (
                rewritten_data[0]["original_entry_count"]
                == sample_policy.summarization_chunk_size
            )
            assert "Mock summary of" in rewritten_data[0]["summary_content"]
            # Check that the raw entries kept are the newest ones
            assert (
                rewritten_data[1]["id"] == 3
            )  # 0, 1, 2 summarized -> 3 is first raw entry
            assert rewritten_data[-1]["id"] == 6  # Last entry


# --- Additional Test Cases ---


@pytest.mark.asyncio
async def test_summarize_segment_not_needed_below_threshold(
    create_segment_file, mock_summarizer_instance, sample_policy, tmp_path
):
    """Test summarization is NOT triggered if entry count is below threshold."""
    segment_filename = "no_summarize_needed.json"
    # Create data *below* the policy's max_entries threshold (5)
    data = [
        {"id": i, "timestamp": f"2023-01-0{i+1}T10:00:00Z", "text": f"Entry {i}"}
        for i in range(sample_policy.max_entries_before_summarize - 1)
    ]
    segment_path = create_segment_file(segment_filename, data)

    with (
        patch(
            "dreamos.memory.summarization_utils._rewrite_memory_safely"
        ) as mock_rewrite,
        patch(
            "dreamos.memory.summarization_utils.summarize_segment_chunk"
        ) as mock_summarize_chunk,
    ):
        result = summarize_segment_file(
            file_path=segment_path,
            summarizer=mock_summarizer_instance,
            policy=sample_policy.dict(),
        )
        assert result is True
        mock_summarize_chunk.assert_not_called()
        mock_rewrite.assert_not_called()


@pytest.mark.asyncio
async def test_summarize_segment_handles_existing_summary(
    create_segment_file, mock_summarizer_instance, sample_policy, tmp_path
):
    """Test that existing summary chunks are preserved and not re-summarized."""
    segment_filename = "existing_summary.json"
    # Existing summary + enough new entries to trigger summarization (total > 5)
    data = [
        # Old existing summary chunk
        {
            "type": "memory_summary",
            "original_entry_count": 10,
            "summary_content": "Old summary",
            "time_range_start": "2022-12-01T00:00:00Z",
            "time_range_end": "2022-12-10T00:00:00Z",
        },
        # New entries that exceed threshold (policy threshold is 5, chunk size 3)
        *[
            {
                "id": i,
                "timestamp": f"2023-01-1{i+1}T10:00:00Z",
                "text": f"New Entry {i}",
            }
            for i in range(6)
        ],  # Needs summarization
    ]
    segment_path = create_segment_file(segment_filename, data)

    with patch(
        "dreamos.memory.summarization_utils._rewrite_memory_safely"
    ) as mock_rewrite:
        with patch.object(
            mock_summarizer_instance,
            "summarize_entries",
            wraps=mock_summarizer_instance.summarize_entries,
        ) as mock_summarize_method:
            summarize_segment_file(
                file_path=segment_path,
                summarizer=mock_summarizer_instance,
                policy=sample_policy.dict(),
            )

            # Assertions
            mock_summarize_method.assert_called_once()  # Should summarize the new entries  # noqa: E501
            mock_rewrite.assert_called_once()

            # Check rewritten data
            rewritten_data = mock_rewrite.call_args[0][1]
            assert (
                len(rewritten_data) == 3
            )  # Old Summary + New Summary + Remaining Raw (6 new - 3 summarized = 3 raw)  # noqa: E501

            # Check order and types
            assert (
                rewritten_data[0]["type"] == "memory_summary"
            )  # Old summary preserved
            assert rewritten_data[0]["original_entry_count"] == 10
            assert rewritten_data[1]["type"] == "memory_summary"  # New summary chunk
            assert (
                rewritten_data[1]["original_entry_count"]
                == sample_policy.summarization_chunk_size
            )  # Summarized 3
            assert (
                rewritten_data[2]["id"] == 3
            )  # Raw entries start after the summarized ones (0,1,2 -> 3)
            assert rewritten_data[-1]["id"] == 5  # Last raw entry


@pytest.mark.asyncio
async def test_summarize_segment_file_not_found(
    mock_summarizer_instance,
    sample_policy,
    tmp_path,  # Use tmp_path to ensure the path itself is valid
):
    """Test that the function handles a non-existent file gracefully."""
    non_existent_path = tmp_path / "non_existent_segment.json"

    # Ensure the file does NOT exist
    assert not non_existent_path.exists()

    with patch(
        "dreamos.memory.summarization_utils._rewrite_memory_safely"
    ) as mock_rewrite:
        with patch.object(
            mock_summarizer_instance, "summarize_entries"
        ) as mock_summarize_method:
            # Call the function - it should catch the FileNotFoundError internally and log it  # noqa: E501
            try:
                summarize_segment_file(
                    file_path=non_existent_path,
                    summarizer=mock_summarizer_instance,
                    policy=sample_policy.dict(),
                )
            except Exception as e:
                pytest.fail(f"summarize_segment_file raised unexpected exception: {e}")

            # Assertions: Nothing should have happened
            mock_summarize_method.assert_not_called()
            mock_rewrite.assert_not_called()
            # We could also check logs if logging is mocked, but ensuring no crash and no calls is sufficient here.  # noqa: E501


@pytest.mark.asyncio
async def test_summarize_segment_summarizer_error(
    create_segment_file, mock_summarizer_instance, sample_policy, tmp_path
):
    """Test that an error during the summarizer call is handled."""
    segment_filename = "summarizer_error.json"
    # Create data that *will* trigger summarization
    data = [
        {"id": i, "timestamp": f"2023-01-0{i+1}T10:00:00Z", "text": f"Entry {i}"}
        for i in range(7)
    ]
    segment_path = create_segment_file(segment_filename, data)

    # Simulate summarizer error
    mock_summarizer_instance.summarize_entries = AsyncMock(
        side_effect=ValueError("Summarizer failed!")
    )

    with patch(
        "dreamos.memory.summarization_utils._rewrite_memory_safely"
    ) as mock_rewrite:
        # Call the function - it should catch the summarizer error and log it
        try:
            summarize_segment_file(
                file_path=segment_path,
                summarizer=mock_summarizer_instance,
                policy=sample_policy.dict(),
            )
        except Exception as e:
            pytest.fail(f"summarize_segment_file raised unexpected exception: {e}")

        # Assertions: Summarizer was called, but rewrite should NOT have been called
        mock_summarizer_instance.summarize_entries.assert_called_once()
        mock_rewrite.assert_not_called()
        # Check logs for the error if logging is mocked.


@pytest.mark.asyncio
async def test_summarize_segment_with_compression(
    create_segment_file, mock_summarizer_instance, sample_policy, tmp_path
):
    """Test that summarization works correctly when compress_after=True."""
    segment_filename = "summarize_me_compressed.json"
    # Create data exceeding the policy's max_entries threshold (5)
    data = [
        {"id": i, "timestamp": f"2023-01-0{i+1}T10:00:00Z", "text": f"Entry {i}"}
        for i in range(7)
    ]
    segment_path = create_segment_file(segment_filename, data)

    # Patch rewrite (to check args) and the os.replace it uses (to check temp file)
    with (
        patch(
            "dreamos.memory.summarization_utils._rewrite_memory_safely",
            wraps=_rewrite_memory_safely,
        ) as mock_rewrite_wrapper,
        patch("dreamos.memory.compaction_utils.os.replace") as mock_os_replace,
    ):
        summarize_segment_file(
            file_path=segment_path,
            summarizer=mock_summarizer_instance,
            policy=sample_policy.dict(),
            compress_after=True,  # Enable compression
        )

        # Assertions
        # 1. Rewrite function was called with compress=True
        mock_rewrite_wrapper.assert_called_once()
        wrapper_call_args = mock_rewrite_wrapper.call_args
        assert wrapper_call_args[1].get("compress") is True

        # 2. os.replace was called (by the rewrite function)
        mock_os_replace.assert_called_once()

        # 3. The file that *would* have been replaced is compressed and contains correct data  # noqa: E501
        temp_file_path = mock_os_replace.call_args[0][0]
        final_target_path = mock_os_replace.call_args[0][1]
        assert final_target_path == str(segment_path)
        assert temp_file_path.endswith(".gz")

        # Verify content of the temp compressed file
        assert os.path.exists(temp_file_path)
        with open(temp_file_path, "rb") as f_gz:
            decompressed_bytes = zlib.decompress(f_gz.read(), 16 + zlib.MAX_WBITS)
        written_data = json.loads(decompressed_bytes.decode("utf-8"))

        # Check structure
        assert len(written_data) == 1 + (
            len(data) - sample_policy.summarization_chunk_size
        )
        assert written_data[0]["type"] == "memory_summary"
        assert written_data[1]["id"] == 3

        # Cleanup the temp file created by _rewrite_memory_safely
        os.remove(temp_file_path)


@pytest.mark.asyncio
async def test_summarize_segment_file_empty_file(
    create_segment_file, mock_summarizer_instance, sample_policy, tmp_path
):
    """Test handling of an empty segment file."""
    segment_filename = "empty_segment.json"
    segment_path = create_segment_file(segment_filename, [])  # Create with empty list
    # Or create an empty file directly:
    # segment_path = tmp_path / segment_filename
    # segment_path.touch()

    with (
        patch(
            "dreamos.memory.summarization_utils._rewrite_memory_safely"
        ) as mock_rewrite,
        patch(
            "dreamos.memory.summarization_utils.summarize_segment_chunk"
        ) as mock_summarize_chunk,
    ):
        result = summarize_segment_file(
            file_path=segment_path,
            summarizer=mock_summarizer_instance,
            policy=sample_policy.dict(),
        )
        # Should return True (no action needed), but log a warning internally
        assert result is True
        mock_summarize_chunk.assert_not_called()
        mock_rewrite.assert_not_called()


@pytest.mark.asyncio
async def test_summarize_segment_file_invalid_json(
    mock_summarizer_instance, sample_policy, tmp_path
):
    """Test handling of a segment file with invalid JSON content."""
    segment_filename = "invalid_json.json"
    segment_path = tmp_path / segment_filename
    with open(segment_path, "w", encoding="utf-8") as f:
        f.write("this is not valid json{")

    with (
        patch(
            "dreamos.memory.summarization_utils._rewrite_memory_safely"
        ) as mock_rewrite,
        patch(
            "dreamos.memory.summarization_utils.summarize_segment_chunk"
        ) as mock_summarize_chunk,
        patch("dreamos.memory.summarization_utils.logger.error") as mock_log_error,
    ):  # Check logs
        result = summarize_segment_file(
            file_path=segment_path,
            summarizer=mock_summarizer_instance,
            policy=sample_policy.dict(),
        )
        # Should return False because loading failed
        assert result is False
        mock_summarize_chunk.assert_not_called()
        mock_rewrite.assert_not_called()
        mock_log_error.assert_called_once()
        assert "Failed to load or parse segment file" in mock_log_error.call_args[0][0]


# --- Tests for Error Handling in summarize_segment_file ---


@pytest.mark.asyncio
async def test_summarize_segment_file_invalid_json_raises(
    mock_summarizer_instance, sample_policy, tmp_path
):
    """Test that invalid JSON in the segment file raises SummarizationError."""
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("not json data", encoding="utf-8")

    with pytest.raises(SummarizationError, match="Failed to parse JSON"):
        summarize_segment_file(
            file_path=invalid_path,
            summarizer=mock_summarizer_instance,
            policy=sample_policy.dict(),
        )


@pytest.mark.asyncio
async def test_summarize_segment_file_non_list_json_raises(
    create_segment_file, mock_summarizer_instance, sample_policy, tmp_path
):
    """Test that JSON that isn't a list raises SummarizationError."""
    dict_path = tmp_path / "dict.json"
    dict_path.write_text('{"key": "value"}', encoding="utf-8")

    with pytest.raises(SummarizationError, match="Expected a list"):
        summarize_segment_file(
            file_path=dict_path,
            summarizer=mock_summarizer_instance,
            policy=sample_policy.dict(),
        )


@pytest.mark.asyncio
async def test_summarize_segment_file_save_failure_raises(
    create_segment_file, mock_summarizer_instance, sample_policy, tmp_path
):
    """Test that a failure during file saving raises SummarizationError."""
    data = [
        {"id": i, "timestamp": f"2023-01-0{i+1}T10:00:00Z", "text": f"Entry {i}"}
        for i in range(7)
    ]
    segment_path = create_segment_file("save_fail.json", data)

    with patch(
        "dreamos.memory.summarization_utils._rewrite_memory_safely", return_value=False
    ):
        with pytest.raises(SummarizationError, match="Failed during atomic save"):
            summarize_segment_file(
                file_path=segment_path,
                summarizer=mock_summarizer_instance,
                policy=sample_policy.dict(),
            )


@patch("dreamos.memory.summarization_utils.logger")  # Mock logger
@pytest.mark.asyncio
async def test_summarize_segment_policy_misconfiguration_warning(
    mock_logger, create_segment_file, mock_summarizer_instance, tmp_path
):
    """Test that a warning is logged for policy misconfiguration."""
    # Policy where chunk size < min chunk size (implicitly 10)
    policy = {
        "trigger_threshold_entries": 5,
        "summarize_n_oldest": 3,
        "min_chunk_size": 10,  # Explicitly set higher
    }
    data = [{"id": i} for i in range(6)]  # Enough to trigger
    segment_path = create_segment_file("policy_warn.json", data)

    # We don't care about the outcome, just the log
    with patch("dreamos.memory.summarization_utils._rewrite_memory_safely"):
        summarize_segment_file(segment_path, policy, mock_summarizer_instance)

    mock_logger.warning.assert_any_call(
        pytest.approx(
            "Policy misconfiguration: summarize_n_oldest (3) < min_chunk_size (10)"
        )
    )


@pytest.mark.asyncio
async def test_summarize_segment_file_chunk_summary_error_raises(
    create_segment_file, mock_summarizer_instance, sample_policy, tmp_path
):
    """Test that an error from summarize_segment_chunk raises SummarizationError."""
    data = [{"id": i} for i in range(6)]  # Enough to trigger
    segment_path = create_segment_file("chunk_fail.json", data)

    with patch(
        "dreamos.memory.summarization_utils.summarize_segment_chunk",
        return_value={"summary_error": "Chunk Fail Test"},
    ):
        with pytest.raises(
            SummarizationError, match="Summarization failed for chunk.*Chunk Fail Test"
        ):
            summarize_segment_file(
                segment_path, sample_policy.dict(), mock_summarizer_instance
            )


# --- Tests for summarize_conversations ---


@pytest.fixture
def sample_conversations():
    return [
        {"sender": "User", "content": "Hello there!", "timestamp": "T1"},
        {"sender": "Agent", "content": "Hi! How can I help?", "timestamp": "T2"},
        {"sender": "User", "content": "Tell me a joke.", "timestamp": "T3"},
        {
            "sender": "Agent",
            "content": "Why did the scarecrow win an award? Because he was outstanding in his field!",  # noqa: E501
            "timestamp": "T4",
        },
    ]


def test_summarize_conversations_simple_concat(sample_conversations):
    summary = summarize_conversations(sample_conversations, strategy="simple_concat")
    assert "User: Hello there!" in summary
    assert "Agent: Hi! How can I help?" in summary
    assert "User: Tell me a joke." in summary
    assert "outstanding in his field!" in summary
    assert len(summary.split("\n")) == 4


def test_summarize_conversations_simple_concat_truncation(sample_conversations):
    max_len = 50
    summary = summarize_conversations(
        sample_conversations, strategy="simple_concat", max_length=max_len
    )
    assert len(summary) <= max_len
    assert summary.endswith("...")
    assert "User: Hello there!" in summary
    assert "Agent: Hi! How can" in summary  # Should be truncated here
    assert "Tell me a joke" not in summary


def test_summarize_conversations_simple_concat_empty():
    summary = summarize_conversations([], strategy="simple_concat")
    assert summary == ""


def test_summarize_conversations_llm_placeholder(sample_conversations):
    mock_client = MagicMock()
    summary = summarize_conversations(
        sample_conversations, strategy="llm_abstractive", llm_client=mock_client
    )
    assert "Abstractive Summary (Placeholder):" in summary
    assert "Start: Hello there!..." in summary
    assert "...outstanding in his field!" in summary


def test_summarize_conversations_llm_placeholder_truncation(sample_conversations):
    mock_client = MagicMock()
    max_len = 70
    summary = summarize_conversations(
        sample_conversations,
        strategy="llm_abstractive",
        llm_client=mock_client,
        max_length=max_len,
    )
    assert len(summary) <= max_len
    assert "Abstractive Summary (Placeholder):" in summary


def test_summarize_conversations_llm_no_client_raises(sample_conversations):
    with pytest.raises(SummarizationError, match="LLM client not provided"):
        summarize_conversations(
            sample_conversations, strategy="llm_abstractive", llm_client=None
        )


def test_summarize_conversations_llm_empty_input():
    mock_client = MagicMock()
    summary = summarize_conversations(
        [], strategy="llm_abstractive", llm_client=mock_client
    )
    assert summary == "No conversation content provided."


def test_summarize_conversations_unknown_strategy_raises(sample_conversations):
    with pytest.raises(
        ValueError, match="Unknown summarization strategy: invalid_strat"
    ):
        summarize_conversations(sample_conversations, strategy="invalid_strat")


# --- Tests for _build_llm_summary_prompt ---


def test_build_llm_summary_prompt_basic(sample_conversations):
    prompt = _build_llm_summary_prompt(sample_conversations)
    assert prompt.startswith("Summarize the following conversation concisely:\n---")
    assert prompt.endswith("\n---\nSummary:")
    assert "User (T1): Hello there!" in prompt
    assert "Agent (T2): Hi! How can I help?" in prompt
    assert "User (T3): Tell me a joke." in prompt
    assert (
        "Agent (T4): Why did the scarecrow win an award? Because he was outstanding in his field!"  # noqa: E501
        in prompt
    )


def test_build_llm_summary_prompt_missing_fields():
    conversations = [
        {"content": "First message."},  # Missing sender and timestamp
        {"sender": "User"},  # Missing content and timestamp
        {"sender": "Agent", "content": "Third message."},  # Missing timestamp
    ]
    prompt = _build_llm_summary_prompt(conversations)
    assert "Unknown: First message." in prompt
    assert "User: [no content]" in prompt
    assert "Agent: Third message." in prompt


def test_build_llm_summary_prompt_empty():
    prompt = _build_llm_summary_prompt([])
    assert (
        prompt == "Summarize the following conversation concisely:\n---\n---\nSummary:"
    )


# (No more TODOs for this file)
