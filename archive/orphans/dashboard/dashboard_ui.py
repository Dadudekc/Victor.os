import logging  # noqa: I001
import os
import sys
from pathlib import Path

from dreamos.core.coordination.agent_bus import AgentBus, EventType
from dreamos.dashboard.models import AgentModel, MailboxModel, TaskModel
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTableView,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class Dashboard(QMainWindow):
    def __init__(self, agent_bus: AgentBus = None):
        super().__init__()
        # Allow running without an agent bus for standalone testing if needed
        self.agent_bus = agent_bus
        self.setWindowTitle("Dream.OS Dashboard")
        self.resize(1200, 800)

        # Data Models
        self.agent_model = AgentModel()
        self.task_model = TaskModel()
        self.mailbox_model = MailboxModel()

        # Main Central Widget & Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # --- Overview Tab ---
        self.overview_tab = QWidget()
        overview_layout = QVBoxLayout(self.overview_tab)
        overview_layout.setContentsMargins(10, 10, 10, 10)

        # Agent Table
        self.agent_table = QTableView()
        self.agent_table.setModel(self.agent_model)
        self.agent_table.setAlternatingRowColors(True)
        self.agent_table.setSelectionBehavior(QTableView.SelectRows)
        self.agent_table.setWordWrap(False)
        # self.agent_table.horizontalHeader().setStretchLastSection(True) # Stretch last column  # noqa: E501
        overview_layout.addWidget(QLabel("<b>Agent Status</b>"))
        overview_layout.addWidget(self.agent_table, 2)  # Give agent table more stretch

        # Health Summary Group
        self.health_group = QGroupBox("Agent Health Summary")
        health_grid_layout = QGridLayout()  # Use grid for better label alignment
        self.agents_active_label = QLabel("Active: Pending...")
        self.agents_breaching_label = QLabel("Breaching: Pending...")
        self.avg_success_label = QLabel("Avg Success: Pending...")
        health_grid_layout.addWidget(self.agents_active_label, 0, 0)
        health_grid_layout.addWidget(self.agents_breaching_label, 0, 1)
        health_grid_layout.addWidget(
            self.avg_success_label, 1, 0, 1, 2
        )  # Span across bottom
        self.health_group.setLayout(health_grid_layout)
        overview_layout.addWidget(self.health_group)

        # Task Table
        self.task_table = QTableView()
        self.task_table.setModel(self.task_model)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setSelectionBehavior(QTableView.SelectRows)
        # self.task_table.horizontalHeader().setStretchLastSection(True)
        overview_layout.addWidget(QLabel("<b>Task List</b>"))
        overview_layout.addWidget(self.task_table, 1)  # Give task table less stretch

        # Task Injection Controls
        task_injection_group = QGroupBox("Inject New Task")
        task_injection_layout = QHBoxLayout()
        self.task_in = QLineEdit()
        self.task_in.setPlaceholderText("Enter Task Title...")
        self.task_in.returnPressed.connect(self._inject_task)  # Allow Enter key press
        self.inject_btn = QPushButton("Inject Task")
        self.inject_btn.clicked.connect(self._inject_task)
        self.task_status_label = QLabel("")  # Status feedback label
        self.task_status_label.setStyleSheet("QLabel { padding-left: 10px; }")
        task_injection_layout.addWidget(self.task_in)
        task_injection_layout.addWidget(self.inject_btn)
        task_injection_layout.addWidget(
            self.task_status_label, 1
        )  # Allow label to stretch
        task_injection_group.setLayout(task_injection_layout)
        overview_layout.addWidget(task_injection_group)

        # Mailbox Table (Optional - uncomment if needed)
        # self.mailbox_table = QTableView()
        # self.mailbox_table.setModel(self.mailbox_model)
        # self.mailbox_table.setAlternatingRowColors(True)
        # overview_layout.addWidget(QLabel("<b>Mailbox Messages</b>"))
        # overview_layout.addWidget(self.mailbox_table, 1)

        # Add Overview Tab to TabWidget
        self.tabs.addTab(self.overview_tab, "Overview")

        # --- Chronicle Tab ---
        self.chronicle_tab = QWidget()
        chronicle_layout = QVBoxLayout(self.chronicle_tab)
        chronicle_layout.setContentsMargins(10, 10, 10, 10)
        self.chronicle_viewer = QTextEdit()
        self.chronicle_viewer.setReadOnly(True)
        self.chronicle_viewer.setLineWrapMode(QTextEdit.NoWrap)  # Prevent wrapping
        chronicle_layout.addWidget(QLabel("<b>Dreamscape Chronicle</b>"))
        chronicle_layout.addWidget(self.chronicle_viewer)

        # Add Chronicle Tab to TabWidget
        self.tabs.addTab(self.chronicle_tab, "Chronicle")

        # Timers
        # Timer to refresh data models & health summary
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(2000)  # Refresh data every 2 seconds

        # Timer to refresh Chronicle
        self.chronicle_timer = QTimer()
        self.chronicle_timer.timeout.connect(self._update_chronicle_viewer)
        self.chronicle_timer.start(5000)  # Refresh chronicle every 5 seconds

        # Initial data load
        self.refresh()
        self._update_chronicle_viewer()

    def refresh(self):
        """Refresh the agent, task, and mailbox data models and health summary."""
        try:
            logger.debug("Refreshing dashboard data...")
            self.agent_model.load_data()  # Assumes models handle data loading
            self.task_model.load_data()
            # self.mailbox_model.load_data()
            self._refresh_health_summary()
            logger.debug("Dashboard refresh complete.")
        except Exception as e:
            logger.error(f"Error during dashboard refresh: {e}", exc_info=True)

    def _inject_task(self):
        """Inject a manual task via the AgentBus."""
        title = self.task_in.text().strip()
        if not title:
            self.task_status_label.setText(
                "<font color='orange'>⚠️ Enter task title.</font>"
            )
            return

        if not self.agent_bus:
            logger.warning("AgentBus not available, cannot inject task.")
            self.task_status_label.setText(
                "<font color='red'>❌ AgentBus unavailable.</font>"
            )
            return

        try:
            task = {
                "type": "manual_task",  # Standardized type
                "payload": {"title": title},
                "source": "dashboard_ui",
            }
            logger.info(f"Injecting task: {title}")
            # Assume publish_event handles the logic or raises exceptions
            self.agent_bus.publish_event(EventType.TASK_RECEIVED, task)
            self.task_status_label.setText(
                "<font color='green'>✅ Task injected!</font>"
            )
            self.task_in.clear()
            # Clear status after a delay
            QTimer.singleShot(3000, lambda: self.task_status_label.setText(""))
        except Exception as e:
            logger.error(f"Error injecting task: {e}", exc_info=True)
            self.task_status_label.setText(
                f"<font color='red'>❌ Injection failed: {e}</font>"
            )

    def _refresh_health_summary(self):
        """Refresh the Agent Health Summary section based on AgentModel data."""
        try:
            agents = self.agent_model.get_all_agents()  # Use model's method
            active_count = len(agents)
            breaching_count = 0
            total_success_rate = 0
            valid_agents_for_rate = 0

            for agent in agents:
                # Define breach criteria (example: status is failure or low success metric)  # noqa: E501
                is_breaching = (
                    agent.get("status", "").lower() == "failure"
                )  # Simple example
                # Add more complex breach logic if needed based on agent data fields
                # e.g., if agent.get('success_rate', 1.0) < 0.5:
                #          is_breaching = True

                if is_breaching:
                    breaching_count += 1

                # Calculate average success rate (requires a success metric in agent data)  # noqa: E501
                success_rate = agent.get("success_rate")  # Example field
                if success_rate is not None:
                    total_success_rate += success_rate
                    valid_agents_for_rate += 1

            avg_success_pc = (
                (total_success_rate / valid_agents_for_rate * 100)
                if valid_agents_for_rate > 0
                else 0
            )

            self.agents_active_label.setText(f"Active: {active_count}")
            breach_color = "red" if breaching_count > 0 else "green"
            self.agents_breaching_label.setText(
                f"<font color='{breach_color}'>Breaching: {breaching_count}</font>"
            )
            self.avg_success_label.setText(f"Avg Success: {avg_success_pc:.1f}%")

        except Exception as e:
            logger.error(f"Error updating health summary: {e}", exc_info=True)
            self.agents_active_label.setText("Active: Error")
            self.agents_breaching_label.setText("Breaching: Error")
            self.avg_success_label.setText("Avg Success: Error")

    def _update_chronicle_viewer(self):
        """Update the Chronicle Viewer by reading the specified markdown file."""
        # Determine path relative to the project root
        # Assume PROJECT_ROOT is correctly set or detectable
        try:
            # EDIT: More robust path finding (relative to this file)
            project_root = Path(__file__).resolve().parents[2]
            chronicle_path = (
                project_root / "runtime" / "chronicle" / "dreamscape_chronicle.md"
            )
            if chronicle_path.exists():
                with open(chronicle_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # TODO: Potential Markdown rendering in future?
                self.chronicle_viewer.setPlainText(content)
                # Scroll to the bottom
                self.chronicle_viewer.verticalScrollBar().setValue(
                    self.chronicle_viewer.verticalScrollBar().maximum()
                )
            else:
                self.chronicle_viewer.setPlainText(
                    f"Chronicle file not found at: {chronicle_path}"
                )
        except Exception as e:
            logger.error(f"Error updating chronicle viewer: {e}", exc_info=True)
            self.chronicle_viewer.setPlainText(f"Error loading chronicle: {e}")


# Bootstrap for running standalone (optional)
if __name__ == "__main__":
    # Basic logging setup for standalone test
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Ensure runtime/logs exists for chronicle file
    if not os.path.exists(os.path.join("runtime", "logs")):
        os.makedirs(os.path.join("runtime", "logs"))
        # Create dummy chronicle file if it doesn't exist
        with open(os.path.join("runtime", "logs", "dreamscape_chronicle.md"), "w") as f:
            f.write("# Dreamscape Chronicle\nInitial entry.\n")

    app = QApplication(sys.argv)
    # Create dummy AgentBus if needed for testing
    # class DummyAgentBus:
    #     def publish_event(self, event_name, payload):
    #         logger.info(f"Dummy Bus: Published {event_name} with {payload}")
    # bus = DummyAgentBus()
    win = Dashboard(agent_bus=None)  # Pass None or dummy bus
    win.show()
    sys.exit(app.exec_())
