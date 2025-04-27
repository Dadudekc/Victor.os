import os
import json
import shutil
import tempfile
from collections import Counter

import pytest
from dream_mode.task_nexus.task_nexus import TaskNexus

@pytest.fixture
def temp_task_file():
    tmp_dir = tempfile.mkdtemp()
    task_file = os.path.join(tmp_dir, "task_list.json")
    yield task_file
    shutil.rmtree(tmp_dir)

def test_add_and_load_task(temp_task_file):
    nexus = TaskNexus(task_file=temp_task_file)
    task = {"id": "task-001", "type": "lore", "payload": {}, "status": "pending"}
    nexus.add_task(task)

    # Re-load to simulate restart
    nexus2 = TaskNexus(task_file=temp_task_file)
    assert len(nexus2.tasks) == 1
    assert nexus2.tasks[0]["id"] == "task-001"

def test_get_next_task_marks_claimed(temp_task_file):
    nexus = TaskNexus(task_file=temp_task_file)
    nexus.add_task({"id": "task-002", "type": "test", "payload": {}})
    task = nexus.get_next_task(agent_id="agent-X")

    assert task is not None
    assert task["status"] == "claimed"
    assert task["claimed_by"] == "agent-X"

def test_get_next_task_filters_by_type(temp_task_file):
    nexus = TaskNexus(task_file=temp_task_file)
    nexus.add_task({"id": "task-003", "type": "compile", "payload": {}})
    nexus.add_task({"id": "task-004", "type": "test", "payload": {}})
    task = nexus.get_next_task(type_filter="compile")

    assert task["id"] == "task-003"
    assert task["type"] == "compile"

def test_update_task_status(temp_task_file):
    nexus = TaskNexus(task_file=temp_task_file)
    nexus.add_task({"id": "task-005", "type": "dispatch", "payload": {}})
    updated = nexus.update_task_status("task-005", "completed")

    assert updated is True
    task = [t for t in nexus.tasks if t["id"] == "task-005"][0]
    assert task["status"] == "completed"

def test_stats_summary(temp_task_file):
    nexus = TaskNexus(task_file=temp_task_file)
    nexus.add_task({"id": "task-006", "type": "a", "payload": {}, "status": "pending"})
    nexus.add_task({"id": "task-007", "type": "b", "payload": {}, "status": "pending"})
    nexus.add_task({"id": "task-008", "type": "c", "payload": {}, "status": "claimed"})
    summary = nexus.stats()

    assert isinstance(summary, Counter)
    assert summary["pending"] == 2
    assert summary["claimed"] == 1 
