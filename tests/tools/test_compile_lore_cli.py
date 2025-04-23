import json
from pathlib import Path
import subprocess
import pytest
import yaml

@pytest.fixture
def translation_yaml(tmp_path):
    path = tmp_path / "dream_translation.yaml"
    data = {
        "components": {
            "AzureBlobChannel": "Sky Archive",
            "agent": "Shadow Disciple",
            "overmind": "The Architect's Will",
            "test_task": "Trial of Resonance"
        }
    }
    path.write_text(yaml.safe_dump(data), encoding='utf-8')
    return path

@pytest.fixture
def tasks_json(tmp_path):
    path = tmp_path / "task_list.json"
    tasks = [
        {
            "payload": {"module_path": "a/b", "agent_id": "AgentX", "description": "desc"},
            "task_type": "test_task",
            "result": "success",
            "timestamp_created": "2025-01-01T00:00:00Z"
        }
    ]
    path.write_text(json.dumps(tasks), encoding='utf-8')
    return path

@pytest.mark.parametrize("verbose", [False, True])
def test_compile_lore_cli(tmp_path, translation_yaml, tasks_json, verbose):
    # Setup output file
    output = tmp_path / "out_lore.md"
    # Build command
    cmd = [
        "python",
        str(Path("_agent_coordination/tools/compile_lore.py").resolve()),
        "--translation", str(translation_yaml),
        "--tasks", str(tasks_json),
        "--output", str(output)
    ]
    if verbose:
        cmd.append("--verbose")
    # Run CLI
    result = subprocess.run(cmd, cwd=Path().resolve(), capture_output=True, text=True)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    # Validate output
    assert output.exists(), "Output lore markdown was not created"
    content = output.read_text(encoding='utf-8')
    # Check translation mappings
    assert "Sky Archive" in content
    assert "Shadow Disciple" in content
    assert "Trial of Resonance" in content
    # Check directive description
    assert "desc" in content