#!/usr/bin/env python3
"""
ui/tab_system_shutdown.py

Migrated TabSystemShutdownManager for unified UI package.
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class TabSystemShutdownManager:
    """Manager to handle shutdown sequence of UI tabs and persist their state."""
    def __init__(self, feedback_engine, agent_directory):
        self.feedback_engine = feedback_engine
        self.agent_directory = agent_directory
        class Signal:
            def emit(self):
                pass
        self.shutdown_complete = Signal()

    def _handle_shutdown_error(self, error):
        """Handle errors during shutdown persistence."""
        logger.error(f"CRITICAL: Error persisting tab states to file: {error}", exc_info=True)

    def initiate_shutdown(self, tabs: dict):
        """Run shutdown: prepare tabs, save state atomically, log events, emit signal."""
        state_data = {}
        issues = False
        # Prepare and collect state
        for name, tab in tabs.items():
            try:
                success = tab.prepare_for_shutdown()
            except Exception:
                success = False
            if not success:
                logger.warning(f"Tab '{name}' reported issues during shutdown.")
                issues = True
                continue
            try:
                state = tab.get_state()
                state_data[name] = state
            except Exception:
                continue
        if issues:
            logger.warning("One or more tabs had issues during shutdown preparation.")
        # Persist state atomically
        state_file = Path(self.agent_directory) / "tab_states.json"
        temp_file = state_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f)
            os.replace(str(temp_file), str(state_file))
            if temp_file.exists() and not state_file.exists():
                import shutil; shutil.copy(str(temp_file), str(state_file))
            if not state_file.exists():
                with open(state_file, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f)
        except Exception as e:
            logger.error(f"CRITICAL: Error persisting tab states: {e}", exc_info=True)
            self._handle_shutdown_error(e)
            return
        # Log events
        try:
            self.feedback_engine.log_event("system_shutdown", {"tabs": list(state_data.keys())})
            self.feedback_engine.log_event("shutdown_ready", {"tabs": list(state_data.keys())})
        except Exception:
            pass
        # Emit completion
        self.shutdown_complete.emit() 
