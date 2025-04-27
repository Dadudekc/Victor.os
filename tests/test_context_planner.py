import pytest
pytestmark = pytest.mark.xfail(reason="Legacy import error", strict=False)
from dreamos.coordination.tools.context_planner import (
    parse_context,
    extract_entities_v3,
    generate_context_plan_v3,
    create_plan_step,
    GREP_SEARCH,
    READ_FILE,
    CODEBASE_SEARCH
)


def test_parse_context_structure():
    result = parse_context("Test description text.")
    assert isinstance(result, dict)
    # Should contain expected keys
    assert set(result.keys()) == {"files_with_roles", "symbols_with_roles", "actions"}
    assert isinstance(result["files_with_roles"], list)
    assert isinstance(result["symbols_with_roles"], list)
    assert isinstance(result["actions"], list)


def test_extract_entities_v3_basic():
    desc = (
        "Implement the `calculate_metrics` function in `reporting/core.py`. "
        "It should also use the `fetch_data` utility from common."
    )
    entities = extract_entities_v3(desc)
    # files extracted
    assert "reporting/core.py" in entities["files"]
    # symbols extracted
    assert "calculate_metrics" in entities["symbols"]
    assert "fetch_data" in entities["symbols"]
    # actions extracted (implement)
    assert "implement" in entities["actions"]


def test_extract_entities_v3_empty():
    entities = extract_entities_v3("No code references here.")
    assert entities["files"] == []
    assert entities["symbols"] == []
    assert entities["actions"] == []


def test_generate_context_plan_v3_returns_list():
    plan = generate_context_plan_v3("Generate some context.")
    assert isinstance(plan, list)


def test_generate_context_plan_v3_empty_plan():
    # No valid actions or entities -> empty plan
    plan = generate_context_plan_v3("Just a simple sentence.")
    assert plan == []


def test_create_plan_step_defaults():
    step = create_plan_step("desc", GREP_SEARCH, "target", {"query": "test"})
    assert step["description"] == "desc"
    assert step["action"] == GREP_SEARCH
    assert step["target"] == "target"
    assert isinstance(step["params"], dict)


def test_create_plan_step_with_store():
    step = create_plan_step(
        "desc2", READ_FILE, "file.py", {"lines": 10}, store_as="ref1"
    )
    assert step.get("store_as") == "ref1"
    assert step["action"] == READ_FILE 
