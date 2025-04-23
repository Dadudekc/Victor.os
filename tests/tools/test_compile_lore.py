import json
import subprocess
from pathlib import Path
import pytest

def create_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

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
    import yaml
    path.write_text(yaml.safe_dump(data), encoding='utf-8')
    return path

@pytest.fixture
def tasks_json(tmp_path):
    path = tmp_path / "tasks.json"
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

def test_compile_lore_cli(tmp_path, translation_yaml, tasks_json):
    output = tmp_path / "out.md"
    script = Path("_agent_coordination/tools/compile_lore.py").resolve()
    cmd = ["python", str(script), "--once", "--translation", str(translation_yaml), "--tasks", str(tasks_json), "--output", str(output)]
    result = subprocess.run(cmd, cwd=Path().resolve(), capture_output=True, text=True)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert output.exists(), "Output file was not created"
    content = output.read_text(encoding='utf-8')
    assert "Sky Archive" in content
    assert "Shadow Disciple" in content
    assert "Trial of Resonance" in content 