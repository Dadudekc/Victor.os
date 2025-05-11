"""Dream.OS  ➜  Cursor ↔ THEA Bridge Loop
=====================================

Autonomously:
1.  Injects a prompt into the active Cursor window via PyAutoGUI
2.  Waits (or polls) for THEA to respond in ChatGPT web UI
3.  Scrapes the response with ChatGPTScraper (undetected‑chromedriver)
4.  Stores the response and (optionally) pipes it back into the agent loop
5.  Repeats until the prompt queue is empty or SIGINT received

Drop this in:  `src/dreamos/bridge/run_bridge_loop.py`
Run with:      `python -m dreamos.bridge.run_bridge_loop --agent-id 1 --prompt-file prompts/hello.txt`"""

from . import argparse
from . import asyncio
from . import datetime
from . import dreamos.agents.chatgpt_web_agent
from . import dreamos.cli.cursor_injector
from . import dreamos.core.config
from . import dreamos.core.tasks.nexus.task_nexus
from . import dreamos.services.utils.chatgpt_scraper
from . import dreamos.tools.cursor_bridge.cursor_bridge
from . import fastapi
from . import json
from . import logging
from . import os
from . import pathlib
from . import pydantic
from . import scraper
from . import signal
from . import sys
from . import time
from . import typing
from . import uuid
from . import uvicorn
from . import yaml


__all__ = [

    'BridgeLoop',
    'ErrorResponse',
    'InteractRequest',
    'InteractResponse',
    'call_gpt_api',
    'cli',
    'get_file_mtime',
    'log_failure_trace',
    'log_interaction',
    'main_loop',
    'relay_prompt_to_gpt',
    'run',
    'write_bridge_output',
]
