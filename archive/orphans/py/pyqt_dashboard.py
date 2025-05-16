import json
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


# Placeholder for agent data structure and fetching logic
# In a real application, this would interact with your AgentBus or other data sources.
def get_agent_inbox_data():
    """
    Placeholder function to simulate fetching agent inbox data.
    Returns a dictionary where keys are agent_ids and values are lists of messages.
    """
    return {
        "Agent-1": [
            "Message 1 from User A",
            "Task update: In progress",
            "System Alert: High CPU",
        ],
        "Agent-2": ["Query: Need sales report", "Message 2 from User B"],
        "Agent-3": [],  # Empty inbox
        "Agent-4": ["Long message that might need scrolling..." * 10],
        "DevOpsAgent": [
            "Deployment successful: v1.2.3",
            "Monitoring alert: Disk space low",
        ],
        "ResearchAgent": ["New paper found on topic X", "Data analysis complete"],
    }


class AgentInboxDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agent Inbox Dashboard - DreamOS")
        self.setGeometry(100, 100, 1000, 700)  # x, y, width, height

        self.agent_data = {}  # To store fetched agent data

        # --- Main Widget and Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Top Controls (e.g., Refresh Button) ---
        controls_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh Inboxes")
        self.refresh_button.clicked.connect(self.load_agent_inboxes)
        controls_layout.addWidget(self.refresh_button)
        controls_layout.addStretch()  # Pushes button to the left
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

        splitter.setSizes([300, 700])  # Initial size ratio for panes
        main_layout.addWidget(splitter)

        # --- Status Bar ---
        self.statusBar().showMessage(
            "Dashboard Ready. Click 'Refresh Inboxes' to load data."
        )

        # Initial load
        self.load_agent_inboxes()

    def load_agent_inboxes(self):
        """Load agent mailboxes from the new location"""
        mailbox_base = Path("runtime/agent_comms/agent_mailboxes")
        if not mailbox_base.exists():
            return

        for agent_dir in mailbox_base.iterdir():
            if agent_dir.is_dir():
                inbox_file = agent_dir / "inbox.json"
                if inbox_file.exists():
                    try:
                        with open(inbox_file, "r") as f:
                            messages = json.load(f)
                            self.update_agent_messages(agent_dir.name, messages)
                    except Exception as e:
                        print(f"Error loading inbox for {agent_dir.name}: {e}")

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
