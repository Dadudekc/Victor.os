import json
import os
import sys
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QMainWindow  # Using QMainWindow for status bar
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # Adjust if script location changes
ALERT_FILE_PATH = (
    PROJECT_ROOT / "runtime" / "supervisor_alerts" / "critical_alerts.jsonl"
)
REFRESH_INTERVAL_MS = 5000  # Refresh every 5 seconds


class AlertViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Supervisor Critical Alert Queue")
        self.setGeometry(100, 100, 1000, 600)  # Adjusted size

        # --- Central Widget and Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Header ---
        header_layout = QHBoxLayout()
        title_label = QLabel("Critical Alerts")
        title_font = QFont("Calibri", 14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.load_alerts)
        header_layout.addWidget(refresh_button)
        main_layout.addLayout(header_layout)

        # --- Table Widget (Alert List) ---
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            [
                "Timestamp",
                "Agent",
                "Blocking Task",
                "Status",
                "Summary",
                "Details Ref",
                "Alert ID",
            ]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # Read-only
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)

        # Configure column widths and header appearance
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # Stretch Summary column
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(5, 150)
        self.table.setColumnWidth(6, 180)
        header.setStyleSheet(
            "QHeaderView::section { background-color: lightgray; padding: 4px; border: 1px solid gray; font-weight: bold; }"
        )

        main_layout.addWidget(self.table)

        # --- Status Bar ---
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # --- Initial Load & Auto-Refresh ---
        self.load_alerts()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_alerts)
        self.timer.start(REFRESH_INTERVAL_MS)

    def load_alerts(self):
        """Loads alerts from the JSONL file and populates the table."""
        self.table.setRowCount(0)  # Clear existing items
        alerts = []

        if ALERT_FILE_PATH.exists():
            try:
                with open(ALERT_FILE_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            alert_data = json.loads(line.strip())
                            alerts.append(alert_data)
                        except json.JSONDecodeError:
                            print(
                                f"Warning: Skipping invalid JSON line: {line.strip()}"
                            )
                self.statusBar.showMessage(
                    f"Loaded {len(alerts)} alerts. Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    5000,
                )  # Show for 5 secs
            except Exception as e:
                self.statusBar.showMessage(f"Error reading alerts file: {e}")
                print(f"Error reading alerts file: {e}")
                return
        else:
            self.statusBar.showMessage("Alert file not found.")
            return

        # Populate table
        self.table.setRowCount(len(alerts))
        for row, alert in enumerate(alerts):
            # Extract data safely
            alert_id = alert.get("alert_id", "N/A")
            agent = alert.get("source_agent_id", "N/A")
            task_id = alert.get("blocking_task_id", "N/A")
            status = alert.get("status", "N/A")
            summary = alert.get("blocker_summary", "N/A")
            details = alert.get("details_reference", "N/A")

            # Timestamp requires BaseEvent info or adding to payload - using dummy
            timestamp_str = "[Timestamp N/A]"

            # Create items (ensure they are strings for the table)
            items = [
                QTableWidgetItem(str(timestamp_str)),
                QTableWidgetItem(str(agent)),
                QTableWidgetItem(str(task_id)),
                QTableWidgetItem(str(status)),
                QTableWidgetItem(str(summary)),
                QTableWidgetItem(str(details)),
                QTableWidgetItem(str(alert_id)),
            ]

            # Set items in the row
            for col, item in enumerate(items):
                self.table.setItem(row, col, item)

        # Optionally resize rows to content if needed, though fixed height is often better
        # self.table.resizeRowsToContents()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AlertViewerWindow()
    window.show()
    sys.exit(app.exec_())
