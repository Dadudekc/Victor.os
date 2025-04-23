import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import pytest
from episode_generator import SagaGenerationWorker

class DummyMem:
    def __init__(self):
        self.store = {}
    def get(self, key, default=None):
        return self.store.get(key, default)
    def set(self, key, data, segment=None):
        self.store[key] = data

@pytest.fixture
def saga_worker():
    mem = DummyMem()
    # minimal worker for testing non-thread methods
    worker = SagaGenerationWorker(
        log_q=lambda m: None,
        memory_manager=mem,
        chat_items=[],
        selected_model="test-model",
        prompt_template_str=""
    )
    return worker


def test_format_raw_excerpt_dict(saga_worker):
    excerpt = saga_worker.format_raw_excerpt({'id': 'abc123'}, 'Chat Title')
    assert '--- START RAW EXCERPT ---' in excerpt
    assert 'Chat Title: Chat Title' in excerpt
    assert 'Chat ID: abc123' in excerpt
    assert '--- END RAW EXCERPT ---' in excerpt


def test_parse_result_no_json(saga_worker):
    narrative, mem_update = saga_worker.parse_result('Just plain text narrative')
    assert narrative == 'Just plain text narrative'
    assert mem_update == {}


def test_parse_result_with_json(saga_worker):
    data = {'foo': 'bar', 'num': 42}
    raw = 'Narrative text```json' + json.dumps(data) + '```'
    narrative, mem_update = saga_worker.parse_result(raw)
    assert narrative == 'Narrative text'
    assert mem_update == data


def test_parse_result_invalid_json(saga_worker):
    raw = 'Narrative```json not really json ```'
    narrative, mem_update = saga_worker.parse_result(raw)
    # Should still return narrative (before json block) and empty dict or default
    assert narrative.strip().startswith('Narrative')
    assert isinstance(mem_update, dict) 