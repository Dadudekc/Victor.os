from abc import ABC, abstractmethod
from typing import Type, Dict, Any

class Adapter(ABC):
    @abstractmethod
    def execute(self, payload: Any) -> Any:
        """Execute the given payload and return the result."""
        pass

class AdapterRegistry:
    _registry: Dict[str, Type[Adapter]] = {}

    @classmethod
    def register(cls, name: str, adapter_cls: Type[Adapter]):
        cls._registry[name] = adapter_cls

    @classmethod
    def get(cls, name: str, *args, **kwargs) -> Adapter:
        adapter_cls = cls._registry.get(name)
        if not adapter_cls:
            raise ValueError(f"Adapter '{name}' not registered.")
        return adapter_cls(*args, **kwargs)

# Auto-register known adapters if they are importable
try:
    from .openai_adapter import OpenAIAdapter
    AdapterRegistry.register("openai", OpenAIAdapter)
except ImportError:
    pass

try:
    from .cursor_rpc_adapter import CursorRPCAdapter
    AdapterRegistry.register("cursor", CursorRPCAdapter)
except ImportError:
    pass

try:
    from .discord_adapter import DiscordAdapter
    AdapterRegistry.register("discord", DiscordAdapter)
except ImportError:
    pass 
