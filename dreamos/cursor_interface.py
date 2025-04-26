#!/usr/bin/env python3
"""
dreamos/cursor_interface.py

Proxy for top-level cursor_interface to satisfy test imports.
"""

from dreamos.cursor_interface import send_prompt, fetch_reply

__all__ = ["send_prompt", "fetch_reply"] 
