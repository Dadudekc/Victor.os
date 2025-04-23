from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QTableView, QListWidget, QPlainTextEdit, QPushButton, QLabel
from PySide6.QtCore import Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor
import logging

# Initialize logger
logger = logging.getLogger(__name__)

class SwarmDashboardTab(QWidget):
    def __init__(self, nexus, channel, data_bridge, parent=None):
        super().__init__(parent)
        self.nexus = nexus
        self.channel = channel
        self.data_bridge = data_bridge

        main_layout = QVBoxLayout(self)

        # Task queue views
        tasks_layout = QHBoxLayout()
        self.pending_view = QTableView()
        self.completed_view = QTableView()
        # Models for tables
        self.pending_model = QStandardItemModel(self)
        self.completed_model = QStandardItemModel(self)
        self.pending_model.setHorizontalHeaderLabels(["ID", "Status", "Agent", "Files", "Time"])
        self.completed_model.setHorizontalHeaderLabels(["ID", "Status", "Agent", "Files", "Time"])
        self.pending_view.setModel(self.pending_model)
        self.completed_view.setModel(self.completed_model)
        tasks_layout.addWidget(self.pending_view)
        tasks_layout.addWidget(self.completed_view)
        main_layout.addLayout(tasks_layout)

        # Agents and stats panel
        info_layout = QHBoxLayout()
        self.agent_list = QListWidget()
        self.stats_label = QLabel("Task Stats: N/A")
        info_layout.addWidget(QLabel("Agents:"))
        info_layout.addWidget(self.agent_list)
        info_layout.addWidget(self.stats_label)
        main_layout.addLayout(info_layout)

        # Lore log stream
        main_layout.addWidget(QLabel("Lore Stream:"))
        self.lore_textbox = QPlainTextEdit()
        self.lore_textbox.setReadOnly(True)
        main_layout.addWidget(self.lore_textbox)

        # Controls
        controls_layout = QHBoxLayout()
        self.pause_button = QPushButton("Pause Swarm")
        self.retry_button = QPushButton("Retry Failed")
        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(self.retry_button)
        main_layout.addLayout(controls_layout)

        # Connect signals from data bridge
        self.data_bridge.tasks_updated.connect(self.update_tasks)
        self.data_bridge.agents_updated.connect(self.update_agents)
        self.data_bridge.stats_updated.connect(self.update_stats)
        self.data_bridge.lore_updated.connect(self.update_lore)

        # Wire control buttons to handlers
        self.pause_button.clicked.connect(self._on_pause_clicked)
        self.retry_button.clicked.connect(self._on_retry_clicked)

    @Slot(list)
    def update_tasks(self, tasks):
        # Clear models
        self.pending_model.removeRows(0, self.pending_model.rowCount())
        self.completed_model.removeRows(0, self.completed_model.rowCount())
        for task in tasks:
            # Build row data
            task_id = task.get("id", "")
            status = task.get("status", "")
            agent = task.get("claimed_by", "—")
            files = ", ".join(task.get("payload", {}).get("module_path", [])) if isinstance(task.get("payload"), dict) else ""
            timestamp = task.get("timestamp_created", "")
            row = [task_id, status, agent, files, timestamp]
            items = [QStandardItem(str(v)) for v in row]
            # Highlight tasks assigned to agent_005
            if agent == "agent_005":
                for item in items:
                    item.setBackground(QBrush(QColor(200, 230, 201)))  # light green background
            if status == "pending":
                self.pending_model.appendRow(items)
            else:
                self.completed_model.appendRow(items)

    @Slot(list)
    def update_agents(self, agents):
        self.agent_list.clear()
        for name, status in agents:
            icon = "✅" if status == "active" else "🟡" if status == "idle" else "❌"
            self.agent_list.addItem(f"{icon} {name} ({status})")

    @Slot(dict)
    def update_stats(self, stats):
        text = f"✔ {stats.get('completed',0)} | ❌ {stats.get('failed',0)} | 🌀 {stats.get('claimed',0)}"
        self.stats_label.setText(text)

    @Slot(str)
    def update_lore(self, lore_text):
        self.lore_textbox.setPlainText(lore_text)
        scrollbar = self.lore_textbox.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @Slot()
    def _on_pause_clicked(self):
        """Handle pause button click to pause the swarm."""
        logger.info("Pause button clicked - pausing swarm")
        try:
            self.nexus.pause_all()
        except Exception as e:
            logger.error(f"Error pausing swarm: {e}")

    @Slot()
    def _on_retry_clicked(self):
        """Handle retry button click to retry failed tasks."""
        logger.info("Retry button clicked - retrying failed tasks")
        try:
            self.nexus.retry_failed()
        except Exception as e:
            logger.error(f"Error retrying failed tasks: {e}") 