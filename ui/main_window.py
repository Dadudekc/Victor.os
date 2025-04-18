import sys
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel, QStatusBar
from PyQt5.QtCore import QTimer
import json
from pathlib import Path
from core.services.event_logger import log_structured_event

logger = logging.getLogger(__name__)

# Define path to task list
TASK_LIST_PATH = Path(__file__).parent.parent / "task_list.json"

# Placeholder for Task Manager logic
class DummyTaskManager:
    def add_task(self, task):
        logger.info(f"[DummyTaskManager] Task added: {task.get('name')}")
        pass # In a real implementation, add to internal list/db

class DreamOSMainWindow(QMainWindow):
    """Main application window for Dream.OS."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.info("Initializing DreamOSMainWindow GUI...")
        self.setWindowTitle("Dream.OS")
        self.setGeometry(100, 100, 1200, 800) # Default size

        # --- Core Components (Placeholders/Basic Implementation) ---
        self.task_manager = DummyTaskManager()
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget)
        
        # Add a default status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Dream.OS Initialized.")

        # Add some example tabs (replace with actual tabs later)
        self._create_example_tabs()
        
        logger.info("DreamOSMainWindow GUI Initialized.")

    def _create_example_tabs(self):
        """Creates placeholder tabs."""
        tab1 = QWidget()
        tab1_layout = QVBoxLayout(tab1)
        tab1_layout.addWidget(QLabel("Welcome to Dream.OS - Dashboard Tab (Placeholder)"))
        self.tab_widget.addTab(tab1, "Dashboard")
        
        tab2 = QWidget()
        tab2_layout = QVBoxLayout(tab2)
        tab2_layout.addWidget(QLabel("Agent Management Tab (Placeholder)"))
        self.tab_widget.addTab(tab2, "Agents")
        
        logger.debug("Example tabs created.")

    # --- Methods called by main.py test mode (Enhanced Stubs) ---
    
    def get_tab_names(self) -> list:
        """Returns names of the tabs."""
        names = [self.tab_widget.tabText(i) for i in range(self.tab_widget.count())]
        logger.debug(f"Returning tab names: {names}")
        return names
        
    def log_event(self, event_name: str, event_data: dict):
        """Logs an event locally and using the core structured event logger."""
        logger.info(f"[Stub] Event logged locally: {event_name} - Data: {event_data}")
        # Log using the core service
        log_structured_event(
            event_type=f"GUI_{event_name}", 
            data=event_data, 
            source="DreamOSMainWindow"
        )
        # Simulate notifying mailbox (as seen in main.py test)
        self.notify_mailbox(event_name, event_data)
        
    def notify_mailbox(self, event_name: str, event_data: dict):
         """Placeholder for sending notification to agent mailbox."""
         log_info = {"event_name": event_name, "event_data_keys": list(event_data.keys())}
         logger.info(f"[Stub] Sending notification to Agent Mailbox: Event '{event_name}' occurred.")
         log_structured_event("GUI_MAILBOX_NOTIFY_SENT", log_info, "DreamOSMainWindow")
         # Simulate syncing with board (as seen in main.py test)
         self.sync_event_with_board("mailbox_update", {"event": event_name})
         
    def sync_event_with_board(self, sync_type: str, data: dict):
         """Placeholder for syncing event/task/state with a central board.
            Enhanced to append test task to task_list.json when sync_type is 'task_add'.
         """
         log_info = {"sync_type": sync_type, "data_keys": list(data.keys())}
         logger.info(f"[Stub] Syncing '{sync_type}' with Central Agent Board. Data: {data}")
         log_structured_event("GUI_BOARD_SYNC_ATTEMPT", log_info, "DreamOSMainWindow")

         # If this is the task add sync, append to task_list.json
         if sync_type == "task_add" and isinstance(data, dict) and 'id' in data:
             self._append_task_to_list(data)
         
    def save_state(self):
        """Placeholder for saving application/agent state."""
        logger.info("[Stub] Saving local agent/application state...")
        # Simulate syncing state with board (as seen in main.py test)
        self.sync_event_with_board("state_save", {"status": "saved"})

    def _append_task_to_list(self, task_data: dict):
        """Appends a task dictionary to the task_list.json file."""
        logger.info(f"Attempting to append task {task_data.get('id')} to {TASK_LIST_PATH}")
        try:
            tasks = []
            if TASK_LIST_PATH.exists():
                try:
                     with open(TASK_LIST_PATH, 'r', encoding='utf-8') as f:
                         content = f.read()
                         if content.strip():
                             tasks = json.loads(content)
                         if not isinstance(tasks, list):
                              logger.warning(f"Task list file {TASK_LIST_PATH} does not contain a valid list. Resetting.")
                              tasks = []
                except json.JSONDecodeError:
                     logger.error(f"Failed to decode existing task list {TASK_LIST_PATH}. Resetting.")
                     tasks = []
            
            tasks.append(task_data)
            
            with open(TASK_LIST_PATH, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, indent=2) # Write back with indentation
            logger.info(f"Successfully appended task {task_data.get('id')} to {TASK_LIST_PATH}")
            log_structured_event("GUI_TASK_APPENDED", {"task_id": task_data.get('id')}, "DreamOSMainWindow")
        except Exception as e:
            logger.error(f"Failed to append task to {TASK_LIST_PATH}: {e}", exc_info=True)
            log_structured_event("GUI_TASK_APPEND_FAILED", {"task_id": task_data.get('id'), "error": str(e)}, "DreamOSMainWindow")

    # --- Window Management ---
        
    def closeEvent(self, event):
        """Handle window close event."""
        logger.info("Close event triggered. Cleaning up...")
        # Add any necessary cleanup here (e.g., stopping threads, saving final state)
        self.cleanup_resources()
        super().closeEvent(event)
        
    def cleanup_resources(self):
         """Placeholder for releasing resources."""
         logger.info("[Stub] Cleaning up resources...")
         # Example: Stop timers, disconnect signals, etc.
         
# Example of running this window directly (for testing)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    main_window = DreamOSMainWindow()
    main_window.show()
    sys.exit(app.exec_()) 