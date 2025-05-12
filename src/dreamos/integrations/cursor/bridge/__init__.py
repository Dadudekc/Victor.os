"""Dream.OS Cursor Integration Bridge
=====================================

This module provides the bridge functionality between Dream.OS and Cursor IDE,
specifically for handling interactions with THEA through the ChatGPT interface.

The bridge autonomously:
1. Injects prompts into the active Cursor window
2. Waits for THEA to respond in ChatGPT web UI
3. Scrapes and processes responses
4. Manages the communication loop
"""

from .bridge_loop import BridgeLoop, main_loop
from .http_bridge_service import app as bridge_service
from .run_bridge_loop import cli

__all__ = [
    'BridgeLoop',
    'bridge_service',
    'cli',
    'main_loop',
]
