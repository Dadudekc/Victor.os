import json
from pathlib import Path

from dreamos.services.event_logger import log_structured_event

# Remove the skipped stub function
# @pytest.mark.skip(reason='Test stub for coverage tracking')
# def test_stub_for_event_logger():
#     pass


def test_log_structured_event_creates_file_and_logs(tmp_path: Path):
    """Test logging a single event creates the file and writes correctly."""
    log_file = tmp_path / "events.jsonl"
    event_type = "TEST_EVENT"
    data = {"key": "value", "num": 1}
    source = "test_source"

    # Ensure file doesn't exist initially
    assert not log_file.exists()

    log_structured_event(event_type, data, source, log_file=str(log_file))

    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    # Parse the logged JSON
    logged_record = json.loads(lines[0])

    assert logged_record["type"] == event_type
    assert logged_record["data"] == data
    assert logged_record["source"] == source
    assert "id" in logged_record
    assert "timestamp" in logged_record
    # Rough check on timestamp format
    assert logged_record["timestamp"].endswith("Z")


def test_log_structured_event_appends(tmp_path: Path):
    """Test that subsequent calls append to the log file."""
    log_file = tmp_path / "append_test.jsonl"
    event_type1 = "EVENT_1"
    data1 = {"a": 1}
    source1 = "src1"

    event_type2 = "EVENT_2"
    data2 = {"b": 2}
    source2 = "src2"

    # Log first event
    log_structured_event(event_type1, data1, source1, log_file=str(log_file))
    # Log second event
    log_structured_event(event_type2, data2, source2, log_file=str(log_file))

    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    # Check second record
    logged_record1 = json.loads(lines[0])
    logged_record2 = json.loads(lines[1])

    assert logged_record1["type"] == event_type1
    assert logged_record2["type"] == event_type2
    assert logged_record2["data"] == data2
    assert logged_record2["source"] == source2


def test_log_structured_event_creates_directory(tmp_path: Path):
    """Test that the logging function creates parent directories if needed."""
    log_dir = tmp_path / "nested" / "logs"
    log_file = log_dir / "deep_events.jsonl"
    event_type = "DEEP_EVENT"
    data = {}
    source = "deep_src"

    assert not log_dir.exists()

    log_structured_event(event_type, data, source, log_file=str(log_file))

    assert log_dir.exists()
    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    logged_record = json.loads(lines[0])
    assert logged_record["type"] == event_type

    # Add more tests as needed
    # ...
