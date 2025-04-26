import json
import threading
import pytest
from pathlib import Path

from _agent_coordination.utils.mailbox_utils import dispatch_message_to_agent
from _agent_coordination.dispatchers.task_dispatcher import TaskDispatcher
from _agent_coordination.dispatchers.config import TaskDispatcherConfig
from _agent_coordination.dispatchers.mailbox_service import MailboxService
from _agent_coordination.utils.task_utils import read_tasks

def test_dispatch_message_to_agent_creates_file_and_valid_json(tmp_path):
    mailbox_root = tmp_path / "mailboxes"
    agent = "agent1"
    payload = {"key": "value"}
    success = dispatch_message_to_agent(mailbox_root, agent, payload)
    assert success
    inbox_dir = mailbox_root / agent / "inbox"
    files = list(inbox_dir.glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding='utf-8'))
    assert data["key"] == "value"
    assert "message_id" in data
    assert "timestamp_dispatched" in data

def test_task_dispatcher_delegates_to_mailbox_util(tmp_path):
    task_list_file = tmp_path / "tasks.json"
    task_list_file.write_text("[]", encoding="utf-8")
    mailbox_root = tmp_path / "mailboxes"
    config = TaskDispatcherConfig(task_list_path=str(task_list_file))
    mailbox_service = MailboxService(mailbox_root)
    dispatcher = TaskDispatcher(config, mailbox_service)
    success = dispatcher._dispatch_message_to_agent("agent2", {"foo": "bar"})
    assert success is True
    inbox_dir = mailbox_root / "agent2" / "inbox"
    files = list(inbox_dir.glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding='utf-8'))
    assert data["foo"] == "bar"
    assert data["sender_agent"] == "TaskDispatcher"

def test_concurrent_dispatch_message(tmp_path):
    mailbox_root = tmp_path / "mailboxes"
    agent = "concurrent_agent"
    payload = {"p": "v"}
    def worker():
        assert dispatch_message_to_agent(mailbox_root, agent, payload)
    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    inbox_dir = mailbox_root / agent / "inbox"
    files = list(inbox_dir.glob("*.json"))
    assert len(files) == 5

def test_handle_task_dispatch_and_status_update(tmp_path):
    # Prepare task list with a pending task
    task_list_file = tmp_path / "tasks.json"
    initial_tasks = [
        {
            "task_id": "task1",
            "status": "PENDING",
            "target_agent": "agent1",
            "task_type": "typeA",
            "params": {"foo": "bar"},
            "action": "do_something"
        }
    ]
    task_list_file.write_text(json.dumps(initial_tasks), encoding="utf-8")
    mailbox_root = tmp_path / "mailboxes"
    # Instantiate dispatcher with DI
    config = TaskDispatcherConfig(task_list_path=task_list_file)
    mailbox_service = MailboxService(mailbox_root)
    dispatcher = TaskDispatcher(config, mailbox_service)

    # Handle the single task
    tasks = read_tasks(task_list_file)
    result, error = dispatcher.handle_task(tasks[0])

    # Ensure the dispatch succeeded
    assert result is True
    assert error is None

    # Check mailbox file created
    inbox_dir = mailbox_root / "agent1" / config.inbox_subdir
    files = list(inbox_dir.glob(f"*{config.message_format}"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["event_type"] == "TASK"
    assert data["task_id"] == "task1"

    # Verify task status updated to COMPLETED
    updated_tasks = read_tasks(task_list_file)
    assert updated_tasks[0]["status"] == "COMPLETED"

def test_process_pending_tasks_workflow(tmp_path):
    # Prepare two pending tasks
    task_list_file = tmp_path / "tasks.json"
    initial_tasks = [
        {"task_id": "t1", "status": "PENDING", "target_agent": "agentA", "task_type": "A", "params": {}, "action": "a"},
        {"task_id": "t2", "status": "PENDING", "target_agent": "agentB", "task_type": "B", "params": {}, "action": "b"},
    ]
    task_list_file.write_text(json.dumps(initial_tasks), encoding="utf-8")
    mailbox_root = tmp_path / "mailboxes"
    config = TaskDispatcherConfig(task_list_path=task_list_file)
    mailbox_service = MailboxService(mailbox_root)
    dispatcher = TaskDispatcher(config, mailbox_service)

    # Process all pending tasks
    dispatcher.process_pending_tasks()

    # Check both mailboxes have messages
    for agent in ["agentA", "agentB"]:
        inbox_dir = mailbox_root / agent / config.inbox_subdir
        files = list(inbox_dir.glob(f"*{config.message_format}"))
        assert len(files) == 1

    # Verify statuses updated
    updated = read_tasks(task_list_file)
    statuses = {t["task_id"]: t["status"] for t in updated}
    assert statuses["t1"] == "COMPLETED"
    assert statuses["t2"] == "COMPLETED" 