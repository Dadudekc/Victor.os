"""Module to launch, detect, and manage a swarm of Cursor instances."""

from . import AppKit
from . import Xlib.X
from . import Xlib.Xatom
from . import Xlib.display
from . import Xlib.error
from . import core.coordination.agent_bus
from . import core.coordination.event_payloads
from . import dataclasses
from . import dreamos.core.bots.orchestrator_bot
from . import integrations.cursor.window_controller
from . import logging
from . import pathlib
from . import platform
from . import pyvda
from . import shutil
from . import subprocess
from . import time
from . import typing
from . import uuid
from . import warnings
from . import win32con
from . import win32gui
from . import win32process


__all__ = [

    'CursorPromptController',
    'CursorWindowController',
    'TheaSwarmBootloader',
    'WindowWrapper',
    'activate_window',
    'close',
    'detect_all_instances',
    'enum_callback',
    'get_window_by_id',
    'get_window_info',
    'launch_instances',
    'move_windows_to_desktop',
    'print_window_map',
    'send_prompt_to_chat',
    'setup_swarm',
    'wait_for_detection',
]
