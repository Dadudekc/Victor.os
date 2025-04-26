import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import dreamscape_generator.threads.saga_worker as saga_mod
from dreamscape_generator.threads.saga_worker import SagaGenerationWorker

# Dummy classes to capture signals and monitor calls
class DummySignal:
    def __init__(self): self.calls = []
    def emit(self, *args, **kwargs): self.calls.append((args, kwargs))

class DummyMemory:
    def __init__(self): self.store = {}
    def save_fragment(self, key, data): self.store[key] = data
    def load_fragment(self, key): return self.store.get(key, {})

class DummyMonitor:
    def __init__(self):
        self.start_calls = []; self.success_calls = []; self.failure_calls = []
    def start_monitoring(self, prompt_id): self.start_calls.append(prompt_id)
    def report_success(self, prompt_id, response): self.success_calls.append((prompt_id, response))
    def report_failure(self, prompt_id, reason): self.failure_calls.append((prompt_id, reason))


def create_worker(chat_items, responses, monkeypatch):
    mem = DummyMemory()
    worker = SagaGenerationWorker(mem, chat_items, "test-model", "{{var}}")
    # Override Qt signals
    worker.saga_output_ready = DummySignal()
    worker.progress_signal = DummySignal()
    worker.error_signal = DummySignal()
    worker.finished = DummySignal()
    # Inject dummy monitor
    dummy_mon = DummyMonitor()
    worker.monitor = dummy_mon
    # Monkeypatch chat_completion sequence
    def fake_chat_completion(model, prompt):
        resp = responses.pop(0)
        if isinstance(resp, Exception): raise resp
        return resp
    monkeypatch.setattr(saga_mod, 'chat_completion', fake_chat_completion)
    return worker, dummy_mon


def test_saga_monitor_success(monkeypatch):
    worker, mon = create_worker([{'var': 'x'}], ['hello'], monkeypatch)
    worker.run()
    # Ensure monitoring and success call
    assert len(mon.start_calls) == 1
    pid = mon.start_calls[0]
    assert mon.success_calls == [(pid, 'hello')]
    assert not mon.failure_calls
    # Signals
    assert worker.saga_output_ready.calls == [(('hello',), {})]
    assert worker.progress_signal.calls == [((1,), {})]
    assert not worker.error_signal.calls
    assert worker.finished.calls == [((), {})]


def test_saga_monitor_failure(monkeypatch):
    worker, mon = create_worker([{'var': 'x'}], [ValueError('oops')], monkeypatch)
    worker.run()
    # Ensure monitoring and failure call
    assert len(mon.start_calls) == 1
    pid = mon.start_calls[0]
    assert not mon.success_calls
    assert mon.failure_calls == [(pid, 'oops')]
    # Signals: error only
    assert not worker.saga_output_ready.calls
    assert not worker.progress_signal.calls
    assert len(worker.error_signal.calls) == 1
    assert worker.finished.calls == [((), {})] 
