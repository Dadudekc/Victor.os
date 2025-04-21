import json
import os
import importlib
import pytest

# Dynamically import the mailbox_monitor_agent module
mb_mod = importlib.import_module('_agent_coordination.monitors.mailbox_monitor_agent')
MailboxMonitorAgent = mb_mod.MailboxMonitorAgent
acquire_lock = mb_mod.acquire_lock
release_lock = mb_mod.release_lock

@pytest.fixture(autouse=True)
def no_lock(monkeypatch, tmp_path):
    """Stub out file locking to simplify tests"""
    def fake_acquire(file_path, lock_flags=None):
        # ensure file exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        return open(file_path, 'a+')
    def fake_release(handle):
        try:
            handle.close()
        except:
            pass
    monkeypatch.setattr(mb_mod, 'acquire_lock', fake_acquire)
    monkeypatch.setattr(mb_mod, 'release_lock', fake_release)

    # Redirect mailbox and task list paths
    monkeypatch.setattr(mb_mod, 'MAILBOX_DIR', tmp_path / 'shared_mailboxes')
    monkeypatch.setattr(mb_mod, 'TASK_LIST_FILE', tmp_path / 'runtime' / 'task_list.json')
    # Create initial runtime task list
    task_list_file = mb_mod.TASK_LIST_FILE
    task_list_file.parent.mkdir(parents=True, exist_ok=True)
    with open(task_list_file, 'w', encoding='utf-8') as f:
        json.dump([], f)
    # Ensure mailbox dir exists
    mb_mod.MAILBOX_DIR.mkdir(parents=True, exist_ok=True)
    yield

def test_process_unread_messages_creates_task(tmp_path):
    # Arrange: create a test mailbox message file
    mb_file = mb_mod.MAILBOX_DIR / 'agent1_mailbox.json'
    message = {
        'message_id': 'msg001',
        'timestamp': '2025-01-01T00:00:00Z',
        'sender': 'tester',
        'target_agent': 'agent1',
        'message_type': 'directive',
        'payload': {'task_type': 'test_task', 'params': {'value': 42}},
        'status': 'unread'
    }
    with open(mb_file, 'w', encoding='utf-8') as f:
        json.dump([message], f)

    # Act: process mailbox messages
    agent = MailboxMonitorAgent()
    agent._process_unread_messages()

    # Assert: task_list.json contains the new task
    task_list = json.loads(open(mb_mod.TASK_LIST_FILE, 'r', encoding='utf-8').read())
    assert len(task_list) == 1
    task = task_list[0]
    assert task['task_type'] == 'test_task'
    assert task['params']['value'] == 42
    assert task['source'] == 'supervisor_mailbox'

    # Assert: mailbox message status updated to processed
    updated_mailbox = json.loads(open(mb_file, 'r', encoding='utf-8').read())
    assert updated_mailbox[0]['status'] == 'processed' 