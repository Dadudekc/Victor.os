"""Defines agent capability schemas and manages capability libraries.

This sub-package provides the Pydantic models for agent capabilities
and may include a registry or library of predefined capabilities.
"""

# Expose key components from this package.
from .schema import AgentCapability

__all__ = [
    "AgentCapability",
]
