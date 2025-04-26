import pytest
import os
import json
from types import SimpleNamespace
import importlib.util

# Dynamically load FeedbackEngineV2 without importing core.chat_engine package
_abs_path = os.path.abspath(os.path.join(os.getcwd(), 'core', 'chat_engine', 'feedback_engine_v2.py'))
_spec = importlib.util.spec_from_file_location('feedback_engine_v2', _abs_path)
_feedback_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_feedback_mod)
FeedbackEngineV2 = _feedback_mod.FeedbackEngineV2

import openai

# Dummy archive service for testing
class DummyArchiveService:
    def __init__(self, entries):
        self._entries = entries
    def get_failures(self, filter_by_reason=None, max_retry=None):
        results = list(self._entries)
        if filter_by_reason is not None:
            results = [e for e in results if e.get('reason') == filter_by_reason]
        if max_retry is not None:
            results = [e for e in results if e.get('retry_count', 0) <= max_retry]
        return results

# Dummy OpenAI response wrapper
class DummyResponse:
    def __init__(self, content):
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]

@pytest.fixture(autouse=True)
def clear_openai_api_key(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    yield

@pytest.mark.parametrize('entries, mock_content, expected_analysis', [
    (
        [{'prompt_id':'p1','reason':'r1','retry_count':0,'prompt':{'x':1}}],
        'Analysis for p1',
        'Analysis for p1'
    ),
])
def test_analyze_failures_success(monkeypatch, entries, mock_content, expected_analysis):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    archive = DummyArchiveService(entries)
    engine = FeedbackEngineV2(archive_service=archive, model='test-model')
    dummy_resp = DummyResponse(mock_content)
    monkeypatch.setattr(openai.ChatCompletion, 'create', lambda **kwargs: dummy_resp)
    results = engine.analyze_failures()
    assert isinstance(results, list)
    assert len(results) == 1
    res = results[0]
    assert res['prompt_id'] == 'p1'
    assert res['analysis'] == expected_analysis
    assert res['raw_response'] is dummy_resp
    assert 'error' not in res


def test_analyze_failures_handles_exception(monkeypatch):
    entries = [{'prompt_id':'p2','reason':'fail','retry_count':1,'prompt':{}}]
    archive = DummyArchiveService(entries)
    engine = FeedbackEngineV2(archive_service=archive)
    def fake_create(**kwargs):
        raise RuntimeError('API error')
    monkeypatch.setattr(openai.ChatCompletion, 'create', fake_create)
    results = engine.analyze_failures()
    assert len(results) == 1
    res = results[0]
    assert res['prompt_id'] == 'p2'
    assert res['analysis'] is None
    assert 'error' in res and 'API error' in res['error']


def test_save_analysis_writes_file(tmp_path):
    entries = []
    engine = FeedbackEngineV2(archive_service=DummyArchiveService(entries))
    analyses = [
        {'prompt_id':'p3','analysis':'a1','raw_response':{}}
    ]
    output_file = str(tmp_path / 'analysis.json')
    success = engine.save_analysis(analyses, output_file)
    assert success is True
    assert os.path.exists(output_file)
    content = json.loads(open(output_file, 'r', encoding='utf-8').read())
    assert content == analyses 
