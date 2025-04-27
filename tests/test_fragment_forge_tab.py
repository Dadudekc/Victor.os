import pytest
from dreamos.gui.fragment_forge_tab import FragmentForgeTab

# Dummy classes to satisfy type hints
class DummyMemoryManager:
    pass

class DummyTemplateEngine:
    pass


def test_init_requires_managers():
    # Missing memory_manager should raise
    with pytest.raises(ValueError):
        FragmentForgeTab(None, DummyTemplateEngine())
    # Missing template_engine should raise
    with pytest.raises(ValueError):
        FragmentForgeTab(DummyMemoryManager(), None)


def test_init_success(tmp_path, monkeypatch):
    # Use dummy backend instances
    mem = DummyMemoryManager()
    tmpl = DummyTemplateEngine()
    # Instantiate without error
    tab = FragmentForgeTab(mem, tmpl)
    assert tab.memory_manager is mem
    assert tab.template_engine is tmpl
    # Check that UI components are set
    assert hasattr(tab, 'fragment_list')
    assert hasattr(tab, 'quote_input')
    assert hasattr(tab, 'save_button') 
