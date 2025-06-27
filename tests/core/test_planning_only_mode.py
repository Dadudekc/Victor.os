"""Ensure the bootstrap runner checks PLANNING_ONLY_MODE."""

import ast
from pathlib import Path


def test_planning_only_mode_check_present():
    source = Path("src/dreamos/tools/agent_bootstrap_runner.py").read_text()
    tree = ast.parse(source)

    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if getattr(getattr(node.func, "attr", None), "lower", lambda: None)() == "getenv":
                if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "PLANNING_ONLY_MODE":
                    found = True
                    break
    assert found, "PLANNING_ONLY_MODE check missing"
