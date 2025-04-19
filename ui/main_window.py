import sys
import logging
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
    QStackedWidget, QLabel, QStatusBar, QListWidgetItem, QSizePolicy
)
from PyQt5.QtCore import QTimer, QSize, Qt
from PyQt5.QtGui import QFont, QIcon # Import QIcon

import json
from pathlib import Path
# Commented out problematic import
# from core.services.event_logger import log_structured_event 

# Import backend components
from core.memory.memory_manager import MemoryManager
from core.rendering.template_engine import TemplateEngine

# Import the new Forge Tab
from .fragment_forge_tab import FragmentForgeTab

logger = logging.getLogger(__name__)

# Define path to task list
TASK_LIST_PATH = Path(__file__).parent.parent / "task_list.json"

# Placeholder for Task Manager logic
class DummyTaskManager:
    def add_task(self, task):
        logger.info(f"[DummyTaskManager] Task added: {task.get('name')}")
        pass # In a real implementation, add to internal list/db

class DreamOSMainWindow(QMainWindow):
    """Main application window for Dream.OS using Sidebar Navigation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        logger.info("Initializing DreamOSMainWindow GUI with Sidebar Navigation...")
        self.setWindowTitle("Dream.OS")
        self.setGeometry(100, 100, 1200, 800) # Default size

        # --- Instantiate Core Backend Components ---
        self.memory_manager = MemoryManager() 
        self.template_engine = TemplateEngine()
        self.task_manager = DummyTaskManager()
        
        # --- Core Components (Placeholders/Basic Implementation) ---
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        # --- Main Layout: Sidebar + Content Stack ---
        self.main_h_layout = QHBoxLayout(self.central_widget)
        self.main_h_layout.setSpacing(0) # No space between sidebar and content
        self.main_h_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Sidebar --- 
        self.sidebar = QListWidget()
        self.sidebar.setViewMode(QListView.IconMode) # Use IconMode for better visuals
        self.sidebar.setMovement(QListView.Static) # Prevent item dragging
        self.sidebar.setMaximumWidth(120) # Set a max width for the sidebar
        self.sidebar.setSpacing(10)
        self.sidebar.setIconSize(QSize(48, 48)) # Example icon size
        # Basic styling (can be enhanced with stylesheets)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background-color: #f0f0f0;
                border-right: 1px solid #d0d0d0;
            }
            QListWidget::item {
                padding: 10px;
                margin: 2px;
                border-radius: 4px; /* Rounded corners */
            }
            QListWidget::item:selected {
                background-color: #cce5ff; /* Light blue for selection */
                color: black;
                border: 1px solid #99cfff;
            }
            QListWidget::item:hover {
                background-color: #e6e6e6;
            }
        """)
        self.main_h_layout.addWidget(self.sidebar)

        # --- Content Stack ---
        self.content_stack = QStackedWidget()
        self.main_h_layout.addWidget(self.content_stack)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Dream.OS Initialized.")

        # --- Populate Sidebar and Content Stack ---
        self._create_navigation()
        
        # Connect sidebar selection to stack change
        self.sidebar.currentRowChanged.connect(self.content_stack.setCurrentIndex)
        
        # Select the first item by default
        self.sidebar.setCurrentRow(0)
        
        logger.info("DreamOSMainWindow GUI Initialized.")

    def _create_navigation(self):
        """Creates sidebar items and corresponding content widgets."""
        # 1. Dashboard (Placeholder)
        dashboard_widget = QWidget()
        dash_layout = QVBoxLayout(dashboard_widget)
        dash_layout.addWidget(QLabel("Welcome to Dream.OS - Dashboard"))
        dash_layout.setAlignment(Qt.AlignCenter)
        self.add_navigation_item("Dashboard", "icons/dashboard.png", dashboard_widget) # Assumes icon path
        
        # 2. Fragment Forge (Pass backend instances)
        forge_widget = FragmentForgeTab( # Pass instances
            memory_manager=self.memory_manager, 
            template_engine=self.template_engine,
            parent=self
        )
        self.add_navigation_item("Forge", "icons/forge.png", forge_widget)
        
        # 3. Agents (Placeholder)
        agents_widget = QWidget()
        agents_layout = QVBoxLayout(agents_widget)
        agents_layout.addWidget(QLabel("Agent Management"))
        agents_layout.setAlignment(Qt.AlignCenter)
        self.add_navigation_item("Agents", "icons/agents.png", agents_widget)
        
        # 4. Tasks (Placeholder)
        tasks_widget = QWidget()
        tasks_layout = QVBoxLayout(tasks_widget)
        tasks_layout.addWidget(QLabel("Task Management"))
        tasks_layout.setAlignment(Qt.AlignCenter)
        self.add_navigation_item("Tasks", "icons/tasks.png", tasks_widget)

        # Add more items here (Logs, Settings, etc.)
        logger.debug("Navigation structure created.")
        
    def add_navigation_item(self, text: str, icon_path: str, widget: QWidget):
        """Adds an item to the sidebar and its corresponding widget to the stack."""
        item = QListWidgetItem(self.sidebar)
        # Try loading icon, fallback to text only if fails
        icon = QIcon(icon_path)
        if not icon.isNull():
             item.setIcon(icon)
        else:
             logger.warning(f"Icon not found or invalid: {icon_path}")
             # Consider adding placeholder icon
             
        item.setText(text)
        item.setTextAlignment(Qt.AlignCenter)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        # item.setSizeHint(QSize(100, 70)) # Adjust size hint if needed
        
        self.content_stack.addWidget(widget)
        logger.debug(f"Added navigation item: '{text}'")

    # --- Methods called by main.py test mode (Enhanced Stubs) ---
    
    def get_sidebar_items(self) -> list:
        """Returns names of the sidebar items."""
        names = [self.sidebar.item(i).text() for i in range(self.sidebar.count())]
        logger.debug(f"Returning sidebar item names: {names}")
        return names
        
    def log_event(self, event_name: str, event_data: dict):
        """Logs an event locally and using the core structured event logger."""
        logger.info(f"[Stub] Event logged locally: {event_name} - Data: {event_data}")
        # Log using the core service (Commented out)
        # log_structured_event(
        #     event_type=f"GUI_{event_name}", 
        #     data=event_data, 
        #     source="DreamOSMainWindow"
        # )
        # Simulate notifying mailbox (as seen in main.py test)
        self.notify_mailbox(event_name, event_data)
        
    def notify_mailbox(self, event_name: str, event_data: dict):
         """Placeholder for sending notification to agent mailbox."""
         log_info = {"event_name": event_name, "event_data_keys": list(event_data.keys())}
         logger.info(f"[Stub] Sending notification to Agent Mailbox: Event '{event_name}' occurred.")
         # Log using the core service (Commented out)
         # log_structured_event("GUI_MAILBOX_NOTIFY_SENT", log_info, "DreamOSMainWindow")
         # Simulate syncing with board (as seen in main.py test)
         self.sync_event_with_board("mailbox_update", {"event": event_name})
         
    def sync_event_with_board(self, sync_type: str, data: dict):
         """Placeholder for syncing event/task/state with a central board.
            Enhanced to append test task to task_list.json when sync_type is 'task_add'.
         """
         log_info = {"sync_type": sync_type, "data_keys": list(data.keys())}
         logger.info(f"[Stub] Syncing '{sync_type}' with Central Agent Board. Data: {data}")
         # Log using the core service (Commented out)
         # log_structured_event("GUI_BOARD_SYNC_ATTEMPT", log_info, "DreamOSMainWindow")

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
            # Log using the core service (Commented out)
            # log_structured_event("GUI_TASK_APPENDED", {"task_id": task_data.get('id')}, "DreamOSMainWindow")
        except Exception as e:
            logger.error(f"Failed to append task to {TASK_LIST_PATH}: {e}", exc_info=True)
            # Log using the core service (Commented out)
            # log_structured_event("GUI_TASK_APPEND_FAILED", {"task_id": task_data.get('id'), "error": str(e)}, "DreamOSMainWindow")

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