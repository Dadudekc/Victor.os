import json
from pathlib import Path
from unittest.mock import call, patch

from dreamos.utils.file_io import (
    FALLBACK_READ_END_LINE,
    WARMUP_READ_END_LINE,
    _extract_content_from_tool_response,
    append_jsonl,
    read_json_file,
    read_jsonl_file,
    read_text_file,
    safe_read_with_tool,
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

# --- Tests for _extract_content_from_tool_response ---


def test_extract_content_success():
    response = {"read_file_response": {"results": ["Test content"]}}
    assert _extract_content_from_tool_response(response, "dummy.txt") == "Test content"


def test_extract_content_no_response():
    assert _extract_content_from_tool_response(None, "dummy.txt") is None


def test_extract_content_empty_dict_response():
    assert _extract_content_from_tool_response({}, "dummy.txt") is None


def test_extract_content_missing_read_file_response_key():
    response = {"other_key": "value"}
    assert _extract_content_from_tool_response(response, "dummy.txt") is None


def test_extract_content_missing_results_key():
    response = {"read_file_response": {"other_key": "value"}}
    assert _extract_content_from_tool_response(response, "dummy.txt") is None


def test_extract_content_results_not_a_list():
    response = {"read_file_response": {"results": "not a list"}}
    assert _extract_content_from_tool_response(response, "dummy.txt") is None


def test_extract_content_results_empty_list():
    response = {"read_file_response": {"results": []}}
    assert _extract_content_from_tool_response(response, "dummy.txt") is None


def test_extract_content_results_list_with_none():
    response = {"read_file_response": {"results": [None]}}
    assert _extract_content_from_tool_response(response, "dummy.txt") is None


def test_extract_content_results_list_with_non_string_becomes_string():
    response = {"read_file_response": {"results": [123]}}
    assert _extract_content_from_tool_response(response, "dummy.txt") == "123"


def test_extract_content_tool_error_in_results_string():
    response = {
        "read_file_response": {"results": ["Error calling tool: File too large"]}
    }
    assert _extract_content_from_tool_response(response, "dummy.txt") is None


def test_extract_content_tool_error_in_error_field():
    response = {"read_file_response": {"error": "Timeout reading file"}}
    assert _extract_content_from_tool_response(response, "dummy.txt") is None


def test_extract_content_malformed_response_completely_unexpected_structure():
    response = {"unexpected_key": {"unexpected_data": "data"}}
    assert _extract_content_from_tool_response(response, "dummy.txt") is None


# --- Tests for safe_read_with_tool ---

MOCK_TARGET_FILE = "test_file.txt"
MOCK_WARMUP_EXPLANATION = f"Safely reading {MOCK_TARGET_FILE}: Warm-up chunked read."
MOCK_FULL_READ_EXPLANATION = f"Safely reading {MOCK_TARGET_FILE}: Attempting full read."
MOCK_FALLBACK_EXPLANATION = f"Safely reading {MOCK_TARGET_FILE}: Fallback chunked read."


@patch("dreamos.utils.file_io.default_api.read_file")
def test_safe_read_success_full_read(mock_read_file):
    """Test successful warm-up and full read."""
    mock_read_file.side_effect = [
        {"read_file_response": {"results": ["Warm-up content"]}},  # Warm-up
        {"read_file_response": {"results": ["Full file content"]}},  # Full read
    ]

    content = safe_read_with_tool(MOCK_TARGET_FILE, read_full_file_if_possible=True)
    assert content == "Full file content"

    expected_calls = [
        call(
            target_file=MOCK_TARGET_FILE,
            start_line_one_indexed=1,
            end_line_one_indexed_inclusive=WARMUP_READ_END_LINE,
            should_read_entire_file=False,
            explanation=MOCK_WARMUP_EXPLANATION,
        ),
        call(
            target_file=MOCK_TARGET_FILE,
            should_read_entire_file=True,
            start_line_one_indexed=1,
            end_line_one_indexed_inclusive=1,
            explanation=MOCK_FULL_READ_EXPLANATION,
        ),
    ]
    mock_read_file.assert_has_calls(expected_calls)
    assert mock_read_file.call_count == 2


@patch("dreamos.utils.file_io.default_api.read_file")
def test_safe_read_full_read_tool_error_fallback_succeeds(mock_read_file):
    """Test full read fails (tool error), fallback chunk succeeds."""
    mock_read_file.side_effect = [
        {"read_file_response": {"results": ["Warm-up content"]}},  # Warm-up
        Exception("Tool error on full read"),  # Full read call fails
        {"read_file_response": {"results": ["Fallback content"]}},  # Fallback
    ]

    content = safe_read_with_tool(MOCK_TARGET_FILE, read_full_file_if_possible=True)
    assert content == "Fallback content"

    expected_calls = [
        call(
            target_file=MOCK_TARGET_FILE,
            start_line_one_indexed=1,
            end_line_one_indexed_inclusive=WARMUP_READ_END_LINE,
            should_read_entire_file=False,
            explanation=MOCK_WARMUP_EXPLANATION,
        ),
        call(
            target_file=MOCK_TARGET_FILE,
            should_read_entire_file=True,
            start_line_one_indexed=1,
            end_line_one_indexed_inclusive=1,
            explanation=MOCK_FULL_READ_EXPLANATION,
        ),
        call(
            target_file=MOCK_TARGET_FILE,
            start_line_one_indexed=1,
            end_line_one_indexed_inclusive=FALLBACK_READ_END_LINE,
            should_read_entire_file=False,
            explanation=MOCK_FALLBACK_EXPLANATION,
        ),
    ]
    mock_read_file.assert_has_calls(expected_calls)
    assert mock_read_file.call_count == 3


@patch("dreamos.utils.file_io.default_api.read_file")
def test_safe_read_full_read_response_no_content_fallback_succeeds(mock_read_file):
    """Test full read response has no content, fallback chunk succeeds."""
    mock_read_file.side_effect = [
        {"read_file_response": {"results": ["Warm-up content"]}},  # Warm-up
        {
            "read_file_response": {"results": [None]}
        },  # Full read (no content in response)
        {"read_file_response": {"results": ["Fallback content"]}},  # Fallback
    ]

    content = safe_read_with_tool(MOCK_TARGET_FILE, read_full_file_if_possible=True)
    assert content == "Fallback content"
    assert mock_read_file.call_count == 3


@patch("dreamos.utils.file_io.default_api.read_file")
def test_safe_read_no_full_read_request_fallback_succeeds(mock_read_file):
    """Test no full read requested, fallback chunk succeeds."""
    mock_read_file.side_effect = [
        {"read_file_response": {"results": ["Warm-up content"]}},  # Warm-up
        {"read_file_response": {"results": ["Fallback content"]}},  # Fallback
    ]

    content = safe_read_with_tool(MOCK_TARGET_FILE, read_full_file_if_possible=False)
    assert content == "Fallback content"

    expected_calls = [
        call(
            target_file=MOCK_TARGET_FILE,
            start_line_one_indexed=1,
            end_line_one_indexed_inclusive=WARMUP_READ_END_LINE,
            should_read_entire_file=False,
            explanation=MOCK_WARMUP_EXPLANATION,
        ),
        call(
            target_file=MOCK_TARGET_FILE,
            start_line_one_indexed=1,
            end_line_one_indexed_inclusive=FALLBACK_READ_END_LINE,
            should_read_entire_file=False,
            explanation=MOCK_FALLBACK_EXPLANATION,
        ),
    ]
    mock_read_file.assert_has_calls(expected_calls)
    assert mock_read_file.call_count == 2


@patch("dreamos.utils.file_io.default_api.read_file")
def test_safe_read_warmup_tool_call_fails_returns_none(mock_read_file):
    """Test if warm-up tool call itself raises an exception, function returns None."""
    mock_read_file.side_effect = [Exception("Tool call critical failure on warm-up")]

    content = safe_read_with_tool(MOCK_TARGET_FILE, read_full_file_if_possible=True)
    assert content is None
    mock_read_file.assert_called_once_with(
        target_file=MOCK_TARGET_FILE,
        start_line_one_indexed=1,
        end_line_one_indexed_inclusive=WARMUP_READ_END_LINE,
        should_read_entire_file=False,
        explanation=MOCK_WARMUP_EXPLANATION,
    )


@patch("dreamos.utils.file_io.default_api.read_file")
def test_safe_read_warmup_response_no_content_full_read_succeeds(mock_read_file):
    """Test warm-up response has no content, but full read is still attempted and succeeds."""
    mock_read_file.side_effect = [
        {"read_file_response": {"results": [None]}},  # Warm-up (no content in response)
        {
            "read_file_response": {"results": ["Full file content"]}
        },  # Full read succeeds
    ]
    content = safe_read_with_tool(MOCK_TARGET_FILE, read_full_file_if_possible=True)
    assert content == "Full file content"
    assert mock_read_file.call_count == 2


@patch("dreamos.utils.file_io.default_api.read_file")
def test_safe_read_all_attempts_fail_various_reasons(mock_read_file):
    """Test all read attempts fail (tool errors, no content, or error responses)."""
    mock_read_file.side_effect = [
        {
            "read_file_response": {"results": ["Error calling tool: Warm-up issue"]}
        },  # Warm-up (tool error string in result)
        Exception("Tool error on full read call"),  # Full read call fails
        {
            "read_file_response": {"error": "Fallback error in response"}
        },  # Fallback fails (error in response dict)
    ]

    content = safe_read_with_tool(MOCK_TARGET_FILE, read_full_file_if_possible=True)
    assert content is None
    assert mock_read_file.call_count == 3


@patch("dreamos.utils.file_io.default_api.read_file")
def test_safe_read_full_read_not_requested_all_attempts_fail(mock_read_file):
    """Test full read not requested, and warm-up and fallback attempts fail."""
    mock_read_file.side_effect = [
        {"read_file_response": {"results": [None]}},  # Warm-up (no content)
        Exception("Tool error on fallback read call"),  # Fallback call fails
    ]

    content = safe_read_with_tool(MOCK_TARGET_FILE, read_full_file_if_possible=False)
    assert content is None
    assert mock_read_file.call_count == 2
