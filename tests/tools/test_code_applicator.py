import os
import shutil
import sys
import tempfile
import pytest
from tools.code_applicator import apply_code

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

@pytest.fixture
def temp_file(tmp_path):
    return tmp_path / "test.txt"

@pytest.fixture
def backup_file(tmp_path):
    return tmp_path / "test.txt.bak"

def test_overwrite_mode(tmp_path):
    target = tmp_path / "out.txt"
    # Write initial content
    write_file(str(target), "old content")
    # Overwrite mode
    apply_code(str(target), code_input="new content", code_file=None, code_stdin=False,
               mode='overwrite', create_dirs=False, backup=False,
               start_marker=None, end_marker=None, verbose=False)
    with open(target, 'r', encoding='utf-8') as f:
        assert f.read() == "new content"

def test_append_mode(tmp_path):
    target = tmp_path / "append.txt"
    write_file(str(target), "line1\n")
    apply_code(str(target), code_input="line2", code_file=None, code_stdin=False,
               mode='append', create_dirs=False, backup=False,
               start_marker=None, end_marker=None, verbose=False)
    with open(target, 'r', encoding='utf-8') as f:
        assert f.read() == "line1\nline2"

def test_replace_markers_mode(tmp_path):
    target = tmp_path / "markers.txt"
    content = "begin\n# START_MARKER\nold\n# END_MARKER\nend\n"
    write_file(str(target), content)
    apply_code(str(target), code_input="new", code_file=None, code_stdin=False,
               mode='replace_markers', create_dirs=False, backup=False,
               start_marker="# START_MARKER", end_marker="# END_MARKER", verbose=False)
    result = target.read_text(encoding='utf-8')
    assert "new" in result
    assert "old" not in result

def test_backup_creation(tmp_path):
    target = tmp_path / "bak.txt"
    write_file(str(target), "original")
    apply_code(str(target), code_input="updated", code_file=None, code_stdin=False,
               mode='overwrite', create_dirs=False, backup=True,
               start_marker=None, end_marker=None, verbose=False)
    bak = target.with_suffix(target.suffix + '.bak')
    assert bak.exists()
    assert bak.read_text(encoding='utf-8') == "original" 