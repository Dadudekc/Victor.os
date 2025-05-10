import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QLabel,
    QPushButton,
    QSplitter,
)
from PyQt5.QtCore import Qt

# Placeholder for agent data structure and fetching logic
# In a real application, this would interact with your AgentBus or other data sources.
def get_agent_inbox_data():
    """
    Placeholder function to simulate fetching agent inbox data.
    Returns a dictionary where keys are agent_ids and values are lists of messages.
    """
    return {
        "Agent-1": ["Message 1 from User A", "Task update: In progress", "System Alert: High CPU"],
        "Agent-2": ["Query: Need sales report", "Message 2 from User B"],
        "Agent-3": [], # Empty inbox
        "Agent-4": ["Long message that might need scrolling..." * 10],
        "DevOpsAgent": ["Deployment successful: v1.2.3", "Monitoring alert: Disk space low"],
        "ResearchAgent": ["New paper found on topic X", "Data analysis complete"]
    }

class AgentInboxDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agent Inbox Dashboard - DreamOS")
        self.setGeometry(100, 100, 1000, 700)  # x, y, width, height

        self.agent_data = {} # To store fetched agent data

        # --- Main Widget and Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Top Controls (e.g., Refresh Button) ---
        controls_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh Inboxes")
        self.refresh_button.clicked.connect(self.load_agent_inboxes)
        controls_layout.addWidget(self.refresh_button)
        controls_layout.addStretch() # Pushes button to the left
        main_layout.addLayout(controls_layout)

        # --- Splitter for Agent List and Inbox View ---
        splitter = QSplitter(Qt.Horizontal)

        # --- Agent List Pane ---
        agent_list_widget = QWidget()
        agent_list_layout = QVBoxLayout(agent_list_widget)
        agent_list_label = QLabel("Agents")
        agent_list_label.setStyleSheet("font-weight: bold;")
        self.agent_list = QListWidget()
        self.agent_list.itemClicked.connect(self.display_agent_inbox)
        agent_list_layout.addWidget(agent_list_label)
        agent_list_layout.addWidget(self.agent_list)
        splitter.addWidget(agent_list_widget)

        # --- Inbox View Pane ---
        inbox_view_widget = QWidget()
        inbox_view_layout = QVBoxLayout(inbox_view_widget)
        self.inbox_label = QLabel("Select an Agent to view Inbox")
        self.inbox_label.setStyleSheet("font-weight: bold;")
        self.inbox_display = QTextEdit()
        self.inbox_display.setReadOnly(True)
        inbox_view_layout.addWidget(self.inbox_label)
        inbox_view_layout.addWidget(self.inbox_display)
        splitter.addWidget(inbox_view_widget)

        splitter.setSizes([300, 700]) # Initial size ratio for panes
        main_layout.addWidget(splitter)

        # --- Status Bar ---
        self.statusBar().showMessage("Dashboard Ready. Click 'Refresh Inboxes' to load data.")

        # Initial load
        self.load_agent_inboxes()

    def load_agent_inboxes(self):
        self.statusBar().showMessage("Loading agent inboxes...")
        self.agent_list.clear()
        self.inbox_display.clear()
        self.inbox_label.setText("Select an Agent to view Inbox")

        # In a real app, replace get_agent_inbox_data() with actual data fetching
        try:
            self.agent_data = get_agent_inbox_data()
            if not self.agent_data:
                self.statusBar().showMessage("No agent data found.")
                self.inbox_label.setText("No agents available.")
                return

            for agent_id in self.agent_data.keys():
                item = QListWidgetItem(agent_id)
                self.agent_list.addItem(item)
            
            if self.agent_list.count() > 0:
                 self.agent_list.setCurrentRow(0) # Select the first agent by default
                 self.display_agent_inbox(self.agent_list.item(0))


            self.statusBar().showMessage(f"Loaded inboxes for {len(self.agent_data)} agents.")
        except Exception as e:
            self.statusBar().showMessage(f"Error loading inboxes: {e}")
            self.inbox_label.setText("Error loading agent data.")
            print(f"Error loading agent data: {e}") # For console debugging

    def display_agent_inbox(self, item):
        agent_id = item.text()
        self.inbox_label.setText(f"Inbox: {agent_id}")
        
        messages = self.agent_data.get(agent_id, [])
        if messages:
            self.inbox_display.setText("\n--- ".join(messages))
        else:
            self.inbox_display.setText("-- Inbox is empty --")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dashboard = AgentInboxDashboard()
    dashboard.show()
    sys.exit(app.exec_()) 