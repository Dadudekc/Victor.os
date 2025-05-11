"""Unified memory subsystem for Dream.OS
-------------------------------------

* MemoryManager   – lightweight JSON fragments (human-readable)
* DatabaseManager – SQLite interaction / conversation store
* UnifiedMemoryManager
    • LRU-compressed cache per segment
    • JSON segment persistence
    • DB bridge for interactions
    • Jinja2 narrative helpers"""

from . import asyncio
from . import cachetools
from . import core.config
from . import core.llm.llm_provider
from . import datetime
from . import dreamos.core.errors
from . import dreamos.core.utils.file_utils
from . import dreamos.integrations.openai_client
from . import jinja2
from . import json
from . import logging
from . import os
from . import pathlib
from . import sqlite3
from . import tempfile
from . import tenacity
from . import typing
from . import utils.summarizer
from . import zlib


__all__ = [

    'CompactionError',
    'DatabaseManager',
    'MemoryManager',
    'SlidingWindowSummarization',
    'SummarizationError',
    'SummarizationStrategy',
    'Summarizer',
    'UnifiedMemoryManager',
    'compact_segment_data',
    'render_narrative',
    'summarize',
    'summarize_memory_file',
]
