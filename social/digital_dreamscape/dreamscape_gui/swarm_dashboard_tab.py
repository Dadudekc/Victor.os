from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QTableView, QLabel, QTextEdit, QPushButton
from PySide6.QtCore import QTimer

class SwarmDashboardTab(QWidget):
    def __init__(self, nexus, channel, parent=None):
        super().__init__(parent)
        self.nexus = nexus
        self.channel = channel

        # Main vertical layout
        main_layout = QVBoxLayout(self)

        # Task queue views
        tasks_layout = QHBoxLayout()
        self.pending_view = QTableView()
        self.completed_view = QTableView()
        tasks_layout.addWidget(self.pending_view)
        tasks_layout.addWidget(self.completed_view)
        main_layout.addLayout(tasks_layout)

        # Agents and stats panel
        info_layout = QHBoxLayout()
        self.agents_label = QLabel("Agents Online: 0")
        self.stats_label = QLabel("Task Stats: N/A")
        info_layout.addWidget(self.agents_label)
        info_layout.addWidget(self.stats_label)
        main_layout.addLayout(info_layout)

        # Lore log stream
        main_layout.addWidget(QLabel("Lore Stream:"))
        self.lore_stream = QTextEdit()
        self.lore_stream.setReadOnly(True)
        main_layout.addWidget(self.lore_stream)

        # Controls
        controls_layout = QHBoxLayout()
        self.pause_button = QPushButton("Pause Swarm")
        self.retry_button = QPushButton("Retry Failed")
        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(self.retry_button)
        main_layout.addLayout(controls_layout)

        # Timer for periodic refresh
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)  # refresh every 2 seconds

    def refresh(self):
        self.update_tasks()
        self.update_agents()
        self.update_stats()
        self.update_lore()

    def update_tasks(self):
        tasks = self.nexus.get_all_tasks()
        # TODO: Populate QTableView models for pending and completed tasks
        pass

    def update_agents(self):
        # TODO: Query agent statuses and update agents_label
        pass

    def update_stats(self):
        stats = self.nexus.stats()
        self.stats_label.setText(f"Task Stats: {stats}")

    def update_lore(self):
        # TODO: Append new lore entries to lore_stream
        pass 