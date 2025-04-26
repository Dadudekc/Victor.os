import json
import os
from pathlib import Path
from PyQt5.QtWidgets import QMessageBox

# Placeholder classes for test patching
class TaskManager:
    """Stub TaskManager for GUI state tests."""
    pass

class FeedbackEngine:
    """Stub FeedbackEngine for GUI state tests."""
    pass

class DreamOSTabManager:
    """Stub tab manager to be replaced by actual or mock in tests."""
    def __init__(self):
        # tests will patch DreamOSTabManager to return a MockTabManager
        self._tabs = {}

    def get_tab_by_name(self, name: str):
        return self._tabs.get(name)

class TabSystemShutdownManager:
    """Stub for shutdown manager used in GUI tests."""
    pass

class DreamOSMainWindow:
    """Stub GUI main window for state management tests."""

    def __init__(self):
        # default state file path; tests override this attribute
        self.state_file = Path("app_state.json")
        # use DreamOSTabManager to get a tab manager instance
        self.tab_manager = DreamOSTabManager()

    def _save_state(self):
        """Save state of tabs to JSON file at self.state_file."""
        data = {}
        # Collect state from each tab stored in _tabs (keyed by normalized names)
        for key, tab in getattr(self.tab_manager, "_tabs", {}).items():
            try:
                data[key] = tab.get_state()
            except Exception:
                pass
        # Ensure directory exists
        try:
            os.makedirs(os.path.dirname(str(self.state_file)), exist_ok=True)
        except Exception:
            pass
        # Write JSON
        with open(self.state_file, "w") as f:
            json.dump(data, f)

    def _load_state(self):
        """Load state from JSON file and restore to tabs."""
        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            # No state file; nothing to restore
            return
        except Exception:
            # Could not parse JSON
            QMessageBox.warning(None, "Error", "Could not load or parse state file.")
            return

        count = 0
        for key, state in data.items():
            tab = None
            if hasattr(self.tab_manager, "get_tab_by_name"):
                tab = self.tab_manager.get_tab_by_name(key)
            if tab:
                try:
                    tab.restore_state(state)
                    count += 1
                except Exception:
                    pass
        # Display status message if statusBar method exists
        try:
            self.statusBar().showMessage(f"Restored state for {count} tabs.", 5000)
        except Exception:
            pass 
