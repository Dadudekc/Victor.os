import json
from pathlib import Path

from dreamos.utils.file_io import (
    append_jsonl,
    read_json_file,
    read_jsonl_file,
    read_text_file,
    write_json_atomic,
    write_text_file_atomic,
)

# --- Tests for JSON functions ---


def test_write_read_json_dict(tmp_path: Path):
    """Test writing and reading a dictionary to/from JSON."""
    file_path = tmp_path / "test_dict.json"
    data_to_write = {"key": "value", "number": 123, "list": [1, 2, 3]}

    write_json_atomic(file_path, data_to_write)
    assert file_path.exists()

    read_data = read_json_file(file_path)
    assert read_data == data_to_write


def test_write_read_json_list(tmp_path: Path):
    """Test writing and reading a list to/from JSON."""
    file_path = tmp_path / "test_list.json"
    data_to_write = [{"id": 1}, {"id": 2}]

    write_json_atomic(file_path, data_to_write)
    assert file_path.exists()

    read_data = read_json_file(file_path)
    assert read_data == data_to_write


def test_read_json_file_not_found(tmp_path: Path):
    """Test reading a non-existent JSON file returns None."""
    file_path = tmp_path / "non_existent.json"
    assert read_json_file(file_path) is None


def test_read_json_invalid_json(tmp_path: Path):
    """Test reading an invalid JSON file returns None."""
    file_path = tmp_path / "invalid.json"
    file_path.write_text("this is not json{")
    assert read_json_file(file_path) is None


# --- Tests for JSONL functions ---


def test_append_read_jsonl(tmp_path: Path):
    """Test appending multiple records to JSONL and reading them back."""
    file_path = tmp_path / "test.jsonl"
    record1 = {"id": 1, "msg": "hello"}
    record2 = {"id": 2, "msg": "world"}

    # Append first record
    append_jsonl(file_path, record1)
    assert file_path.exists()
    content1 = file_path.read_text().strip()
    assert content1 == json.dumps(record1, separators=(",", ":"))

    # Append second record
    append_jsonl(file_path, record2)
    content2 = file_path.read_text().strip().split("\n")
    assert len(content2) == 2
    assert content2[1] == json.dumps(record2, separators=(",", ":"))

    # Read back both records
    read_data = read_jsonl_file(file_path)
    assert read_data == [record1, record2]


def test_read_jsonl_file_not_found(tmp_path: Path):
    """Test reading a non-existent JSONL file returns an empty list."""
    file_path = tmp_path / "non_existent.jsonl"
    assert read_jsonl_file(file_path) == []


def test_read_jsonl_invalid_line(tmp_path: Path):
    """Test reading JSONL with an invalid line skips that line."""
    file_path = tmp_path / "mixed.jsonl"
    record1 = {"id": 1}
    record3 = {"id": 3}
    file_path.write_text(
        json.dumps(record1) + "\n" + "this is not json\n" + json.dumps(record3) + "\n"
    )
    read_data = read_jsonl_file(file_path)
    assert read_data == [record1, record3]


# --- Tests for Text functions ---


def test_write_read_text(tmp_path: Path):
    """Test writing and reading plain text."""
    file_path = tmp_path / "test.txt"
    content_to_write = "Line 1\nLine 2\nUTF-8: öäüß"

    write_text_file_atomic(file_path, content_to_write)
    assert file_path.exists()

    read_content = read_text_file(file_path)
    assert read_content == content_to_write


def test_read_text_file_not_found(tmp_path: Path):
    """Test reading non-existent text file returns None."""
    file_path = tmp_path / "non_existent.txt"
    assert read_text_file(file_path) is None


# Note: Testing ensure_directory_exists is slightly more complex
# as it involves side effects on the filesystem, often done via mocking os.makedirs
# or by checking directory creation within the test, which can be less isolated.
# Skipping for this basic implementation round.
