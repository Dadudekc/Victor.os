import json  # noqa: I001
import os
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dreamos.memory.compaction_utils import (
    CompactionError,
    _rewrite_memory_safely,
    compact_segment_data,
    compact_segment_file,
)

# --- Fixtures ---


@pytest.fixture
def temp_file(tmp_path):
    return tmp_path / "test_segment.json"


@pytest.fixture
def sample_data():
    now = datetime.now(timezone.utc)
    return [
        {"id": 1, "timestamp": (now - timedelta(days=40)).isoformat(), "data": "old"},
        {
            "id": 2,
            "timestamp": (now - timedelta(days=20)).isoformat(),
            "data": "recent1",
        },
        {
            "id": 3,
            "timestamp": (now - timedelta(days=10)).isoformat(),
            "data": "recent2",
        },
        {"id": 4, "timestamp": (now - timedelta(days=5)).isoformat(), "data": "newest"},
        {"id": 5, "data": "no_timestamp"},
        {"id": 6, "timestamp": "invalid-date", "data": "bad_timestamp"},
    ]


@pytest.fixture
def setup_segment_file(tmp_path, sample_data):
    json_path = tmp_path / "segment.json"
    compressed_path = tmp_path / "segment.z"
    empty_path = tmp_path / "empty.json"
    invalid_path = tmp_path / "invalid.json"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(sample_data, f)

    json_bytes = json.dumps(sample_data).encode("utf-8")
    with compressed_path.open("wb") as f:
        f.write(zlib.compress(json_bytes))

    empty_path.touch()
    invalid_path.write_text("not json", encoding="utf-8")

    return {
        "json": json_path,
        "z": compressed_path,
        "empty": empty_path,
        "invalid": invalid_path,
    }


# --- _rewrite_memory_safely ---


def test_rewrite_memory_safely_basic_write(temp_file):
    data = {"key": "value", "list": [1, 2, 3]}
    with patch("os.replace") as mock_replace:
        _rewrite_memory_safely(temp_file, data, compress=False)
        temp_path = mock_replace.call_args[0][0]
        assert Path(temp_path).exists()
        with open(temp_path, "r", encoding="utf-8") as f:
            assert json.load(f) == data
        os.remove(temp_path)


def test_rewrite_memory_safely_compressed_write(temp_file):
    data = {"compressed": True}
    compressed_path = temp_file.with_suffix(".json.gz")

    with patch("os.replace") as mock_replace:
        _rewrite_memory_safely(compressed_path, data, compress=True)
        gz_temp_path = mock_replace.call_args[0][0]
        with open(gz_temp_path, "rb") as f:
            raw = zlib.decompress(f.read(), 16 + zlib.MAX_WBITS)
            assert json.loads(raw.decode("utf-8")) == data
        os.remove(gz_temp_path)


def test_rewrite_memory_safely_serializes_datetime(temp_file):
    now = datetime.now(timezone.utc)
    input_data = {"timestamp": now}
    with patch("os.replace") as mock_replace:
        _rewrite_memory_safely(temp_file, input_data, compress=False)
        tmp_path = mock_replace.call_args[0][0]
        with open(tmp_path, "r", encoding="utf-8") as f:
            written = json.load(f)
        assert written["timestamp"] == now.isoformat()
        os.remove(tmp_path)


# --- Exception Handling ---


def test_rewrite_memory_safely_write_failure(temp_file):
    mock_file = MagicMock()
    mock_file.write.side_effect = OSError("Disk full")
    context = MagicMock()
    context.__enter__.return_value = mock_file

    with (
        patch("tempfile.NamedTemporaryFile", return_value=context),
        pytest.raises(OSError, match="Disk full"),
    ):
        _rewrite_memory_safely(temp_file, {"test": 1}, compress=False)


def test_rewrite_memory_safely_replace_failure(temp_file):
    with (
        patch("os.replace", side_effect=OSError("Permission denied")),
        patch("os.remove") as mock_rm,
        pytest.raises(OSError, match="Permission denied"),
    ):
        _rewrite_memory_safely(temp_file, {"x": 1}, compress=False)
        assert mock_rm.call_count > 0


# --- compact_segment_data ---


def test_compact_segment_data_time_policy(sample_data):
    compacted = compact_segment_data(
        sample_data, {"type": "time_based", "max_age_days": 30}
    )
    ids = {e["id"] for e in compacted}
    assert ids == {2, 3, 4, 5, 6}


def test_compact_segment_data_keep_n_policy(sample_data):
    compacted = compact_segment_data(sample_data, {"type": "keep_n", "keep_n": 3})
    ids = {e["id"] for e in compacted}
    assert ids == {4, 5, 6}


def test_compact_segment_data_unknown_policy_returns_original(sample_data):
    compacted = compact_segment_data(sample_data, {"type": "garbage"})
    assert compacted == sample_data


def test_compact_segment_data_default_policy_values(sample_data):
    assert len(compact_segment_data(sample_data, {"type": "time_based"})) == 5
    assert len(compact_segment_data(sample_data, {"type": "keep_n"})) == len(
        sample_data
    )


# --- compact_segment_file ---


def test_compact_segment_file_on_json(setup_segment_file):
    path = setup_segment_file["json"]
    assert (
        compact_segment_file(path, {"type": "time_based", "max_age_days": 30}) is True
    )
    with path.open("r", encoding="utf-8") as f:
        assert len(json.load(f)) == 5


def test_compact_segment_file_on_compressed(setup_segment_file):
    path = setup_segment_file["z"]
    assert compact_segment_file(path, {"type": "keep_n", "keep_n": 3}) is True
    with open(path, "rb") as f:
        decompressed = zlib.decompress(f.read())
        assert len(json.loads(decompressed.decode("utf-8"))) == 3


def test_compact_segment_file_no_op(setup_segment_file):
    path = setup_segment_file["json"]
    before = path.read_text()
    assert compact_segment_file(path, {"type": "keep_n", "keep_n": 999}) is True
    after = path.read_text()
    assert before == after


def test_compact_segment_file_missing_ok(tmp_path):
    path = tmp_path / "nope.json"
    assert compact_segment_file(path, {"type": "keep_n", "keep_n": 10}) is True


def test_compact_segment_file_empty_ok(setup_segment_file):
    path = setup_segment_file["empty"]
    assert compact_segment_file(path, {"type": "keep_n", "keep_n": 10}) is True


def test_compact_segment_file_invalid_json_raises(setup_segment_file):
    path = setup_segment_file["invalid"]
    with pytest.raises(CompactionError, match="Failed to parse JSON"):
        compact_segment_file(path, {"type": "keep_n", "keep_n": 10})


def test_compact_segment_file_non_list_json_raises(tmp_path):
    path = tmp_path / "dict.json"
    path.write_text('{"key": "value"}', encoding="utf-8")
    with pytest.raises(CompactionError, match="Expected a list"):
        compact_segment_file(path, {"type": "keep_n", "keep_n": 10})


def test_compact_segment_file_load_failure_raises(tmp_path):
    path = tmp_path / "unreadable.json"
    path.touch()
    path.chmod(0o000)  # Make unreadable
    with (
        pytest.raises(CompactionError, match="Failed to load file"),
        patch("builtins.open", side_effect=IOError("Permission denied")),
    ):
        # Need to mock open because chmod might not work reliably across OS/filesystems
        compact_segment_file(path, {"type": "keep_n", "keep_n": 10})
    # Clean up permissions if possible
    try:
        path.chmod(0o666)
    except Exception:
        pass


def test_compact_segment_file_save_failure_raises(setup_segment_file):
    path = setup_segment_file["json"]
    with patch(
        "dreamos.memory.compaction_utils._rewrite_memory_safely", return_value=False
    ):
        with pytest.raises(CompactionError, match="Failed during atomic save"):
            compact_segment_file(path, {"type": "time_based", "max_age_days": 1})


def test_compact_segment_data_time_policy_with_tz(sample_data):
    now_aware = datetime.now(timezone(timedelta(hours=-5)))
    data_with_tz = [
        {
            "id": 1,
            "timestamp": (now_aware - timedelta(days=40)).isoformat(),
            "data": "old_tz",
        },
        {
            "id": 2,
            "timestamp": (now_aware - timedelta(days=20)).isoformat(),
            "data": "recent_tz",
        },
    ]
    compacted = compact_segment_data(
        data_with_tz, {"type": "time_based", "max_age_days": 30}
    )
    ids = {e["id"] for e in compacted}
    assert ids == {2}


def test_compact_segment_data_keep_n_edge_cases(sample_data):
    # Keep 0
    compacted_zero = compact_segment_data(sample_data, {"type": "keep_n", "keep_n": 0})
    assert len(compacted_zero) == 0
    # Keep exact number
    compacted_exact = compact_segment_data(
        sample_data, {"type": "keep_n", "keep_n": len(sample_data)}
    )
    assert len(compacted_exact) == len(sample_data)
    assert compacted_exact == sample_data
    # Keep more than available
    compacted_more = compact_segment_data(
        sample_data, {"type": "keep_n", "keep_n": len(sample_data) + 5}
    )
    assert len(compacted_more) == len(sample_data)
    assert compacted_more == sample_data


@patch("dreamos.memory.compaction_utils.logger")
def test_compact_segment_data_logs_warnings(mock_logger, sample_data):
    compact_segment_data(sample_data, {"type": "time_based", "max_age_days": 1})
    # Check that warnings were logged for the missing and bad timestamps
    assert any(
        "missing 'timestamp'" in call.args[0]
        for call in mock_logger.warning.call_args_list
    )
    assert any(
        "Could not parse timestamp 'invalid-date'" in call.args[0]
        for call in mock_logger.warning.call_args_list
    )


def test_rewrite_memory_safely_non_serializable_fails(temp_file):
    class NonSerializable:
        pass

    data = [{"item": NonSerializable()}]
    # Expect _rewrite_memory_safely to catch the TypeError from json.dumps and return False  # noqa: E501
    assert _rewrite_memory_safely(temp_file, data, is_compressed=False) is False


def test_compact_segment_file_invalid_json_fails(setup_segment_file):
    path = setup_segment_file["invalid"]
    assert compact_segment_file(path, {"type": "keep_n", "keep_n": 10}) is False


@patch("dreamos.memory.compaction_utils._rewrite_memory_safely")
def test_compact_segment_file_rewrite_failure(mock_rewrite, setup_segment_file):
    """Test that compact_segment_file returns False if _rewrite_memory_safely fails."""
    path = setup_segment_file["json"]
    # Configure mock to raise an error simulating write/replace failure
    mock_rewrite.side_effect = CompactionError("Simulated rewrite failure")

    # Policy that *would* cause a rewrite
    policy = {"type": "time_based", "max_age_days": 30}

    result = compact_segment_file(path, policy)

    # Assertions
    assert result is False
    mock_rewrite.assert_called_once()  # Ensure rewrite was attempted


@patch("dreamos.memory.compaction_utils.logger.error")
@patch("dreamos.memory.compaction_utils._rewrite_memory_safely")
def test_compact_segment_file_logs_rewrite_failure(
    mock_rewrite, mock_log_error, setup_segment_file
):
    """Test that compact_segment_file logs an error if _rewrite_memory_safely fails."""
    path = setup_segment_file["json"]
    mock_rewrite.side_effect = OSError(
        "Disk full simulation"
    )  # Use a standard OS error
    policy = {"type": "time_based", "max_age_days": 30}

    compact_segment_file(path, policy)

    # Assertions
    mock_rewrite.assert_called_once()
    mock_log_error.assert_called_once()
    assert "Failed to rewrite compacted segment file" in mock_log_error.call_args[0][0]
    assert "Disk full simulation" in mock_log_error.call_args[0][1]
