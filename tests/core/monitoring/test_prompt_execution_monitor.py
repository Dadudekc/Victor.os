import pytest
from datetime import datetime, timedelta

import dreamos.monitoring.prompt_execution_monitor as pem_mod
from dreamos.monitoring.prompt_execution_monitor import PromptExecutionMonitor

def make_monitor(timeout_sec=0):
    class DummyMemory:
        def __init__(self):
            self.store = {}
        def save_fragment(self, prompt_id, data):
            self.store[prompt_id] = data
        def load_fragment(self, prompt_id):
            return self.store.get(prompt_id, {})

    class DummyDispatcher:
        def __init__(self):
            self.queued = []
        def queue_prompt(self, prompt_data, retry=False):
            self.queued.append((prompt_data, retry))

    class DummyArchive:
        def __init__(self):
            self.entries = []
        def get_by_prompt_id(self, prompt_id):
            # filter entries by prompt_id
            return [e for e in self.entries if e[0] == prompt_id]
        def log_failure(self, prompt_id, prompt_data, reason, retry_count):
            self.entries.append((prompt_id, prompt_data, reason, retry_count))

    mem = DummyMemory()
    disp = DummyDispatcher()
    arch = DummyArchive()
    monitor = PromptExecutionMonitor(memory=mem,
                                      dispatcher=disp,
                                      timeout_sec=timeout_sec,
                                      archive_service=arch)
    return monitor, mem, disp, arch


def test_success_removes_from_tracking():
    monitor, mem, disp, arch = make_monitor()
    pid = "prompt-success"
    monitor.start_monitoring(pid)
    assert pid in monitor.active_prompts

    monitor.report_success(pid, response="ok response")
    # After success, prompt should no longer be tracked
    assert pid not in monitor.active_prompts


def test_duplicate_failure_not_archived_twice():
    monitor, mem, disp, arch = make_monitor()
    pid = "prompt-dup"
    monitor.start_monitoring(pid)
    # Pre-seed archive with an entry for this prompt
    arch.entries.append((pid, {}, "error", 0))

    # First failure report should detect existing and skip archiving
    monitor.report_failure(pid, reason="error")
    assert len([e for e in arch.entries if e[0] == pid]) == 1


def test_recovery_requeues_prompt():
    monitor, mem, disp, arch = make_monitor()
    pid = "prompt-recover"
    # Preload memory so load_fragment returns non-empty dict
    mem.store[pid] = {"foo": "bar", "retry_count": 2}
    monitor.start_monitoring(pid)

    monitor.report_failure(pid, reason="fail")
    # Dispatcher should have queued the prompt data for retry
    assert disp.queued == [(mem.store[pid], True)]


def test_monitor_timeout_triggers_failure(monkeypatch):
    # Set timeout to zero so any age > 0 triggers expiry
    monitor, mem, disp, arch = make_monitor(timeout_sec=0)
    pid = "prompt-timeout"
    monitor.start_monitoring(pid)
    # Backdate start time so it's expired
    monitor.active_prompts[pid] = datetime.utcnow() - timedelta(seconds=1)

    # Replace sleep to fast-forward and then stop the loop with exception
    call_count = {"n": 0}
    class Done(Exception):
        pass
    def fake_sleep(sec):
        call_count["n"] += 1
        if call_count["n"] > 1:
            raise Done()
    monkeypatch.setattr(pem_mod.time, 'sleep', fake_sleep)

    # Run one iteration of monitor loop; it should archive timeout and then exit
    with pytest.raises(Done):
        monitor._monitor_loop()

    # Check that timeout failure was archived
    assert len(arch.entries) == 1
    archived = arch.entries[0]
    assert archived[0] == pid
    assert archived[2] == "timeout"
    # Also verify dispatcher requeued after timeout
    assert disp.queued == [(mem.load_fragment(pid), True)] 
