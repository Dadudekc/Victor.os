import pytest
import pandas as pd
from pathlib import Path
from ui.task_visualizer_app import read_tasks_from_json, load_task_data
import json

@pytest.fixture
def temp_empty_file(tmp_path):
    path = tmp_path / "task_list.json"
    path.write_text("", encoding='utf-8')
    return path

@pytest.fixture
def temp_invalid_json(tmp_path):
    path = tmp_path / "task_list.json"
    path.write_text("not a json", encoding='utf-8')
    return path

@pytest.fixture
def temp_valid_tasks(tmp_path):
    path = tmp_path / "task_list.json"
    data = [
        {"task_id": "t1", "status": "PENDING", "task_type": "typeA", "action": "act", "target_agent": "A", "timestamp_created": "2023-01-01T00:00:00Z", "timestamp_updated": "2023-01-01T00:00:00Z", "result_summary": "sum", "error_message": None}
    ]
    path.write_text(json.dumps(data), encoding='utf-8')
    return path


def test_read_tasks_empty(temp_empty_file):
    tasks = read_tasks_from_json(temp_empty_file)
    assert tasks == []


def test_read_tasks_invalid(temp_invalid_json, monkeypatch):
    # Monkeypatch logger and streamlit st.error
    import ui.task_visualizer_app as app_mod
    class DummySt:
        def error(self, msg): pass
    monkeypatch.setattr('ui.task_visualizer_app.st', DummySt())
    tasks = read_tasks_from_json(temp_invalid_json)
    assert tasks == []


def test_read_tasks_valid(temp_valid_tasks):
    tasks = read_tasks_from_json(temp_valid_tasks)
    assert isinstance(tasks, list)
    assert tasks[0]['task_id'] == 't1'


def test_load_task_data_empty(tmp_path):
    df = load_task_data(tmp_path / 'noexist.json')
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_load_task_data_valid(temp_valid_tasks):
    df = load_task_data(temp_valid_tasks)
    assert isinstance(df, pd.DataFrame)
    assert 'task_id' in df.columns
    assert df.loc[0, 'task_id'] == 't1' 
