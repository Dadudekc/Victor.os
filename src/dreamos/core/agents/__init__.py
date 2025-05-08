"""Core agent definitions and base classes for DreamOS.

This package provides the foundational structures for agents operating
within the DreamOS system, including their lifecycle, capabilities,
and communication mechanisms.
"""

# Expose key components from this package.
from .capabilities import AgentCapability

__all__ = [
    "AgentCapability",
] 