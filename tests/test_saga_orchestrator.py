import os
import sys
# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from queue import Queue

# Import orchestrator module to monkeypatch
import social.digital_dreamscape.saga_orchestrator as so

# Dummy classes
class DummyReflectionAgent:
    def __init__(self, agent_id):
        assert agent_id == "saga_reflector"
    def run(self, context):
        return {"emotion": "dummy", "reason": "just testing"}

class DummySagaWorker:
    def __init__(self, log_q, memory_manager, chat_items, prompt_template_str, selected_model, current_emotion):
        self.log_q = log_q
        log_q.put(f"DummySagaWorker init with emotion {current_emotion}")
    saga_output_ready = None
    finished = None
    progress_signal = None
    error_signal = None
    def start(self):
        self.log_q.put("DummySagaWorker started")

@pytest.fixture(autouse=True)
def patch_dependencies():
    # Monkeypatch ReflectionAgent and SagaGenerationWorker
    so.ReflectionAgent = DummyReflectionAgent
    so.SagaGenerationWorker = DummySagaWorker
    yield


def test_orchestrator_run():
    from social.digital_dreamscape.saga_orchestrator import OrchestratedSagaRunner
    log_q = Queue()
    class FakeMemoryManager:
        def get(self, key, default=None): return default
        def set(self, key, value): pass
    # Fake chat items with minimal interface
    ChatItem = type('CI', (), {'data': lambda self, role: {}, 'text': lambda self: 'Title'})
    chat_items = [ChatItem()]

    orchestrator = OrchestratedSagaRunner(
        log_q=log_q,
        memory_manager=FakeMemoryManager(),
        chat_items=chat_items,
        prompt_template_str="template",
        saga_worker_signals={},
        selected_model="modelX"
    )
    orchestrator.run()

    # Collect all log messages
    logs = []
    while not log_q.empty():
        logs.append(log_q.get())

    # Assertions to ensure key steps occurred
    assert any("Starting orchestrated saga run" in msg for msg in logs)
    assert any("Detected emotion: dummy" in msg for msg in logs)
    assert any("DummySagaWorker init with emotion dummy" in msg for msg in logs)
    assert any("DummySagaWorker started" in msg for msg in logs) 
