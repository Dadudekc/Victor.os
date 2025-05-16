"""Configuration management utilities."""

import time
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .cache_provider import CacheProvider, InMemoryCacheProvider


class ConfigManager:
    """Manages system configuration loading and validation."""

    def __init__(
        self,
        config_dir: str = "config",
        cache_ttl: int = 300,
        cache_provider: Optional[CacheProvider] = None,
        max_in_memory_cache_size: int = 1000,
    ):
        self.config_dir = Path(config_dir)
        self.cache_ttl = cache_ttl
        if cache_provider is None:
            self.cache_provider = InMemoryCacheProvider(
                max_cache_size=max_in_memory_cache_size
            )
        else:
            self.cache_provider = cache_provider

    def load_config(self, config_name: str) -> Dict[str, Any]:
        cached_item = self.cache_provider.get(config_name)
        if cached_item:
            config, timestamp = cached_item
            if time.time() - timestamp < self.cache_ttl:
                self.cache_provider.record_hit(config_name)
                return config
            else:
                self.cache_provider.delete(config_name)
        self.cache_provider.record_miss(config_name)
        config_path = self.config_dir / f"{config_name}.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        self.cache_provider.set(config_name, config, time.time())
        return config

    def validate_config(self, config: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        def _validate_type(value: Any, expected_type: Any) -> bool:
            if expected_type == "string":
                return isinstance(value, str)
            elif expected_type == "number":
                return isinstance(value, (int, float))
            elif expected_type == "boolean":
                return isinstance(value, bool)
            elif expected_type == "object":
                return isinstance(value, dict)
            elif expected_type == "array":
                return isinstance(value, list)
            return False

        def _validate_schema(data: Any, schema_node: Any) -> bool:
            if isinstance(schema_node, dict):
                if not isinstance(data, dict):
                    return False
                for key, value_schema in schema_node.items():
                    if key not in data:
                        return False
                    if not _validate_schema(data[key], value_schema):
                        return False
            elif isinstance(schema_node, list):
                if not isinstance(data, list):
                    return False
                if len(schema_node) > 0:
                    item_schema = schema_node[0]
                    for item in data:
                        if not _validate_schema(item, item_schema):
                            return False
            else:
                return _validate_type(data, schema_node)
            return True

        return _validate_schema(config, schema)

    def get_config_value(
        self, config_name: str, key_path: str, default: Any = None
    ) -> Any:
        try:
            config = self.load_config(config_name)
            value = config
            for key in key_path.split("."):
                value = value[key]
            return value
        except (KeyError, TypeError, AttributeError):
            return default

    def get_cache_stats(self) -> Dict[str, Any]:
        return self.cache_provider.get_stats()

    def clear_cache(self) -> None:
        self.cache_provider.clear()


__all__ = ["ConfigManager"]
