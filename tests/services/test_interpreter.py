# tests/services/test_interpreter.py
import pytest
pytestmark = pytest.mark.xfail(reason="Legacy import error", strict=False)

from _agent_coordination.services.interpreter import DefaultResponseInterpreter
from _agent_coordination.core.config import CursorCoordinatorConfig

@ pytest.fixture
def interpreter():
    config = CursorCoordinatorConfig()
    return DefaultResponseInterpreter(config)


def test_parse_python_code_block(interpreter):
    text = "Here is the code:\n```python\nprint('Hello')\n```\nEnd."
    action = interpreter.parse(text)
    assert action is not None
    assert action["action"] == "save_file"
    assert action["params"]["content"] == "print('Hello')"
    assert action["params"]["type"] == "python"


def test_parse_diff_code_block(interpreter):
    text = "Here is diff:\n```diff\n- old_line\n+ new_line\n```"
    action = interpreter.parse(text)
    assert action is not None
    assert action["action"] == "save_file"
    assert action["params"]["type"] == "diff"
    assert "- old_line" in action["params"]["content"]


def test_parse_generic_code_block(interpreter):
    text = "```bash\nls -la\n```"
    action = interpreter.parse(text)
    assert action is not None
    assert action["action"] == "save_file"
    assert action["params"]["type"] == "generic"
    assert action["params"]["content"] == "ls -la"


def test_parse_accept_prompt(interpreter):
    text = "Looks good. Click Accept to apply."
    action = interpreter.parse(text)
    assert action is not None
    assert action["action"] == "execute_cursor_goal"
    assert action["goal"]["type"] == "apply_changes"


def test_parse_task_complete(interpreter):
    text = "Task complete. Files updated."
    action = interpreter.parse(text)
    assert action is not None
    assert action["action"] == "task_complete"


def test_parse_no_action(interpreter):
    text = "I understand the request."
    action = interpreter.parse(text)
    assert action is None


def test_parse_error_detected(interpreter):
    text = "An error occurred while saving."
    action = interpreter.parse(text)
    assert action is not None
    assert action["action"] == "error_detected"
    assert "message" in action["params"]


def test_parse_clarification(interpreter):
    text = "Which file should I save this to?"
    action = interpreter.parse(text)
    assert action is not None
    assert action["action"] == "clarification_needed"
    assert "message" in action["params"] 
