"""ChatGPT Web Scraper - Automated chat history extraction tool.
Uses undetected-chromedriver to avoid detection and provides robust session management."""

from . import apscheduler.schedulers.background
from . import apscheduler.triggers.date
from . import core.strategies.linkedin_strategy
from . import core.strategies.twitter_strategy
from . import dataclasses
from . import datetime
from . import dreamforge.core.governance_memory_engine
from . import dreamos.core.config
from . import dreamos.core.strategies.linkedin_strategy
from . import dreamos.core.strategies.twitter_strategy
from . import dreamos.services.utils.devlog_analyzer
from . import dreamos.services.utils.logging_utils
from . import dreamos.utils.ai_output_logger
from . import dreamos.utils.common_utils
from . import frontmatter
from . import functools
from . import hashlib
from . import jinja2
from . import json
from . import logging
from . import os
from . import pandas
from . import pathlib
from . import pickle
from . import queue
from . import re
from . import selenium.common.exceptions
from . import selenium.webdriver.common.by
from . import selenium.webdriver.common.keys
from . import selenium.webdriver.remote.webdriver
from . import selenium.webdriver.support
from . import selenium.webdriver.support.ui
from . import shutil
from . import sqlite3
from . import sys
from . import threading
from . import time
from . import typing
from . import undetected_chromedriver
from . import uuid
from . import watchdog.events
from . import watchdog.observers
from . import webdriver_manager.chrome


__all__ = [

    'ChatContext',
    'ContentBlock',
    'ContentHandler',
    'CursorState',
    'DevLogAnalyzer',
    'DevLogDispatcher',
    'DevLogGenerator',
    'DevLogPost',
    'FeedbackProcessor',
    'HybridResponseHandler',
    'ResponseHandler',
    'add_message',
    'add_to_history',
    'auto_publish',
    'clean_response',
    'clear',
    'clear_history',
    'decorator',
    'default_queue_fn',
    'ensure_chat_page',
    'ensure_login_session',
    'execute_prompt_cycle',
    'execute_prompts_on_all_chats',
    'fetch_response',
    'generate_blog_post',
    'generate_social_content',
    'get_available_models',
    'get_best_posting_times',
    'get_content_insights',
    'get_context',
    'get_conversation_content',
    'get_conversation_links',
    'get_file_context',
    'get_logger',
    'get_top_performing_tags',
    'handle_hybrid_response',
    'handle_new_blog_post',
    'handle_new_social_content',
    'is_logged_in',
    'is_rate_limited',
    'load_cookies',
    'log_event',
    'main',
    'navigate_to',
    'on_created',
    'parse_hybrid_response',
    'process_conversation',
    'process_feedback',
    'prompt_with_fallback',
    'publish_job',
    'record_command',
    'retry_selenium_action',
    'safe_click',
    'safe_send_keys',
    'save_cookies',
    'schedule_post',
    'scroll_to_bottom',
    'select_model',
    'send_prompt',
    'set_current_file',
    'shutdown',
    'start',
    'stop',
    'track_post',
    'update_context',
    'update_metrics',
    'wait_for_element',
    'wait_for_stable_response',
    'wrapper',
]
