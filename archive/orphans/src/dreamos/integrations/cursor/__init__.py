"""Dream.OS Cursor Integration
=============================

This module provides integration capabilities with the Cursor IDE,
including the bridge functionality for THEA interactions.
"""

from .bridge import BridgeLoop, bridge_service, cli, main_loop

__all__ = [
    "BridgeLoop",
    "bridge_service",
    "cli",
    "main_loop",
]
