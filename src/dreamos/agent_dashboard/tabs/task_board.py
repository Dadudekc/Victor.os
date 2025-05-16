from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget
import json
from pathlib import Path

class TaskBoardTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        task_file = Path("task_backlog.json")
        if not task_file.exists():
            layout.addWidget(QLabel("task_backlog.json not found"))
            return

        try:
            with open(task_file, "r") as f:
                tasks = json.load(f)
        except Exception as e:
            layout.addWidget(QLabel(f"Error reading task_backlog.json: {e}"))
            return

        task_list = QListWidget()
        for task in tasks:
            task_id = task.get("id", "UNKNOWN")
            title = task.get("title", "Untitled Task")
            owner = task.get("owner", "Unclaimed")
            has_verify = "✅" if "how_to_verify" in task else "⚠️ Missing verification"

            item_str = f"{task_id} | {title} | Owner: {owner} | {has_verify}"
            task_list.addItem(item_str)

        layout.addWidget(QLabel("Backlog Tasks:"))
        layout.addWidget(task_list)
