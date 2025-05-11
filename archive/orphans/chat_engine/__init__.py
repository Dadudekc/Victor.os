"""Package chat_engine."""

from . import PyQt5
from . import PyQt5.QtWidgets
from . import asyncio
from . import chat_mate_config
from . import concurrent.futures
from . import datetime
from . import discord
from . import discord.ext
from . import dreamos.chat_engine.chat_scraper_service
from . import dreamos.chat_engine.discord_dispatcher
from . import dreamos.chat_engine.prompt_execution_service
from . import dreamos.core.config
from . import dreamos.feedback.feedback_engine
from . import dreamos.integrations.openai_client
from . import dreamos.services.prompt_archive
from . import json
from . import logging
from . import os
from . import pathlib
from . import pickle
from . import platform
from . import selenium
from . import selenium.webdriver.chrome.options
from . import selenium.webdriver.chrome.service
from . import selenium.webdriver.common.by
from . import selenium.webdriver.support
from . import selenium.webdriver.support.ui
from . import shutil
from . import subprocess
from . import sys
from . import tempfile
from . import threading
from . import time
from . import typing
from . import undetected_chromedriver
from . import webdriver_manager.chrome


__all__ = [

    'ChatCycleController',
    'ChatScraperService',
    'Config',
    'DiscordDispatcher',
    'DriverManager',
    'FeedbackEngine',
    'FeedbackEngineV2',
    'GUIEventHandler',
    'PromptExecutionService',
    'QApplication',
    'QCheckBox',
    'QLabel',
    'QMainWindow',
    'QPushButton',
    'QTextEdit',
    'QtCore',
    'QtWidgets',
    'analyze_feedback',
    'append_output',
    'apply_memory_updates',
    'clear_cookies',
    'dispatch_dreamscape_episode',
    'dispatch_feedback_loop',
    'dispatch_memory_update',
    'example_main',
    'exec_',
    'execute_prompt_cycle',
    'execute_prompts_concurrently',
    'execute_prompts_single_chat',
    'execute_with_retry',
    'export_feedback_log',
    'feedback_loop',
    'get',
    'get_all_chats',
    'get_driver',
    'get_filtered_chats',
    'get_instance',
    'get_prompt',
    'get_session_info',
    'init_ui',
    'is_logged_in',
    'load_cookies',
    'log',
    'log_feedback',
    'manual_login_flow',
    'parse_and_update_memory',
    'process_chat',
    'release_driver',
    'review_context_memory',
    'review_memory',
    'run_bot',
    'run_gui',
    'run_single_chat',
    'sanitize_filename',
    'save_analysis',
    'save_context_db',
    'save_context_memory_async',
    'save_cookies',
    'save_memory_async',
    'scroll_into_view',
    'scroll_page',
    'scroll_to_bottom_smoothly',
    'send_message',
    'send_prompt_and_wait',
    'set_session_timeout',
    'setup_logger',
    'shutdown',
    'start',
    'start_dispatcher',
    'stop_dispatcher',
    'toggle_archive',
    'toggle_headless',
    'toggle_reverse',
    'update_options',
    'validate_login',
]
