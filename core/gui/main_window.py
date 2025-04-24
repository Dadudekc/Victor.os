import json
from pathlib import Path
import os

# Attempt to import PyQt components; if unavailable, provide dummies
try:
    from PyQt5.QtWidgets import QMainWindow, QMessageBox, QStatusBar, QLabel
    from PyQt5.QtCore import QTimer
except ImportError:
    class QMainWindow:
        def __init__(self, *args, **kwargs): pass
    class QMessageBox:
        @staticmethod
        def warning(*args, **kwargs): pass
    class QStatusBar: pass
    class QLabel: pass
    class QTimer: pass

# Import shutdown manager for patching
from core.gui.tab_system_shutdown import TabSystemShutdownManager

# Placeholder classes for patching
class TaskManager:
    pass

class FeedbackEngine:
    pass

class DreamOSTabManager:
    def __init__(self):
        self._tabs = {}
    def add_tab(self, widget, name):
        key = name.lower().replace(" ", "_")
        self._tabs[key] = widget
    def get_tab_by_name(self, name):
        return self._tabs.get(name)

class DreamOSMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__()
        # File path for saving/loading tab states
        self.state_file = Path("./tab_states.json")
        # Core components
        self.task_manager = TaskManager()
        self.feedback_engine = FeedbackEngine()
        self.tab_manager = DreamOSTabManager()
        # Initialize shutdown manager (not used directly in these tests)
        self.shutdown_manager = TabSystemShutdownManager(self.feedback_engine, os.getcwd())

    def _save_state(self):
        # Gather state from each tab
        states = {}
        for key, tab in getattr(self.tab_manager, '_tabs', {}).items():
            try:
                states[key] = tab.get_state()
            except Exception:
                continue
        # Ensure directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        # Write state to file
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(states, f)

    def _load_state(self):
        # If no state file, do nothing
        if not self.state_file.exists():
            return
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            # Notify user of invalid format via patched QMessageBox
            import importlib
            mod = importlib.import_module(__name__)
            mod.QMessageBox.warning(None, f"Invalid format: {e}")
            return
        # Restore each tab state
        for key, state in data.items():
            tab = self.tab_manager.get_tab_by_name(key)
            if tab and hasattr(tab, 'restore_state'):
                tab.restore_state(state)
        # Show confirmation in status bar
        try:
            sb = self.statusBar()
            sb.showMessage(f"Restored state for {len(data)} tabs.", 5000)
        except Exception:
            pass

    def manual_save_state(self):
        """Public method to manually save the current tab states."""
        self._save_state()

    def auto_save_state(self):
        """Public method to automatically save the current tab states."""
        self._save_state() 