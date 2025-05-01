import json
from pathlib import Path

import pytest

from dreamos.tools.discovery.find_todos import find_todos_in_file

# Remove the skipped stub function
# @pytest.mark.skip(reason='Test stub for coverage tracking')
# def test_stub_for_find_todos():
#     pass


def test_find_todos_in_file_basic(tmp_path: Path):
    """Test finding simple TODO and FIXME comments."""
    base_dir = tmp_path
    file_path = base_dir / "test_file.py"
    file_content = (
        "# Regular comment\n"
        "# TODO: Implement this feature\n"
        "print('hello')\n"
        "# FIXME: Fix this bug asap\n"
        "# BUG: Another issue\n"
    )
    file_path.write_text(file_content, encoding="utf-8")

    patterns = ["TODO", "FIXME", "BUG"]
    findings = find_todos_in_file(file_path, patterns, base_dir)

    assert len(findings) == 3

    # Check TODO finding
    assert findings[0]["data"]["pattern"] == "TODO"
    assert findings[0]["data"]["file"] == "test_file.py"
    assert findings[0]["data"]["line"] == 2
    assert findings[0]["data"]["comment"] == "Implement this feature"
    assert findings[0]["level"] == "INFO"

    # Check FIXME finding
    assert findings[1]["data"]["pattern"] == "FIXME"
    assert findings[1]["data"]["file"] == "test_file.py"
    assert findings[1]["data"]["line"] == 4
    assert findings[1]["data"]["comment"] == "Fix this bug asap"
    assert findings[1]["level"] == "WARNING"

    # Check BUG finding
    assert findings[2]["data"]["pattern"] == "BUG"
    assert findings[2]["data"]["file"] == "test_file.py"
    assert findings[2]["data"]["line"] == 5
    assert findings[2]["data"]["comment"] == "Another issue"
    assert findings[2]["level"] == "ERROR"


def test_find_todos_in_file_no_matches(tmp_path: Path):
    """Test file with no matching patterns."""
    base_dir = tmp_path
    file_path = base_dir / "no_match.txt"
    file_content = "# Just a comment\nAnother line\n"
    file_path.write_text(file_content, encoding="utf-8")

    patterns = ["TODO", "FIXME"]
    findings = find_todos_in_file(file_path, patterns, base_dir)
    assert len(findings) == 0


def test_find_todos_in_file_empty_file(tmp_path: Path):
    """Test scanning an empty file."""
    base_dir = tmp_path
    file_path = base_dir / "empty.py"
    file_path.touch()

    patterns = ["TODO", "FIXME"]
    findings = find_todos_in_file(file_path, patterns, base_dir)
    assert len(findings) == 0


# TODO: Add tests for scan_directory which requires more setup (mocking os.walk or creating directory structure)


# Test scan_directory
def test_scan_directory(tmp_path: Path):
    """Test scanning a directory structure."""
    # Setup directory structure
    base_dir = tmp_path
    sub_dir = base_dir / "subdir"
    ignored_dir = base_dir / ".ignored"
    sub_dir.mkdir()
    ignored_dir.mkdir()

    # Create test files
    file1 = base_dir / "file1.py"
    file1.write_text("# TODO: Top level todo\n", encoding="utf-8")

    file2 = sub_dir / "file2.js"
    file2.write_text("// FIXME: Subdir fixme\n", encoding="utf-8")

    file3_ignored = sub_dir / "file3.txt"  # Ignored extension
    file3_ignored.write_text("# TODO: Should be ignored (ext)\n", encoding="utf-8")

    file4_ignored_dir = ignored_dir / "file4.py"
    file4_ignored_dir.write_text("# TODO: Should be ignored (dir)\n", encoding="utf-8")

    log_file = base_dir / "findings.jsonl"
    patterns = ["TODO", "FIXME"]
    # Use default ignore list + our specific ignored dir name
    ignore_list = [".ignored"]
    extensions = [".py", ".js"]  # Scan only these

    # Call the function (assuming it's imported)
    from dreamos.tools.discovery.find_todos import scan_directory

    scan_directory(base_dir, patterns, log_file, ignore_list, extensions)

    # Verify log file content
    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2  # Should find 2 items

    findings_data = [json.loads(line) for line in lines]

    # Check findings (order might vary based on os.walk)
    found_todo = False
    found_fixme = False
    for finding in findings_data:
        assert finding["type"] == "discovery"
        if finding["data"]["pattern"] == "TODO":
            assert finding["data"]["file"] == "file1.py"
            assert finding["data"]["comment"] == "Top level todo"
            found_todo = True
        elif finding["data"]["pattern"] == "FIXME":
            assert finding["data"]["file"] == "subdir/file2.js"
            assert finding["data"]["comment"] == "Subdir fixme"
            found_fixme = True

    assert found_todo
    assert found_fixme
