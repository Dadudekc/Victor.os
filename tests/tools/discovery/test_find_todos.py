import json
from pathlib import Path
from typing import Dict
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


# TODO: Add tests for scan_directory which requires more setup (mocking os.walk or creating directory structure)  # noqa: E501


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

@pytest.mark.parametrize(
    "file_contents, ignore_list, extensions, expected_count",
    [
        # Basic case: Find one TODO
        ({"file1.py": "# TODO: Test this"}, [], [".py"], 1),
        # No patterns found
        ({"file1.py": "# Just a comment"}, [], [".py"], 0),
        # File ignored by extension
        ({"file1.txt": "# TODO: Ignore me"}, [], [".py"], 0),
        # Directory ignored
        ({"ignore_dir/file1.py": "# TODO: Ignore me"}, ["ignore_dir"], [".py"], 0),
        # File ignored by name
        ({"ignore_me.py": "# TODO: Ignore me"}, ["ignore_me.py"], [".py"], 0),
        # Multiple files, mixed results
        ({"file1.py": "# TODO: Find me", "file2.py": "# Just code", "sub/file3.py": "# FIXME: Find me too"}, [], [".py"], 2),
        # Default ignore patterns (.venv)
        ({".venv/lib/file.py": "# TODO: Should be ignored"}, [], [".py"], 0),
        # Case-insensitive pattern matching
        ({"file1.py": "# todo: lowercase"}, ["TODO"], [".py"], 1),
        # Custom patterns
        ({"file1.py": "# HACK: Nasty workaround"}, ["HACK"], [".py"], 1),
    ]
)
def test_scan_directory(
    tmp_path: Path,
    file_contents: Dict[str, str],
    ignore_list: list[str],
    extensions: list[str],
    expected_count: int,
    patterns = ["TODO", "FIXME", "BUG", "HACK"] # Use combined patterns for testing
):
    """Tests scan_directory with various file structures and ignore rules."""
    # Create directory structure
    for rel_path, content in file_contents.items():
        full_path = tmp_path / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")

    # Create a dummy log file path within tmp_path
    log_file = tmp_path / "test_feedback.jsonl"

    # Run the scan
    scan_directory(tmp_path, patterns, log_file, ignore_list, extensions)

    # Check the log file content
    found_count = 0
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    # Basic check that it looks like our finding structure
                    assert "type" in entry
                    assert "data" in entry
                    assert "pattern" in entry["data"]
                    found_count += 1
                except json.JSONDecodeError:
                    pytest.fail(f"Log file contains invalid JSON: {line.strip()}")
                except AssertionError as e:
                    pytest.fail(f"Log entry format unexpected: {e} - Entry: {line.strip()}")

    assert found_count == expected_count


if __name__ == "__main__":
    pytest.main()
