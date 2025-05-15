"""
UI Interaction utilities for Agent Bootstrap Runner with enhanced error handling and recovery
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import pyautogui
import pyperclip
try:
    import pygetwindow as gw  # For smart window focus
except ImportError:
    gw = None
    logging.warning("pygetwindow not installed - smart window focus disabled")

from dreamos.utils.gui.injector import CursorInjector
from dreamos.utils.gui.retriever import ResponseRetriever
from dreamos.core.coordination.agent_bus import AgentBus

from .config import AgentConfig, RESPONSE_WAIT_SEC, RETRIEVE_RETRIES, RETRY_DELAY_SEC
from .messaging import publish_event

# UI interaction configuration with environment overrides
UI_CONFIG = {
    'retries': int(os.getenv('UI_RETRIES', '3')),
    'retry_delay': float(os.getenv('UI_RETRY_DELAY', '2.0')),
    'screenshot_on_fail': os.getenv('UI_SCREENSHOT_ON_FAIL', 'true').lower() == 'true',
    'failure_log_enabled': os.getenv('UI_LOG_FAILURES', 'true').lower() == 'true'
}

class UIFailureLogger:
    """Handles logging of UI automation failures"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.failure_dir = Path("runtime/ui_failures")
        self.failure_dir.mkdir(parents=True, exist_ok=True)
        self.failure_log = self.failure_dir / f"{agent_id}.json"
        
    def log_failure(self, stage: str, error: Exception, retries: int, **extra: Dict[str, Any]):
        """Log a UI automation failure with metadata"""
        if not UI_CONFIG['failure_log_enabled']:
            return
            
        timestamp = datetime.now(timezone.utc).isoformat()
        failure_data = {
            "stage": stage,
            "timestamp": timestamp,
            "exception": f"{type(error).__name__}: {str(error)}",
            "retries": retries,
            **extra
        }
        
        # Load existing failures
        failures = []
        if self.failure_log.exists():
            try:
                failures = json.loads(self.failure_log.read_text())
            except json.JSONDecodeError:
                pass
                
        # Add new failure and save
        failures.append(failure_data)
        self.failure_log.write_text(json.dumps(failures, indent=2))
        
    def screenshot_failure(self, stage: str) -> Optional[str]:
        """Capture screenshot of failure state"""
        if not UI_CONFIG['screenshot_on_fail']:
            return None
            
        try:
            screens_dir = Path("runtime/failure_screens")
            screens_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            screenshot_path = screens_dir / f"{self.agent_id}_{stage}_{timestamp}.png"
            
            pyautogui.screenshot().save(str(screenshot_path))
            return str(screenshot_path)
        except Exception as e:
            logging.error(f"Failed to capture failure screenshot: {e}")
            return None

class SmartWindowManager:
    """Handles intelligent window focus and recovery"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.window_title_patterns = [
            f"Cursor - {agent_id}",
            f"cursor - {agent_id.lower()}",
            agent_id
        ]
        
    def find_agent_window(self) -> Optional[Any]:
        """Find the agent's Cursor window"""
        if not gw:
            return None
            
        try:
            for pattern in self.window_title_patterns:
                for window in gw.getAllWindows():
                    if pattern in window.title:
                        return window
            return None
        except Exception as e:
            logging.error(f"Error finding window for {self.agent_id}: {e}")
            return None
            
    def ensure_window_focus(self) -> bool:
        """Ensure the agent's window is focused"""
        if not gw:
            return True  # Skip focus check if pygetwindow not available
            
        window = self.find_agent_window()
        if not window:
            return False
            
        try:
            if not window.isActive:
                window.activate()
                time.sleep(0.5)  # Allow window activation to complete
            return True
        except Exception as e:
            logging.error(f"Error focusing window for {self.agent_id}: {e}")
            return False

class AgentUIInteractor:
    """Handles UI interaction for agent bootstrap operations with enhanced error handling"""
    
    def __init__(self, logger: logging.Logger, config: AgentConfig):
        self.logger = logger
        self.config = config
        self.injector = None
        self.retriever = None
        self.failure_logger = UIFailureLogger(config.agent_id)
        self.window_manager = SmartWindowManager(config.agent_id)
        
    def initialize(self) -> bool:
        """Initialize UI components with validation"""
        if not self._validate_coordinates():
            return False
            
        self.injector = CursorInjector(
            agent_id=self.config.agent_id,
            coords_file=str(self.config.coords_file)
        )
        self.retriever = ResponseRetriever(
            agent_id=self.config.agent_id_for_retriever,
            coords_file=str(self.config.copy_coords_file)
        )
        
        self.logger.info(
            f"UI Interactor initialized for {self.config.agent_id} "
            f"(retriever: {self.config.agent_id_for_retriever})"
        )
        return True
        
    def _validate_coordinates(self) -> bool:
        """Validate coordinate files exist"""
        if not self.config.coords_file.exists():
            self.logger.error(f"Coordinates file not found: {self.config.coords_file}")
            return False
            
        if not self.config.copy_coords_file.exists():
            self.logger.error(f"Copy coordinates file not found: {self.config.copy_coords_file}")
            return False
            
        return True
        
    async def inject_prompt(self, bus: AgentBus, prompt: str) -> bool:
        """Inject prompt with enhanced error handling and recovery"""
        if not prompt:
            self.logger.warning("Empty prompt; skipping.")
            return False
            
        # Extract inject command if present
        inject_text = prompt.split("inject:", 1)[1].strip() if "inject:" in prompt.lower() else prompt
        
        # Enforce clipboard = prompt_text
        pyperclip.copy(inject_text)
        self.logger.debug("Clipboard primed with prompt_text")
        
        for attempt in range(UI_CONFIG['retries']):
            try:
                # Ensure window focus
                if not self.window_manager.ensure_window_focus():
                    self.logger.warning(f"Could not focus window for {self.config.agent_id}")
                    continue
                    
                # Attempt injection
                if self.injector.inject(inject_text):
                    await publish_event(
                        bus,
                        self.logger,
                        self.config.agent_id,
                        "inject.ok",
                        {"preview": inject_text[:50]}
                    )
                    pyautogui.press("enter")  # Send enter after injection
                    return True
                    
            except Exception as e:
                self.logger.error(
                    f"Injection attempt {attempt + 1}/{UI_CONFIG['retries']} failed: {e}"
                )
                
                # Capture failure state
                screenshot_path = self.failure_logger.screenshot_failure("inject")
                self.failure_logger.log_failure(
                    "inject",
                    e,
                    attempt + 1,
                    prompt_preview=inject_text[:50],
                    screenshot=screenshot_path
                )
                
                if attempt < UI_CONFIG['retries'] - 1:
                    await asyncio.sleep(UI_CONFIG['retry_delay'])
                    
        # All attempts failed
        await publish_event(
            bus,
            self.logger,
            self.config.agent_id,
            "inject.fail",
            {"error": "Max retries exceeded"}
        )
        return False
        
    async def retrieve_response(self, bus: AgentBus) -> Optional[str]:
        """Retrieve response with enhanced error handling and recovery"""
        await asyncio.sleep(RESPONSE_WAIT_SEC)
        
        for attempt in range(UI_CONFIG['retries']):
            try:
                # Ensure window focus
                if not self.window_manager.ensure_window_focus():
                    self.logger.warning(f"Could not focus window for {self.config.agent_id}")
                    continue
                    
                # Attempt retrieval
                response = self.retriever.retrieve()
                if response:
                    await publish_event(
                        bus,
                        self.logger,
                        self.config.agent_id,
                        "retrieve.ok",
                        {"preview": response[:50]}
                    )
                    
                    # Log successful response
                    with self.config.devlog_path.open("a", encoding="utf-8") as fh:
                        fh.write(
                            f"[{datetime.now(timezone.utc).isoformat()}] "
                            f"RESPONSE: {response}\n"
                        )
                    return response
                    
            except Exception as e:
                self.logger.error(
                    f"Retrieval attempt {attempt + 1}/{UI_CONFIG['retries']} failed: {e}"
                )
                
                # Capture failure state
                screenshot_path = self.failure_logger.screenshot_failure("retrieve")
                self.failure_logger.log_failure(
                    "retrieve",
                    e,
                    attempt + 1,
                    screenshot=screenshot_path
                )
                
                if attempt < UI_CONFIG['retries'] - 1:
                    await asyncio.sleep(UI_CONFIG['retry_delay'])
                    
        # All attempts failed
        await publish_event(
            bus,
            self.logger,
            self.config.agent_id,
            "retrieve.fail",
            {"error": "Max retries exceeded"}
        )
        return None 