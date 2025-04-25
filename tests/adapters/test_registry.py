import os
import pytest
from dream_os.adapters.base_adapter import AdapterRegistry
from dream_os.adapters.openai_adapter import OpenAIAdapter
from dream_os.adapters.cursor_rpc_adapter import CursorRPCAdapter
from dream_os.adapters.discord_adapter import DiscordAdapter
from dream_os.core.crew_agent_base import CrewAgent


def test_registry_contains_adapters():
    # Ensure adapters are registered
    assert "openai" in AdapterRegistry._registry
    assert "cursor" in AdapterRegistry._registry
    assert "discord" in AdapterRegistry._registry


def test_openai_adapter_instantiation(monkeypatch):
    # Provide dummy API key
    monkeypatch.setenv("OPENAI_API_KEY", "testkey")
    adapter = AdapterRegistry.get("openai")
    assert isinstance(adapter, OpenAIAdapter)
    # Model default
    assert adapter.model is not None


def test_cursor_rpc_adapter_instantiation():
    adapter = AdapterRegistry.get("cursor")
    assert isinstance(adapter, CursorRPCAdapter)


def test_discord_adapter_instantiation(monkeypatch):
    # Provide dummy webhook url
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.com/webhook")
    adapter = AdapterRegistry.get("discord")
    assert isinstance(adapter, DiscordAdapter)


def test_invalid_adapter_name():
    with pytest.raises(ValueError):
        AdapterRegistry.get("nonexistent")


class DummyAdapter:
    def __init__(self, *args, **kwargs):
        pass
    def execute(self, payload):
        return "dummy"


def test_crew_agent_uses_default_adapter(monkeypatch):
    # Replace the 'openai' adapter with a dummy for testing
    monkeypatch.setitem(AdapterRegistry._registry, "openai", DummyAdapter)
    # Instantiate a Strategist, which defaults to the 'openai' adapter
    agent = CrewAgent(name="TestAgent", role_name="Strategist")
    result = agent.execute({"type": "plan"})
    assert result["status"] == "ok"
    assert result["output"] == "dummy" 